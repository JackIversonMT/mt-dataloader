# Generation Profiles

Three profiles control how much detail to include in a generated config.
**For Modern Treasury PSP / marketplace demos, treat the canonical reference
as `examples/marketplace_demo.json`:** wallets (IAs), book settlement, optional
sandbox IPD for inbound simulation, **no ledgers, no expected payments, no
virtual accounts** unless the user explicitly asks.

---

## Minimal

**Purpose:** Smallest runnable slice — often a **book transfer between two
wallets** (`examples/psp_minimal.json`).

**Include:**
- 1 connection
- 2 internal accounts (wallets) **or** 1 IA + 1 counterparty for a single ACH PO
- `payment_order` with required fields

**Exclude by default:**
- Legal entities (optional on minimal ACH+CP-only configs)
- Ledgers, ledger accounts, ledger transactions
- Virtual accounts, expected payments
- IPDs (unless testing inbound simulation)
- `depends_on` unless timing requires it

---

## Demo-Rich (Default)

**Purpose:** Customer-facing PSP / marketplace onboarding + money movement.

**Include:**
- Connection(s), legal entities, counterparties with `sandbox_behavior`,
  internal accounts (buyer/seller/platform revenue wallets)
- Payment orders: `book` for settlement and fees, `ach` for payout (and
  optionally ACH **debit collection** when demonstrating `sandbox_behavior`
  returns — describe as **pull / collection**, not buyer-push deposit)
- Rich metadata (listing, user_id, transaction_type)
- **`depends_on`** where book payouts follow simulated inbound IPD or prior book transfer

**Do not add unless the user explicitly wants that story:**
- `ledger*`, inline `ledger_transaction` on POs
- `expected_payment` (reconciliation-only; see decision rubrics)
- `virtual_account` (rare; not for wallet balances)

---

## Lifecycle

**Purpose:** Broader platform story — may include reconciliation, ledgering, or
explicit returns **when the user asks**.

**May include (only on request):**
- Expected payments + IPDs with **EP before IPD** in the DAG if demonstrating
  reconciliation matching
- Ledgers and ledger transactions
- Virtual accounts for inbound attribution demos
- Explicit `return` resources on IPDs
- Reversals (sandbox limitations apply)

**PSP marketplace default remains:** wallets + POs + optional IPD; no EP/VA/ledger
unless specified.

---

## Profile Selection Guide

| Question | Minimal | Demo-Rich | Lifecycle |
|----------|---------|-----------|-----------|
| Smallest internal transfer | **Yes** (`psp_minimal`) | | |
| Boats-style marketplace PSP | | **Yes** (`marketplace_demo`) | |
| Show reconciliation matching | | | **Yes** |
| Show ledgering | | | **Yes** |
| Show VA inbound attribution | | | **Yes** |

---

## Field Inclusion Matrix (PSP Marketplace Default)

| Field / feature | Default PSP demo |
|----------------|------------------|
| `connections` | 1 |
| `legal_entities` | Yes (buyers/sellers/platform) |
| `counterparties` | Yes |
| `internal_accounts` | Wallets + platform revenue |
| `payment_orders` | book + ach |
| `incoming_payment_details` | Optional: simulate buyer **push** deposit |
| `expected_payments` | **No** unless recon demo |
| `virtual_accounts` | **No** unless VA demo |
| `ledgers` / `ledger_accounts` / `ledger_transactions` | **No** unless accounting demo |
| `sandbox_behavior` | On CP accounts; understand PO-only constraint |
| `depends_on` | IPD → settle; settle → fee/payout as needed |
