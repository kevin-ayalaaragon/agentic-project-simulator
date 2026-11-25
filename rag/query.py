"""Build the retrieval query for one role call from what that role can see.

Takes ProjectState, artifact text and the role, never a Scenario: a Scenario also
carries `description` and `seeded_defects`, and retrieval must not see the answer key.
tests/test_rag_query.py enforces both the signature and the absence of seeded text.
"""

from __future__ import annotations

import re

from core_engine.schemas import AgentRole, ProjectState

# What each role looks for, in the vocabulary of the corpus it searches.
ROLE_FOCUS: dict[AgentRole, str] = {
    AgentRole.SECURITY_PRIVACY: (
        "security and privacy controls: personally identifiable information, encryption, "
        "access control, audit logging, data retention, data residency, secrets management"
    ),
    AgentRole.ENGINEERING_LEAD: (
        "system and communications protection, contingency planning, resilience, "
        "denial of service protection, configuration management"
    ),
}

CONTROL_ID = re.compile(r"\b([A-Za-z]{2})-(\d{1,2})(?:\s*\((\d{1,2})\))?")


def build_query(project_state: ProjectState, artifacts: dict[str, str], role: AgentRole) -> str:
    """Role focus, project name, acceptance criteria and artifact text, whitespace-normalized."""
    if role not in ROLE_FOCUS:
        raise ValueError(f"no retrieval focus defined for {role.value}")
    parts = [ROLE_FOCUS[role], project_state.name, *project_state.acceptance_criteria]
    parts += [text for _, text in sorted(artifacts.items())]
    return " ".join(" ".join(parts).split())


def control_ids_in(text: str) -> list[str]:
    """Normalized OSCAL IDs for control references written in the text: `AC-2(1)` -> `ac-2.1`."""
    ids = []
    for family, number, enhancement in CONTROL_ID.findall(text):
        cid = f"{family.lower()}-{int(number)}" + (f".{int(enhancement)}" if enhancement else "")
        if cid not in ids:
            ids.append(cid)
    return ids
