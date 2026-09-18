"""Critic loop: strategist -> critic -> (rebuttal -> final verdict). Every call is one system + one user message."""
import json
import logging

from .exceptions import CycleCapExceeded, WalletEmpty
from .metered import metered_call
from .prompts import render_critic, render_critic_final, render_rebuttal, render_strategist
from .schemas import Critique, Rebuttal, StrategistResponse, parse_model
from .state import build_state

log = logging.getLogger("swarm50.review")
STRATEGIST_MAX_TOKENS = 4000
CRITIC_MAX_TOKENS = 2000


def _ask(ledger, cycle, agent, role, system, user, max_tokens) -> str:
    return metered_call(ledger, cycle, agent, role, [{"role": "user", "content": user}],
                        system=system, max_tokens=max_tokens).text


def _ask_parsed(ledger, cycle, agent, role, system, user, model_cls, max_tokens):
    """One call plus ONE repair retry that quotes the validation error. Returns (parsed, None) or (None, info)."""
    text = _ask(ledger, cycle, agent, role, system, user, max_tokens)
    try:
        return parse_model(model_cls, text), None
    except ValueError as first:
        repair = (f"{user}\n\n## Validation error in your previous response\n{first}\n\n"
                  f"## Your previous response\n{text}")
        text2 = _ask(ledger, cycle, agent, role, system, repair, max_tokens)
        try:
            return parse_model(model_cls, text2), None
        except ValueError as second:
            return None, {"schema": model_cls.__name__, "first_error": str(first), "first_response": text,
                          "error": str(second), "response": text2}


def _section(title, obj) -> str:
    return f"## {title}\n{json.dumps(obj, indent=1)}"


def _review_memo(ledger, betlog, cycle, bet_id, memo, state):
    config = ledger.config
    critic_system = render_critic(state)
    critique, err = _ask_parsed(ledger, cycle, "critic", "critic", critic_system,
                                f"{state}\n\n{_section('Memo', memo.model_dump())}", Critique, CRITIC_MAX_TOKENS)
    if critique is None:
        betlog.append(cycle, bet_id, "malformed", err, "critic")
        return
    betlog.append(cycle, bet_id, "critiqued", critique.model_dump(), "critic")
    if critique.verdict == "approve":
        return  # derived status: queued

    rebuttal, err = _ask_parsed(
        ledger, cycle, "strategist", "strategist", render_rebuttal(config),
        f"{state}\n\n{_section('Memo', memo.model_dump())}\n\n{_section('Critique', critique.model_dump())}",
        Rebuttal, STRATEGIST_MAX_TOKENS)
    if rebuttal is None:
        betlog.append(cycle, bet_id, "malformed", err, "strategist")
        return
    if rebuttal.decision == "withdraw":
        betlog.append(cycle, bet_id, "withdrawn", rebuttal.model_dump(), "strategist")
        return
    betlog.append(cycle, bet_id, "rebutted", rebuttal.model_dump(), "strategist")

    # Final round reuses the critic prompt and schema, with the critic_final.md instruction appended;
    # "revise" is not available here and counts as reject.
    final_system = render_critic_final(state)
    final, err = _ask_parsed(
        ledger, cycle, "critic", "critic", final_system,
        f"{state}\n\n{_section('Memo', rebuttal.revised_memo.model_dump())}\n\n"
        f"{_section('Prior critique', critique.model_dump())}\n\n"
        f"{_section('Rebuttal', {'responses': [r.model_dump() for r in rebuttal.responses]})}",
        Critique, CRITIC_MAX_TOKENS)
    if final is None:
        betlog.append(cycle, bet_id, "malformed", err, "critic")
        return
    verdict = "approve" if final.verdict == "approve" else "reject"
    betlog.append(cycle, bet_id, "final_verdict", {**final.model_dump(), "verdict": verdict,
                                                   "critic_verdict": final.verdict}, "critic")


def run_cycle(ledger, betlog, cycle, today=None) -> dict:
    """Returns {"proposed": [bet_ids], "stopped": reason-or-None, "no_bet_reason": str-or-None}."""
    summary = {"proposed": [], "stopped": None, "no_bet_reason": None}
    state = build_state(ledger, betlog, cycle, today)
    try:
        strategist_system = render_strategist(ledger.config)
        resp, err = _ask_parsed(ledger, cycle, "strategist", "strategist", strategist_system, state,
                                StrategistResponse, STRATEGIST_MAX_TOKENS)
        if resp is None:
            betlog.append(cycle, f"c{cycle}-strategist", "malformed", err, "strategist")
            return summary
        if not resp.memos:
            summary["no_bet_reason"] = resp.no_bet_reason
            log.info("cycle %s: no bet proposed: %s", cycle, resp.no_bet_reason)
            return summary
        for i, memo in enumerate(resp.memos, 1):
            bet_id = f"c{cycle}-{i}"
            betlog.append(cycle, bet_id, "proposed", memo.model_dump(), "strategist")
            summary["proposed"].append(bet_id)
            _review_memo(ledger, betlog, cycle, bet_id, memo, state)
    except (CycleCapExceeded, WalletEmpty) as e:
        summary["stopped"] = f"{type(e).__name__}: {e}"
        log.warning("cycle %s stopped early: %s", cycle, summary["stopped"])
    return summary
