import os
import sys
import json
from github import Github
from github.GithubException import GithubException

# Add the project root to Python path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.github_config import get_github_client, get_target_repo

# Initialize GitHub client and get repository
g = get_github_client()
repo = get_target_repo(g)

print(f"Fetching PRs from {repo.full_name}...")
all_prs = []

try:
    for pr in repo.get_pulls(state="all", sort="created", direction="desc"):
        print(f"Fetching details for PR #{pr.number}: {pr.title}")

        # Basic PR details
        pr_data = {
            'id': pr.id,
            'number': pr.number,
            'title': pr.title,
            'body': pr.body,
            'state': pr.state, # open, closed
            'merged': pr.merged,
            'draft': pr.draft,
            'created_at': pr.created_at.isoformat() if pr.created_at else None,
            'updated_at': pr.updated_at.isoformat() if pr.updated_at else None,
            'closed_at': pr.closed_at.isoformat() if pr.closed_at else None,
            'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
            'user': pr.user.login,
            'assignees': [a.login for a in pr.assignees],
            'labels': [l.name for l in pr.labels],
            'source_branch': pr.head.ref if pr.head else None,
            'target_branch': pr.base.ref if pr.base else None,
            'commits_count': pr.commits,
            'additions': pr.additions,
            'deletions': pr.deletions,
            'changed_files': pr.changed_files
        }

        # Commits in the PR
        commits_data = []
        try:
            for commit in pr.get_commits():
                commits_data.append({
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author_name': commit.commit.author.name,
                    'author_email': commit.commit.author.email,
                    'author_date': commit.commit.author.date.isoformat() if commit.commit.author.date else None,
                    'committer_name': commit.commit.committer.name,
                    'committer_email': commit.commit.committer.email,
                    'committer_date': commit.commit.committer.date.isoformat() if commit.commit.committer.date else None,
                    'parents': [p.sha for p in commit.parents],
                })
        except Exception as e:
            print(f"  Error fetching commits for PR #{pr.number}: {e}")
        pr_data['commits_data'] = commits_data

        # File Changes (Diffs)
        files_data = []
        try:
            for file_commit in pr.get_files():
                files_data.append({
                    'sha': file_commit.sha,
                    'filename': file_commit.filename,
                    'status': file_commit.status, # added, removed, modified, renamed, copied, changed, unchanged
                    'additions': file_commit.additions,
                    'deletions': file_commit.deletions,
                    'changes': file_commit.changes,
                    'blob_url': file_commit.blob_url,
                    'raw_url': file_commit.raw_url,
                    'contents_url': file_commit.contents_url,
                    'patch': file_commit.patch # The diff text
                })
        except Exception as e:
            print(f"  Error fetching file changes for PR #{pr.number}: {e}")
        pr_data['files_changed_data'] = files_data

        # Review Comments
        review_comments_data = []
        try:
            for review_comment in pr.get_review_comments():
                review_comments_data.append({
                    'id': review_comment.id,
                    'user': review_comment.user.login,
                    'body': review_comment.body,
                    'created_at': review_comment.created_at.isoformat() if review_comment.created_at else None,
                    'updated_at': review_comment.updated_at.isoformat() if review_comment.updated_at else None,
                    'path': review_comment.path,
                    'position': review_comment.position, # Line number in the diff
                    'original_position': review_comment.original_position,
                    'commit_id': review_comment.commit_id,
                    'diff_hunk': review_comment.diff_hunk
                })
        except Exception as e:
            print(f"  Error fetching review comments for PR #{pr.number}: {e}")
        pr_data['review_comments_data'] = review_comments_data
        
        all_prs.append(pr_data)
        print(f"  Fetched details for PR #{pr.number} ({len(commits_data)} commits, {len(files_data)} files, {len(review_comments_data)} review comments)")

except Exception as e:
    print(f"Error fetching PRs: {e}")
    print(f"Fetched {len(all_prs)} PRs before encountering an error.")

print(f"Finished fetching. Total PRs fetched: {len(all_prs)}")

output_dir = os.path.join("..", "repo-contents")
output_filename = "prs_with_details.json"
output_path = os.path.join(output_dir, output_filename)

print(f"Saving fetched PRs to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_prs, f, ensure_ascii=False, indent=4)

    print(f"Successfully saved {len(all_prs)} PRs to {output_path}")

except Exception as e:
    print(f"Error saving PRs to {output_path}: {e}")

