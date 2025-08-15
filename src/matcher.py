from sentence_transformers import SentenceTransformer, util
import os

# 1. Load pre-trained model
# You can use 'all-MiniLM-L6-v2' (fast + good accuracy) or 'all-mpnet-base-v2' (slower + better accuracy)
model = SentenceTransformer('all-MiniLM-L6-v2')

def read_file(file_path):
    """Reads text from a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def calculate_similarity(resume_text, jd_text):
    """Calculates similarity between resume and JD"""
    # Create embeddings
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    jd_embedding = model.encode(jd_text, convert_to_tensor=True)
    
    # Cosine similarity
    similarity_score = util.cos_sim(resume_embedding, jd_embedding).item()
    return round(similarity_score * 100, 2)  # percentage

if __name__ == "__main__":
    # Example file paths (replace with your actual files)
    resume_path = "ingested_resumes/cleaned/PraroopResume_cleaned.txt"
    jd_path = "JDs/machine-learning-engineer-job-description.txt"

    # Read the files
    resume_text = read_file(resume_path)
    jd_text = read_file(jd_path)

    # Calculate score
    score = calculate_similarity(resume_text, jd_text)
    print(f"Resume matches JD with a score of: {score}%")
