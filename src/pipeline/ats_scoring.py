# src/pipeline/ats_scoring.py
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from src.pipeline.preprocess_resume_text import preprocess_resume_text

# ----------------- Config / Lexicons -----------------
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\+\.#]*")

TECH_HINTS = {
    "python","pandas","numpy","matplotlib","seaborn","sklearn","scikit-learn",
    "tensorflow","pytorch","keras","sql","mysql","postgresql","git","github",
    "docker","kubernetes","aws","gcp","azure","linux","spark","nlp","vision",
    "opencv","xgboost","lightgbm","regression","classification","clustering",
    "fastapi","streamlit","etl","airflow","hadoop","tableau","powerbi",
    "mlops","helm","terraform","flask","django","kafka","elasticsearch",
    "redis","rest","graphql","bigquery","sagemaker","ray","huggingface",
    "transformers","llm","generative","langchain","rag","faiss","vector"
}
SOFT_HINTS = {
    "communication","leadership","teamwork","collaboration","analytical",
    "problem","critical","management","organization","presentation",
    "stakeholder","mentoring","ownership","initiative","adaptability"
}

GENERIC_NOISE = {
    "job","description","requirements","related","field","strong","excellent","knowledge",
    "ability","experience","team","teams","manager","engineer","developer","bachelor","master",
    "ph.d","ms","bs","ba","bsc","msc","degree","preferred","record","track","successful",
    "thinker","understanding","communication","detail","attention","industry","standards",
    "laws","guidelines","systems","practices","projects","project","stakeholders","technology",
    "technologies","fields","responsibilities","role","position","apply","location","about"
}

PHRASES = {
    "machine learning","deep learning","computer vision","natural language processing",
    "data analysis","data engineering","data visualization","time series","recommendation systems",
    "feature engineering","model deployment"
}

DATE_RE = re.compile(
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|"
    r"january|february|march|april|june|july|august|september|october|november|december)"
    r"\s+\d{2,4}|\d{1,2}/\d{4}|\d{4}", re.I
)
NUMBER_RE = re.compile(r"\b\d+(\.\d+)?%?\b")

# ----------------- Helpers -----------------
def _clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text.lower())]

def _jd_terms_set(jd_text: str) -> Set[str]:
    """Extract a deduped set of important JD terms (tokens + key phrases)."""
    clean = _clean(jd_text)
    toks = [t for t in clean.split() if t not in ENGLISH_STOP_WORDS and t not in GENERIC_NOISE and len(t) > 2]
    terms = set(toks)
    # add multi-words phrases if present
    for ph in PHRASES:
        if ph in jd_text.lower():
            terms.add(ph)
    return terms

def _is_fresher(prep: Dict) -> bool:
    """Heuristic: no real 'experience' section or very short, or 'fresher' keyword."""
    sections = prep.get("sections", {})
    exp_txt = sections.get("experience", "")
    if not exp_txt or len(exp_txt) < 150:
        return True
    # If it says internship but no FT roles, still consider fresher-ish
    if "intern" in exp_txt.lower() and "engineer" not in exp_txt.lower() and "developer" not in exp_txt.lower():
        return True
    return False

def _readability_score(rb: Dict) -> float:
    """
    Return 0..100 based on simple heuristics:
    - target avg sentence length ~ 10–22 words
    - bullet ratio >= 0.15
    - total words 250–900
    """
    words = rb.get("words", 0)
    avg_len = rb.get("avg_sentence_len", 0.0)
    bullet_ratio = rb.get("bullet_ratio", 0.0)

    # sentence length
    if avg_len <= 0:
        s1 = 0.0
    elif 10 <= avg_len <= 22:
        s1 = 100.0
    else:
        # linear falloff
        diff = min(abs(avg_len - 16), 16)
        s1 = max(0.0, 100.0 - diff * 6.0)

    # bullets
    s2 = min(100.0, bullet_ratio / 0.15 * 100.0) if bullet_ratio > 0 else 0.0

    # words
    if 250 <= words <= 900:
        s3 = 100.0
    else:
        # 0–250 -> 0..100; >900 -> 100 down
        if words < 250:
            s3 = (words / 250.0) * 100.0
        else:
            # gentle penalty above 900
            over = min(words - 900, 600)
            s3 = max(40.0, 100.0 - (over / 6.0))

    return round(0.45 * s1 + 0.25 * s2 + 0.30 * s3, 1)

def _section_presence_score(sections: Dict, key: str) -> float:
    """0 or 100 if the section exists with non-trivial text."""
    txt = sections.get(key, "")
    return 100.0 if txt and len(txt.strip()) > 30 else 0.0

def _project_score(sections: Dict, resume_tokens: Set[str]) -> float:
    """Score projects based on presence, count-ish, numbers, skills used."""
    txt = sections.get("projects", "")
    if not txt:
        return 0.0
    lines = [ln for ln in txt.split("\n") if ln.strip()]
    approx_projects = sum(1 for ln in lines if "project" in ln.lower() or ln.strip().startswith(("-", "•")))
    approx_projects = max(approx_projects, 1 if txt else 0)

    numbers = 1 if NUMBER_RE.search(txt) else 0
    skills_used = len({t for t in resume_tokens if t in TECH_HINTS and t in txt.lower()})
    skills_used_score = min(1.0, skills_used / 3.0)

    base = min(1.0, approx_projects / 2.0) * 60.0    # up to 60
    base += (20.0 if numbers else 0.0)               # +20 for metrics/accuracy
    base += skills_used_score * 20.0                  # + up to 20 for skills in context
    return round(min(100.0, base), 1)

