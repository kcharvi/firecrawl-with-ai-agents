# ai-agents\agents\issue-triage\auto_labelling_existing_issues_agent.py

import os
import re 
import sys
import time
import traceback
from github import Github
from github.GithubException import GithubException


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_agents.models.gemini_langchain import get_langchain_gemini
from utils.github_config import get_github_client, get_target_repo
from ai_agents.prompts.issue_triage_prompts import ISSUE_LABELING_PROMPT

g = get_github_client()
target_repo = get_target_repo(g)

print("Initializing LLM client...")
try:
    gemini_llm = get_langchain_gemini()
    print("LLM client initialized successfully.")
except Exception as e:
    print(f"Error initializing LLM client: {e}")
    print(traceback.format_exc())
    sys.exit(1)

def prepare_issue_text_for_llm(issue, comments):
    """Combines issue title, body, and comments into a structured format for LLM analysis."""
    try:
        comments_text = ""
        if comments:
            comments_text = "\n".join([f"- {comment.user.login}: {comment.body}" for comment in comments])
        
        return {
            "issue_title": issue.title,
            "issue_body": issue.body or "No description provided",
            "comments": comments_text or "No comments"
        }
    except Exception as e:
        print(f"Error preparing issue text: {e}")
        print(traceback.format_exc())
        return None

def parse_llm_response_for_labels(response, available_labels):
    """Parse the LLM response to extract valid labels."""
    try:
        response_content = response.content if response else ""

        if not response_content or response_content.strip() == "NO_SUITABLE_LABELS":
            return []
        
        suggested_labels = [label.strip() for label in response_content.split(",")]
        
        valid_labels = [label for label in suggested_labels if label in available_labels]
        
        return valid_labels
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(traceback.format_exc())
        return []

def get_label_suggestions_from_llm(issue_data, available_labels):
    """Get label suggestions from LLM using the structured prompt."""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"\nAnalyzing issue: {issue_data['issue_title']}")
            print(f"Attempt {attempt + 1} of {max_retries}")
            
            formatted_prompt = ISSUE_LABELING_PROMPT.format(
                available_labels=", ".join(available_labels),
                issue_title=issue_data["issue_title"],
                issue_body=issue_data["issue_body"],
                comments=issue_data["comments"]
            )
            
            print("Sending request to LLM...")
            try:
                response = gemini_llm.invoke(formatted_prompt)
                print(f"Received response from LLM: {response}")
                
                suggested_labels = parse_llm_response_for_labels(response, available_labels)
                print(f"Parsed suggested labels: {suggested_labels}")
                
                return suggested_labels
            except Exception as llm_error:
                print(f"LLM request failed: {llm_error}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                raise
            
        except Exception as e:
            print(f"Error getting label suggestions from LLM: {e}")
            print(traceback.format_exc())
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return []
    
    return []

def run_labeling_agent():
    """Main function to run the labeling agent."""
    print("\n--- Running Labeling Agent ---")

    # 1. Fetch available labels
    print("Fetching available labels from target repository...")
    available_labels = set()
    try:
        for label in target_repo.get_labels():
            available_labels.add(label.name)
        print(f"Found {len(available_labels)} available labels.")
        if not available_labels:
            print("Warning: No labels found in the target repository.")
            return
    except Exception as e:
        print(f"Error fetching available labels: {e}")
        print(traceback.format_exc())
        return

    # 2. Find unlabeled issues
    print("\nSearching for unlabeled issues...")
    unlabeled_issues = []
    try:
        query = f"repo:{target_repo.full_name} no:label type:issue"
        search_results = g.search_issues(query)
        
        for issue_result in search_results:
            try:
                full_issue = target_repo.get_issue(issue_result.number)
                if not full_issue.labels and not hasattr(full_issue, 'pull_request') or full_issue.pull_request is None:
                    unlabeled_issues.append(full_issue)
            except Exception as fetch_e:
                print(f"Error fetching issue #{issue_result.number}: {fetch_e}")
                print(traceback.format_exc())
        
        print(f"Found {len(unlabeled_issues)} unlabeled issues.")
    except Exception as e:
        print(f"Error searching for unlabeled issues: {e}")
        print(traceback.format_exc())
        return

    # 3. Process unlabeled issues
    if not unlabeled_issues:
        print("No unlabeled issues to process.")
        return

    print(f"\nProcessing {len(unlabeled_issues)} unlabeled issues...")
    
    stats = {
        "processed": 0,
        "labeled": 0,
        "failed": 0
    }

    for issue in unlabeled_issues:
        print(f"\nProcessing issue #{issue.number}: '{issue.title}'")
        
        try:
            print("Fetching issue comments...")
            comments = list(issue.get_comments())
            print(f"Found {len(comments)} comments.")
            
            issue_data = prepare_issue_text_for_llm(issue, comments)
            if not issue_data:
                print("Failed to prepare issue data, skipping...")
                stats["failed"] += 1
                continue
            
            suggested_labels = get_label_suggestions_from_llm(issue_data, list(available_labels))
            
            if suggested_labels:
                print(f"  Applying labels: {', '.join(suggested_labels)}")
                try:
                    issue.add_to_labels(*suggested_labels)
                    stats["labeled"] += 1
                    print("  Successfully applied labels.")
                except GithubException as e:
                    print(f"  Error applying labels: {e}")
                    print(traceback.format_exc())
                    stats["failed"] += 1
            else:
                print("  No suitable labels suggested.")
                stats["failed"] += 1
                
        except Exception as e:
            print(f"  Error processing issue: {e}")
            print(traceback.format_exc())
            stats["failed"] += 1
            
        stats["processed"] += 1
        
        rate_limit = g.get_rate_limit()
        if rate_limit.core.remaining < 20:
            reset_time = rate_limit.core.reset.timestamp()
            sleep_duration = reset_time - time.time() + 15
            if sleep_duration > 0:
                print(f"Rate limit almost reached. Sleeping for {sleep_duration:.2f} seconds...")
                time.sleep(sleep_duration)

    print("\n--- Labeling Agent Summary ---")
    print(f"Total issues processed: {stats['processed']}")
    print(f"Successfully labeled: {stats['labeled']}")
    print(f"Failed to label: {stats['failed']}")
    print("----------------------------")

if __name__ == "__main__":
    run_labeling_agent()