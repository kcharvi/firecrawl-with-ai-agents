import os
import json
from pathlib import Path
import sys
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

# Add the project root to Python path to import from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.github_config import get_github_client, get_target_repo

# Define the root directory to analyze
root_dir = Path("code-base")

# Define file type patterns
file_patterns = {
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "markdown": [".md"],
    "yaml": [".yaml", ".yml"],
    "json": [".json"],
    "docker": ["Dockerfile", "docker-compose.yaml", "docker-compose.yml"],
    "git": [".gitignore", ".gitattributes", ".gitmodules"],
    "github": [".github/workflows/"],
    "test_typescript": [".test.ts", ".spec.ts"],
    "test_go": ["_test.go"],
    "config": ["package.json", "go.mod", "go.sum", "tsconfig.json", ".env", ".env.example"]
}

# Initialize counters and lists
file_counts = {category: 0 for category in file_patterns.keys()}
file_counts["other"] = 0
detected_languages = set()
documentation_files = []
test_files = []
config_files = []
structure = {}

def analyze_directory(directory_path, structure_dict):
    """Recursively analyzes a directory and its contents."""
    for item in directory_path.iterdir():
        if item.is_file():
            # Determine file type
            file_type = "other"
            for category, patterns in file_patterns.items():
                if any(item.name.endswith(ext) for ext in patterns if not ext.endswith("/")) or \
                   any(pattern in str(item) for pattern in patterns if pattern.endswith("/")):
                    file_type = category
                    break

            # Update counters and lists
            file_counts[file_type] += 1

            if file_type == "typescript" or file_type == "go":
                detected_languages.add(file_type)
            elif file_type == "markdown":
                documentation_files.append(str(item.relative_to(root_dir)))
            elif file_type.startswith("test_"):
                test_files.append(str(item.relative_to(root_dir)))
            elif file_type == "config":
                config_files.append(str(item.relative_to(root_dir)))

            # Add file to structure
            structure_dict[item.name] = {"type": "file", "file_type": file_type}

        elif item.is_dir():
            # Recursively analyze subdirectory
            subdir_structure = {}
            analyze_directory(item, subdir_structure)
            structure_dict[item.name] = {"type": "directory", "contents": subdir_structure}

# Start analysis
print(f"Analyzing repository structure in {root_dir}...")
analyze_directory(root_dir, structure)

# Prepare the report
report = {
    "directory_structure": structure,
    "file_counts": file_counts,
    "detected_languages": list(detected_languages),
    "documentation_files": documentation_files,
    "test_files": test_files,
    "config_files": config_files
}

# Save the report
output_filename = "repo_structure_analysis.json"
output_path = Path("repo-data/repo-contents") / output_filename

print(f"Saving repository structure analysis to {output_path}...")

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved repository structure analysis to {output_path}")

except Exception as e:
    print(f"Error saving repository structure analysis to {output_path}: {e}")

# Initialize GitHub client and get repository
g = get_github_client()
target_repo = get_target_repo(g) 