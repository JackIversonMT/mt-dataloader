# Generation Profiles

Three profiles control how much detail to include in a generated config.
Choose the profile based on the demo purpose.

---

## Minimal

**Purpose:** Quick API testing, SDK validation, or sanity-checking a single
flow. Smallest possible config that actually creates resources and moves money.

**Include:**
- 1 connection
- Counterparties with `sandbox_behavior: "success"` (no LE, no legal details)
- 1 internal account
- Payment orders with required fields only (`type`, `amount`, `direction`,
  `originating_account_id`, `receiving_account_id`)

**Exclude:**
- Legal entities (counterparties work without them)
- Ledgers, ledger accounts, ledger transactions
- Virtual accounts
- Expected payments / IPDs
- Returns, reversals
- `depends_on` (no lifecycle flows)
- Metadata (empty or omitted)
- `description`, `statement_descriptor`, `effective_date`
- Line items

**Example scope:** 1 connection + 1 counterparty + 1 internal account + 1 PO

---

## Demo-Rich (Default)

**Purpose:** Customer demos, sales engineering walkthroughs, or onboarding
showcases. Realistic data, full entity onboarding, meaningful metadata.

**Include everything from Minimal, plus:**
- Legal entities with full KYB/KYC fields (`identifications`, `addresses`,
  `date_formed`, `legal_structure`, etc.)
- Counterparties linked to legal entities via `legal_entity_id`
- `sandbox_behavior` on all counterparty accounts
- Multiple payment orders showing different rails (`ach`, `wire`, `book`)
- Metadata on all resources that support it (use vertical-specific patterns)
- `description` and `statement_descriptor` on POs
- Multiple counterparties representing different roles (vendor, customer,
  buyer, seller)

**Optionally include:**
- Ledger with ledger accounts and categories (if the demo involves accounting)
- Inline `ledger_transaction` on payment orders (if showing payment-level
  accounting)
- Virtual accounts (if showing per-payer inbound attribution)
- Expected payments + IPDs (if showing reconciliation)
- `depends_on` (only if the flow has business-timing dependencies)

**Exclude:**
- Returns, reversals (unless specifically requested)
- `sandbox_behavior: "return"` or `"failure"` (unless demonstrating failure
  handling)

**Example scope:** 1 connection + 2-3 LEs + 3-5 counterparties +
2-3 internal accounts + 4-8 POs + optional ledger

---

## Lifecycle

**Purpose:** Full platform demo showing the complete money movement lifecycle
— onboarding, funding, settlement, fees, payouts, reconciliation, and
optionally returns or failures.

**Include everything from Demo-Rich, plus:**
- Expected payments with `reconciliation_rule_variables`
- Incoming payment details simulating deposits
- `depends_on` for business timing (IPD → settlement → fee → payout chains)
- `sandbox_behavior: "return"` on at least one counterparty to show return
  handling
- Multiple `type: book` POs for internal fund movement
- Ledger with full chart of accounts (cash, AR, AP, revenue, refunds)
- Inline `ledger_transaction` on key POs
- Category memberships and optionally nested categories

**Optionally include:**
- Returns (manual, if not using sandbox_behavior)
- Reversals (if demonstrating PO reversal flow — note sandbox limitations)
- Virtual accounts for inbound attribution

**Example scope:** 1-2 connections + 3-5 LEs + 4-6 counterparties +
3-6 internal accounts + 6-12 POs + 1-3 IPDs + 1-2 expected payments +
1 ledger + 5-8 ledger accounts + optional returns

---

## Profile Selection Guide

| Question | Minimal | Demo-Rich | Lifecycle |
|----------|---------|-----------|-----------|
| "Just test that POs work" | **Yes** | | |
| "Show the customer our payments flow" | | **Yes** | |
| "Demonstrate the full marketplace" | | | **Yes** |
| "Quick counterparty + payment" | **Yes** | | |
| "Onboarding with KYB" | | **Yes** | |
| "Reconciliation demo" | | | **Yes** |
| "Show how book transfers work" | | **Yes** | |
| "End-to-end PSP flow" | | | **Yes** |
| "Sandbox behavior testing" | | **Yes** | |
| "Full accounting with ledger" | | | **Yes** |

---

## Field Inclusion Matrix

| Field / feature | Minimal | Demo-Rich | Lifecycle |
|----------------|---------|-----------|-----------|
| `connections` | 1 | 1 | 1-2 |
| `legal_entities` | 0 | 2-3 | 3-5 |
| `counterparties` | 1 | 3-5 | 4-6 |
| `internal_accounts` | 1 | 2-3 | 3-6 |
| `payment_orders` | 1 | 4-8 | 6-12 |
| `sandbox_behavior` | `success` only | all `success` | mix of `success` + `return` |
| `metadata` | omit | per-vertical | per-vertical |
| `legal_entity_id` on CP | omit | include | include |
| `identifications` on LE | omit | include | include |
| `ledgers` | 0 | 0-1 | 1 |
| `ledger_accounts` | 0 | 0-5 | 5-8 |
| `virtual_accounts` | 0 | 0 | 0-3 |
| `expected_payments` | 0 | 0 | 1-2 |
| `incoming_payment_details` | 0 | 0 | 1-3 |
| `returns` | 0 | 0 | 0-1 |
| `reversals` | 0 | 0 | 0-1 |
| `depends_on` | never | rarely | commonly |
| `description` on POs | omit | include | include |
| inline `ledger_transaction` | never | optional | include on key POs |
