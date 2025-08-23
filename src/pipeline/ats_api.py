# src/pipeline/ats_api.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import tempfile
from PyPDF2 import PdfReader
import docx2txt

from src.pipeline.ats_scoring import compute_ats

router = APIRouter()

JD_FOLDER = Path("JDs")
JD_CSV = "job_keywords.csv"  # your CSV lexicon used by preprocess_resume_text()

def _extract_resume_text(file: UploadFile) -> str:
    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in {"pdf", "docx", "txt"}:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, or TXT files are supported.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(file.file.read())
        tmp_path = Path(tmp.name)

    if ext == "pdf":
        text = ""
        reader = PdfReader(str(tmp_path))
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    elif ext == "docx":
        text = docx2txt.process(str(tmp_path)) or ""
    else:
        text = tmp_path.read_text(encoding="utf-8", errors="ignore")

    return text

@router.post("/analyze_resume")
async def analyze_resume(file: UploadFile = File(...), jd_file: str = Form(...)):
    # Validate & load JD text
    jd_path = JD_FOLDER / jd_file
    if not jd_path.exists():
        raise HTTPException(status_code=404, detail=f"JD file not found: {jd_file}")
    jd_text = jd_path.read_text(encoding="utf-8", errors="ignore")

    # Extract resume text
    resume_text = _extract_resume_text(file)

    # Compute ATS
    result = compute_ats(resume_text, jd_text, JD_CSV)

    return {
        "status": "ok",
        **result  # label, total_score, components, matched/missing, contact, skills_top
    }
