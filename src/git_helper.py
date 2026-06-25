"""Git helper module for repository management."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GitHelper:
    """Wrapper around Git commands for repository management."""

    def __init__(self, repo_path: str):
        """
        Initialize GitHelper with repository path.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path).resolve()

    def _run_git_command(self, command: List[str], check: bool = True) -> str:
        """
        Run a git command in the repository.

        Args:
            command: List of git command arguments
            check: Whether to raise exception on non-zero exit code

        Returns:
            Command output as string
        """
        full_command = ["git"] + command
        try:
            result = subprocess.run(
                full_command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(full_command)}")
            logger.error(f"Error: {e.stderr}")
            raise

    def clone_repo(self, repo_url: str, path: str) -> bool:
        """
        Clone a repository if it does not exist.

        Args:
            repo_url: URL of the repository to clone
            path: Local path where repository should be cloned

        Returns:
            True if cloned or already exists, False otherwise
        """
        repo_path = Path(path).resolve()

        if repo_path.exists():
            logger.info(f"Repository already exists at {repo_path}")
            return True

        logger.info(f"Cloning repository from {repo_url} to {repo_path}")
        try:
            subprocess.run(
                ["git", "clone", repo_url, str(repo_path)],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Repository cloned successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            return False

    def get_commit_history(self, count: int = 50) -> List[str]:
        """
        Get list of recent commit hashes.

        Args:
            count: Number of commits to retrieve

        Returns:
            List of commit hashes (oldest first)
        """
        logger.info(f"Retrieving last {count} commits")
        # Get commits in reverse chronological order, then reverse to get oldest first
        output = self._run_git_command([
            "log",
            "--format=%H",
            f"-{count}"
        ])
        commits = [c.strip() for c in output.split("\n") if c.strip()] if output else []
        commits.reverse()  # Oldest first
        logger.info(f"Retrieved {len(commits)} commits")
        return commits

    def checkout_commit(self, commit_hash: str) -> bool:
        """
        Checkout a specific commit.

        Args:
            commit_hash: Git commit hash to checkout

        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Checking out commit {commit_hash[:8]}")
        try:
            self._run_git_command(["checkout", commit_hash])
            return True
        except Exception as e:
            logger.error(f"Failed to checkout commit {commit_hash[:8]}: {e}")
            return False

    def get_modified_files(self, commit_a: str, commit_b: str) -> List[str]:
        """
        Get list of files modified between two commits.

        Args:
            commit_a: Earlier commit hash
            commit_b: Later commit hash

        Returns:
            List of modified file paths (relative to repo root)
        """
        logger.debug(f"Getting modified files between {commit_a[:8]} and {commit_b[:8]}")
        output = self._run_git_command([
            "diff",
            "--name-only",
            commit_a,
            commit_b
        ])
        files = [f.strip() for f in output.split("\n") if f.strip()] if output else []
        return files

    def get_file_content_at_commit(self, commit_hash: str, file_path: str) -> Optional[str]:
        """
        Get content of a file at a specific commit.

        Args:
            commit_hash: Git commit hash
            file_path: Path to file (relative to repo root)

        Returns:
            File content as string, or None if file doesn't exist
        """
        try:
            output = self._run_git_command([
                "show",
                f"{commit_hash}:{file_path}"
            ])
            return output
        except Exception:
            # File might not exist at this commit
            return None

    def get_current_commit(self) -> str:
        """
        Get the current commit hash.

        Returns:
            Current commit hash
        """
        return self._run_git_command(["rev-parse", "HEAD"])

    def get_commit_info(self, commit_hash: str) -> dict:
        """
        Get detailed information about a commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            Dictionary with commit information
        """
        # Get commit message
        message = self._run_git_command([
            "log",
            "-1",
            "--format=%B",
            commit_hash
        ])

        # Get author and date
        author = self._run_git_command([
            "log",
            "-1",
            "--format=%an",
            commit_hash
        ])

        date = self._run_git_command([
            "log",
            "-1",
            "--format=%ai",
            commit_hash
        ])

        return {
            "hash": commit_hash,
            "message": message,
            "author": author,
            "date": date
        }

    def get_file_diff_stats(self, commit_a: str, commit_b: str, file_path: str) -> dict:
        """
        Get diff statistics for a specific file between two commits.

        Args:
            commit_a: Earlier commit hash
            commit_b: Later commit hash
            file_path: Path to file

        Returns:
            Dictionary with lines added/deleted
        """
        output = self._run_git_command([
            "diff",
            "--numstat",
            commit_a,
            commit_b,
            "--",
            file_path
        ])

        if not output:
            return {"added": 0, "deleted": 0}

        parts = output.split("\t")
        if len(parts) >= 2:
            added = int(parts[0]) if parts[0] != "-" else 0
            deleted = int(parts[1]) if parts[1] != "-" else 0
            return {"added": added, "deleted": deleted}

        return {"added": 0, "deleted": 0}

    def get_all_files_diff_stats(self, commit_a: str, commit_b: str) -> dict:
        """
        Get diff statistics for all files modified between two commits.

        Args:
            commit_a: Earlier commit hash
            commit_b: Later commit hash

        Returns:
            Dictionary mapping file_path to {"added": added, "deleted": deleted}
        """
        output = self._run_git_command([
            "diff",
            "--numstat",
            commit_a,
            commit_b
        ])

        stats = {}
        if not output:
            return stats

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                added = int(parts[0]) if parts[0] != "-" else 0
                deleted = int(parts[1]) if parts[1] != "-" else 0
                file_path = parts[2].strip().replace("\\", "/")
                stats[file_path] = {"added": added, "deleted": deleted}

        return stats