"""The ONLY module that touches the Anthropic SDK or the Claude Code CLI."""
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

from .exceptions import BackendError

load_dotenv()

OVERHEAD_TOKENS = 50          # fixed per-request framing overhead added to every input estimate
CLI_TIMEOUT_S = 180
MINIMAL_SYSTEM = "You are a helpful assistant."


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    web_search_requests: int = 0


@dataclass
class Result:
    """Backend-agnostic response. Callers never learn which backend ran."""
    text: str
    usage: Usage
    model: str                       # model the backend reports it used
    backend: str
    reported_cost_usd: float | None  # backend's own cost estimate (CLI only); ours is in the ledger
    raw: object = None
    note: str | None = None          # backend-specific comparison data, stored on the ledger row


# ---- estimation (shared by both backends) ----

def _text(messages) -> str:
    parts = []
    for m in messages:
        c = m.get("content", "")
        if isinstance(c, str):
            parts.append(c)
        else:  # list of content blocks
            parts.extend(b.get("text", "") for b in c if isinstance(b, dict))
    return "".join(parts)


def _tokens(s: str) -> int:
    # ponytail: len/3 is a conservative proxy for the current tokenizer; swap for
    # client.messages.count_tokens if estimates prove too loose or too tight.
    return -(-len(s) // 3)


def input_overhead(config, backend) -> int:
    """Fixed per-request input tokens: 50 for the API; the CLI adds its own configured overhead on top."""
    extra = int(config.get("cli_input_overhead_tokens", 0)) if backend == "claude_cli" else 0
    return OVERHEAD_TOKENS + extra


def estimate_input_tokens(messages, system, overhead=OVERHEAD_TOKENS) -> int:
    return _tokens(_text(messages)) + _tokens(system or "") + overhead


def worst_case_cost(ledger, model, messages, system, max_tokens, cache=False, backend="api") -> int:
    """Micro-dollars. System prompt is priced at the cache-write rate when cache=True."""
    sys_tokens = _tokens(system or "")
    msg_tokens = _tokens(_text(messages)) + input_overhead(ledger.config, backend)
    if cache and system:
        return ledger.cost_micro(model, msg_tokens, max_tokens, cache_write_tokens=sys_tokens)
    return ledger.cost_micro(model, msg_tokens + sys_tokens, max_tokens)


# ---- usage parsing (SDK objects or CLI dicts) ----

def _get(obj, name):
    if obj is None:
        return None
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _int(obj, name) -> int:
    return int(_get(obj, name) or 0)


def _usage_from(u) -> Usage:
    return Usage(
        input_tokens=_int(u, "input_tokens"),
        output_tokens=_int(u, "output_tokens"),
        cache_creation_input_tokens=_int(u, "cache_creation_input_tokens"),
        cache_read_input_tokens=_int(u, "cache_read_input_tokens"),
        web_search_requests=_int(_get(u, "server_tool_use"), "web_search_requests"),
    )


# ---- backend: Anthropic Messages API ----

def _call_api(model, messages, system, max_tokens, cache) -> Result:
    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = ([{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                            if cache else system)
    resp = anthropic.Anthropic().messages.create(**kwargs)
    text = "".join(b.text for b in (getattr(resp, "content", None) or []) if getattr(b, "type", None) == "text")
    return Result(text, _usage_from(resp.usage), getattr(resp, "model", model), "api", None, resp)


# ---- backend: Claude Code CLI (subscription) ----

def _cli_exe() -> str:
    exe = shutil.which("claude")
    if not exe:
        raise BackendError("claude CLI not found on PATH")
    if exe.lower().endswith((".cmd", ".bat")):
        # npm shim re-parses args through cmd.exe (mangles the empty --tools ""); call the native binary.
        native = os.path.join(os.path.dirname(exe), "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe")
        if os.path.exists(native):
            exe = native
    return exe


def cli_argv(model, system=None) -> list[str]:
    """Exact argv used for a CLI call. --bare would also isolate the run but locks auth to
    ANTHROPIC_API_KEY, defeating subscription use, so isolation is done flag by flag."""
    return [_cli_exe(), "-p", "--output-format", "json",
            "--model", model,
            "--system-prompt", system or MINIMAL_SYSTEM,   # REPLACES the default Claude Code prompt
            "--tools", "",                                 # no tools -> a single turn is all that can happen
            "--no-session-persistence",
            "--permission-prompts", "none",
            "--setting-sources", "",                       # no user/project settings (hooks, permission rules)
            "--strict-mcp-config"]                         # no MCP servers


def _call_cli(model, messages, system, max_tokens, cache) -> Result:
    # NOTE: max_tokens is NOT enforceable on this backend (the CLI has no such flag); the pre-call
    # budget check still reserves for it. cache=True is a no-op: the CLI manages its own caching.
    # ponytail: the CLI takes a single prompt, so multi-message history is flattened with role labels.
    if len(messages) == 1 and isinstance(messages[0].get("content"), str):
        prompt = messages[0]["content"]
    else:
        prompt = "\n\n".join(f"{m['role']}: {_text([m])}" for m in messages)

    cmd = cli_argv(model, system)
    env = {**os.environ, "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=CLI_TIMEOUT_S, env=env, cwd=tempfile.gettempdir())
    except subprocess.TimeoutExpired as e:
        raise BackendError(f"claude CLI timed out after {CLI_TIMEOUT_S}s") from e
    if proc.returncode != 0:
        raise BackendError(f"claude CLI exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:2000]}")
    try:
        data = json.loads(proc.stdout)
    except ValueError as e:
        raise BackendError(f"claude CLI returned non-JSON output: {proc.stdout[:500]!r}") from e
    if not isinstance(data, dict):
        raise BackendError(f"claude CLI returned unexpected JSON: {proc.stdout[:500]!r}")
    if data.get("is_error"):
        raise BackendError(f"claude CLI error ({data.get('subtype')}): {data.get('result') or data.get('errors')}")

    model_usage = data.get("modelUsage") or {}
    used = next((k for k, v in model_usage.items()
                 if k == model or (isinstance(v, dict) and v.get("canonicalModel") == model)), None)
    if used is None:
        raise BackendError(f"requested model {model!r} was not the one that ran; "
                           f"modelUsage keys: {list(model_usage)}")
    cost = data.get("total_cost_usd")
    note = f"cli_cost_usd={cost} " + (f"cli_models={','.join(model_usage)}" if len(model_usage) > 1
                                       else f"cli_model={used}")
    return Result(data.get("result", ""), _usage_from(data.get("usage")), used, "claude_cli", cost, data, note)


BACKENDS = {"api": _call_api, "claude_cli": _call_cli}


def metered_call(ledger, cycle, agent, role, messages, system=None, max_tokens=1024, cache=False) -> Result:
    model = ledger.config["roles"][role]
    backend = ledger.config.get("backend", "api")
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; expected one of {sorted(BACKENDS)}")

    # Identical for both backends, and raises BEFORE any SDK call or subprocess is spawned.
    ledger.assert_can_spend(cycle, worst_case_cost(ledger, model, messages, system, max_tokens, cache, backend))

    result = BACKENDS[backend](model, messages, system, max_tokens, cache)

    u = result.usage
    ledger.record_token_usage(cycle, agent, model, u.input_tokens, u.output_tokens,
                              u.cache_creation_input_tokens, u.cache_read_input_tokens,
                              u.web_search_requests, backend=backend, note=result.note)
    return result
