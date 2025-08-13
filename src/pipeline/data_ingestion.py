from fastapi import FastAPI, File, UploadFile
import os, tempfile
from PyPDF2 import PdfReader
import docx2txt

app = FastAPI()

@app.post("/ingest")
async def ingest_resume(file: UploadFile = File(...)):
    file_type = file.filename.split('.')[-1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
        tmp_file.write(await file.read())
        temp_path = tmp_file.name

    extracted_text = ""
    if file_type == "pdf":
        pdf_reader = PdfReader(temp_path)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
    elif file_type == "docx":
        extracted_text = docx2txt.process(temp_path)

    os.makedirs("ingested_resumes", exist_ok=True)
    raw_path = os.path.join("ingested_resumes", file.filename)
    os.rename(temp_path, raw_path)

    text_path = raw_path.rsplit(".", 1)[0] + ".txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(extracted_text.strip())

    return {"status": "success", "file_saved": raw_path, "text_saved": text_path}
