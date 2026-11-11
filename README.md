# Blockchain IQ x402 API as LangChain tools

LangChain tools for the [Blockchain IQ](https://www.blockchainiq.co) x402 API:
crypto data and research sold one request at a time, paid in USDC on Base
with no account and no API key. An unpaid request returns HTTP 402 with the
price; the client pays and retries.

Built for the [Blockchain IQ x402 build bounties](https://www.blockchainiq.co/blog/x402-build-bounties)
(LangChain tool slot, $150 first passing claim / $125 after).

## Tools

| Tool | Cost | What it returns |
| --- | --- | --- |
| `blockchain_iq_brief` | $0.01 | BTC/ETH/SOL/XRP prices, 24h/7d/30d moves, next-48h events, risk flags |
| `blockchain_iq_event_risk` | $0.05 | Scheduled market-moving events, next N days (default 7) |
| `blockchain_iq_catalog` | free | Every resource, path, price and response shape |

Paid tools return the data **plus the settlement proof** (payer, network,
transaction hash) from the `PAYMENT-RESPONSE` header. A 404 or any error
response is never charged, and the client refuses any single payment above
`max_usd` (default $0.60; the dearest catalog call is $0.50).

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
npm install   # @x402/fetch + viem, the official x402 payment client
```

Node 18+ is needed for the payment step only: the Python tool shells out to
`scripts/x402_call.mjs`, which uses the official `@x402/fetch` client (the
same code Blockchain IQ runs against production), because the EIP-3009
authorization must be built exactly as the facilitator expects.

## Use

```python
from langchain_core.agents import create_agent  # or any LangChain agent
from blockchainiq_langchain import brief_tool, event_risk_tool, catalog_tool

# Free: no key, no payment
print(catalog_tool.invoke({}))

# Paid: needs a Base wallet with a little USDC
# export AGENT_PRIVATE_KEY=0x...   (never commit it; see .env.example)
print(brief_tool.invoke({}))
print(event_risk_tool.invoke({"days": 7}))
```

Or with the raw client:

```python
from blockchainiq_langchain import BlockchainIQClient

client = BlockchainIQClient()
result = client.brief()          # {"data": {...}, "payment": {...}}
print(result["payment"]["txHash"])
```

## How a paid call works

1. Plain GET to `https://www.blockchainiq.co/api/x402/v1/brief`.
2. Server answers HTTP 402; the `PAYMENT-REQUIRED` header (base64 JSON,
   x402 v2) names the price ($0.01 = 10000 units of 6-decimal USDC), the
   asset (`0x833589fCD6eDb6E08f4c7C32D4f71b54bd029029`), the network
   (`eip155:8453`, Base) and the payee.
3. The client signs a USDC authorization locally and retries with it.
   Settlement is gasless for the payer.
4. Server answers 200 with the data and a `PAYMENT-RESPONSE` header
   carrying the transaction hash.

## Prove a paid call (for the bounty claim)

```bash
export AGENT_PRIVATE_KEY=0x...   # Base wallet with >= $0.01 USDC
python3 scripts/paid_call.py    # makes ONE $0.01 call, writes proof/proof-of-payment.json
```

The proof file holds the resource, price, timestamp, payment settlement
(payer, network, tx hash) and a summary of the returned data. Re-running
spends another $0.01 per call.

## Tests (spend nothing)

```bash
.venv/bin/python -m pytest tests/ -v
```

The tests hit the live API's free paths and the 402 handshake itself — an
unpaid request is never charged — plus a no-key refusal check (the client
must not attempt payment without `AGENT_PRIVATE_KEY`).

## Security

- The private key is read from the `AGENT_PRIVATE_KEY` env var only. It is
  never written to disk, never logged, and never sent anywhere except as a
  local signature for the x402 payment you asked for.
- `max_usd` caps every single payment; raise it only deliberately.
