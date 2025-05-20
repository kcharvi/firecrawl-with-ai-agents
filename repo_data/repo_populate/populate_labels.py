import os
import sys
import json
from github import Github
from github.GithubException import GithubException
import time # Import time for potential rate limiting

# Add the project root to Python path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.github_config import get_github_client, get_target_repo

# --- Configuration ---
# Define the path to your scraped labels JSON file
LABELS_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "repo-contents", "repo_labels_list.json")

# Initialize GitHub client and get repository
g = get_github_client()
target_repo = get_target_repo(g)

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

# --- Create Labels in the Target Repository ---
print(f"\nCreating labels in {target_repo.full_name}...")

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
        # Check if label already exists before attempting creation
        try:
            target_repo.get_label(label_name)
            print(f" --> Label '{label_name}' already exists. Skipping creation.")
            skipped_count += 1
            continue # Skip to the next label if it exists
        except GithubException as e:
             if e.status != 404: # If error is not 'Not Found', something else went wrong
                 print(f" --> Error checking existence of label '{label_name}': {e}")
                 error_count += 1
                 continue

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
    rate_limit = g.get_rate_limit()
    if rate_limit.core.remaining < 10: # If fewer than 10 requests remain
        reset_time = rate_limit.core.reset.timestamp()
        sleep_duration = reset_time - time.time() + 5 # Sleep until reset + a buffer
        if sleep_duration > 0:
            print(f"Rate limit almost reached ({rate_limit.core.remaining} remaining). Sleeping for {sleep_duration:.2f} seconds until {rate_limit.core.reset}...")
            time.sleep(sleep_duration)

print("\n--- Summary ---")
print(f"Total labels processed from JSON: {len(scraped_labels)}")
print(f"Labels successfully created in target repo: {created_count}")
print(f"Labels skipped (already exist or no name): {skipped_count}")
print(f"Errors during creation: {error_count}")
print("---------------")
