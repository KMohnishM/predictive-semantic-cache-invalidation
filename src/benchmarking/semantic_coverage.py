"""Semantic Coverage (SC) Framework for Predictive Semantic Cache Invalidation.

Formalizes query dataset sufficiency by evaluating:
    SC(e, Q) = |D(e, Q)| / |D(e)|

where D(e) is the set of semantic dimensions for entity e extracted from its AST,
and D(e, Q) is the subset of dimensions covered by the query workload Q.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class EntitySemanticDimensions:
    """Represents the complete semantic surface area D(e) of an entity."""

    entity_id: str
    entity_type: str  # class, function, method
    file_path: str
    dimensions: Set[str] = field(default_factory=set)

    @property
    def total_dimensions_count(self) -> int:
        return len(self.dimensions)


@dataclass
class SemanticCoverageResult:
    """Evaluation result for an entity's semantic coverage SC(e, Q)."""

    entity_id: str
    entity_type: str
    total_dimensions: int
    covered_dimensions: int
    coverage_ratio: float  # SC(e, Q) in [0.0, 1.0]
    uncovered_dimension_names: List[str]
    covered_dimension_names: List[str]
    query_count: int


def extract_entity_semantic_dimensions(entity) -> EntitySemanticDimensions:
    """Extract semantic dimensions D(e) from an entity using AST metadata.

    Args:
        entity: Entity object parsed by TreeSitterRepoParser.

    Returns:
        EntitySemanticDimensions object containing set D(e).
    """
    dims: Set[str] = set()
    eid = entity.entity_id
    code = entity.source_code

    # 1. Base Functional Intent Dimension
    dims.add("intent:core_functionality")

    # 2. Parameters & Signature Dimensions
    if entity.param_count > 0:
        dims.add("param:signature_args")

    # 3. Exception Handling Dimensions
    if "raise " in code or "except " in code or "try:" in code:
        dims.add("error:exception_handling")

    # 4. Domain & Protocol Specific Dimensions
    domain_keywords = {
        "jwt": "domain:jwt_authentication",
        "rs256": "domain:rs256_algorithm",
        "pbkdf2": "domain:pbkdf2_hashing",
        "salt": "domain:salt_security",
        "session": "domain:session_lifetime",
        "rbac": "domain:rbac_authorization",
        "permission": "domain:permission_check",
        "replica": "domain:read_replica",
        "pool": "domain:connection_pool",
        "lru": "domain:lru_cache_policy",
        "ttl": "domain:ttl_expiry",
        "rate_limit": "domain:rate_limiting",
        "iso": "domain:iso_8601_date",
        "aes": "domain:aes_256_encryption",
    }
    code_lower = code.lower()
    for kw, dim_name in domain_keywords.items():
        if kw in code_lower:
            dims.add(dim_name)

    # 5. Method-Level Dimensions for Classes
    if entity.entity_type == "class":
        method_matches = re.findall(r"def\s+([a-zA-Z0-9_]+)\s*\(", code)
        for m_name in method_matches:
            if not m_name.startswith("__"):
                dims.add(f"method:{m_name}")
            elif m_name == "__init__":
                dims.add("method:__init__")

    return EntitySemanticDimensions(
        entity_id=eid,
        entity_type=entity.entity_type,
        file_path=entity.file_path,
        dimensions=dims,
    )


def compute_semantic_coverage(
    entities: List, queries: List
) -> Dict[str, SemanticCoverageResult]:
    """Compute Semantic Coverage ratio SC(e, Q) for all entities across query set Q.

    Args:
        entities: List of Entity objects from TreeSitterRepoParser.
        queries: List of QueryCase objects.

    Returns:
        Dict mapping entity_id -> SemanticCoverageResult.
    """
    entity_queries: Dict[str, List] = {}
    for q in queries:
        eid = getattr(q, "target_entity_id", None)
        if eid:
            entity_queries.setdefault(eid, []).append(q)

    results = {}

    for ent in entities:
        eid = ent.entity_id
        sem_dims = extract_entity_semantic_dimensions(ent)
        all_dims = sem_dims.dimensions
        q_list = entity_queries.get(eid, [])

        covered: Set[str] = set()

        for q in q_list:
            q_text = q.query_text.lower()

            for d in all_dims:
                if d == "intent:core_functionality":
                    covered.add(d)
                elif d == "param:signature_args" and any(
                    k in q_text for k in ["parameter", "argument", "initialize", "accept", "mode", "option"]
                ):
                    covered.add(d)
                elif d == "error:exception_handling" and any(
                    k in q_text for k in ["error", "exception", "raise", "catch", "invalid", "fail"]
                ):
                    covered.add(d)
                elif d.startswith("domain:"):
                    dom_key = d.split(":")[1].replace("_", " ")
                    raw_kw = dom_key.split()[0]
                    if raw_kw in q_text or dom_key in q_text:
                        covered.add(d)
                elif d.startswith("method:"):
                    m_name = d.split(":")[1]
                    if m_name in q_text or m_name.replace("_", " ") in q_text:
                        covered.add(d)

        total_cnt = len(all_dims)
        covered_cnt = len(covered)
        sc_ratio = covered_cnt / total_cnt if total_cnt > 0 else 1.0
        uncovered = list(all_dims - covered)

        results[eid] = SemanticCoverageResult(
            entity_id=eid,
            entity_type=ent.entity_type,
            total_dimensions=total_cnt,
            covered_dimensions=covered_cnt,
            coverage_ratio=sc_ratio,
            uncovered_dimension_names=uncovered,
            covered_dimension_names=list(covered),
            query_count=len(q_list),
        )

    return results
