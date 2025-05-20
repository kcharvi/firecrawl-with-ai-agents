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
    g = get_github_client()
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

print(f"Fetching workflow runs from {repo_owner}/{repo_name}...")
all_runs_data = []

try:
    workflow_runs = repo.get_workflow_runs()
    if workflow_runs.totalCount == 0:
        print("No workflow runs found in this repository.")
    else:
        for run in workflow_runs:
            print(f"Fetching details for run ID: {run.id} (Workflow: {run.name}, SHA: {run.head_sha[:7]})")
            
            # Get workflow details (path and name)
            workflow_path = "N/A"
            workflow_actual_name = "N/A"
            try:
                workflow = repo.get_workflow(run.workflow_id)
                workflow_path = workflow.path
                workflow_actual_name = workflow.name
            except GithubException as ghe:
                print(f"  Warning: Could not fetch details for workflow ID {run.workflow_id}: {ghe.status} {ghe.data.get('message','')}")
            except Exception as e_wf:
                print(f"  Warning: An unexpected error occurred while fetching workflow ID {run.workflow_id}: {e_wf}")

            run_data = {
                'run_id': run.id,
                'run_number': run.run_number,
                'run_name': run.name, # This is the name of the workflow YML file, not the run's display title
                'run_display_title': run.display_title, # More descriptive title of the run
                'status': run.status,
                'conclusion': run.conclusion,
                'event': run.event,
                'branch': run.head_branch,
                'commit_sha': run.head_sha,
                'actor': run.actor.login if run.actor else 'N/A',
                'created_at': run.created_at.isoformat() if run.created_at else None,
                'updated_at': run.updated_at.isoformat() if run.updated_at else None,
                'run_started_at': run.run_started_at.isoformat() if run.run_started_at else None,
                'html_url': run.html_url,
                'workflow_id': run.workflow_id,
                'workflow_path': workflow_path,
                'workflow_name': workflow_actual_name,
                'jobs': []
            }

            # Fetch jobs for the run
            try:
                jobs = run.jobs()
                if jobs.totalCount == 0:
                    print(f"  No jobs found for run ID: {run.id}")
                else:
                    for job in jobs:
                        job_data = {
                            'job_id': job.id,
                            'job_name': job.name,
                            'status': job.status,
                            'conclusion': job.conclusion,
                            'started_at': job.started_at.isoformat() if job.started_at else None,
                            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                            'html_url': job.html_url, # Link to job logs
                            'steps_count': len(job.steps) if job.steps else 0 # Number of steps in the job
                        }
                        run_data['jobs'].append(job_data)
                    print(f"  Fetched {jobs.totalCount} jobs for run ID: {run.id}. Example job: {run_data['jobs'][0]['job_name'] if run_data['jobs'] else 'N/A'}")
            except Exception as e_job:
                print(f"  Error fetching jobs for run ID {run.id}: {e_job}")
            
            all_runs_data.append(run_data)

except GithubException as e:
    print(f"GitHub API Error fetching workflow runs: {e.status} {e.data.get('message','')}")
except Exception as e:
    print(f"An unexpected error occurred while fetching workflow runs: {e}")

print(f"Finished fetching. Total workflow runs processed: {len(all_runs_data)}")

output_dir = os.path.join("..", "repo-contents")
output_filename = "repo_actions_runs.json"
output_path = os.path.join(output_dir, output_filename)

print(f"Saving fetched workflow runs to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_runs_data, f, ensure_ascii=False, indent=4)
    
    if all_runs_data:
        print(f"Successfully saved {len(all_runs_data)} workflow runs to {output_path}")
    elif not os.path.exists(output_path):
        print(f"No workflow runs data to save. {output_path} was not created.")
    else:
        print(f"No workflow runs data to save, but an empty file {output_path} might have been created.")

except Exception as e:
    print(f"Error saving workflow runs to {output_path}: {e}") 