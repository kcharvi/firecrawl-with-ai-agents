import os
import json
from github import Github
from dotenv import load_dotenv

load_dotenv()

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


print(f"Fetching issues from {repo_owner}/{repo_name}...")
all_issues = []

try:
    for issue in repo.get_issues(state="all"):
        comments = []
        for comment in issue.get_comments():
            comments.append({
                "id": comment.id,
                "user": comment.user.login,
                "body": comment.body,
                "created_at": comment.created_at.isoformat(),
                "updated_at": comment.updated_at.isoformat(),
            })

        issue_data = {
            'id': issue.id,
            'number': issue.number,
            'title': issue.title,
            'body': issue.body,
            'state': issue.state,
            'created_at': issue.created_at.isoformat(),
            'updated_at': issue.updated_at.isoformat(),
            'closed_at': issue.closed_at.isoformat() if issue.closed_at else None,
            'user': issue.user.login,
            'assignees': [a.login for a in issue.assignees],
            'labels': [l.name for l in issue.labels],
            'comments_count': issue.comments,
            'comments_data': comments,
            'is_pull_request': hasattr(issue, 'pull_request') and issue.pull_request is not None
        }
        all_issues.append(issue_data)

        print(f"Fetched issue #{issue.number} ({len(comments)} comments)")

except Exception as e:
    print(f"Error fetching issues: {e}")
    print(f"Fetched {len(all_issues)} issues before encountering an error.")


print(f"Finished fetching. Total issues fetched: {len(all_issues)}")

output_dir = os.path.join("..", "repo-contents")
output_path = os.path.join(output_dir, "issues_with_comments.json")

print(f"Saving fetched issues to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_issues, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved {len(all_issues)} issues to {output_path}")

except Exception as e:
    print(f"Error saving issues to {output_path}: {e}")

