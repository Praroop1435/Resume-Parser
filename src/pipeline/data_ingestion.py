# src/pipeline/data_ingestion.py
from fastapi import FastAPI, File, UploadFile
import os, json, tempfile, re
from PyPDF2 import PdfReader
import docx2txt
from src.pipeline.preprocess_resume_text import preprocess_resume_text

JD_CSV = "JD_preprocessing.csv"

app = FastAPI()

def clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9.,;:!?()/%$@ ]", "", text)
    return text.lower().strip()

def extract_resume_text(file: UploadFile):
    """Extract text from PDF or DOCX"""
    file_type = file.filename.split('.')[-1].lower()
    if file_type not in ["pdf", "docx"]:
        raise ValueError("Only PDF and DOCX files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
        tmp_file.write(file.file.read())
        temp_path = tmp_file.name

    extracted_text = ""
    if file_type == "pdf":
        pdf_reader = PdfReader(temp_path)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
    else:
        extracted_text = docx2txt.process(temp_path)

    return extracted_text, temp_path

@app.post("/ingest")
async def ingest_resume(file: UploadFile = File(...)):
    extracted_text, temp_path = extract_resume_text(file)

    os.makedirs("ingested_resumes/raw", exist_ok=True)
    os.makedirs("ingested_resumes/cleaned", exist_ok=True)

    raw_path = os.path.join("ingested_resumes/raw", file.filename)
    os.rename(temp_path, raw_path)

    text_path = raw_path.rsplit(".", 1)[0] + ".txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(extracted_text.strip())

    cleaned_text = clean_text(extracted_text)
    cleaned_path = os.path.join("ingested_resumes/cleaned", file.filename.rsplit(".", 1)[0] + "_cleaned.txt")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    return {
        "status": "success",
        "raw_file": raw_path,
        "raw_text_file": text_path,
        "cleaned_text_file": cleaned_path,
        "text_preview": cleaned_text[:300]
    }

@app.post("/preprocess")
async def preprocess_endpoint(file: UploadFile = File(...)):
    extracted_text, _ = extract_resume_text(file)
    result = preprocess_resume_text(extracted_text, JD_CSV)

    os.makedirs("processed_resumes", exist_ok=True)
    json_path = os.path.join("processed_resumes", file.filename.rsplit(".", 1)[0] + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "json_path": json_path,
        "preview": {
            "name": result["contact"]["name"],
            "email": result["contact"]["email"],
            "skills_top": result["skills"]["all"][:10]
        }
    }
