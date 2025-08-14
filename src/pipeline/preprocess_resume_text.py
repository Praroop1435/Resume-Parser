import re, os, json, csv, ast
from collections import defaultdict
from typing import Dict, List, Tuple, Set
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# ---------- 1) Helpers: normalization ----------
MULTISPACE = re.compile(r"[ \t]+")
LINEJUNK = re.compile(r"^\s*(page\s*\d+|resume|curriculum vitae|cv)\s*$", re.I)

def normalize_text(text: str) -> str:
    # unify newlines, strip invisible, remove common header/footer junk
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for ln in text.split("\n"):
        ln = MULTISPACE.sub(" ", ln).strip()
        if not ln or LINEJUNK.match(ln):
            continue
        lines.append(ln)
    text = "\n".join(lines)
    # join broken lines when the previous line doesn’t end with punctuation and next starts lowercase
    fixed = []
    for i, ln in enumerate(text.split("\n")):
        if fixed and not fixed[-1].endswith((".", "!", "?", ":" )) and ln and ln[:1].islower():
            fixed[-1] += " " + ln
        else:
            fixed.append(ln)
    return "\n".join(fixed).strip()

# ---------- 2) Contact info ----------
RE_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+")
RE_PHONE = re.compile(r"(?:\+?91[-.\s]?)?(?:\d{10}|\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
RE_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/\S+", re.I)
RE_GITHUB = re.compile(r"(?:https?://)?(?:www\.)?github\.com/\S+", re.I)
RE_KAGGLE = re.compile(r"(?:https?://)?(?:www\.)?kaggle\.com/\S+", re.I)

def extract_contact(text: str) -> Dict:
    email = RE_EMAIL.search(text)
    phone = RE_PHONE.search(text)
    name = None
    # crude name heuristic: first non-empty line that contains 2–4 capitalized words and not an email/link
    for ln in text.split("\n")[:6]:
        if RE_EMAIL.search(ln) or "linkedin" in ln.lower() or "github" in ln.lower():
            continue
        tokens = [t for t in re.split(r"[\s,|•]+", ln) if t]
        caps = [t for t in tokens if t[:1].isupper()]
        if 2 <= len(caps) <= 4 and len(" ".join(tokens)) <= 60:
            name = " ".join(tokens)
            break
    links = {
        "linkedin": (RE_LINKEDIN.search(text) or [None]).group(0) if RE_LINKEDIN.search(text) else None,
        "github":   (RE_GITHUB.search(text) or [None]).group(0) if RE_GITHUB.search(text) else None,
        "kaggle":   (RE_KAGGLE.search(text) or [None]).group(0) if RE_KAGGLE.search(text) else None,
    }
    return {
        "name": name,
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
        "links": links
    }

# ---------- 3) Sectionizer ----------
SECTION_HEADS = {
    "summary": ["summary","profile","objective","about"],
    "skills": ["skills","technical skills","tech stack","competencies"],
    "experience": ["experience","work experience","professional experience","employment","internship","internships"],
    "education": ["education","academics","qualifications"],
    "projects": ["projects","project work"],
    "certifications": ["certifications","certificates","courses","licenses"],
    "achievements": ["achievements","awards","honors","accomplishments"],
}

def sectionize(text: str) -> Dict[str, str]:
    # make a regex that captures headings as their own lines
    pattern = r"^(?:%s)\s*$" % "|".join(
        [re.escape(h) for heads in SECTION_HEADS.values() for h in heads]
    )
    head_re = re.compile(pattern, re.I | re.M)

    # find headings
    indices = []
    for m in head_re.finditer(text):
        indices.append((m.start(), m.group(0).strip().lower()))
    indices.sort()
    # slice sections
    sections = defaultdict(str)
    if not indices:
        sections["other"] = text
        return sections
    for i, (pos, hdr) in enumerate(indices):
        end = indices[i+1][0] if i+1 < len(indices) else len(text)
        block = text[pos:end].split("\n", 1)
        body = block[1] if len(block) > 1 else ""
        # map canonical key
        key = None
        for k, aliases in SECTION_HEADS.items():
            if any(hdr.lower() == a.lower() for a in aliases):
                key = k; break
        sections[key] += body.strip() + "\n"
    return {k:v.strip() for k,v in sections.items() if v.strip()}

# ---------- 4) Bullets & Dates ----------
BULLET_RE = re.compile(r"^\s*(?:[-*•\u2022\u25CF]|\d+[.)])\s+(.*)$")
MONTHS = "(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)"
DATE_RE = re.compile(rf"({MONTHS}\s+\d{{2,4}}|\d{{1,2}}/\d{{4}}|\d{{4}})", re.I)

def collect_bullets_and_dates(section_text: str, section_name: str) -> List[Dict]:
    out = []
    for ln in section_text.split("\n"):
        m = BULLET_RE.match(ln)
        if m:
            txt = m.group(1).strip()
            dates = DATE_RE.findall(txt)
            if dates:
                # flatten tuples produced by regex with groups
                dates = [" ".join([d for d in tup if d and len(d) > 2]).strip() for tup in dates]
            out.append({"section": section_name, "text": txt, "dates": dates})
    return out

# ---------- 5) Tokenization & stopwords ----------
SAFE_STOP = set(ENGLISH_STOP_WORDS) | {"b.tech","btech","m.tech","msc","bsc","gpa","cgpa"}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\+\.#]*")

def tokenize(text: str) -> List[str]:
    toks = [t.lower() for t in TOKEN_RE.findall(text)]
    toks = [t for t in toks if t not in SAFE_STOP and len(t) > 1]
    return toks

# ---------- 6) JD lexicon loading & cleaning ----------
GENERIC_NOISE = {
    "job","description","requirements","related","field","strong","excellent","knowledge",
    "ability","experience","team","teams","manager","engineer","developer","bachelor","master",
    "ph.d","ms","bs","ba","bsc","msc","degree","requirements","preferred","record","track",
    "successful","thinker","understanding","communication","detail","attention","extensive",
    "industry","standards","laws","guidelines","systems","practices","projects","project",
    "stakeholders","teams","teamwork","technology","technologies","field","fields"
}

def load_jd_lexicon(csv_path: str) -> Set[str]:
    vocab = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                kw_list = ast.literal_eval(row["keywords"])
            except Exception:
                continue
            for kw in kw_list:
                w = kw.strip().lower()
                if w and w not in GENERIC_NOISE and w not in ENGLISH_STOP_WORDS and w.isalpha():
                    vocab.add(w)
    return vocab

# ---------- 7) Skill aliasing (normalize synonyms) ----------
ALIASES = {
    "scikit-learn": "sklearn",
    "scikit": "sklearn",
    "py-torch": "pytorch",
    "tf": "tensorflow",
    "ml": "machine learning",
    "dl": "deep learning",
    "postgres": "postgresql",
    "matplotlib": "matplotlib",
    "np": "numpy",
}

TECH_HINTS = {
    "python","pandas","numpy","matplotlib","seaborn","sklearn","scikit-learn","tensorflow",
    "pytorch","keras","sql","mysql","postgresql","git","github","docker","kubernetes",
    "aws","gcp","azure","linux","spark","nlp","vision","opencv","xgboost","lightgbm",
    "random","forest","regression","classification","clustering","fastapi","streamlit"
}
NONTECH_HINTS = {
    "communication","leadership","teamwork","analytical","problem","critical","management",
    "attention","organization","presentation","collaboration","stakeholder"
}

def normalize_term(t: str) -> str:
    t = t.lower()
    return ALIASES.get(t, t)

def extract_skills(tokens: List[str], jd_vocab: Set[str]) -> Dict[str, List[str]]:
    # keep only tokens present in JD vocab OR clear tech hints
    raw = set(normalize_term(t) for t in tokens)
    keep = {t for t in raw if (t in jd_vocab) or (t in TECH_HINTS) or (t in NONTECH_HINTS)}
    tech = sorted([t for t in keep if t in TECH_HINTS])
    nontech = sorted([t for t in keep if t in NONTECH_HINTS])
    # extra: keep compound phrases "machine learning", "deep learning"
    text_join = " " + " ".join(tokens) + " "
    for phrase in ["machine learning","deep learning","computer vision"]:
        if f" {phrase} " in text_join:
            keep.add(phrase)
            TECH_HINTS.add(phrase)
            tech = sorted(set(tech) | {phrase})
    all_skills = sorted(keep)
    return {"all": all_skills, "technical": tech, "non_technical": nontech}

# ---------- 8) Readability features ----------
def readability_features(text: str, bullets: List[Dict]) -> Dict[str, float]:
    sentences = re.split(r"[.!?;\n]+", text)
    sentences = [s for s in sentences if s.strip()]
    words = TOKEN_RE.findall(text)
    total_lines = len([ln for ln in text.split("\n") if ln.strip()])
    bullet_lines = len(bullets)
    return {
        "words": len(words),
        "sentences": len(sentences),
        "avg_sentence_len": (len(words) / max(1, len(sentences))),
        "bullet_ratio": (bullet_lines / max(1, total_lines))
    }

# ---------- 9) Main entry ----------
def preprocess_resume_text(raw_text: str, jd_csv_path: str) -> Dict:
    text = normalize_text(raw_text)
    contact = extract_contact(text)
    sections = sectionize(text)

    # bullets + dates across selected sections
    bullets = []
    for sec in ["experience","projects","internships"]:
        if sec in sections:
            bullets.extend(collect_bullets_and_dates(sections[sec], sec))

    # tokens
    tokens = tokenize(text)

    # skills from JD lexicon + hints
    jd_vocab = load_jd_lexicon(jd_csv_path)
    skills = extract_skills(tokens, jd_vocab)

    # readability
    rb = readability_features(text, bullets)

    out = {
        "contact": contact,
        "sections": sections,
        "bullets": bullets,
        "dates": [],   # you can add normalized YYYY-MM from bullets if needed
        "tokens": tokens,
        "skills": skills,
        "readability": rb
    }
    return out
