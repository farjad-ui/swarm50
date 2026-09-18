"""Guardrails checked at stake time. A violation writes a `blocked` event and never raises."""
from decimal import Decimal

from .exceptions import StakeCapExceeded
from .ledger import usd_to_micro


def _pct_of(config, key, base_micro) -> int:
    return int(Decimal(str(config[key])) * base_micro)


def guardrail_violation(ledger, betlog, memo) -> dict | None:
    """First violated rule with its numbers (micro-dollars), or None if the stake is allowed."""
    cfg = ledger.config
    balance = ledger.balance()
    stake = usd_to_micro(memo.stake_usd)
    exposure = betlog.open_exposure_micro()
    base = balance + exposure  # exposure limits are measured against balance plus open exposure
    checks = [
        ("max_stake_pct", stake, _pct_of(cfg, "max_stake_pct", balance)),
        ("max_open_exposure_pct", exposure + stake, _pct_of(cfg, "max_open_exposure_pct", base)),
    ]
    if memo.category == "trading":
        checks.append(("max_trading_exposure_pct", betlog.open_exposure_micro("trading") + stake,
                       _pct_of(cfg, "max_trading_exposure_pct", base)))
    for rule, value, limit in checks:
        if value > limit:
            return {"rule": rule, "pct": cfg[rule], "value_micro": value, "limit_micro": limit,
                    "stake_micro": stake, "balance_micro": balance, "open_exposure_micro": exposure}
    return None


def try_stake(ledger, betlog, cycle, bet_id, memo) -> bool:
    """Stake the bet if every guardrail passes. Returns True if staked, False if a `blocked` event was written."""
    violation = guardrail_violation(ledger, betlog, memo)
    if violation is None:
        try:
            ledger.stake_bet(cycle, bet_id, memo.stake_usd, note=memo.title)
        except StakeCapExceeded as e:  # ledger's own floor; unreachable if config is consistent
            violation = {"rule": "ledger.max_stake_pct", "error": str(e), "stake_micro": usd_to_micro(memo.stake_usd)}
    if violation:
        betlog.append(cycle, bet_id, "blocked", {**violation, "memo": memo.model_dump()}, "cfo")
        return False
    betlog.append(cycle, bet_id, "staked", {"stake_usd": memo.stake_usd, "category": memo.category,
                                            "title": memo.title}, "cfo")
    return True
