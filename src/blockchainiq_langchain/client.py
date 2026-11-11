"""HTTP client for the Blockchain IQ x402 API (no account, no API key).

Flow (x402 v2, Base eip155:8453, USDC):
  1. Plain GET. Free resources answer 200 at once.
  2. Paid resources answer HTTP 402 with a base64 PAYMENT-REQUIRED header
     naming price, asset, network and payTo.
  3. The client signs a USDC authorization locally and retries; the server
     settles through the facilitator and answers 200 with the data plus a
     PAYMENT-RESPONSE header carrying the transaction hash.
  4. A 404 or any error response is never charged.

Only stdlib is used here. The signing step runs in scripts/x402_call.mjs,
which uses the official @x402/fetch client (the same code Blockchain IQ runs
against production), because the EIP-3009 authorization must be built exactly
as the facilitator expects.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request

BASE_URL = "https://www.blockchainiq.co/api/x402/v1"
USDC_DECIMALS = 6
# The dearest single call in the catalog is $0.50; the default cap refuses
# anything above $0.60 whatever a server asks for.
DEFAULT_MAX_USD = 0.60


class PaymentRequired(Exception):
    """Raised when a resource needs payment. Carries the decoded 402 offer."""

    def __init__(self, offer: dict):
        self.offer = offer
        accepts = (offer.get("accepts") or [{}])[0]
        amount = int(accepts.get("amount", "0") or 0)
        self.amount_usd = amount / 10**USDC_DECIMALS
        self.network = accepts.get("network")
        self.asset = accepts.get("asset")
        self.pay_to = accepts.get("payTo")
        super().__init__(
            f"payment required: ${self.amount_usd:.2f} in USDC on "
            f"{self.network} to {self.pay_to}"
        )


class BlockchainIQError(Exception):
    pass


def _plain_get(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": "blockchainiq-langchain/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()


def decode_payment_required(header_value: str) -> dict:
    """Decode the base64 PAYMENT-REQUIRED header from a 402 response."""
    padded = header_value + "=" * (-len(header_value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


class BlockchainIQClient:
    """Minimal client. `paid` calls need AGENT_PRIVATE_KEY in the env."""

    def __init__(self, base_url: str = BASE_URL, max_usd: float = DEFAULT_MAX_USD,
                 node_script: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.max_usd = max_usd
        here = os.path.dirname(os.path.abspath(__file__))
        self.node_script = node_script or os.path.join(
            here, "..", "scripts", "x402_call.mjs")

    # -- free resources -------------------------------------------------
    def get_free(self, path: str) -> dict:
        """GET a free resource (catalog, sample, free indexes). No payment."""
        status, _headers, body = _plain_get(self.base_url + path)
        data = json.loads(body.decode("utf-8"))
        if status == 200:
            return data
        raise BlockchainIQError(f"GET {path} returned {status}: {data}")

    def catalog(self) -> dict:
        return self.get_free("")

    # -- paid resources --------------------------------------------------
    def get_paid(self, path: str) -> dict:
        """GET a paid resource, paying via x402 when the server asks (402).

        Returns {"data": ..., "payment": {...}} where payment is the decoded
        PAYMENT-RESPONSE header (payer, network, transaction hash).
        Raises PaymentRequired when the price is above max_usd, and
        BlockchainIQError when the server answers an error (never charged).
        """
        url = self.base_url + path
        status, headers, body = _plain_get(url)
        if status == 200:
            return {"data": json.loads(body.decode("utf-8")).get("data"), "payment": None}
        if status != 402:
            raise BlockchainIQError(
                f"GET {path} returned {status}: {body.decode('utf-8')[:300]}")
        offer = decode_payment_required(headers.get("Payment-Required", ""))
        needed = PaymentRequired(offer)
        if needed.amount_usd > self.max_usd:
            raise needed
        return self._pay(url, needed.amount_usd)

    def _pay(self, url: str, amount_usd: float) -> dict:
        key = os.environ.get("AGENT_PRIVATE_KEY")
        if not key:
            raise BlockchainIQError(
                "payment needed ($%.2f) but AGENT_PRIVATE_KEY is not set; "
                "set it to a Base wallet holding a little USDC" % amount_usd)
        proc = subprocess.run(
            ["node", self.node_script, url, str(self.max_usd)],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "AGENT_PRIVATE_KEY": key},
        )
        out = (proc.stdout or "").strip()
        if proc.returncode != 0:
            detail = out or proc.stderr.strip()[:500]
            raise BlockchainIQError(f"paid call failed: {detail}")
        result = json.loads(out)
        if result.get("status") != 200:
            raise BlockchainIQError(
                f"paid call returned {result.get('status')}: {result.get('error')}")
        return {"data": result["data"], "payment": result.get("payment")}

    # -- the two agent-shaped resources ----------------------------------
    def brief(self) -> dict:
        """Market brief: BTC/ETH/SOL/XRP prices, moves, next-48h events, flags.

        Parameter-free, $0.01 per call — the cheapest paid call in the catalog.
        """
        return self.get_paid("/brief")

    def event_risk(self, days: int = 7) -> dict:
        """Scheduled market-moving events for the next N days (default 7). $0.05."""
        if not 1 <= days <= 90:
            raise ValueError("days must be 1-90")
        return self.get_paid(f"/event-risk?days={days}")
