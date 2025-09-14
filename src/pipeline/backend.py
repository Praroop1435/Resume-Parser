from fastapi import FastAPI, File, UploadFile, Form, HTTPException, APIRouter
import os, json, tempfile, re
from pathlib import Path
from PyPDF2 import PdfReader
import docx2txt

from src.pipeline.preprocess_resume_text import preprocess_resume_text
from src.pipeline.matcher import calculate_similarity
from src.pipeline.ats_scoring import compute_ats

# ------------------ Paths / Config ------------------ #
BASE_DIR = Path(__file__).resolve().parent.parent.parent
JD_FOLDER = BASE_DIR / "JD"
JD_CSV = str(BASE_DIR / "job_keywords.csv")

app = FastAPI()
ats_router = APIRouter()   # ✅ define once here

# ------------------ Helpers ------------------ #
MULTI_WS = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-\+\.#]*")

def compute_weighted_score(resume_data, jd_text, semantic_score, fresher=True):
    """
    Weighted ATS scoring system:
    fresher=True  → Experience = 0, Internship & Projects weighted more
    fresher=False → Normal distribution
    """

    weights_fresher = {
        "readability": 6,
        "skills": 50,
        "education": 10,
        "experience": 0,
        "projects": 15,
        "contact": 4,
        "summary": 3,
        "certifications": 3,
        "achievements": 4,
        "internship": 5,
    }

    weights_non_fresher = {
        "readability": 7,
        "skills": 50,
        "education": 10,
        "experience": 10,
        "projects": 15,
        "contact": 5,
        "summary": 3,
    }

    weights = weights_fresher if fresher else weights_non_fresher
    breakdown = {}

    # --- Simple heuristics ---
    breakdown["readability"] = min(100, len(resume_data["raw_text"]) / 2000 * 100)
    breakdown["skills"] = min(100, len(resume_data["skills"]["all"]) / 15 * 100)
    breakdown["education"] = 100 if resume_data.get("education") else 0
    breakdown["experience"] = 100 if resume_data.get("experience") else 0
    breakdown["projects"] = 100 if resume_data.get("projects") else 0
    breakdown["contact"] = 100 if resume_data["contact"].get("email") != "N/A" else 0
    breakdown["summary"] = 100 if resume_data.get("summary") else 0
    breakdown["certifications"] = 100 if resume_data.get("certifications") else 0
    breakdown["achievements"] = 100 if resume_data.get("achievements") else 0
    breakdown["internship"] = 100 if resume_data.get("internship") else 0

    # --- Weighted sum ---
    final_score = 0
    total_weight = sum(weights.values())
    for k, w in weights.items():
        final_score += breakdown.get(k, 0) * (w / total_weight)

    # Blend with semantic similarity (60:40 ratio)
    final_score = round((0.6 * semantic_score) + (0.4 * final_score), 2)

    return final_score, breakdown


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return MULTI_WS.sub(" ", text).lower().strip()

def extract_resume_text(file: UploadFile):
    file_type = file.filename.split(".")[-1].lower()
    if file_type not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
        tmp_file.write(file.file.read())
        temp_path = tmp_file.name
    if file_type == "pdf":
        text = "".join([(pg.extract_text() or "") + "\n" for pg in PdfReader(temp_path).pages])
    else:
        text = docx2txt.process(temp_path) or ""
    return text, temp_path

def jd_terms_set(jd_text: str):
    toks = [t.lower() for t in TOKEN_RE.findall(jd_text)]
    return {t for t in toks if len(t) > 2}

def extract_contact_info(text: str):
    email = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    phone = re.search(r"\+?\d[\d\s\-\(\)]{8,}\d", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    name = lines[0] if lines else "N/A"
    return {"name": name, "email": email.group(0) if email else "N/A", "phone": phone.group(0) if phone else "N/A"}

# ------------------ Endpoints ------------------ #
@app.post("/ingest")
async def ingest_resume(file: UploadFile = File(...)):
    text, temp_path = extract_resume_text(file)
    return {"status": "success", "text_preview": clean_text(text)[:300]}

@app.post("/preprocess")
async def preprocess_endpoint(file: UploadFile = File(...)):
    text, _ = extract_resume_text(file)
    result = preprocess_resume_text(text, JD_CSV)
    return {"status": "ok", "preview": {"name": result["contact"]["name"], "email": result["contact"]["email"], "skills_top": result["skills"]["all"][:10]}}

@app.post("/score")
async def score_resume(file: UploadFile = File(...), jd_file: str = Form(...)):
    jd_path = JD_FOLDER / jd_file
    if not jd_path.exists():
        raise HTTPException(status_code=404, detail=f"JD file not found: {jd_file}")
    resume_text, _ = extract_resume_text(file)
    jd_text = jd_path.read_text(encoding="utf-8", errors="ignore")
    score = calculate_similarity(clean_text(resume_text), clean_text(jd_text))
    return {"status": "scored", "score": score}

@ats_router.post("/analyze_resume")
async def analyze_resume(file: UploadFile = File(...), jd_file: str = Form(...), fresher: bool = Form(None)):
    jd_path = JD_FOLDER / jd_file
    if not jd_path.exists():
        raise HTTPException(status_code=404, detail=f"JD file not found: {jd_file}")

    resume_text, _ = extract_resume_text(file)
    jd_text = jd_path.read_text(encoding="utf-8", errors="ignore")

    contact = extract_contact_info(resume_text)

    # ATS scoring with fresher override
    ats_result = compute_ats(resume_text, jd_text, JD_CSV, fresher=fresher)

    return {
        "preview": {
            "name": contact["name"],
            "email": contact["email"],
            "skills_top": ats_result["skills_top"],
        },
        "semantic_score": calculate_similarity(resume_text, jd_text),
        "final_score": ats_result["total_score"],
        "breakdown": ats_result["components"],
        "matched_keywords": ats_result["matched_skills"],
        "missing_keywords": ats_result["missing_skills"],
    }

# ✅ register router
app.include_router(ats_router)

