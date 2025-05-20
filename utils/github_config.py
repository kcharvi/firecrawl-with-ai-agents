import os
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

def get_github_client():
    """
    Initialize and return a GitHub client with authentication.
    Exits the program if authentication fails.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Get GitHub PAT from environment
    github_pat = os.getenv("GITHUB_PAT")
    if not github_pat:
        print("Error: GITHUB_PAT environment variable not set.")
        print("Please ensure your .env file in the project root has GITHUB_PAT=YOUR_TOKEN")
        exit(1)

    try:
        g = Github(github_pat)
        user = g.get_user()
        print(f"Authenticated as: {user.login}")
        return g
    except Exception as e:
        print(f"Error authenticating with GitHub. Check your PAT: {e}")
        exit(1)

def get_target_repo(github_client, repo_owner="kcharvi", repo_name="firecrawl-with-ai-agents"):
    """
    Get the target repository object.
    Exits the program if repository access fails.
    
    Args:
        github_client: Authenticated GitHub client
        repo_owner: Repository owner username (default: "kcharvi")
        repo_name: Repository name (default: "firecrawl-with-ai-agents")
    
    Returns:
        Repository object
    """
    try:
        repo = github_client.get_user(repo_owner).get_repo(repo_name)
        print(f"Accessing target repository: {repo_owner}/{repo_name}")
        return repo
    except Exception as e:
        print(f"Error accessing target repository {repo_owner}/{repo_name}: {e}")
        print("Please check the repository name and ensure your PAT has sufficient permissions.")
        exit(1)

# Default configuration
DEFAULT_REPO_OWNER = "kcharvi"
DEFAULT_REPO_NAME = "firecrawl-with-ai-agents" 