import os
import json
from github import Github, GithubException
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

print(f"Fetching commit history from {repo_owner}/{repo_name}...")
all_commits_data = []

try:
    commits = repo.get_commits()
    if commits.totalCount == 0:
        print("No commits found in this repository.")
    else:
        for commit in commits:
            print(f"Fetching details for commit: {commit.sha[:7]} - {commit.commit.message.splitlines()[0]}")
            
            # Get files changed in the commit
            files_changed = []
            try:
                for file in commit.files:
                    files_changed.append({
                        'filename': file.filename,
                        'status': file.status,
                        'additions': file.additions,
                        'deletions': file.deletions,
                        'changes': file.changes,
                        'patch': file.patch
                    })
            except Exception as e_files:
                print(f"  Error fetching files for commit {commit.sha}: {e_files}")

            commit_data = {
                'sha': commit.sha,
                'author_name': commit.commit.author.name,
                'author_email': commit.commit.author.email,
                'author_date': commit.commit.author.date.isoformat() if commit.commit.author.date else None,
                'committer_name': commit.commit.committer.name,
                'committer_email': commit.commit.committer.email,
                'committer_date': commit.commit.committer.date.isoformat() if commit.commit.committer.date else None,
                'message': commit.commit.message,
                'parents': [p.sha for p in commit.parents],
                'files_changed': files_changed
            }
            all_commits_data.append(commit_data)

except GithubException as e:
    print(f"GitHub API Error fetching commits: {e.status} {e.data.get('message','')}")
except Exception as e:
    print(f"An unexpected error occurred while fetching commits: {e}")

print(f"Finished fetching. Total commits processed: {len(all_commits_data)}")

output_dir = os.path.join("..", "repo-contents")
output_filename = "repo_commits.json"
output_path = os.path.join(output_dir, output_filename)

print(f"Saving fetched commits to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_commits_data, f, ensure_ascii=False, indent=4)
    
    if all_commits_data:
        print(f"Successfully saved {len(all_commits_data)} commits to {output_path}")
    elif not os.path.exists(output_path):
        print(f"No commits data to save. {output_path} was not created.")
    else:
        print(f"No commits data to save, but an empty file {output_path} might have been created.")

except Exception as e:
    print(f"Error saving commits to {output_path}: {e}") 