# repo-data\repo-scrappers\repo_labels.py

import os
import sys
import json
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

# Add the project root to Python path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.github_config import get_github_client, get_target_repo

# Initialize GitHub client and get repository
g = get_github_client()
repo = get_target_repo(g, repo_owner="mendableai", repo_name="firecrawl")

print(f"Fetching labels from mendableai/firecrawl...")
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