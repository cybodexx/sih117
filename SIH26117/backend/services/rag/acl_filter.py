"""ACL pre-filter for Qdrant queries. Fail-closed on every edge case."""
from __future__ import annotations

from qdrant_client import models

from backend.core.rbac import CROSS_DEPARTMENT, Clearance, ServerUserContext


def build_acl_filter(user: ServerUserContext) -> models.Filter:
    """Build a Qdrant pre-filter from a verified JWT context.

    MUST conditions (fail-closed):
      - clearance_level <= user's level  (Bell-LaPadula no-read-up)
      - status == READY                  (only committed documents)
      - department in user.departments   (need-to-know, skip for CROSS_DEPARTMENT)
    """
    clearance = int(user.clearance_level) if isinstance(user.clearance_level, Clearance) else int(user.clearance_level)
    departments = list(user.departments) if user.departments else []

    if not user.departments and user.role not in CROSS_DEPARTMENT:
        raise ValueError("User has no departments assigned — FAIL CLOSED")

    must: list[models.FieldCondition] = [
        models.FieldCondition(
            key="clearance_level",
            range=models.Range(lte=clearance),
        ),
        models.FieldCondition(
            key="status",
            match=models.MatchValue(value="READY"),
        ),
    ]

    if user.role not in CROSS_DEPARTMENT:
        must.append(
            models.FieldCondition(
                key="department",
                match=models.MatchAny(any=departments),
            )
        )

    return models.Filter(must=must)
