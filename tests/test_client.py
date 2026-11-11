"""Tests that spend nothing. They use the live API's free paths and the 402
handshake itself (an unpaid request is never charged).

Run:  .venv/bin/python -m pytest tests/ -v
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blockchainiq_langchain.client import (  # noqa: E402
    BASE_URL,
    BlockchainIQClient,
    BlockchainIQError,
    PaymentRequired,
    _plain_get,
    decode_payment_required,
)

BRIEF_URL = BASE_URL + "/brief"


def test_catalog_is_free_and_lists_brief():
    client = BlockchainIQClient()
    catalog = client.catalog()
    assert catalog.get("x402Version") == 2
    assert catalog.get("network") == "eip155:8453"
    assert catalog.get("asset") == "USDC"
    brief = next(r for r in catalog["data"] if r["id"] == "brief")
    assert brief["price"] == "$0.01"
    assert brief["path"] == "/api/x402/v1/brief"


def test_unpaid_brief_returns_402_with_price():
    status, headers, body = _plain_get(BRIEF_URL)
    assert status == 402
    offer = decode_payment_required(headers["Payment-Required"])
    assert offer["x402Version"] == 2
    accepts = offer["accepts"][0]
    assert accepts["scheme"] == "exact"
    assert accepts["network"] == "eip155:8453"
    assert accepts["amount"] == "10000"  # 6-decimal USDC: $0.01
    assert accepts["asset"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Circle native USDC on Base
    assert json.loads(body)["price"] == "$0.01"


def test_brief_without_key_raises_before_spending():
    # No AGENT_PRIVATE_KEY in the test env: the client must refuse to pay
    # instead of attempting anything.
    os.environ.pop("AGENT_PRIVATE_KEY", None)
    client = BlockchainIQClient()
    try:
        client.brief()
    except BlockchainIQError as err:
        assert "AGENT_PRIVATE_KEY" in str(err)
    else:
        raise AssertionError("expected BlockchainIQError without a key")


def test_payment_required_carries_amount():
    offer = {
        "accepts": [{
            "scheme": "exact", "network": "eip155:8453",
            "amount": "10000", "asset": "0x8335",
            "payTo": "0x617d",
        }]
    }
    exc = PaymentRequired(offer)
    assert exc.amount_usd == 0.01
    assert exc.network == "eip155:8453"


def test_unknown_resource_is_never_charged():
    # A 404 from a mistyped path: the server must not ask for payment.
    # (The 404 body is Vercel's HTML error page, not JSON.)
    status, headers, _body = _plain_get(BASE_URL + "/no-such-resource")
    assert status == 404
    assert "Payment-Required" not in headers


def test_catalog_tool_lists_resources():
    from blockchainiq_langchain.tools import catalog_tool

    text = catalog_tool.invoke({})
    assert "brief" in text
    assert "$0.01" in text
