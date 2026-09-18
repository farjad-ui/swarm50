import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from swarm50.exceptions import BackendError, CycleCapExceeded
from swarm50.metered import cli_argv, estimate_input_tokens, input_overhead, metered_call, worst_case_cost

MSGS = [{"role": "user", "content": "hi"}]


def fake_response(**usage):
    return SimpleNamespace(usage=SimpleNamespace(**usage), model="big-2026",
                           content=[SimpleNamespace(type="text", text="OK")])


# ---- estimation ----

def test_estimate_is_len_over_three_plus_overhead():
    msgs = [{"role": "user", "content": "a" * 30},
            {"role": "user", "content": [{"type": "text", "text": "b" * 31}]}]
    # messages ceil(61/3)=21 and system ceil(2/3)=1 are rounded separately (they can carry
    # different rates), plus the fixed 50-token overhead
    assert estimate_input_tokens(msgs, "c" * 2) == 21 + 1 + 50


def test_cache_flag_prices_system_at_cache_write_rate(ledger):
    system = "s" * 300  # 100 tokens
    msgs = [{"role": "user", "content": ""}]  # 0 tokens + 50 overhead
    # uncached: 150 input @3 + 100 output @15 = 450 + 1500
    assert worst_case_cost(ledger, "big", msgs, system, 100, cache=False) == 1950
    # cached:   50 input @3 + 100 cache-write @3.75 + 100 output @15 = 150 + 375 + 1500
    assert worst_case_cost(ledger, "big", msgs, system, 100, cache=True) == 2025


def test_cli_backend_adds_configured_input_overhead(ledger):
    system, msgs = "s" * 300, [{"role": "user", "content": ""}]
    assert input_overhead(ledger.config, "api") == 50
    assert input_overhead(ledger.config, "claude_cli") == 650
    # api: 1950 (above); cli: + 600 extra input tokens @3 = +1800
    assert worst_case_cost(ledger, "big", msgs, system, 100, backend="claude_cli") == 1950 + 1800
    assert estimate_input_tokens(msgs, system, input_overhead(ledger.config, "claude_cli")) == 100 + 650


# ---- api backend ----

def test_refuses_before_api_call_when_over_budget(ledger):
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        with pytest.raises(CycleCapExceeded):
            # 100k output tokens @ $15/MTok = $1.50 worst case > $0.75 cap
            metered_call(ledger, 1, "a", "worker", MSGS, max_tokens=100_000)
        cls.assert_not_called()
    assert ledger.cycle_spend(1) == 0


def test_debits_actual_usage_not_estimate(ledger):
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        create = cls.return_value.messages.create
        create.return_value = fake_response(input_tokens=1000, output_tokens=500)
        resp = metered_call(ledger, 1, "a", "worker", MSGS, system="sys", max_tokens=4000)
    assert resp.raw is create.return_value
    assert (resp.text, resp.model, resp.backend, resp.reported_cost_usd) == ("OK", "big-2026", "api", None)
    create.assert_called_once()
    assert create.call_args.kwargs["model"] == "big"
    assert create.call_args.kwargs["system"] == "sys"
    assert ledger.cycle_spend(1) == 10_500  # actual, not the 4000-token worst case
    assert ledger.history(1)[0]["backend"] == "api"


def test_all_usage_fields_priced(ledger):
    usage = dict(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=2000,
                 cache_read_input_tokens=4000, server_tool_use=SimpleNamespace(web_search_requests=3))
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = fake_response(**usage)
        metered_call(ledger, 1, "a", "worker", MSGS)
    assert ledger.cycle_spend(1) == 49_200
    row = ledger.history(1)[0]
    assert (row["cache_write_tokens"], row["cache_read_tokens"], row["web_search_requests"]) == (2000, 4000, 3)


def test_missing_usage_fields_default_to_zero(ledger):
    # SDK returns None for cache fields on some responses and omits server_tool_use entirely
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = fake_response(
            input_tokens=1000, output_tokens=500, cache_creation_input_tokens=None,
            cache_read_input_tokens=None, server_tool_use=None)
        metered_call(ledger, 1, "a", "worker", MSGS)
    assert ledger.cycle_spend(1) == 10_500
    row = ledger.history(1)[0]
    assert (row["cache_write_tokens"], row["cache_read_tokens"], row["web_search_requests"]) == (0, 0, 0)


def test_cache_flag_adds_cache_control_to_system(ledger):
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = fake_response(input_tokens=1, output_tokens=1)
        metered_call(ledger, 1, "a", "worker", MSGS, system="sys", cache=True)
        system = cls.return_value.messages.create.call_args.kwargs["system"]
    assert system == [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]


# ---- claude_cli backend ----

CLI_JSON = {
    "type": "result", "subtype": "success", "is_error": False, "result": "OK",
    "session_id": "abc", "num_turns": 1, "stop_reason": "end_turn", "total_cost_usd": 0.0123,
    "usage": {"input_tokens": 1000, "output_tokens": 500, "cache_creation_input_tokens": 2000,
              "cache_read_input_tokens": 4000, "server_tool_use": {"web_search_requests": 3}},
    "modelUsage": {"big": {"inputTokens": 1000, "outputTokens": 500, "costUSD": 0.0123}},
}


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["claude"], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def cli_ledger(make_ledger):
    return make_ledger(backend="claude_cli")


