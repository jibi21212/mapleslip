"""Configuration management for TaxKing AI."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_FILE = DATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "plaid_client_id": "",
    "plaid_secret": "",
    "plaid_env": "development",  # "sandbox" for testing, "development" for real banks (free)
    "province": "ON",  # Canadian province code for tax calculations
    "watch_folder": "",  # Folder to auto-import PDFs from (empty = disabled)
    "watch_folder_enabled": False,
}


def load_config() -> dict:
    """Load config from disk, merging with defaults."""
    config = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            saved = json.load(f)
        config.update(saved)
    return config


def save_config(config: dict):
    """Save config to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_plaid_configured(config: dict = None) -> bool:
    """Check if Plaid credentials are set."""
    if config is None:
        config = load_config()
    return bool(config.get("plaid_client_id")) and bool(config.get("plaid_secret"))
