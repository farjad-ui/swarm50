"""Human task lifecycle. No new table: a task is derived by folding `human_task_requested` /
`human_task_done` bet_events, keyed by task_id (bet_events is already append-only)."""
from datetime import date


def all_tasks(betlog) -> dict:
    """task_id -> {task_id, bet_id, cycle, description, requested_ts, done, done_note}."""
    out = {}
    for e in betlog.events():
        if e["event_type"] == "human_task_requested":
            tid = e["payload"]["task_id"]
            out[tid] = {"task_id": tid, "bet_id": e["bet_id"], "cycle": e["cycle"],
                       "description": e["payload"]["description"], "requested_ts": e["ts"],
                       "done": False, "done_note": None}
        elif e["event_type"] == "human_task_done":
            tid = e["payload"]["task_id"]
            if tid in out:
                out[tid]["done"] = True
                out[tid]["done_note"] = e["payload"].get("note")
    return out


def open_tasks(betlog) -> dict:
    return {k: v for k, v in all_tasks(betlog).items() if not v["done"]}


def age_days(task, today=None) -> int:
    today = today or date.today()
    return (today - date.fromisoformat(task["requested_ts"][:10])).days


def request_tasks(betlog, cycle, bet_id, actions):
    """Writes one human_task_requested event per action in `actions` (a bet's human_actions_required)."""
    existing = len([t for t in all_tasks(betlog).values() if t["bet_id"] == bet_id])
    task_ids = []
    for i, description in enumerate(actions, existing + 1):
        task_id = f"{bet_id}-t{i}"
        betlog.append(cycle, bet_id, "human_task_requested",
                     {"task_id": task_id, "description": description}, "cfo")
        task_ids.append(task_id)
    return task_ids


def mark_done(betlog, task_id, note=None):
    tasks = all_tasks(betlog)
    task = tasks.get(task_id)
    if task is None:
        raise KeyError(f"unknown task {task_id}")
    betlog.append(task["cycle"], task["bet_id"], "human_task_done", {"task_id": task_id, "note": note}, "human")
