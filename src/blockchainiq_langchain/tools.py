"""LangChain tools for the Blockchain IQ x402 API.

Three tools:
  - blockchain_iq_brief: the $0.01 market brief (paid, x402 on Base USDC).
  - blockchain_iq_event_risk: scheduled events, $0.05 (paid).
  - blockchain_iq_catalog: the free resource catalog (no payment).

Paid tools only spend when the server answers 402, and never more than
max_usd per call (default $0.60; the dearest catalog call is $0.50).
The wallet key comes from the AGENT_PRIVATE_KEY env var only — never from
a file committed to the repo and never from a tool argument.
"""
from __future__ import annotations

from langchain_core.tools import tool

from .client import BlockchainIQClient


def _client() -> BlockchainIQClient:
    return BlockchainIQClient()


@tool("blockchain_iq_brief")
def brief_tool() -> str:
    """Market brief: BTC, ETH, SOL and XRP prices with 24h/7d/30d moves and
    rank, scheduled macro and crypto events in the next 48 hours, and short
    risk flags. Parameter-free. Costs $0.01 in USDC on Base per call (x402);
    returns the brief plus the payment settlement proof (transaction hash)."""
    result = _client().brief()
    return _format(result, "Market brief")


@tool("blockchain_iq_event_risk")
def event_risk_tool(days: int = 7) -> str:
    """Scheduled market-moving events for the next N days (default 7, up to
    90): US data releases with times, FOMC/ECB/BoJ decisions, Treasury
    auctions and crypto events. Costs $0.05 in USDC on Base per call (x402);
    returns the events plus the payment settlement proof."""
    result = _client().event_risk(days)
    return _format(result, "Event risk")


@tool("blockchain_iq_catalog")
def catalog_tool() -> str:
    """Free catalog of everything the Blockchain IQ x402 API sells: every
    resource, its path, price and response shape. No payment, no key."""
    catalog = _client().catalog()
    lines = ["Blockchain IQ x402 catalog (free):"]
    for item in catalog.get("data", []):
        lines.append(
            f"- {item['id']}: {item.get('method', 'GET')} {item['path']} "
            f"— {item.get('price')} — {item.get('title')}")
    return "\n".join(lines)


def _format(result: dict, title: str) -> str:
    import json

    data = result["data"]
    payment = result.get("payment")
    text = f"{title} (Blockchain IQ, x402 paid call):\n{json.dumps(data, indent=2)}"
    if payment:
        text += (
            f"\n\nPayment settled: {payment.get('amount', '')} "
            f"{payment.get('asset', 'USDC')} on {payment.get('network', '')}, "
            f"payer {payment.get('payer', '')}, "
            f"tx {payment.get('txHash', payment.get('transactionHash', ''))}"
        )
    return text


__all__ = ["brief_tool", "event_risk_tool", "catalog_tool"]
