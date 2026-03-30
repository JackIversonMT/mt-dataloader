# Funds Flow Step Field Reference

Every step shares: `step_id`, `type`, `description`, `depends_on`, `timing`, `metadata`.

## Type-specific fields

| `type` | Type-specific fields |
|--------|---------------------|
| `payment_order` | `payment_type`, `direction`, `amount`, `originating_account_id`, `receiving_account_id`, `currency`, `statement_descriptor`, **`effective_date`**, `staged`, `ledger_entries`, `ledger_inline`, `ledger_status` |
| `incoming_payment_detail` | `payment_type`, `amount`, `originating_account_id`, `internal_account_id`, `direction` (always `"credit"`), `currency`, `virtual_account_id`, **`as_of_date`** (**NOT** `effective_date`), `fulfills`, `staged`, `ledger_entries`, `ledger_inline`, `ledger_status` |
| `expected_payment` | `amount`, `direction`, `originating_account_id`, `internal_account_id`, `currency`, `date_lower_bound`, `date_upper_bound`, `staged`, `ledger_entries`, `ledger_inline`, `ledger_status` |
| `ledger_transaction` | `ledger_entries` (required), `ledger_status`, `effective_at`, **`effective_date`**, `staged` |
| `return` | `returnable_id`, `code`, `reason`, `ledger_entries`, `ledger_inline`, `ledger_status` |
| `reversal` | `payment_order_id`, `reason`, `ledger_entries`, `ledger_inline`, `ledger_status` |
| `transition_ledger_transaction` | `ledger_transaction_id`, `status` (required) |
| `verify_external_account` | `external_account_id`, `originating_account_id`, `payment_type` (default `"rtp"`) |
| `complete_verification` | `external_account_id`, `staged` (default `true`) |
| `archive_resource` | `target_ref`, `archive_method` (`delete` / `archive` / `request_closure`) |

## Common field mistakes

- IPD uses `as_of_date`, NOT `effective_date`. PO and LT use `effective_date`.
- IPD uses `internal_account_id`, NOT `receiving_account_id`. PO uses `receiving_account_id`.
- IPD `direction` is always `"credit"`. For ACH collections use a PO with `direction: "debit"`.
- ACH debit PO: `originating_account_id` = IA receiving funds, `receiving_account_id` = EA being debited.

## Step types summary

| `type` | Resource | Notes |
|--------|----------|-------|
| `payment_order` | PO | Set `payment_type` + `direction` |
| `incoming_payment_detail` | IPD | Sandbox inbound sim |
| `expected_payment` | EP | Reconciliation matcher |
| `ledger_transaction` | LT | Standalone double-entry |
| `return` | Return | IPD return |
| `reversal` | Reversal | PO reversal |
| `transition_ledger_transaction` | TLT | Status change on existing LT |
| `verify_external_account` | EA verify | Sends micro-deposits (default RTP) |
| `complete_verification` | EA complete | Reads amounts + confirms (staged by default) |
| `archive_resource` | Cleanup | Delete / archive / close a resource |
