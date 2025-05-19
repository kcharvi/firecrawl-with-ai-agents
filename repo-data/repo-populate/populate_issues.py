import os
import json
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv
import time # Import time for potential rate limiting
import re # Import the regular expression module


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
    g = Github(GITHUB_PAT)
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
ISSUES_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "repo-contents","issues_with_comments.json")


# Define your TARGET repository where issues will be created
# Replace 'kcharvi' with your GitHub username if different if necessary
TARGET_REPO_OWNER = "kcharvi"
TARGET_REPO_NAME = "firecrawl-with-ai-agents"

# --- Helper function to remove GitHub user mentions (@username) ---
def remove_user_mentions(text):
    """Removes text starting with '@' followed by word characters."""
    if text is None:
        return ""
    # This regex looks for '@' followed by one or more word characters (\w+)
    # and replaces the match with an empty string.
    # It handles mentions at the beginning, middle, or end of text.
    return re.sub(r'@\w+', '', text)


# --- Access the Target Repository ---
try:
    target_repo = g.get_user(TARGET_REPO_OWNER).get_repo(TARGET_REPO_NAME)
    print(f"Accessing target repository: {TARGET_REPO_OWNER}/{TARGET_REPO_NAME}")
except Exception as e:
    print(f"Error accessing target repository {TARGET_REPO_OWNER}/{TARGET_REPO_NAME}: {e}")
    print("Please check the repository name and ensure your PAT has sufficient permissions (write access to issues, labels, comments).")
    exit(1)


# --- Get available labels in the target repository (needed for issue population) ---
# This is important because you can only add labels that already exist in the target repo
print(f"\nFetching available labels in {TARGET_REPO_OWNER}/{TARGET_REPO_NAME} for issue population...")
available_labels_in_target = []
try:
    for label in target_repo.get_labels():
        available_labels_in_target.append(label.name)
    print(f"Fetched {len(available_labels_in_target)} labels from target repo.")
except Exception as e:
    print(f"Error fetching labels from target repo for issue population: {e}")
    print("Labels from the source repo that do not exist in the target repo will be skipped during issue creation.")


# --- Create Issues in the Target Repository ---
print(f"\n--- Creating issues in {TARGET_REPO_OWNER}/{TARGET_REPO_NAME} ---")
print(f"Loading issues data from {ISSUES_JSON_PATH}...")

scraped_issues = []
if not os.path.exists(ISSUES_JSON_PATH):
    print(f"Error: Issues JSON file not found at {ISSUES_JSON_PATH}")
    print("Please run the fetching script first to create this file.")
    # Continue, but no issues will be created
else:
    try:
        with open(ISSUES_JSON_PATH, 'r', encoding='utf-8') as f:
            scraped_issues = json.load(f)
        print(f"Successfully loaded {len(scraped_issues)} issues from JSON.")
    except Exception as e:
        print(f"Error loading issues data from JSON: {e}. No issues will be created.")


