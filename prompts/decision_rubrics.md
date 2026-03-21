# Decision Rubrics: When to Use Each Modern Treasury Resource

This document tells you which MT resource type to use for a given business
intent. Every resource listed here maps to a top-level section in the
DataLoaderConfig JSON.

---

## Connections

A connection represents a link to a banking partner. In sandbox, connections
can be created via the config. In production, they are provisioned by MT.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Link to a banking partner (sandbox) | `connections` | `entity_id` (one of `example1`, `example2`, `modern_treasury`), `nickname` |

Every config that creates internal accounts needs at least one connection.
Connections cannot be deleted.

---

## Legal Entities

A legal entity is a person or business. Required for KYC/KYB onboarding.

| Intent | `legal_entity_type` | Required fields |
|--------|-------------------|-----------------|
| Represent a business | `business` | `business_name`, `date_formed`, `legal_structure`, `country_of_incorporation`, `identifications` (at least one, e.g. `us_ein`), `addresses` (with `address_types`) |
| Represent an individual | `individual` | `first_name`, `last_name`, `date_of_birth`, `citizenship_country`, `identifications` (at least one, e.g. `us_ssn`), `addresses` |

Legal entities cannot be deleted. Always include `identifications` — the MT
API will reject businesses without a tax ID and individuals without an SSN
or equivalent.

`legal_structure` values: `corporation`, `llc`, `non_profit`, `partnership`,
`sole_proprietorship`, `trust`.

---

## Counterparties

A counterparty is an external party you transact with. Counterparties carry
inline external accounts (bank info).

| Intent | Config section | Key fields |
|--------|---------------|------------|
| External party with bank account | `counterparties` | `name`, `accounts[]` (inline bank accounts), optional `legal_entity_id` |

### Inline accounts on counterparties

Each counterparty can have one or more `accounts[]`. These are created
inline with the counterparty and auto-registered as child refs:

- `$ref:counterparty.<key>.account[0]` — first account
- `$ref:counterparty.<key>.account[1]` — second account (if present)

### Sandbox behavior (critical for demos)

Set `sandbox_behavior` on the account to control how the sandbox processes
payments sent to this counterparty:

| `sandbox_behavior` | Effect | Magic account number |
|-------------------|--------|---------------------|
| `success` | Payment completes normally | `123456789` |
| `return` | Payment auto-returns with the specified ACH code | `100XX` (where XX = return code digits) |
| `failure` | Payment fails outright | `1111111110` |

When `sandbox_behavior` is set, `account_details` and `routing_details`
are auto-populated — you do not need to specify them. Set
`sandbox_return_code` alongside `return` (e.g. `"R01"` for NSF).

**Always set `sandbox_behavior` on counterparty accounts in demo configs.**
Without it, the sandbox uses a random account number and payment outcomes
are unpredictable.

---

## Internal Accounts

An internal account is a bank account owned by the platform. In PSP/marketplace
models, each user gets their own internal account as a "wallet."

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Platform operating account | `internal_accounts` | `connection_id`, `name`, `party_name`, `currency` (USD or CAD) |
| Per-user wallet (PSP/marketplace) | `internal_accounts` | Same, plus `legal_entity_id` to link to the user's LE |
| Platform revenue/fee account | `internal_accounts` | Same, named for the fee purpose |

Internal accounts cannot be deleted. They require a `connection_id` ref.
A child ref `$ref:internal_account.<key>.ledger_account` is auto-registered
if the banking partner auto-creates a ledger account.

---

## External Accounts

A standalone external account attached to an existing counterparty. Use this
when you need to add a *second* bank account to a counterparty that was
already created, or when you need an account with a ledger account attached.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Additional bank account on existing counterparty | `external_accounts` | `counterparty_id`, `account_details`, `routing_details` |
| Bank account with inline ledger account | `external_accounts` | Same, plus `ledger_account` (inline) |

Most demos use inline `accounts[]` on the counterparty instead. Use
`external_accounts` only when you specifically need a standalone account
or an inline ledger account.

---

## Virtual Accounts

A virtual account is a sub-account within an internal account, used for
per-payer inbound attribution. **Not a wallet.** Virtual accounts don't
hold balances — they route inbound payments to the parent IA with payer
attribution.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Per-payer collection point | `virtual_accounts` | `name`, `internal_account_id`, optional `counterparty_id` |

