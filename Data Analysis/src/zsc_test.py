import json
import random
from transformers import pipeline

INPUT_FILE = "/Users/benjaminrussell/Desktop/Fashion/FashionDB/Data Analysis/data/reddit_fashion_data_unique.json"
CANDIDATE_LABELS = [
    "rules",
    "advice",
    "dos and don'ts"
]
NUM_SAMPLES = 10

try:
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading data: {e}")
    exit()

all_comments = [
    c['body']
    for post in data
    for c in post.get('comments', [])
    if c.get('body') and c['body'] not in ['[deleted]', 'removed']
]

if not all_comments:
    print("No comments found.")
    exit()

sample_comments = random.sample(all_comments, min(NUM_SAMPLES, len(all_comments)))

classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")

print(f"Classifying {len(sample_comments)} comments with labels: {CANDIDATE_LABELS}\n")

for comment in sample_comments:
    result = classifier(comment[:512], CANDIDATE_LABELS)
    print(f"Comment: {comment[:80]}...")
    print(f"-> Label: {result['labels'][0]} (Score: {result['scores'][0]:.4f})\n")
