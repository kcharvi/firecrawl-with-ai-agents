import os
import json
from github import Github
from github.GithubException import GithubException # Import specific exceptions
from dotenv import load_dotenv
import time # Import time for potential rate limiting

# Load environment variables from .env file
load_dotenv()

# Initialize GitHub API
GITHUB_PAT = os.getenv("GITHUB_PAT")
if not GITHUB_PAT:
    print("Error: GITHUB_PAT environment variable not set.")
    print("Please ensure your .env file in the project root has GITHUB_PAT=YOUR_TOKEN")
    exit(1)

# Connect to GitHub
try:
    g = Github(GITHUB_PAT)
    # Verify authentication
    user = g.get_user()
    print(f"Authenticated as: {user.login}")
except Exception as e:
    print(f"Error authenticating with GitHub. Check your PAT: {e}")
    exit(1)

# --- Configuration ---
# Define the path to your scraped labels JSON file
# Adjust the path based on your exact directory structure if needed
LABELS_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "repo-contents", "repo_labels_list.json")

# Define your TARGET repository where labels will be created
# Replace 'KCHARVI' with your GitHub username if different
TARGET_REPO_OWNER = "kcharvi"
TARGET_REPO_NAME = "firecrawl-with-ai-agents"

# --- Load Scraped Labels Data ---
print(f"Loading scraped labels data from {LABELS_JSON_PATH}...")
if not os.path.exists(LABELS_JSON_PATH):
    print(f"Error: Labels JSON file not found at {LABELS_JSON_PATH}")
    print("Please ensure the file exists and the path is correct.")
    exit(1)

try:
    with open(LABELS_JSON_PATH, 'r', encoding='utf-8') as f:
        scraped_labels = json.load(f)
    print(f"Successfully loaded {len(scraped_labels)} labels from JSON.")
except Exception as e:
    print(f"Error loading labels data from JSON: {e}")
    exit(1)

# --- Access the Target Repository ---
try:
    target_repo = g.get_user(TARGET_REPO_OWNER).get_repo(TARGET_REPO_NAME)
    print(f"Accessing target repository: {TARGET_REPO_OWNER}/{TARGET_REPO_NAME}")
except Exception as e:
    print(f"Error accessing target repository {TARGET_REPO_OWNER}/{TARGET_REPO_NAME}: {e}")
    print("Please check the repository name and ensure your PAT has sufficient permissions (write access to labels).")
    exit(1)

# --- Create Labels in the Target Repository ---
print(f"\nCreating labels in {TARGET_REPO_OWNER}/{TARGET_REPO_NAME}...")

created_count = 0
skipped_count = 0
error_count = 0

for label_data in scraped_labels:
    label_name = label_data.get('name')
    label_color = label_data.get('color') # Hex color without '#'
    label_description = label_data.get('description')

    if not label_name:
        print("Skipping label data with no name.")
        skipped_count += 1
        continue

    print(f"Attempting to create label: '{label_name}' (Color: {label_color})")

    try:
        # Check if label already exists before attempting creation (optional, but can reduce errors)
        # PyGithub's create_label often handles "already exists" gracefully, but explicit check is clearer
        try:
            target_repo.get_label(label_name)
            print(f" --> Label '{label_name}' already exists. Skipping creation.")
            skipped_count += 1
            continue # Skip to the next label if it exists
        except GithubException as e:
             if e.status != 404: # If error is not 'Not Found', something else went wrong
                 print(f" --> Error checking existence of label '{label_name}': {e}")
                 # Decide whether to continue or break on unexpected errors
                 error_count += 1
                 continue # Or break

        # If we reached here, the label does not exist (or get_label failed with 404)
        new_label = target_repo.create_label(
            name=label_name,
            color=label_color,
            description=label_description if label_description else "" # Ensure description is not None
        )

        print(f" --> Successfully created label: '{new_label.name}'")
        created_count += 1

    except GithubException as e:
        if e.status == 403:
            print(f" --> Permission denied: Your GitHub token doesn't have sufficient permissions to create labels.")
            print("Please ensure your token has the 'repo' scope enabled.")
            print("You can create a new token with proper permissions at: https://github.com/settings/tokens")
            error_count += 1
            break  # Exit the loop since we can't proceed without proper permissions
        elif e.status == 422:
            print(f" --> Error creating label '{label_name}'. It might already exist or have invalid data: {e}")
            skipped_count += 1
        else:
            print(f" --> Unexpected error creating label '{label_name}': {e}")
            error_count += 1

    # --- Rate Limit Handling ---
    # Check GitHub API rate limit status
    rate_limit = g.get_rate_limit()
    if rate_limit.core.remaining < 10: # If fewer than 10 requests remain
        reset_time = rate_limit.core.reset.timestamp()
        sleep_duration = reset_time - time.time() + 5 # Sleep until reset + a buffer
        if sleep_duration > 0:
            print(f"Rate limit almost reached ({rate_limit.core.remaining} remaining). Sleeping for {sleep_duration:.2f} seconds until {rate_limit.core.reset}...")
            time.sleep(sleep_duration)

    # time.sleep(0.1) # Optional: Add a small delay between creating labels


print("\n--- Summary ---")
print(f"Total labels processed from JSON: {len(scraped_labels)}")
print(f"Labels successfully created in target repo: {created_count}")
print(f"Labels skipped (already exist or no name): {skipped_count}")
print(f"Errors during creation: {error_count}")
print("---------------")
