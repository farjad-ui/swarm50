"""M1: prompt rendering. Verifies the two reward arms differ ONLY in the objective paragraph,
and that templates substitute cleanly with no leftover $placeholders."""
import re

from swarm50.prompts import render_critic, render_critic_final, render_rebuttal, render_strategist
from swarm50.schemas import BetAction, Rebuttal, StrategistResponse, WorkOrder, parse_model
from tests.conftest import CONFIG


def _no_placeholders(text):
    # a bare $identifier that string.Template would have substituted; "$$" (escaped literal) is fine.
    return not re.search(r"(?<!\$)\$[A-Za-z_]", text)


def test_arms_differ_only_in_objective_paragraph():
    linear = render_strategist({**CONFIG, "reward_arm": "linear"})
    convex = render_strategist({**CONFIG, "reward_arm": "convex"})
    assert linear != convex
    lin_lines = linear.splitlines()
    con_lines = convex.splitlines()
    assert len(lin_lines) == len(con_lines)
    diff_lines = [i for i, (a, b) in enumerate(zip(lin_lines, con_lines)) if a != b]
    # every differing line must belong to the objective paragraph (starts right after "Your objective")
    obj_idx = lin_lines.index("Your objective")
    assert diff_lines, "arms rendered identically; objective paragraph did not substitute"
    assert all(i > obj_idx for i in diff_lines)
    assert _no_placeholders(linear) and _no_placeholders(convex)


def test_strategist_prompt_never_says_public_or_nudges_category():
    text = render_strategist(CONFIG).lower()
    assert "public" not in text
    for cat in ("digital_product", "service", "content", "tool", "trading", "other"):
        assert f"prefer {cat}" not in text and f"avoid {cat}" not in text


def test_rebuttal_and_critic_render_cleanly():
    assert _no_placeholders(render_rebuttal(CONFIG))
    assert _no_placeholders(render_critic("STATE BLOCK HERE"))
    final = render_critic_final("STATE BLOCK HERE")
    assert "final review" in final.lower()
    assert _no_placeholders(final)


def test_strategist_response_parses_bet_actions_and_work_orders():
    text = ('{"cycle_reasoning": "r", "memos": [], "no_bet_reason": "n", '
            '"bet_actions": [{"bet_id": "c1-1", "action": "kill", "reason": "dead"}], '
            '"work_orders": [{"bet_id": "c1-2", "task": "write copy", '
            '"deliverable_type": "text", "max_tokens": 500}]}')
    resp = parse_model(StrategistResponse, text)
    assert resp.bet_actions == [BetAction(bet_id="c1-1", action="kill", reason="dead")]
    assert resp.work_orders == [WorkOrder(bet_id="c1-2", task="write copy",
                                          deliverable_type="text", max_tokens=500)]


def test_strategist_response_defaults_are_empty():
    resp = parse_model(StrategistResponse, '{"cycle_reasoning": "r", "memos": [], "no_bet_reason": "n"}')
    assert resp.bet_actions == [] and resp.work_orders == []


def test_rebuttal_schema_uses_decision_and_revised_memo():
    text = '{"responses": [{"objection": "a", "response": "b"}], "decision": "withdraw"}'
    r = parse_model(Rebuttal, text)
    assert r.decision == "withdraw" and r.revised_memo is None
