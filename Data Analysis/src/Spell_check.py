# pip install bertopic sentence-transformers umap-learn hdbscan
import argparse
import json
from bertopic import BERTopic

def main():
    parser = argparse.ArgumentParser(description='Run BERTopic on JSON data.')
    parser.add_argument('--input', type=str, required=True, help='Input JSON file path')
    parser.add_argument('--out', type=str, help='Output file path')
    parser.add_argument('--map-csv', type=str, help='Path to spellmap CSV')
    parser.add_argument('--changes-csv', type=str, help='Path to spell changes CSV')
    parser.add_argument('--top-k', type=int, default=200, help='Top K')
    parser.add_argument('--min-misspell', type=int, default=15, help='Min misspell')
    parser.add_argument('--min-ratio', type=int, default=8, help='Min ratio')
    parser.add_argument('--min-sim', type=float, default=0.85, help='Min similarity')
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    docs = []
    for cat, posts in data.items():
        if isinstance(posts, list):
            for p in posts:
                if p.get("title"): docs.append(p["title"])
                for c in p.get("comments", []):
                    if c.get("body"): docs.append(c["body"])

    topic_model = BERTopic(n_gram_range=(1,2), min_topic_size=150, calculate_probabilities=False, verbose=True, seed_topic_list=None)
    topics, _ = topic_model.fit_transform(docs)

    print(topic_model.get_topic_info().head(15))     # topic sizes
    print(topic_model.get_topic(0))                  # top terms for topic id 0

if __name__ == '__main__':
    main()