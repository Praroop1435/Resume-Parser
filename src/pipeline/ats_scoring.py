from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import textract
import re

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/calculate_ats")
async def calculate_ats(resume: UploadFile = File(...), jd: str = Form(...)):
    # Extract resume text
    resume_text = textract.process(resume.file).decode("utf-8", errors="ignore").lower()

    # Clean JD text
    jd_clean = re.sub(r"[^a-zA-Z0-9\s]", "", jd.lower())
    resume_clean = re.sub(r"[^a-zA-Z0-9\s]", "", resume_text)

    # Extract keywords from JD
    jd_keywords = set(jd_clean.split())

    # Count matches
    matches = [word for word in jd_keywords if word in resume_clean]
    score = int((len(matches) / len(jd_keywords)) * 100)

    missing_keywords = list(jd_keywords - set(matches))

    return {"score": score, "missing_keywords": missing_keywords}
