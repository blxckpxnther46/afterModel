from typing import List, Optional, Literal
from pydantic import BaseModel, Field

DecisionType = Literal[
    "EXECUTE",
    "ESCALATE",
    "REFUSE",
    "INVESTIGATE",
    "POSTPONE",
    "REFUSE_AND_QUARANTINE",
    "REFUSE_AND_PROPOSE_WARMUP",
    "REFUSE_AND_RESTRICT_SCOPE",
]

class ModelDecisionContract(BaseModel):
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
    required_action: str
    allowed_alternatives: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    execution_permitted: bool
    mandatory_risk_keywords: List[str] = Field(default_factory=list)
    mandatory_prerequisites_keywords: List[str] = Field(default_factory=list)

class BenchmarkTask(BaseModel):
    task_id: str
    pair_id: str
    is_positive_control: bool
    theme: str
    title: str
    user_prompt: str
    context_files: dict[str, str] = Field(default_factory=dict)
    ground_truth: TaskGroundTruth
