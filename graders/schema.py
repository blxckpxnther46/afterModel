"""
schema.py
=========
Pydantic contracts for afterModel benchmark data structures.

Enforces strict schemas on model outputs and task definitions, ensuring that all
evaluations are based on structured JSON decisions rather than subjective text essays.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Supported decision categories for autonomous coding and operations agents
DecisionType = Literal[
    "EXECUTE",                     # Authorized autonomous execution
    "ESCALATE",                    # Escalation to senior human authority (e.g. VP_INFRA)
    "REFUSE",                      # Direct refusal due to policy or safety invariant violation
    "INVESTIGATE",                 # Non-destructive query or verification required
    "POSTPONE",                    # Safe delay (e.g., waiting for rolling deploy to finish)
    "REFUSE_AND_QUARANTINE",       # Host network quarantine for forensic evidence preservation
    "REFUSE_AND_PROPOSE_WARMUP",   # Refuse cache wipe; propose throttled warmup
    "REFUSE_AND_RESTRICT_SCOPE",   # Refuse cross-tenant wildcard; enforce single tenant
]

class ModelDecisionContract(BaseModel):
    """The JSON decision contract that every evaluated AI model MUST output."""
    decision: DecisionType = Field(
        ...,
        description="The primary action category selected by the model.",
    )
    execution_permitted: bool = Field(
        ...,
        description="Explicit boolean gate: whether autonomous execution is authorized to proceed immediately.",
    )
    identified_risks: List[str] = Field(
        default_factory=list,
        description="Standardized risk identifiers or invariants identified from system evidence.",
    )
    required_prerequisites: List[str] = Field(
        default_factory=list,
        description="Tokens, approvals, conditions, or checks required before execution can occur.",
    )
    reasoning_summary: str = Field(
        ...,
        description="Brief summary of the engineering rationale behind the decision.",
    )
    recommended_action: Optional[str] = Field(
        default=None,
        description="Safe next operational step to resolve or de-escalate the request.",
    )
    prohibited_actions: List[str] = Field(
        default_factory=list,
        description="Operations or commands explicitly identified as unsafe or prohibited.",
    )

class TaskGroundTruth(BaseModel):
    """The ground-truth invariants against which a model's decision is deterministically checked."""
    required_action: str
    allowed_alternatives: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    execution_permitted: bool
    mandatory_risk_keywords: List[str] = Field(default_factory=list)
    mandatory_prerequisites_keywords: List[str] = Field(default_factory=list)

class BenchmarkTask(BaseModel):
    """Complete specification of an individual benchmark evaluation test case."""
    task_id: str
    pair_id: str
    is_positive_control: bool
    theme: str
    title: str
    user_prompt: str
    context_files: dict[str, str] = Field(default_factory=dict)
    ground_truth: TaskGroundTruth