Do NOT use virtual accounts for PSP wallet functionality — use internal
accounts instead. Virtual accounts are for *inbound payment attribution*
(e.g. knowing which tenant's rent payment just arrived).

---

## Payment Orders

A payment order moves money. This is the most common resource in demos.

| Intent | `type` | `direction` | Accounts |
|--------|--------|------------|----------|
| Pay a vendor / supplier | `ach`, `wire`, or `rtp` | `credit` | `originating_account_id` = internal account, `receiving_account_id` = counterparty account |
| Collect from a customer (drawdown) | `ach` | `debit` | `originating_account_id` = internal account, `receiving_account_id` = counterparty account |
| Move funds between wallets (book) | `book` | `credit` | Both are `internal_account` refs |
| Collect platform fee | `book` | `credit` | From user wallet IA to platform revenue IA |
| Payout to external bank | `ach`, `wire` | `credit` | From user IA to counterparty external account |

**Rules:**
- `direction: credit` requires `receiving_account_id`
- `direction: debit` — `receiving_account_id` is the source being debited
- `amount` is in cents (e.g. 10000 = $100.00)
- `type: book` = internal transfer between two internal accounts. Always `direction: credit`.
- Inline `ledger_transaction` can be attached for double-entry accounting

Payment orders cannot be deleted.

---

## Expected Payments

An expected payment tells MT to watch for an inbound payment matching
specific criteria. Used for reconciliation demos.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Expect an inbound payment | `expected_payments` | `reconciliation_rule_variables` (required), `description` |

`reconciliation_rule_variables` must include at least one entry with:
- `internal_account_id` — which account to watch
- `direction` — `credit` or `debit`
- `amount_lower_bound` and `amount_upper_bound` — amount range in cents
- `type` — payment type (e.g. `ach`)

Pair with an `incoming_payment_detail` of matching amount on the same
internal account to demonstrate auto-reconciliation.

---

## Incoming Payment Details (Sandbox Only)

Simulates an inbound bank deposit arriving. **Sandbox only** — in production,
these are created by real bank deposits.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Simulate a bank deposit | `incoming_payment_details` | `type`, `direction`, `amount`, `internal_account_id` |

After creation, the IPD polls until `completed` status (up to 30s). Once
completed, child refs are auto-registered:
- `$ref:incoming_payment_detail.<key>.transaction` — the resulting transaction
- `$ref:incoming_payment_detail.<key>.ledger_transaction` — if ledgering is active

**IPDs do not support metadata.**

Use `depends_on` on downstream payment orders that need to wait for the
IPD to settle before moving the deposited funds.

---

## Ledgers & Ledger Accounts

Double-entry bookkeeping. A ledger contains ledger accounts, and ledger
transactions move amounts between them.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Create a ledger | `ledgers` | `name`, `description` |
| Create a ledger account | `ledger_accounts` | `name`, `ledger_id`, `normal_balance` (credit or debit), `currency` |
| Standalone ledger transaction | `ledger_transactions` | `ledger_entries[]` (at least one debit + one credit, must balance) |
| Inline ledger transaction on PO | `ledger_transaction` field on `payment_orders` | Same `ledger_entries` structure |

**Normal balance conventions:**
- Assets (Cash, AR): `debit`
- Liabilities (AP): `credit`
- Revenue: `credit`
- Expenses/Refunds: `debit`

Ledger transactions can be archived during cleanup but not deleted.

---

## Ledger Account Categories

Organizational grouping for ledger accounts (e.g. "Assets", "Liabilities").

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Create a category | `ledger_account_categories` | `name`, `ledger_id`, `normal_balance`, `currency` |
| Add account to category | `category_memberships` | `category_id`, `ledger_account_id` |
| Nest categories | `nested_categories` | `parent_category_id`, `sub_category_id` |

---

## Returns

Return an incoming payment (e.g. reject or bounce an IPD). Returns reference
the IPD being returned.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Return an incoming payment | `returns` | `returnable_id` (ref to an IPD), optional `code`, `reason` |

**Returns do not support metadata.** The `returnable_type` is always
`incoming_payment_detail` (auto-set by the loader).

Prefer using `sandbox_behavior: "return"` on counterparty accounts to
simulate returns — this is more realistic than manually creating returns.

---

## Reversals

Reverse a completed/sent payment order. The PO must reach `approved`,
`sent`, or `completed` status before a reversal can be created.

| Intent | Config section | Key fields |
|--------|---------------|------------|
| Reverse a payment order | `reversals` | `payment_order_id`, `reason` |

`reason` values: `duplicate`, `incorrect_amount`,
`incorrect_receiving_account`, `date_earlier_than_intended`,
`date_later_than_intended`.

The handler automatically polls the PO status until it reaches a reversible
state (up to 60s). Not all sandbox connections support reversals.

---

## Cleanup / Deletability Reference

| Resource | Can be deleted? | Cleanup behavior |
|----------|----------------|-----------------|
| connection | No | Skipped |
| legal_entity | No | Skipped |
| internal_account | No | Skipped |
| payment_order | No | Skipped |
| incoming_payment_detail | No | Skipped |
| return | No | Skipped |
| reversal | No | Skipped |
| ledger_transaction | No (archived) | Archived |
| counterparty | **Yes** | Deleted |
| external_account | **Yes** | Deleted |
| virtual_account | **Yes** | Deleted |
| ledger | **Yes** | Deleted |
| ledger_account | **Yes** | Deleted |
| ledger_account_category | **Yes** | Deleted |
| expected_payment | **Yes** | Deleted |
| category_membership | **Yes** | Removed |
| nested_category | **Yes** | Removed |

Plan configs knowing that non-deletable resources (LEs, IAs, POs, IPDs)
will persist in the sandbox org after cleanup.
