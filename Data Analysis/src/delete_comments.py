from utils import load_json, save_json, DATA_DIR

json_input = DATA_DIR / "reddit_fashion_data.json"
json_output = DATA_DIR / "reddit_fashion_deletions.json"

data = load_json(json_input)
if not data:
    print(f"Error: Could not load {json_input}")
    exit(1)

removed = sum(
    len([c for c in post['comments'] if c['body'] == '[deleted]'])
    for subreddit_posts in data.values()
    for post in subreddit_posts
)

for posts in data.values():
    for post in posts:
        post['comments'] = [c for c in post['comments'] if c['body'] != '[deleted]']

save_json(data, json_output)
print(f"Removed {removed} deleted comments")
