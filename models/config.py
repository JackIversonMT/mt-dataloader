"""Top-level DataLoaderConfig — the root schema parsed from the user's JSON."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.flow_dsl import FundsFlowConfig
from models.resources import (
    CategoryMembershipConfig,
    ConnectionConfig,
    CounterpartyConfig,
    ExternalAccountConfig,
    ExpectedPaymentConfig,
    IncomingPaymentDetailConfig,
    InternalAccountConfig,
    LedgerAccountCategoryConfig,
    LedgerAccountConfig,
    LedgerConfig,
    LedgerTransactionConfig,
    LegalEntityConfig,
    NestedCategoryConfig,
    PaymentOrderConfig,
    ReturnConfig,
    ReversalConfig,
    TransitionLedgerTransactionConfig,
    VirtualAccountConfig,
)


class DataLoaderConfig(BaseModel):
    """Top-level dataloader configuration parsed from the user's JSON file.

    Sections default to empty lists so the user only includes what they need.
    ``extra='forbid'`` catches typos in section names immediately.
    """

    model_config = ConfigDict(extra="forbid")

    # Layer 0 — connections (sandbox-only)
    connections: list[ConnectionConfig] = []

    # Layer 1
    legal_entities: list[LegalEntityConfig] = []
    ledgers: list[LedgerConfig] = []

    # Layer 2
    counterparties: list[CounterpartyConfig] = []
    ledger_accounts: list[LedgerAccountConfig] = []

    # Layer 3
    internal_accounts: list[InternalAccountConfig] = []
    external_accounts: list[ExternalAccountConfig] = []
    ledger_account_categories: list[LedgerAccountCategoryConfig] = []

    # Layer 4
    virtual_accounts: list[VirtualAccountConfig] = []
    expected_payments: list[ExpectedPaymentConfig] = []
    payment_orders: list[PaymentOrderConfig] = []

    # Layer 5
    incoming_payment_details: list[IncomingPaymentDetailConfig] = []
    ledger_transactions: list[LedgerTransactionConfig] = []
    returns: list[ReturnConfig] = []

    # Layer 6
    reversals: list[ReversalConfig] = []
    category_memberships: list[CategoryMembershipConfig] = []
    nested_categories: list[NestedCategoryConfig] = []
    transition_ledger_transactions: list[TransitionLedgerTransactionConfig] = []

    # Display / branding
    customer_name: str = Field(
        default="direct",
        description=(
            "Label used for customer-facing account participants in "
            "Mermaid diagrams, e.g. '{{ customer_name }} Account'. "
            "Defaults to 'direct'."
        ),
    )

    # Funds Flow DSL (compiler input, not an MT resource).
    # Intentionally skipped by _refs_are_unique_within_type — these items
    # have no resource_type ClassVar.  The compiler validates flow refs.
    funds_flows: list[FundsFlowConfig] = Field(
        default_factory=list,
        description=(
            "High-level funds flow definitions. Compiled to FlowIR and "
            "emitted into the resource sections above. If empty, the "
            "config is treated as a raw resource config (passthrough)."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _drop_ipd_ep_originating_account_on_raw_resources(cls, data: Any) -> Any:
        """LLMs often copy PO-style `originating_account_id` onto raw IPD/EP rows.

        The Funds Flow DSL allows `originating_account_id` on IPD/EP *steps*; the
        compiler strips it when emitting. Raw ``incoming_payment_details`` and
        ``expected_payments`` entries use the narrower resource schema (no
        ``originating_account_id``), so we discard the key here to match emit
        behavior and avoid spurious validation failures.
        """
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for key in ("incoming_payment_details", "expected_payments"):
            items = out.get(key)
            if not isinstance(items, list):
                continue
            coerced: list[Any] = []
            changed = False
            for item in items:
                if isinstance(item, dict) and "originating_account_id" in item:
                    coerced.append(
                        {k: v for k, v in item.items() if k != "originating_account_id"}
                    )
                    changed = True
                else:
                    coerced.append(item)
            if changed:
                out[key] = coerced
        return out

    @model_validator(mode="after")
    def _refs_are_unique_within_type(self) -> DataLoaderConfig:
        """Catch duplicate refs before the engine even sees them."""
        seen: dict[str, str] = {}
        for section_name in type(self).model_fields:
            items = getattr(self, section_name)
            for item in items:
                if not hasattr(item, "resource_type"):
                    continue
                typed_ref = f"{item.resource_type}.{item.ref}"
                if typed_ref in seen:
                    raise ValueError(
                        f"Duplicate ref '{typed_ref}' in sections "
                        f"'{seen[typed_ref]}' and '{section_name}'"
                    )
                seen[typed_ref] = section_name
        return self
