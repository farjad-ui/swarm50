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


class StrategistResponse(Strict):
    cycle_reasoning: str
    memos: list[Memo] = Field(max_length=3)
    no_bet_reason: str | None = None

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


class Rebuttal(Strict):
    action: Literal["revise", "withdraw"]
    reason: str
    memo: Memo | None = None

    @model_validator(mode="after")
    def _memo_required_when_revising(self):
        if self.action == "revise" and self.memo is None:
            raise ValueError("memo is required when action is 'revise'")
        return self


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