def _experience_score(sections: Dict) -> float:
    txt = sections.get("experience", "")
    if not txt:
        return 0.0
    bullets_like = sum(1 for ln in txt.split("\n") if ln.strip().startswith(("-", "•")))
    dates_present = 1 if DATE_RE.search(txt) else 0
    numbers = 1 if NUMBER_RE.search(txt) else 0
    base = 50.0 if bullets_like >= 3 else bullets_like / 3.0 * 50.0
    base += 25.0 if dates_present else 0.0
    base += 25.0 if numbers else 0.0
    return round(min(100.0, base), 1)

def _contact_score(contact: Dict) -> float:
    score = 0.0
    if contact.get("email"): score += 50.0
    if contact.get("phone"): score += 30.0
    links = contact.get("links", {}) or {}
    if links.get("linkedin"): score += 20.0
    return round(min(100.0, score), 1)

def _split_skills_for_jd(jd_terms: Set[str]) -> Tuple[Set[str], Set[str]]:
    jd_tech = {t for t in jd_terms if t in TECH_HINTS or t in PHRASES}
    jd_soft = {t for t in jd_terms if t in SOFT_HINTS}
    return jd_tech, jd_soft

def _skills_scores(resume_skills: Dict[str, List[str]], jd_terms: Set[str]) -> Tuple[float, float, List[str], List[str]]:
    jd_tech, jd_soft = _split_skills_for_jd(jd_terms)
    r_tech = set(resume_skills.get("technical", []))
    r_soft = set(resume_skills.get("non_technical", []))

    # coverage ratios
    tech_match = sorted(jd_tech & r_tech)
    soft_match = sorted(jd_soft & r_soft)
    tech_miss = sorted(jd_tech - r_tech)
    soft_miss = sorted(jd_soft - r_soft)

    tech_cov = (len(tech_match) / max(1, len(jd_tech))) * 100.0 if jd_tech else 100.0
    soft_cov = (len(soft_match) / max(1, len(jd_soft))) * 100.0 if jd_soft else 100.0

    return round(tech_cov, 1), round(soft_cov, 1), tech_match + soft_match, tech_miss + soft_miss

# ----------------- Public API -----------------
def compute_ats(raw_resume_text: str, jd_text: str, jd_csv_path: str, fresher: bool = None) -> Dict:
    """
    Returns a dict with:
      label (fresher/non_fresher), total_score, components{...}, matched_skills, missing_skills
    fresher: optional override. If None -> auto-detect.
    """
    # Preprocess resume once (reuses your existing pipeline)
    prep = preprocess_resume_text(raw_resume_text, jd_csv_path)
    sections = prep.get("sections", {})
    tokens = set(_tokenize(raw_resume_text))
    jd_terms = _jd_terms_set(jd_text)

    # Skills coverage
    tech_cov, soft_cov, matched_skills, missing_skills = _skills_scores(prep.get("skills", {}), jd_terms)

    # Components (0..100 each)
    readability = _readability_score(prep.get("readability", {}))
    education = _section_presence_score(sections, "education")
    projects = _project_score(sections, tokens)
    experience = _experience_score(sections)
    contact = _contact_score(prep.get("contact", {}))
    summary = _section_presence_score(sections, "summary")
    certifications = _section_presence_score(sections, "certifications")
    achievements = _section_presence_score(sections, "achievements")

    # FIX: internship detection across all sections
    internship = 100.0 if any("intern" in v.lower() for v in sections.values()) else 0.0

    # Fresher / Non-Fresher decision
    if fresher is None:
        fresher = _is_fresher(prep)

    if fresher:
        # Fresher Weights
        total = (
            0.06 * readability +
            0.45 * tech_cov +
            0.05 * soft_cov +
            0.10 * education +
            0.00 * experience +
            0.15 * projects +
            0.04 * contact +
            0.03 * summary +
            0.03 * certifications +
            0.04 * achievements +
            0.05 * internship
        )
        label = "fresher"
    else:
        # Non-Fresher Weights
        total = (
            0.07 * readability +
            0.45 * tech_cov +
            0.05 * soft_cov +
            0.10 * education +
            0.10 * experience +
            0.15 * projects +
            0.05 * contact +
            0.03 * summary
        )
        label = "non_fresher"

    # Clamp and round
    total_score = round(min(100.0, max(0.0, total)), 1)

    components = {
        "readability": readability,
        "skills_technical": tech_cov,
        "skills_non_technical": soft_cov,
        "education": education,
        "experience": experience,
        "projects": projects,
        "contact": contact,
        "summary": summary,
        "certifications": certifications,
        "achievements": achievements,
        "internship": internship,
    }

    return {
        "label": label,
        "total_score": total_score,
        "components": components,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "contact": prep.get("contact", {}),
        "skills_top": prep.get("skills", {}).get("all", [])[:10],
    }
