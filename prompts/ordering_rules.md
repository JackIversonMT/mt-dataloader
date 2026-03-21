# Ordering Rules: How Resources Are Sequenced

The dataloader builds a directed acyclic graph (DAG) from the config and
executes resources in topological order. Within each batch, resources with
no dependencies between them run concurrently.

You almost never need to think about ordering — the engine handles it. This
document explains the rare cases where you do.

---

## Automatic Ordering (Default — No Action Required)

Any `$ref:` in a data field automatically creates a DAG edge. The engine
scans every field value in `model_dump()` for `$ref:` strings and adds
dependency edges.

**Example:** A payment order with `originating_account_id: "$ref:internal_account.main_checking"`
automatically waits for `internal_account.main_checking` to be created first.

**Child ref expansion:** If you reference a child ref like
`$ref:counterparty.vendor_bob.account[0]`, the engine automatically adds
an edge to the parent `counterparty.vendor_bob` too. You don't need to
declare both.

This covers the vast majority of cases. If resource A references resource B
in any field, A will wait for B.

---

## When `depends_on` Is Needed

`depends_on` is for **business timing** — when a resource must wait for
another resource that it does NOT reference in any data field.

The classic example: **a book transfer that moves funds deposited by an IPD**.

```json
{
    "ref": "po_settle_to_seller",
    "type": "book",
    "direction": "credit",
    "amount": 500000,
    "originating_account_id": "$ref:internal_account.buyer_john_wallet",
    "receiving_account_id": "$ref:internal_account.seller_jacks_wallet",
    "depends_on": ["$ref:incoming_payment_detail.ipd_buyer_deposit"]
}
```

This PO has no field that references the IPD — `originating_account_id` and
`receiving_account_id` are internal accounts, not IPDs. But the PO can only
succeed if the IPD has already deposited funds into the buyer's wallet. The
`depends_on` creates the necessary ordering edge.

---

## Common Patterns Requiring `depends_on`

### 1. IPD settlement before book transfer

When funds arrive via an IPD into a wallet, and a book transfer then moves
those funds to another wallet:

```
incoming_payment_detail.ipd_buyer_deposit  →  payment_order.po_settle_to_seller
```

The book transfer depends_on the IPD.

### 2. Sequential book transfers (settlement chain)

When funds flow through multiple wallets: buyer → seller → platform fee:

```
incoming_payment_detail.ipd_buyer_deposit
    → payment_order.po_settle_to_seller
        → payment_order.po_platform_fee
```

Each step depends_on the previous:

```json
{
    "ref": "po_platform_fee",
    "type": "book",
    "depends_on": ["$ref:payment_order.po_settle_to_seller"]
}
```

### 3. Payout after settlement

An ACH payout to a seller's external bank that must wait until the
settlement book transfer completes:

```json
{
    "ref": "po_seller_payout",
    "type": "ach",
    "depends_on": ["$ref:payment_order.po_settle_to_seller"]
}
```

### 4. Return after IPD

If you manually create a return (rather than using `sandbox_behavior: "return"`),
the return already references the IPD via `returnable_id`, so you do NOT need
`depends_on` — automatic ordering handles it.

---

## What NOT to Do

### Redundant depends_on

Do NOT add `depends_on` for something already referenced in a data field:

```json
{
    "ref": "po_pay_vendor",
    "originating_account_id": "$ref:internal_account.main_checking",
    "depends_on": ["$ref:internal_account.main_checking"]
}
```

This is redundant — the field ref already creates the edge.

### Circular dependencies

The DAG cannot have cycles. This will fail validation:

```
A depends_on B, B depends_on A
```

The engine raises a `CycleError` during dry run.

### depends_on to non-existent resource

Every `depends_on` target must exist in the config or baseline. The dry run
validates this and raises a `KeyError` with a clear message if the target
is unresolvable.

---

## Execution Order Summary

1. **Connections** — created first (no dependencies)
2. **Legal entities, Ledgers** — foundation resources
3. **Counterparties, Ledger accounts** — depend on LEs and ledgers
4. **Internal accounts, External accounts, Categories** — depend on
   connections, counterparties
5. **Virtual accounts, Expected payments, Payment orders** — depend on IAs,
   counterparties
6. **Incoming payment details** — depend on IAs (and optionally VAs)
7. **Ledger transactions** — depend on ledger accounts
8. **Returns** — depend on IPDs
9. **Reversals** — depend on POs
10. **Category memberships, Nested categories** — depend on categories and
    ledger accounts

Within each batch, all resources with satisfied dependencies execute
concurrently (up to `max_concurrent_requests`, default 5).

The actual batch grouping depends on the specific dependency graph — the
layers above are the *typical* order, not a fixed requirement.
