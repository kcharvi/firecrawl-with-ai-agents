import os
import sys
import json
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

# Add the project root to Python path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.github_config import get_github_client, get_target_repo

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

print(f"Fetching discussions from {repo_owner}/{repo_name}...")
all_discussions_data = []

try:
    discussions = repo.get_discussions()
    if discussions.totalCount == 0:
        print("No discussions found in this repository.")
    else:
        for discussion in discussions:
            print(f"Fetching discussion: {discussion.title} (ID: {discussion.id})")
            discussion_comments = []
            try:
                for comment in discussion.get_comments():
                    discussion_comments.append({
                        'id': comment.id,
                        'body': comment.body,
                        'user': comment.user.login if comment.user else 'N/A',
                        'created_at': comment.created_at.isoformat() if comment.created_at else None,
                        'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
                    })
            except Exception as e_comment:
                print(f"  Error fetching comments for discussion ID {discussion.id}: {e_comment}")

            discussion_data = {
                'id': discussion.id,
                'number': discussion.number,
                'title': discussion.title,
                'body': discussion.body,
                'user': discussion.user.login if discussion.user else 'N/A',
                'created_at': discussion.created_at.isoformat() if discussion.created_at else None,
                'updated_at': discussion.updated_at.isoformat() if discussion.updated_at else None,
                'comments_count': len(discussion_comments), # Or discussion.comments_count if available
                'comments_data': discussion_comments
            }
            all_discussions_data.append(discussion_data)
            print(f"  Fetched discussion ID {discussion.id} with {len(discussion_comments)} comments.")

except GithubException as e:
    if e.status == 404 and "Repository discussions are not enabled" in str(e.data.get("message", "")):
        print(f"Discussions are not enabled for the repository {repo_owner}/{repo_name}.")
    elif e.status == 403 and "Must have push access to view repository discussions" in str(e.data.get("message", "")):
        print(f"Your PAT does not have sufficient permissions to view discussions for {repo_owner}/{repo_name}. Ensure it has 'repo' scope or discussions read access.")
    else:
        print(f"Error fetching discussions: {e} (Status: {e.status}, Data: {e.data})")
except AttributeError as e:
    if "'Repository' object has no attribute 'get_discussions'" in str(e):
        print("Error: The version of PyGithub you are using does not support fetching discussions directly via get_discussions(). You might need to update PyGithub or use the GraphQL API.")
    else:
        print(f"An unexpected AttributeError occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print(f"Finished fetching. Total discussions fetched: {len(all_discussions_data)}")

output_dir = os.path.join("..", "repo-contents")
output_filename = "repo_discussions_with_comments.json"
output_path = os.path.join(output_dir, output_filename)

print(f"Saving fetched discussions to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_discussions_data, f, ensure_ascii=False, indent=4)
    if all_discussions_data: # Only print success if some data was actually processed or attempted to save
        print(f"Successfully saved {len(all_discussions_data)} discussions to {output_path}")
    elif not os.path.exists(output_path): # If no discussions and file wasn't created
        print(f"No discussions data to save. {output_path} was not created.")
    else: # If no discussions but an empty file was created
        print(f"No discussions data to save, but an empty file {output_path} might have been created.")


except Exception as e:
    print(f"Error saving discussions to {output_path}: {e}") 