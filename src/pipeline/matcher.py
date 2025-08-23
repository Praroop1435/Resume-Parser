# src/pipeline/matcher.py
from sentence_transformers import SentenceTransformer, util

# Load model once at startup (fast inference)
_model = SentenceTransformer("all-MiniLM-L6-v2")

def calculate_similarity(resume_text: str, jd_text: str) -> float:
    """
    Calculates semantic similarity between resume and JD.
    Returns score as percentage (0-100).
    """
    if not resume_text.strip() or not jd_text.strip():
        return 0.0

    resume_embedding = _model.encode(resume_text, convert_to_tensor=True)
    jd_embedding = _model.encode(jd_text, convert_to_tensor=True)

    similarity_score = util.cos_sim(resume_embedding, jd_embedding).item()
    return round(similarity_score * 100, 2)