if scraped_issues:
    issue_created_count = 0
    issue_skipped_count = 0
    issue_error_count = 0
    comments_added_count = 0
    labels_added_to_issues_count = 0

    # Optional: Limit the number of issues to create for testing
    # scraped_issues_subset = scraped_issues[:10] # Create only the first 10 issues
    # print(f"Processing a subset of {len(scraped_issues_subset)} issues.")
    # issues_to_process = scraped_issues_subset

    issues_to_process = scraped_issues # Process all loaded issues

    for issue_data in issues_to_process:
        # Skip if it was originally a Pull Request (optional, focus on issues first)
        if issue_data.get('is_pull_request', False):
             # print(f"Skipping original PR #{issue_data.get('number')} '{issue_data.get('title')}'") # Uncomment for verbose output
             issue_skipped_count += 1
             continue

        # --- Sanitize Title and Body ---
        original_title = issue_data.get('title', 'No Title Provided')
        original_body = issue_data.get('body', 'No body provided.')

        sanitized_title = remove_user_mentions(original_title)
        sanitized_body = remove_user_mentions(original_body)


        original_issue_number = issue_data.get('number', 'N/A')
        original_author = issue_data.get('user', 'Unknown User')
        original_created_at = issue_data.get('created_at', 'Unknown Date')


        # Add context to the body to indicate it's a migrated issue and include original author/date
        migration_context = f"\n\n---\n*Originally from mendableai/firecrawl #{original_issue_number} by @{original_author} on {original_created_at}*\n"
        full_body = f"{sanitized_body}{migration_context}" # Concatenate sanitized body with context


        print(f"Attempting to create issue original #{original_issue_number}: '{sanitized_title}'") # Use sanitized title in print


        try:
            # Create the issue. The author will be the authenticated user (kcharvi).
            new_issue = target_repo.create_issue(
                title=sanitized_title, # Use sanitized title
                body=full_body, # Use body with sanitized original content
                # Assignees could be added here if they exist as collaborators in the target repo
                # assignees=[assignee_login for assignee_login in issue_data.get('assignees', []) if assignee_login in [u.login for u in target_repo.get_collaborators()]] # Example
            )

            print(f" --> Successfully created issue #{new_issue.number}")
            issue_created_count += 1

            # --- Add Labels to the new issue ---
            labels_to_add = [
                label_name for label_name in issue_data.get('labels', [])
                if label_name in available_labels_in_target # Only add labels that exist in the target repo
            ]
            if labels_to_add:
                try:
                    new_issue.add_to_labels(*labels_to_add)
                    # print(f"    Added labels: {', '.join(labels_to_add)}") # Uncomment for verbose output
                    labels_added_to_issues_count += len(labels_to_add)
                except Exception as label_e:
                    print(f"    Error adding labels {labels_to_add} to issue #{new_issue.number}: {label_e}")


            # --- Add comments to the new issue ---
            # Note: Adding comments requires making separate API calls for each comment *after* the issue is created.
            # This can significantly increase the number of API calls and hit rate limits.
            comments_to_add = issue_data.get('comments_data', [])
            if comments_to_add:
                # print(f"    Adding {len(comments_to_add)} comments...") # Uncomment for verbose output
                for comment in comments_to_add:
                    try:
                        # --- Sanitize Comment Body ---
                        sanitized_comment_body = remove_user_mentions(comment.get('body', ''))

                        # GitHub API has rate limits. Add a small delay between comment creation if needed.
                        # time.sleep(0.1) # Small delay might be needed here
                        comment_body_with_context = f"**{comment.get('user')} commented on {comment.get('created_at')} (Original)**:\n\n{sanitized_comment_body}" # Use sanitized body
                        new_issue.create_comment(comment_body_with_context)
                        comments_added_count += 1
                        # print(f"        Added comment {comment.get('id')}") # Uncomment for verbose output
                    except Exception as comment_e:
                        print(f"    Error adding comment (original ID {comment.get('id')}) to issue #{new_issue.number}: {comment_e}")

        # --- Specific Exception Handling for Issue Creation ---
        except GithubException as e:
            if e.status == 403:
                print(f" --> Permission denied (403): Your GitHub token doesn't have sufficient permissions to create issues.")
                print("Please ensure your token has the 'repo' scope enabled or write access to issues.")
                print("You can create a new token with proper permissions at: https://github.com/settings/tokens")
                issue_error_count += 1
                # Depending on your needs, you might break here if permissions are fundamentally wrong
                # break
            elif e.status == 422:
                 # This can happen for various reasons, e.g., invalid characters in title/body,
                 # trying to set a field that's not allowed during creation, etc.
                 print(f" --> Validation failed (422) for issue '{sanitized_title}': {e}") # Use sanitized title in error message
                 issue_error_count += 1
            elif e.status == 410: # Added handling for the 410 Gone error (Issues disabled)
                 print(f" --> Issues are disabled (410) for the target repository. Please enable them in settings: {e}")
                 issue_error_count += 1
                 # You might want to break here if issues are disabled, as you can't create any.
                 # break
            else:
                print(f" --> Unexpected GithubException (Status: {e.status}) creating issue '{sanitized_title}': {e}") # Use sanitized title in error message
                issue_error_count += 1
        except Exception as e:
            # Catch any other non-GithubException errors
            print(f" --> An unexpected error occurred creating issue '{sanitized_title}': {e}") # Use sanitized title in error message
            issue_error_count += 1


        # --- Rate Limit Handling ---
        # Check GitHub API rate limit status
        rate_limit = g.get_rate_limit()
        # Adjust the threshold (e.g., 50 or 100) based on how many requests adding comments/labels takes
        if rate_limit.core.remaining < 50:
            reset_time = rate_limit.core.reset.timestamp()
            sleep_duration = reset_time - time.time() + 10 # Sleep until reset + a buffer
            if sleep_duration > 0:
                print(f"Rate limit almost reached ({rate_limit.core.remaining} remaining). Sleeping for {sleep_duration:.2f} seconds until {rate_limit.core.reset}...")
                time.sleep(sleep_duration)

        # time.sleep(0.2) # Optional: Add a small delay between processing each issue


    print("\nIssue Creation Summary:")
    print(f"Total issues processed from JSON: {len(issues_to_process)}")
    print(f"Original PRs skipped: {issue_skipped_count}")
    print(f"Issues successfully created in target repo: {issue_created_count}")
    print(f"Comments added to issues: {comments_added_count}")
    print(f"Labels added to issues: {labels_added_to_issues_count}")
    print(f"Errors during issue creation: {issue_error_count}")
    print("--------------------------------------------------")

else:
    print("No issues loaded from JSON. Skipping issue creation.")

