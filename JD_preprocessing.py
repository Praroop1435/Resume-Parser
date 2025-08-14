import os
import re
import spacy
from collections import Counter
import pandas as pd

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

def extract_keywords(text, min_freq=1):
    # Clean text
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s\+\#\.\-]', ' ', text)  # keep words, +, #, ., -
    
    # Process with spaCy
    doc = nlp(text)
    
    # Extract candidate keywords (nouns, proper nouns, adjectives)
    candidates = [
        token.text for token in doc
        if token.pos_ in ["NOUN", "PROPN", "ADJ"] and len(token.text) > 1
    ]
    
    # Count frequency
    freq = Counter(candidates)
    
    # Filter stopwords and low-frequency words
    keywords = [
        word for word, count in freq.items()
        if count >= min_freq and not nlp.vocab[word].is_stop
    ]
    
    return sorted(keywords)

# Path to folder containing job description TXT files
folder_path = "JDs"

# Store results
all_keywords_data = []

# Loop through each TXT file
for file_name in os.listdir(folder_path):
    if file_name.endswith(".txt"):
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        keywords = extract_keywords(text, min_freq=1)
        all_keywords_data.append({
            "file_name": file_name,
            "keywords": keywords
        })

# Save to CSV
df = pd.DataFrame(all_keywords_data)
df.to_csv("job_keywords.csv", index=False)

print("✅ Keywords extracted and saved to job_keywords.csv")
