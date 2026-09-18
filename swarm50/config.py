from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "state" / "ledger.db"


def load_config(path=CONFIG_PATH):
    with open(path) as f:
        return yaml.safe_load(f)
