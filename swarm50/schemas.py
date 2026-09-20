"""Strict schemas for every agent response, plus the one JSON parser all of them go through."""
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Category = Literal["digital_product", "service", "content", "tool", "trading", "other"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Memo(Strict):
    title: str
    category: Category
    description: str
    stake_usd: float = Field(gt=0)
    expected_value_usd: float
    ev_reasoning: str
    p_total_loss: float = Field(ge=0, le=1)
    variance_notes: str
    token_cost_estimate_usd: float = Field(ge=0)
    kill_criteria: str
    kill_by_cycle: int
    next_best_alternative: str
    why_this_beats_it: str
    human_actions_required: list[str]
    human_minutes_required: int = Field(ge=0)


class BetAction(Strict):
    bet_id: str
    action: Literal["hold", "kill"]
    reason: str


class WorkOrder(Strict):
    bet_id: str
    task: str
    deliverable_type: Literal["text", "code", "listing_copy", "plan"]
    max_tokens: int = Field(ge=0)


class StrategistResponse(Strict):
    cycle_reasoning: str
    memos: list[Memo] = Field(max_length=3)
    no_bet_reason: str | None = None
    bet_actions: list[BetAction] = Field(default_factory=list)
    work_orders: list[WorkOrder] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reason_required_when_empty(self):
        if not self.memos and not self.no_bet_reason:
            raise ValueError("no_bet_reason is required when memos is empty")
        return self


class Objection(Strict):
    point: str
    severity: Literal["low", "medium", "high"]


class Critique(Strict):
    objections: list[Objection]
    key_risk: str
    verdict: Literal["approve", "revise", "reject"]


class Response(Strict):
    objection: str
    response: str


class Rebuttal(Strict):
    responses: list[Response]
    decision: Literal["revise", "withdraw"]
    revised_memo: Memo | None = None

    @model_validator(mode="after")
    def _memo_required_when_revising(self):
        if self.decision == "revise" and self.revised_memo is None:
            raise ValueError("revised_memo is required when decision is 'revise'")
        return self


def memo_schema_text() -> str:
    """Compact field: type list for the Memo schema, embedded in prompts via $memo_schema."""
    lines = []
    for name, field in Memo.model_fields.items():
        ann = field.annotation
        typ = getattr(ann, "__name__", str(ann))
        lines.append(f"  {name}: {typ}")
    return "{\n" + "\n".join(lines) + "\n}"


def parse_model(model_cls, text: str):
    """Parse the first {...} block in `text` into model_cls. Raises ValueError with a readable message."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found in response")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}") from e
    try:
        return model_cls.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"schema validation failed for {model_cls.__name__}: {e}") from e
