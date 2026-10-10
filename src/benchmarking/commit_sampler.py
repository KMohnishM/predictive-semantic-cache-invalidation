"""Deterministic commit pair sampling for benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:
    from parser.git_helper import GitHelper
except ImportError:
    try:
        from src.parser.git_helper import GitHelper
    except ImportError:
        from ..parser.git_helper import GitHelper

from .types import CommitPair


def sample_commit_pairs(
    git_helper: GitHelper,
    num_commits: int,
    sampling_mode: str = "adjacent",
    commit_stride: int = 1,
    history_offset: int = 0,
    ref: str = "HEAD",
) -> List[CommitPair]:
    """Sample commit pair transitions chronologically from repository history.

    Args:
        git_helper: GitHelper instance attached to the repository.
        num_commits: Number of commits to sample ("adjacent"); pairs = num_commits - 1.
            In "stride" mode, the number of stride-sized steps to fetch.
        sampling_mode: 'adjacent' — consecutive pairs of the commits sampled every
            ``commit_stride`` commits (stride 1 = truly adjacent commits);
            'stride' — legacy alias kept for old configs, same chain of pairs.
        commit_stride: Step between sampled commits.
        history_offset: Skip this many of the most recent commits, so the sampled
            window ends ``history_offset`` commits before HEAD (used to give each
            multi-seed run its own disjoint window).
        ref: Git ref the window ends at (default HEAD).

    Returns:
        List of sampled CommitPair instances (oldest first).
    """
    commit_stride = max(1, int(commit_stride))
    if sampling_mode == "stride":
        span = num_commits * commit_stride
    else:
        span = (num_commits - 1) * commit_stride + 1
    history = git_helper.get_commit_history(count=span + history_offset, ref=ref)
    commits = history[:len(history) - history_offset] if history_offset else history
    commits = commits[-span:]
    if len(commits) < 2:
        return []

    # Sample every commit_stride-th commit ending at the newest one in the window.
    sampled = commits[::-1][::commit_stride][::-1]
    return [CommitPair(sampled[i], sampled[i + 1], i) for i in range(len(sampled) - 1)]
