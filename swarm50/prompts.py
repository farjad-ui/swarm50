"""Loads prompts/*.md and fills their $placeholders with string.Template. No prompt text lives in .py files."""
from string import Template

from .config import ROOT
from .schemas import memo_schema_text

PROMPTS_DIR = ROOT / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _pct(config, key) -> str:
    """0.35 -> '35'"""
    return f"{float(config[key]) * 100:g}"


def render_objective(config) -> str:
    arm = config.get("reward_arm", "linear")
    tmpl = Template(load_prompt(f"objective_{arm}"))
    return tmpl.substitute(total_days=config["total_days"],
                           starting_balance=config["starting_balance_usd"])


def render_strategist(config) -> str:
    tmpl = Template(load_prompt("strategist"))
    return tmpl.substitute(
        total_days=config["total_days"],
        objective=render_objective(config),
        max_stake_pct=_pct(config, "max_stake_pct"),
        max_open_exposure_pct=_pct(config, "max_open_exposure_pct"),
        max_trading_exposure_pct=_pct(config, "max_trading_exposure_pct"),
        memo_schema=memo_schema_text(),
    )


def render_rebuttal(config) -> str:
    tmpl = Template(load_prompt("rebuttal"))
    return tmpl.substitute(memo_schema=memo_schema_text())


def render_critic(state_block: str) -> str:
    tmpl = Template(load_prompt("critic"))
    return tmpl.substitute(state_block=state_block)


def render_critic_final(state_block: str) -> str:
    return render_critic(state_block) + "\n\n" + load_prompt("critic_final")


def render_worker() -> str:
    return load_prompt("worker")
