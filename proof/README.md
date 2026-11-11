# Proof of the paid call

`scripts/paid_call.py` writes `proof-of-payment.json` here after one real
$0.01 call to `/brief`. It is gitignored in the working copy on purpose —
the claim email carries the transaction hash, and the file is regenerated
by re-running the script (each run spends another $0.01).

Not yet run: the wallet holds $0.00. Run it once 0.10 USDC lands.
