#!/usr/bin/env python3
"""Make ONE real paid call to the Blockchain IQ x402 API and save the proof.

Runs the $0.01 market brief through the LangChain tool path and writes
proof/proof-of-payment.json with the data summary and the settlement proof
(payer, network, transaction hash) from the PAYMENT-RESPONSE header.

Requires AGENT_PRIVATE_KEY in the env: a Base wallet holding a little USDC
($0.01 + nothing else; settlement is gasless for the payer). The key is
never written to disk by this script. Run it exactly once for the bounty
claim — re-running spends another $0.01 per call.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blockchainiq_langchain import BlockchainIQClient  # noqa: E402

PROOF_PATH = os.path.join(os.path.dirname(__file__), "..", "proof", "proof-of-payment.json")


def main() -> int:
    if not os.environ.get("AGENT_PRIVATE_KEY"):
        print("AGENT_PRIVATE_KEY is not set. Nothing was spent.", file=sys.stderr)
        return 2
    client = BlockchainIQClient()
    result = client.brief()
    proof = {
        "resource": "brief",
        "url": "https://www.blockchainiq.co/api/x402/v1/brief",
        "price_usd": 0.01,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "payment": result.get("payment"),
        "data_summary": {
            "asOf": (result["data"] or {}).get("asOf"),
            "coins": [
                {"symbol": c.get("symbol"), "price": c.get("price")}
                for c in (result["data"] or {}).get("coins", [])
            ],
            "flagCount": (result["data"] or {}).get("flagCount"),
            "eventCount": (result["data"] or {}).get("eventCount"),
        },
    }
    os.makedirs(os.path.dirname(PROOF_PATH), exist_ok=True)
    with open(PROOF_PATH, "w") as f:
        json.dump(proof, f, indent=2)
    print(json.dumps(proof, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
