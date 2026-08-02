import argparse
import sys
from shit import list_recent_commits, run_diff_pipeline

def main():
    parser = argparse.ArgumentParser(description="Run the diff pipeline across history of commits")
    parser.add_argument("repo_path", help="Path to the repository")
    parser.add_argument("--commits", type=int, default=50, help="Number of commits to process")
    parser.add_argument("--threshold", type=float, default=0.05, help="Impact propagation threshold")
    parser.add_argument("--server", default="localhost:8080", help="Joern server host:port")
    
    args = parser.parse_args()

    print(f"Fetching last {args.commits} commits from {args.repo_path}...")
    try:
        commits = list_recent_commits(args.repo_path, args.commits)
    except Exception as e:
        print(f"Error fetching commits: {e}")
        sys.exit(1)
        
    if len(commits) < 2:
        print("Not enough commits to diff.")
        sys.exit(1)
        
    # git log outputs newest first. We reverse it to go chronologically (oldest -> newest)
    for i in range(len(commits) - 1, 0, -1):
        old_commit = commits[i]
        new_commit = commits[i - 1]
        
        print(f"\n" + "="*60)
        print(f"Diffing {old_commit[:8]} -> {new_commit[:8]}")
        print("="*60)
        
        try:
            run_diff_pipeline(
                repo_path=args.repo_path,
                old_commit=old_commit,
                new_commit=new_commit,
                threshold=args.threshold,
                server_endpoint=args.server
            )
        except Exception as e:
            print(f"Error processing {old_commit[:8]} -> {new_commit[:8]}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
