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
    # Gmail OAuth — one Google Cloud project shared across all connected Gmail accounts
    "google_client_id": "",
    "google_client_secret": "",
    # List of connected email accounts:
    # [{"email": "user@gmail.com", "credentials": {...OAuth token dict...}, "added": "iso-date"}]
    "email_accounts": [],
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


def is_google_configured(config: dict = None) -> bool:
    """Check if Google OAuth credentials are set."""
    if config is None:
        config = load_config()
    return bool(config.get("google_client_id")) and bool(config.get("google_client_secret"))


def add_email_account(config: dict, email: str, credentials: dict) -> dict:
    """Add (or update) a connected email account."""
    from datetime import datetime
    accounts = config.get("email_accounts", [])
    # Remove any existing entry for this email
    accounts = [a for a in accounts if a.get("email") != email]
    accounts.append({
        "email": email,
        "credentials": credentials,
        "added": datetime.now().isoformat(),
    })
    config["email_accounts"] = accounts
    save_config(config)
    return config


def remove_email_account(config: dict, email: str) -> dict:
    """Remove a connected email account by address."""
    config["email_accounts"] = [
        a for a in config.get("email_accounts", []) if a.get("email") != email
    ]
    save_config(config)
    return config
