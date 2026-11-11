// Paid x402 fetch helper for Blockchain IQ.
// Uses the official @x402/fetch client (the same code Blockchain IQ runs
// against production). The Python LangChain tool calls this only after a
// plain GET returned HTTP 402, so no payment is attempted for free resources.
//
// Usage:
//   AGENT_PRIVATE_KEY=0x... node scripts/x402_call.mjs <url> [max-usd]
// Output: JSON on stdout:
//   { "status": 200, "data": {...}, "payment": { payer, network, txHash, ... } }
//   or { "status": <http>, "error": "...", "payment_required": {...} } on failure.
// Exit code 0 only when the call returned HTTP 200 with data.
// The wallet must hold a little USDC on Base (eip155:8453). Settlement is
// gasless for the payer. Never commit a private key; pass it via env only.
import { privateKeyToAccount } from "viem/accounts";
import { wrapFetchWithPayment, x402Client, decodePaymentResponseHeader } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm/exact/client";

const url = process.argv[2];
const maxUsd = Number(process.argv[3] ?? "0.6");
if (!url) {
  console.error(JSON.stringify({ error: "usage: x402_call.mjs <url> [max-usd]" }));
  process.exit(2);
}
const key = process.env.AGENT_PRIVATE_KEY;
if (!key || !/^0x[0-9a-fA-F]{64}$/.test(key)) {
  console.error(JSON.stringify({ error: "AGENT_PRIVATE_KEY env var missing or not a 0x-prefixed 64-hex private key" }));
  process.exit(2);
}

const account = privateKeyToAccount(key);
const client = x402Client.fromConfig({
  schemes: [{ network: "eip155:*", client: new ExactEvmScheme(account) }],
  spendControls: { maxAmountPerPayment: maxUsd },
});
const payFetch = wrapFetchWithPayment(fetch, client);

let res;
try {
  res = await payFetch(url);
} catch (err) {
  console.log(JSON.stringify({ status: 0, error: `fetch failed: ${err.message}` }));
  process.exit(1);
}

const bodyText = await res.text();
let body;
try {
  body = JSON.parse(bodyText);
} catch {
  body = { raw: bodyText.slice(0, 500) };
}

if (res.status !== 200) {
  console.log(JSON.stringify({ status: res.status, error: body.error ?? bodyText.slice(0, 300) }));
  process.exit(1);
}

let payment = null;
const pr = res.headers.get("payment-response");
if (pr) {
  try {
    payment = decodePaymentResponseHeader(pr);
  } catch (err) {
    payment = { decodeError: err.message, raw: pr.slice(0, 200) };
  }
}
console.log(JSON.stringify({ status: 200, data: body.data ?? body, payment }));
