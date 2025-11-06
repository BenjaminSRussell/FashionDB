import json
import os

json_input = os.path.join("data", "reddit_fashion_data.json")
json_output = os.path.join("data", "reddit_fashion_deletions.json")

with open(json_input, 'r') as file:
    data = json.load(file)

removed = sum(
    len([c for c in post['comments'] if c['body'] == '[deleted]'])
    for subreddit_posts in data.values()
    for post in subreddit_posts
)

for posts in data.values():
    for post in posts:
        post['comments'] = [c for c in post['comments'] if c['body'] != '[deleted]']

with open(json_output, 'w') as file:
    json.dump(data, file, indent=4)

print(f"Removed {removed} deleted comments")
