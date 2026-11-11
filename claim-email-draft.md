# Claim email draft — DO NOT SEND until the paid call succeeds

To: partnerships@blockchainiq.co
Subject: x402 bounty claim — LangChain tool (paid call proof inside)

Hi Jeremy,

Claiming the LangChain slot of the x402 build bounties.

- Repository: [REPO URL — fill in after the repo is public]
- Framework: LangChain — a tool (`blockchain_iq_brief`, plus
  `blockchain_iq_event_risk` and the free `blockchain_iq_catalog`).
- Paid call: one $0.01 call to GET /api/x402/v1/brief, paid in USDC on
  Base via x402 v2. Proof below (also in the repo at
  proof/proof-of-payment.json).
- Payout address (Base USDC): 0xF77E6b4f9182a9Ca6Fb6DB28930D5a0178F054B5

Paid-call proof (fill in after `scripts/paid_call.py` runs):
- paid_at (UTC): [TODO]
- payer: [TODO — must match the claim wallet or be stated]
- network: eip155:8453 (Base)
- tx hash: [TODO]
- Basescan: https://basescan.org/tx/[TODO]
- data returned: asOf [TODO], coins BTC/ETH/SOL/XRP with prices [TODO]

How to verify: clone the repo, `pip install -r requirements.txt`,
`npm install`, set AGENT_PRIVATE_KEY to a Base wallet holding a little
USDC, then `python3 scripts/paid_call.py` — one $0.01 call, prints the
settlement proof. Free checks need no key: `pytest tests/` (catalog +
402 handshake, spends nothing).

Thanks,
Leo (AI agent, operated by @cxing4307-afk)
