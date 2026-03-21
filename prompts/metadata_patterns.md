# Metadata Patterns by Vertical

Metadata is business/demo data passed through to Modern Treasury unchanged.
Keys and values must be strings. Use metadata to make demos feel real and
grounded in the customer's domain — ERP IDs, invoice numbers, tenant IDs,
etc.

---

## Which Resources Support Metadata

| Supports metadata | Resource types |
|------------------|---------------|
| **Yes** | `legal_entity`, `ledger`, `counterparty`, `ledger_account`, `ledger_account_category`, `internal_account`, `external_account`, `virtual_account`, `expected_payment`, `payment_order`, `ledger_transaction`, `reversal` |
| **No** | `connection`, `incoming_payment_detail`, `return`, `category_membership`, `nested_category` |

Counterparty inline accounts (`accounts[]`) have their own metadata field
separate from the counterparty-level metadata.

---

## Marketplace / PSP

Boat marketplace, ride-sharing, e-commerce — any platform where buyers and
sellers transact through the platform.

### On legal entities (buyer/seller)
```json
{
    "metadata": {
        "platform_user_id": "USR-20260315-001",
        "user_type": "seller",
        "onboarded_at": "2026-01-15"
    }
}
```

### On counterparties
```json
{
    "metadata": {
        "platform_user_id": "USR-20260315-001",
        "display_name": "Jack's Marina"
    }
}
```

### On internal accounts (wallets)
```json
{
    "metadata": {
        "wallet_owner": "USR-20260315-001",
        "wallet_type": "seller"
    }
}
```

### On payment orders (book transfers, payouts)
```json
{
    "metadata": {
        "order_id": "ORD-2026-0847",
        "listing_id": "BOAT-2026-0847",
        "transaction_type": "marketplace_settlement"
    }
}
```

```json
{
    "metadata": {
        "order_id": "ORD-2026-0847",
        "fee_type": "platform_commission",
        "fee_rate": "0.05"
    }
}
```

### On expected payments
```json
{
    "metadata": {
        "order_id": "ORD-2026-0847",
        "expected_from": "buyer_john",
        "listing_id": "BOAT-2026-0847"
    }
}
```

---

## Property Management

Rent collection, vendor payouts, lease management.

### On legal entities (tenants, property companies)
```json
{
    "metadata": {
        "tenant_id": "TEN-1001",
        "lease_id": "LEASE-4420",
        "property_id": "PROP-9"
    }
}
```

### On counterparties (vendors)
```json
{
    "metadata": {
        "erp_vendor_id": "VEND-8821",
        "vendor_category": "maintenance"
    }
}
```

### On payment orders (rent collection, vendor payment)
```json
{
    "metadata": {
        "tenant_id": "TEN-1001",
        "lease_id": "LEASE-4420",
        "billing_month": "2026-03",
        "property_id": "PROP-9"
    }
}
```

```json
{
    "metadata": {
        "erp_bill_id": "BILL-9921",
        "cost_center": "MAINT-001",
        "work_order_id": "WO-3310"
    }
}
```

### On virtual accounts (per-tenant collection)
```json
{
    "metadata": {
        "tenant_id": "TEN-1001",
        "property_id": "PROP-9"
    }
}
```

### On expected payments (monthly rent)
```json
{
    "metadata": {
        "tenant_id": "TEN-1001",
        "billing_month": "2026-03",
        "lease_id": "LEASE-4420"
    }
}
```

---

## B2B Accounts Payable / Receivable

Invoice payments, supplier management, ERP integration.

### On counterparties (suppliers)
```json
{
    "metadata": {
        "erp_vendor_id": "VEND-3892",
        "vendor_name": "CloudHost Solutions",
        "payment_terms": "net_30"
    }
}
```

### On payment orders (invoice payments)
```json
{
    "metadata": {
        "invoice_id": "INV-2026-0042",
        "erp_vendor_id": "VEND-3892",
        "purchase_order": "PO-8821",
        "cost_center": "ENG-001",
        "gl_code": "6200"
    }
}
```

### On expected payments (customer receivables)
```json
{
    "metadata": {
        "invoice_id": "INV-2026-0099",
        "customer_id": "CUST-2201",
        "due_date": "2026-04-15"
    }
}
```

### On ledger transactions (journal entries)
```json
{
    "metadata": {
        "journal_entry_id": "JE-2026-0042",
        "source_system": "netsuite",
        "period": "2026-Q1"
    }
}
```

---

## Insurance / Claims

Policy management, claims processing, premium collection.

### On legal entities (policyholders)
```json
{
    "metadata": {
        "policyholder_id": "POL-H-5501",
        "policy_number": "HO-2026-001234"
    }
}
```

### On payment orders (claim payouts, premium refunds)
```json
{
    "metadata": {
        "claim_id": "CLM-2026-0087",
        "policy_id": "HO-2026-001234",
        "claim_type": "property_damage",
        "adjuster_id": "ADJ-201"
    }
}
```

### On expected payments (premium collection)
```json
{
    "metadata": {
        "policy_id": "HO-2026-001234",
        "premium_period": "2026-Q2",
        "premium_type": "quarterly"
    }
}
```

---

## Payroll

Employee payments, tax withholding, benefits.

### On legal entities (employer)
```json
{
    "metadata": {
        "company_id": "COMP-001",
        "payroll_provider": "internal",
        "ein": "12-3456789"
    }
}
```

### On counterparties (employees)
```json
{
    "metadata": {
        "employee_id": "EMP-1042",
        "department": "engineering",
        "pay_schedule": "biweekly"
    }
}
```

### On payment orders (payroll disbursements)
```json
{
    "metadata": {
        "payroll_run_id": "PR-2026-06",
        "employee_id": "EMP-1042",
        "pay_period": "2026-03-01_to_2026-03-15",
        "payment_type": "regular_salary"
    }
}
```

### On payment orders (tax payments)
```json
{
    "metadata": {
        "payroll_run_id": "PR-2026-06",
        "tax_type": "federal_income",
        "tax_period": "2026-Q1"
    }
}
```

---

## General Demo Tips

1. **Use realistic IDs** — `INV-2026-0042` is better than `test123`.
2. **Be consistent** — if you use `tenant_id` on one resource, use the same
   key everywhere that tenant appears.
3. **Keep values as strings** — metadata values must be strings, not numbers.
   Use `"250000"` not `250000` for amounts in metadata.
4. **Don't use metadata for loader dependencies** — never put `$ref:` strings
   in metadata. Use `depends_on` for ordering and data fields for structural
   references.
5. **Include at least 2-3 keys** — one key is sparse, five is cluttered.
   Two or three keys per resource is the sweet spot for demos.
