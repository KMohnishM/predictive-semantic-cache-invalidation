"""Embedding manager for generating code embeddings and computing drift."""

import re
from typing import Dict, List, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages code embeddings and semantic drift calculation."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 clean_mode: bool = False):
        """
        Initialize embedding manager.

        Args:
            model_name: Name of the sentence-transformers model
            clean_mode: If True, remove comments and docstrings before embedding
        """
        self.model_name = model_name
        self.clean_mode = clean_mode
        self.model = None
        self.embeddings: Dict[str, np.ndarray] = {}

    def _load_model(self) -> None:
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
            
            # Enforce safe max sequence length to prevent IndexError in position embeddings
            if "unixcoder" in self.model_name.lower():
                self.model.max_seq_length = 512
            elif "jina" in self.model_name.lower():
                self.model.max_seq_length = 8192
            else:
                try:
                    config = self.model._first_module().auto_model.config
                    max_pos = getattr(config, "max_position_embeddings", None)
                    if max_pos is not None:
                        model_type = getattr(config, "model_type", "")
                        offset = 2 if "roberta" in model_type else 0
                        self.model.max_seq_length = max_pos - offset
                except Exception:
                    self.model.max_seq_length = min(getattr(self.model, "max_seq_length", 512), 512)
                    
            logger.info(f"Model loaded successfully with max_seq_length={self.model.max_seq_length}")

    def _remove_comments_and_docstrings(self, source: str) -> str:
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

    def _prepare_text(self, source_code: str) -> str:
        """
        Prepare source code for embedding.

        Args:
            source_code: Raw source code

        Returns:
            Prepared text for embedding
        """
        if self.clean_mode:
            return self._remove_comments_and_docstrings(source_code)
        return source_code

    def generate_embedding(self, entity_id: str, source_code: str) -> np.ndarray:
        """
        Generate embedding for a code entity.

        Args:
            entity_id: Entity identifier
            source_code: Source code of the entity

        Returns:
            Embedding vector
        """
        self._load_model()

        prepared_text = self._prepare_text(source_code)
        embedding = self.model.encode(prepared_text, convert_to_numpy=True)

        # Normalize embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        self.embeddings[entity_id] = embedding
        return embedding

    def generate_embeddings_batch(self, entities: Dict[str, str]) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for multiple entities.

        Args:
            entities: Dictionary mapping entity_id to source_code

        Returns:
            Dictionary mapping entity_id to embedding
        """
        self._load_model()

        entity_ids = list(entities.keys())
        texts = [self._prepare_text(source) for source in entities.values()]

        logger.info(f"Generating embeddings for {len(entity_ids)} entities")
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        embeddings = embeddings / norms

        result = {}
        for entity_id, embedding in zip(entity_ids, embeddings):
            result[entity_id] = embedding
            self.embeddings[entity_id] = embedding

        return result

    def get_embedding(self, entity_id: str) -> Optional[np.ndarray]:
        """
        Get cached embedding for an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            Embedding vector or None if not cached
        """
        return self.embeddings.get(entity_id)

    def compute_cosine_similarity(self, embedding1: np.ndarray,
                                  embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        return float(np.dot(embedding1, embedding2))

    def compute_drift(self, entity_id: str, old_embedding: np.ndarray,
                      new_embedding: np.ndarray) -> float:
        """
        Compute semantic drift for an entity.

        Drift = 1 - cosine_similarity(old, new)

        Args:
            entity_id: Entity identifier
            old_embedding: Embedding at time t
            new_embedding: Embedding at time t+1

        Returns:
            Drift score (0 = no change, 1 = complete change)
        """
        similarity = self.compute_cosine_similarity(old_embedding, new_embedding)
        drift = 1.0 - similarity
        return drift

    def compute_all_drifts(self, old_embeddings: Dict[str, np.ndarray],
                           new_embeddings: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Compute drift for all entities that exist in both old and new embeddings.

        Args:
            old_embeddings: Embeddings at time t
            new_embeddings: Embeddings at time t+1

        Returns:
            Dictionary mapping entity_id to drift score
        """
        drifts = {}

        common_entities = set(old_embeddings.keys()) & set(new_embeddings.keys())

        for entity_id in common_entities:
            drift = self.compute_drift(
                entity_id,
                old_embeddings[entity_id],
                new_embeddings[entity_id]
            )
            drifts[entity_id] = drift

        return drifts

    def find_similar_entities(self, query_embedding: np.ndarray,
                              entity_embeddings: Dict[str, np.ndarray],
                              top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Find most similar entities to a query embedding.

        Args:
            query_embedding: Query embedding vector
            entity_embeddings: Dictionary of entity embeddings
            top_k: Number of top results to return

        Returns:
            List of (entity_id, similarity_score) tuples, sorted by similarity
        """
        similarities = []

        for entity_id, embedding in entity_embeddings.items():
            similarity = self.compute_cosine_similarity(query_embedding, embedding)
            similarities.append((entity_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def clear_cache(self) -> None:
        """Clear cached embeddings."""
        self.embeddings.clear()
        logger.debug("Embedding cache cleared")

    def get_cache_size(self) -> int:
        """
        Get number of cached embeddings.

        Returns:
            Number of cached embeddings
        """
        return len(self.embeddings)