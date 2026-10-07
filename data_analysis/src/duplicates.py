from utils import load_json, save_json, DATA_DIR

INPUT_FILE = DATA_DIR / "reddit_fashion_deletions.json"
OUTPUT_FILE = DATA_DIR / "reddit_fashion_data_unique.json"

data = load_json(INPUT_FILE)
if not data:
    print(f"Error: Could not load {INPUT_FILE}")
    exit(1)

print("Finding and removing duplicate posts...")
unique_data = {}
total_post_count = 0
duplicate_post_count = 0
duplicate_comment_count = 0

for category, posts in data.items():
    if not isinstance(posts, list):
        unique_data[category] = posts
        continue

    unique_posts = []
    seen_titles = set()
    total_post_count += len(posts)

    for post in posts:
        title = post.get('title')
        if title not in seen_titles:
            seen_titles.add(title)
            
            # Remove duplicate comments within the post
            if 'comments' in post and isinstance(post['comments'], list):
                unique_comments = []
                seen_comment_bodies = set()
                for comment in post['comments']:
                    body = comment.get('body')
                    if body not in seen_comment_bodies:
                        unique_comments.append(comment)
                        seen_comment_bodies.add(body)
                    else:
                        duplicate_comment_count += 1
                post['comments'] = unique_comments
            
            unique_posts.append(post)
        else:
            duplicate_post_count += 1
    
    unique_data[category] = unique_posts

print(f"Total posts processed: {total_post_count}")
print(f"Duplicate posts removed: {duplicate_post_count}")
print(f"Duplicate comments removed: {duplicate_comment_count}")
print(f"Posts remaining: {total_post_count - duplicate_post_count}")

print(f"Writing unique data to {OUTPUT_FILE}...")
save_json(unique_data, OUTPUT_FILE)
print(f"Successfully created {OUTPUT_FILE}")
