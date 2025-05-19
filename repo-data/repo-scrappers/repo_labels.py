import os
import json
from github import Github
from dotenv import load_dotenv

load_dotenv()

# Initialize GitHub API
GITHUB_PAT = os.getenv("GITHUB_GITHUB_PAT")
if not GITHUB_PAT:
    print("Error: GITHUB_GITHUB_PAT environment variable not set.")
    exit(1)

try:
    g = Github(GITHUB_PAT)
    user = g.get_user()
    print(f"Authenticated as: {user.login}")
except Exception as e:
    print(f"Error authenticating with GitHub: {e}")
    exit(1)

repo_owner = "mendableai"
repo_name = "firecrawl"

try:
    repo = g.get_user(repo_owner).get_repo(repo_name)
    print(f"Accessing repository: {repo_owner}/{repo_name}")
except Exception as e:
    print(f"Error accessing repository {repo_owner}/{repo_name}: {e}")
    print("Please check if the repository exists and your PAT has sufficient permissions.")
    exit(1)

print(f"Fetching labels from {repo_owner}/{repo_name}...")
all_labels_data = []

try:
    for label in repo.get_labels():
        label_data = {
            'name': label.name,
            'color': label.color,
            'description': label.description
        }
        all_labels_data.append(label_data)
        print(f"Fetched label: {label.name}")

except Exception as e:
    print(f"Error fetching labels: {e}")

print(f"Finished fetching. Total labels fetched: {len(all_labels_data)}")

output_dir = os.path.join("..", "repo-contents")
output_filename = "repo_labels_list.json"
output_path = os.path.join(output_dir, output_filename)

print(f"Saving fetched labels to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_labels_data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved {len(all_labels_data)} labels to {output_path}")

except Exception as e:
    print(f"Error saving labels to {output_path}: {e}") 