"""Plaid API integration for bank account connections."""

import json
import threading
import webbrowser
from datetime import datetime, timedelta
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.accounts_get_request import AccountsGetRequest

from config import load_config, is_plaid_configured

LINK_HTML_PATH = Path(__file__).parent / "plaid_link.html"

# ── Plaid Client ────────────────────────────────────────────────

ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "development": "https://development.plaid.com",
    "production": plaid.Environment.Production,
}


def _get_client(config: dict = None) -> plaid_api.PlaidApi:
    """Create a Plaid API client from config."""
    if config is None:
        config = load_config()

    env = config.get("plaid_env", "development")
    configuration = plaid.Configuration(
        host=ENV_MAP.get(env, plaid.Environment.Development),
        api_key={
            "clientId": config["plaid_client_id"],
            "secret": config["plaid_secret"],
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


# ── Link Token ──────────────────────────────────────────────────

def create_link_token(config: dict = None) -> str:
    """Create a Plaid Link token to start the connection flow."""
    client = _get_client(config)
    request = LinkTokenCreateRequest(
        products=[Products("transactions")],
        client_name="TaxKing AI",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id="taxking-local-user"),
    )
    response = client.link_token_create(request)
    return response.link_token


# ── Token Exchange ──────────────────────────────────────────────

def exchange_public_token(public_token: str, config: dict = None) -> dict:
    """Exchange a public token from Plaid Link for an access token."""
    client = _get_client(config)
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return {
        "access_token": response.access_token,
        "item_id": response.item_id,
    }


# ── Accounts ────────────────────────────────────────────────────

def get_accounts(access_token: str, config: dict = None) -> list[dict]:
    """Fetch accounts for a connected item."""
    client = _get_client(config)
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)

    accounts = []
    for acct in response.accounts:
        accounts.append({
            "account_id": acct.account_id,
            "name": acct.name,
            "official_name": acct.official_name,
            "type": str(acct.type),
            "subtype": str(acct.subtype) if acct.subtype else "",
            "mask": acct.mask,
            "balance_current": float(acct.balances.current) if acct.balances.current else 0.0,
            "balance_available": float(acct.balances.available) if acct.balances.available else None,
        })
    return accounts


# ── Transactions ────────────────────────────────────────────────

def get_transactions(access_token: str, start_date: str = None,
                     end_date: str = None, config: dict = None) -> list[dict]:
    """Fetch transactions for a connected item.

    Dates should be YYYY-MM-DD strings. Defaults to the current tax year.
    """
    client = _get_client(config)

    if not start_date:
        year = datetime.now().year - 1
        start_date = f"{year}-01-01"
    if not end_date:
        year = datetime.now().year - 1
        end_date = f"{year}-12-31"

    from datetime import date as dt_date
    start = dt_date.fromisoformat(start_date)
    end = dt_date.fromisoformat(end_date)

    all_transactions = []
    offset = 0
    total = None

    while total is None or offset < total:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start,
            end_date=end,
            options=TransactionsGetRequestOptions(
                count=100,
                offset=offset,
            ),
        )
        response = client.transactions_get(request)
        total = response.total_transactions

        for txn in response.transactions:
            all_transactions.append({
                "transaction_id": txn.transaction_id,
                "account_id": txn.account_id,
                "date": str(txn.date),
                "name": txn.name,
                "merchant_name": txn.merchant_name,
                "amount": float(txn.amount),
                "category": txn.category if txn.category else [],
                "pending": txn.pending,
            })
        offset += len(response.transactions)

    return all_transactions


# ── Plaid Link Local Server ─────────────────────────────────────

class PlaidLinkHandler(SimpleHTTPRequestHandler):
    """Serves the Plaid Link HTML page and handles the callback."""

    def __init__(self, *args, link_token="", callback=None, **kwargs):
        self.link_token = link_token
        self.callback = callback
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            # Serve the Plaid Link HTML with the link token injected
            html = LINK_HTML_PATH.read_text()
            html = html.replace("{{LINK_TOKEN}}", self.link_token)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        elif parsed.path == "/callback":
            params = parse_qs(parsed.query)
            public_token = params.get("public_token", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="background:#1a1a2e;color:white;font-family:sans-serif;
                display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
                <div style="text-align:center">
                <h1>Bank Connected!</h1>
                <p>You can close this tab and return to TaxKing AI.</p>
                </div></body></html>
            """)

            if public_token and self.callback:
                self.callback(public_token)

            # Shut down the server after handling
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # Suppress console output


def start_plaid_link(link_token: str, callback) -> threading.Thread:
    """Start a local server, open the browser for Plaid Link, and return the thread.

    The callback receives the public_token string when the user completes Link.
    """
    handler = partial(PlaidLinkHandler, link_token=link_token, callback=callback)
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    webbrowser.open(f"http://127.0.0.1:{port}/")
    return thread
