"""Stateless text and vector helpers for embedding generation."""

import re

import numpy as np


def remove_comments_and_docstrings(source: str) -> str:
    """
    Remove comments and docstrings from Python source code.

    Args:
        source: Python source code

    Returns:
        Cleaned source code
    """
    # Remove docstrings (triple-quoted strings)
    # Pattern matches triple-quoted strings at the beginning of lines
    docstring_pattern = r'""".*?"""|\'\'\'.*?\'\'\''
    source = re.sub(docstring_pattern, '', source, flags=re.DOTALL)

    # Remove single-line comments
    # Be careful not to remove strings that contain #
    lines = source.split('\n')
    cleaned_lines = []
    for line in lines:
        # Simple approach: remove # that are not inside strings
        in_string = False
        string_char = None
        result = []
        i = 0
        while i < len(line):
            char = line[i]
            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
                result.append(char)
            elif in_string and char == string_char:
                in_string = False
                string_char = None
                result.append(char)
            elif not in_string and char == '#':
                # Skip rest of line
                break
            else:
                result.append(char)
            i += 1
        cleaned_lines.append(''.join(result))

    return '\n'.join(cleaned_lines)


def compute_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Cosine similarity score (0 to 1)
    """
    return float(np.dot(embedding1, embedding2))
