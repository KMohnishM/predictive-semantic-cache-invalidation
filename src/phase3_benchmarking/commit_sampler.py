"""Deterministic commit pair sampling for benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:
    from core.git_helper import GitHelper
except ImportError:
    try:
        from src.core.git_helper import GitHelper
    except ImportError:
        from ..core.git_helper import GitHelper

from .types import CommitPair


def sample_commit_pairs(
    git_helper: GitHelper,
    num_commits: int,
    sampling_mode: str = "adjacent",
    commit_stride: int = 1,
) -> List[CommitPair]:
    # Auto-adjust count to fetch enough raw commits for stride pairs
    raw_count = num_commits * commit_stride if sampling_mode == "stride" else num_commits
    commits = git_helper.get_commit_history(count=raw_count)
    if len(commits) < 2:
        return []

    pairs: List[CommitPair] = []
    if sampling_mode == "adjacent":
        for index in range(len(commits) - 1):
            pairs.append(CommitPair(commits[index], commits[index + 1], index))
    elif sampling_mode == "stride":
        pair_index = 0
        for index in range(0, len(commits) - 1, commit_stride):
            target_index = min(index + commit_stride, len(commits) - 1)
            if index == target_index:
                continue
            pairs.append(CommitPair(commits[index], commits[target_index], pair_index))
            pair_index += 1
    else:
        for index in range(len(commits) - 1):
            pairs.append(CommitPair(commits[index], commits[index + 1], index))

    return pairs
