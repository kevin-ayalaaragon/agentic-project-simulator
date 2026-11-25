"""L5 stand-in for rag runs: are concerns grounded in the controls the agent was shown?

Two numbers per run, for the roles that ran in rag mode:
  citation rate       share of concerns that cite at least one retrieved chunk
  citation relevance  share of cited chunks whose control is labeled relevant for
                      that scenario (eval/retrieval/queries.yaml pipeline labels)

The schema already guarantees validity: a concern can cite only chunk IDs that were
shown (an enum built per call). These metrics say how often agents ground concerns
and whether what they cite is right. Relevance is reported only for scenarios with
labels; the calibrated judge for full groundedness is later work.
"""

from __future__ import annotations

from dataclasses import dataclass

from eval.metrics.retrieval import control_of


@dataclass
class CitationStats:
    concerns: int
    citing: int
    cited: int
    cited_relevant: int | None  # None when the scenario has no labels

    @property
    def citation_rate(self) -> float | None:
        return self.citing / self.concerns if self.concerns else None

    @property
    def citation_relevance(self) -> float | None:
        if self.cited_relevant is None or not self.cited:
            return None
        return self.cited_relevant / self.cited


def citation_stats(run: dict, rag_agents: set[str], relevant_controls: set[str] | None) -> CitationStats:
    """`run` is a ScenarioRun as JSON; counts concerns from `rag_agents` (the runner's RAG_ROLES values)."""
    concerns = [
        c
        for gate in run["gate_results"]
        for response in gate["agent_responses"]
        if response["agent"] in rag_agents
        for c in response["concerns"]
    ]
    cited = [ref for c in concerns for ref in c.get("references", [])]
    relevant = None
    if relevant_controls is not None:
        relevant = sum(control_of(ref) in relevant_controls for ref in cited)
    return CitationStats(
        concerns=len(concerns),
        citing=sum(bool(c.get("references")) for c in concerns),
        cited=len(cited),
        cited_relevant=relevant,
    )