@pytest.fixture
def run():
    with patch("swarm50.metered.shutil.which", return_value="claude"), \
         patch("swarm50.metered.subprocess.run") as run:
        yield run


def test_cli_parses_and_shadow_prices(cli_ledger, run):
    run.return_value = completed(json.dumps(CLI_JSON))
    r = metered_call(cli_ledger, 1, "a", "worker", MSGS, system="sys")

    assert (r.text, r.model, r.backend, r.reported_cost_usd) == ("OK", "big", "claude_cli", 0.0123)
    assert r.usage.cache_read_input_tokens == 4000 and r.usage.web_search_requests == 3
    assert cli_ledger.cycle_spend(1) == 49_200  # OUR rates, not the CLI's $0.0123
    row = cli_ledger.history(1)[0]
    assert row["backend"] == "claude_cli"
    assert row["model"] == "big"
    assert row["note"] == "cli_cost_usd=0.0123 cli_model=big"

    args, kw = run.call_args
    cmd = args[0]
    assert cmd == cli_argv("big", "sys")             # what the smoke test prints is what ran
    assert kw["input"] == "hi"                       # prompt via stdin, not argv
    assert kw["encoding"] == "utf-8" and kw["timeout"] > 0
    assert cmd[1:4] == ["-p", "--output-format", "json"]
    for flag, value in (("--model", "big"), ("--system-prompt", "sys"), ("--tools", ""),
                        ("--permission-prompts", "none"), ("--setting-sources", "")):
        assert cmd[cmd.index(flag) + 1] == value
    assert "--no-session-persistence" in cmd and "--bare" not in cmd


def test_cli_precheck_refuses_before_spawn(cli_ledger, run):
    with pytest.raises(CycleCapExceeded):
        metered_call(cli_ledger, 1, "a", "worker", MSGS, max_tokens=100_000)
    run.assert_not_called()
    assert cli_ledger.cycle_spend(1) == 0


def test_cli_precheck_uses_cli_overhead(ledger, cli_ledger, run):
    # 49,900 output @15 = 748,500; api overhead 51 input @3 = 153 -> 748,653 fits the 750,000 cap;
    # cli adds 600 @3 = 1,800 -> 750,453, over the cap. Only the CLI backend refuses.
    with pytest.raises(CycleCapExceeded):
        metered_call(cli_ledger, 1, "a", "worker", MSGS, max_tokens=49_900)
    run.assert_not_called()
    with patch("swarm50.metered.anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = fake_response(input_tokens=1, output_tokens=1)
        metered_call(ledger, 1, "a", "worker", MSGS, max_tokens=49_900)
        cls.return_value.messages.create.assert_called_once()


def test_cli_matches_requested_model_by_canonical_name(cli_ledger, run):
    run.return_value = completed(json.dumps({**CLI_JSON, "modelUsage": {
        "big-20260101": {"costUSD": 0.01, "canonicalModel": "big"}}}))
    r = metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert r.model == "big-20260101"
    assert cli_ledger.history(1)[0]["note"].endswith("cli_model=big-20260101")


def test_cli_wrong_model_raises_and_lists_keys(cli_ledger, run):
    run.return_value = completed(json.dumps({**CLI_JSON, "modelUsage": {"other-model": {"costUSD": 0.01}}}))
    with pytest.raises(BackendError, match=r"requested model 'big' was not the one that ran.*\['other-model'\]"):
        metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert cli_ledger.cycle_spend(1) == 0
    run.return_value = completed(json.dumps({**CLI_JSON, "modelUsage": {}}))
    with pytest.raises(BackendError, match=r"modelUsage keys: \[\]"):
        metered_call(cli_ledger, 1, "a", "worker", MSGS)


def test_cli_nonzero_exit_raises_without_debit(cli_ledger, run):
    run.return_value = completed("", returncode=1, stderr="Not logged in")
    with pytest.raises(BackendError, match="exited 1.*Not logged in"):
        metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert cli_ledger.cycle_spend(1) == 0


def test_cli_malformed_json_raises_without_debit(cli_ledger, run):
    run.return_value = completed("this is not json")
    with pytest.raises(BackendError, match="non-JSON"):
        metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert cli_ledger.cycle_spend(1) == 0


def test_cli_error_result_raises_without_debit(cli_ledger, run):
    run.return_value = completed(json.dumps({**CLI_JSON, "is_error": True, "subtype": "error_during_execution",
                                             "result": "Invalid API key"}))
    with pytest.raises(BackendError, match="Invalid API key"):
        metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert cli_ledger.cycle_spend(1) == 0


def test_cli_multiple_models_all_recorded_in_note(cli_ledger, run):
    run.return_value = completed(json.dumps({**CLI_JSON, "modelUsage": {
        "small-2026": {"costUSD": 0.0023}, "big": {"costUSD": 0.01}}}))
    r = metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert r.model == "big"  # the requested one, not the first key
    assert cli_ledger.history(1)[0]["note"] == "cli_cost_usd=0.0123 cli_models=small-2026,big"


def test_cli_missing_usage_fields_default_to_zero(cli_ledger, run):
    run.return_value = completed(json.dumps({**CLI_JSON, "usage": {"input_tokens": 1000, "output_tokens": 500}}))
    r = metered_call(cli_ledger, 1, "a", "worker", MSGS)
    assert cli_ledger.cycle_spend(1) == 10_500
    assert r.usage.cache_read_input_tokens == 0 and r.usage.web_search_requests == 0
