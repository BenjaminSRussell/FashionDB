
import json
import os
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- Setup ---
# Download the VADER lexicon if not already present
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    print("Downloading VADER lexicon (one-time setup)...")
    nltk.download('vader_lexicon')

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
INPUT_FILE = os.path.join(DATA_DIR, "reddit_fashion_data_unique.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "reddit_fashion_semantic.json")

# --- Read Data ---
print(f"Reading unique data from {INPUT_FILE}...")
try:
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: Input file not found at {INPUT_FILE}")
    print("Please run the duplicates.py script first to generate it.")
    exit()

# --- Process Data ---
print("Performing sentiment analysis on post titles...")
sid = SentimentIntensityAnalyzer()
semantic_data = {"positive": {}, "negative": {}, "neutral": {}}

for category, posts in data.items():
    if not isinstance(posts, list):
        continue

    # Initialize categories in each sentiment bucket
    for sentiment in semantic_data:
        semantic_data[sentiment][category] = []

    for post in posts:
        title = post.get('title', '')
        score = sid.polarity_scores(title)['compound']

        if score >= 0.05:
            sentiment_category = "positive"
        elif score <= -0.05:
            sentiment_category = "negative"
        else:
            sentiment_category = "neutral"
        
        semantic_data[sentiment_category][category].append(post)

# --- Write Output ---
print(f"Writing semantically separated data to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w') as f:
    json.dump(semantic_data, f, indent=2)

print(f"Successfully created {OUTPUT_FILE}")
