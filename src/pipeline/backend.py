# src/pipeline/backend.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import os, json, tempfile, re
from pathlib import Path
from PyPDF2 import PdfReader
import docx2txt

from src.pipeline.preprocess_resume_text import preprocess_resume_text
# We use calculate_similarity from your matcher.py
from src.pipeline.matcher import calculate_similarity

# ------------------ Paths / Config ------------------ #
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root (adjust if needed)
JD_FOLDER = BASE_DIR / "JDs"                    # folder containing .txt JDs
JD_CSV = str(BASE_DIR / "job_keywords.csv")    # CSV used by preprocess_resume_text

app = FastAPI()

# ------------------ Helpers ------------------ #
MULTI_WS = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\+\.#]*")

def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MULTI_WS.sub(" ", text)
    # keep common symbols; lowercasing helps similarity be consistent
    return text.lower().strip()

def extract_resume_text(file: UploadFile):
    """Extract text from PDF or DOCX and return (text, tmp_path)."""
    file_type = file.filename.split(".")[-1].lower()
    if file_type not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
        tmp_file.write(file.file.read())
        temp_path = tmp_file.name

    try:
        if file_type == "pdf":
            extracted_text = ""
            reader = PdfReader(temp_path)
            for page in reader.pages:
                pg = page.extract_text() or ""
                extracted_text += pg + "\n"
        else:
            extracted_text = docx2txt.process(temp_path) or ""
    finally:
        # we only keep the file in /ingest; for others we can safely remove
        pass

    return extracted_text, temp_path

def jd_terms_set(jd_text: str):
    """Very simple JD keywords set (for matched/missing preview)."""
    toks = [t.lower() for t in TOKEN_RE.findall(jd_text)]
    # keep medium+ length tokens; you can refine with stopwords if you want
    return {t for t in toks if len(t) > 2}

# ------------------ Endpoints ------------------ #
@app.post("/ingest")
async def ingest_resume(file: UploadFile = File(...)):
    """Save raw and cleaned versions of the uploaded resume."""
    extracted_text, temp_path = extract_resume_text(file)

    raw_dir = BASE_DIR / "ingested_resumes" / "raw"
    cleaned_dir = BASE_DIR / "ingested_resumes" / "cleaned"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / file.filename
    # move the temp file into raw/
    os.replace(temp_path, raw_path)

    # also store raw text
    text_path = raw_path.with_suffix(".txt")
    text_path.write_text(extracted_text.strip(), encoding="utf-8")

    # cleaned (normalized) text
    cleaned_text = clean_text(extracted_text)
    cleaned_path = cleaned_dir / f"{raw_path.stem}_cleaned.txt"
    cleaned_path.write_text(cleaned_text, encoding="utf-8")

    return {
        "status": "success",
        "raw_file": str(raw_path),
        "raw_text_file": str(text_path),
        "cleaned_text_file": str(cleaned_path),
        "text_preview": cleaned_text[:300],
    }

@app.post("/preprocess")
async def preprocess_endpoint(file: UploadFile = File(...)):
    """Return structured JSON from resume (contact, sections, skills, etc.)."""
    extracted_text, _ = extract_resume_text(file)
    result = preprocess_resume_text(extracted_text, JD_CSV)

    out_dir = BASE_DIR / "processed_resumes"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{Path(file.filename).stem}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "json_path": str(json_path),
        "preview": {
            "name": result["contact"]["name"],
            "email": result["contact"]["email"],
            "skills_top": result["skills"]["all"][:10],
        },
    }

@app.post("/score")
async def score_resume(file: UploadFile = File(...), jd_file: str = Form(...)):
    """
    Compute a similarity score between the uploaded resume and a selected JD (.txt).
    Returns score only (use /analyze_resume for full preview + score).
    """
    # validate JD
    jd_path = JD_FOLDER / jd_file
    if not jd_path.exists():
        raise HTTPException(status_code=404, detail=f"JD file not found: {jd_file}")

    resume_text, _ = extract_resume_text(file)
    jd_text = jd_path.read_text(encoding="utf-8", errors="ignore")

    score = calculate_similarity(clean_text(resume_text), clean_text(jd_text))
    return {"status": "scored", "score": score}

@app.post("/analyze_resume")
async def analyze_resume(file: UploadFile = File(...), jd_file: str = Form(...)):
    """
    Full pipeline: Extract → Preprocess (for preview) → Similarity score vs. selected JD.
    Also returns a lightweight matched/missing keyword view.
    """
    # Validate JD
    jd_path = JD_FOLDER / jd_file
    if not jd_path.exists():
        raise HTTPException(status_code=404, detail=f"JD file not found: {jd_file}")

    # Step 1: extract & preprocess
    extracted_text, _ = extract_resume_text(file)
    resume_data = preprocess_resume_text(extracted_text, JD_CSV)  # uses CSV lexicon

    # Step 2: similarity score (embeddings)
    jd_text = jd_path.read_text(encoding="utf-8", errors="ignore")
    score = calculate_similarity(clean_text(extracted_text), clean_text(jd_text))

    # Step 3: quick keyword overlap preview
    resume_skills = set(resume_data.get("skills", {}).get("all", []))
    jd_terms = jd_terms_set(jd_text)
    matched = sorted(resume_skills & jd_terms)
    missing = sorted([t for t in jd_terms if t not in resume_skills])[:50]

    return {
        "status": "ok",
        "preview": {
            "name": resume_data["contact"]["name"],
            "email": resume_data["contact"]["email"],
            "skills_top": resume_data["skills"]["all"][:10],
        },
        "score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
    }
