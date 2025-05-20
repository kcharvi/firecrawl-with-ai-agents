import os
import json
import sys
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv
import time # Import time for potential rate limiting
import re # Import the regular expression module

# Add the project root to Python path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.github_config import get_github_client, get_target_repo

# Load environment variables from .env file
# Assumes .env is in the project root (firecrawl-main)
load_dotenv()

# Initialize GitHub API
GITHUB_PAT = os.getenv("GITHUB_PAT")
if not GITHUB_PAT:
    print("Error: GITHUB_PAT environment variable not set.")
    print("Please ensure your .env file in the project root has GITHUB_PAT=YOUR_TOKEN")
    exit(1)

# Connect to GitHub
try:
    g = get_github_client()
    # Verify authentication
    user = g.get_user()
    print(f"Authenticated as: {user.login}")
except Exception as e:
    print(f"Error authenticating with GitHub. Check your PAT: {e}")
    exit(1)

# --- Configuration ---
# Define the path to your scraped issues JSON file
# Adjust the path based on your exact directory structure if needed
# Assuming populate_issues.py is in repo-data/repo-populate
ISSUES_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "repo-contents", "issues_with_comments.json")

# Initialize GitHub client and get repository
target_repo = get_target_repo(g)

# --- Load Scraped Issues Data ---
print(f"Loading scraped issues data from {ISSUES_JSON_PATH}...")
if not os.path.exists(ISSUES_JSON_PATH):
    print(f"Error: Issues JSON file not found at {ISSUES_JSON_PATH}")
    print("Please ensure the file exists and the path is correct.")
    exit(1)

try:
    with open(ISSUES_JSON_PATH, 'r', encoding='utf-8') as f:
        scraped_issues = json.load(f)
    print(f"Successfully loaded {len(scraped_issues)} issues from JSON.")
except Exception as e:
    print(f"Error loading issues data from JSON: {e}")
    exit(1)

# --- Create Issues in the Target Repository ---
print(f"\nCreating issues in {target_repo.full_name}...")

created_count = 0
skipped_count = 0
error_count = 0

for issue_data in scraped_issues:
    title = issue_data.get('title')
    body = issue_data.get('body')
    labels = issue_data.get('labels', [])
    assignees = issue_data.get('assignees', [])

    if not title:
        print("Skipping issue data with no title.")
        skipped_count += 1
        continue

    print(f"Attempting to create issue: '{title}'")

    try:
        # Create the issue
        new_issue = target_repo.create_issue(
            title=title,
            body=body if body else "",
            labels=labels,
            assignees=assignees
        )

        print(f" --> Successfully created issue: '{new_issue.title}'")
        created_count += 1

    except GithubException as e:
        if e.status == 403:
            print(f" --> Permission denied: Your GitHub token doesn't have sufficient permissions to create issues.")
            print("Please ensure your token has the 'repo' scope enabled.")
            print("You can create a new token with proper permissions at: https://github.com/settings/tokens")
            error_count += 1
            break
        else:
            print(f" --> Error creating issue '{title}': {e}")
            error_count += 1

    # --- Rate Limit Handling ---
    rate_limit = g.get_rate_limit()
    if rate_limit.core.remaining < 10:
        reset_time = rate_limit.core.reset.timestamp()
        sleep_duration = reset_time - time.time() + 5
        if sleep_duration > 0:
            print(f"Rate limit almost reached ({rate_limit.core.remaining} remaining). Sleeping for {sleep_duration:.2f} seconds until {rate_limit.core.reset}...")
            time.sleep(sleep_duration)

print("\n--- Summary ---")
print(f"Total issues processed from JSON: {len(scraped_issues)}")
print(f"Issues successfully created in target repo: {created_count}")
print(f"Issues skipped (no title): {skipped_count}")
print(f"Errors during creation: {error_count}")
print("---------------")

