"""Tests for org reconciliation (connection fallback, etc.)."""

from __future__ import annotations

from models import (
    ConnectionConfig,
    DataLoaderConfig,
    InternalAccountConfig,
    LegalEntityConfig,
)
from org.discovery import DiscoveredConnection, DiscoveryResult
from org.reconciliation import reconcile_config


def test_connection_reuses_single_live_when_entity_id_unmatched():
    """If vendor_id does not match config entity_id but org has one connection, map to it."""
    config = DataLoaderConfig(
        connections=[
            ConnectionConfig(
                ref="platform_bank",
                entity_id="modern_treasury",
                nickname="PSP",
            )
        ],
        legal_entities=[
            LegalEntityConfig(
                ref="le1",
                legal_entity_type="business",
                business_name="Demo PSP Co",
            )
        ],
        internal_accounts=[
            InternalAccountConfig(
                ref="usd_wallet",
                connection_id="$ref:connection.platform_bank",
                name="Wallet",
                party_name="Demo PSP Co",
                currency="USD",
                legal_entity_id="$ref:legal_entity.le1",
            )
        ],
    )
    live = DiscoveredConnection(
        id="conn-live-uuid",
        vendor_name="Legacy Sandbox Bank",
        vendor_id="legacy_vendor_not_mt",
        currencies=["USD"],
    )
    discovery = DiscoveryResult(connections=[live])

    result = reconcile_config(config, discovery)

    conn_matches = [m for m in result.matches if m.config_ref == "connection.platform_bank"]
    assert len(conn_matches) == 1
    assert conn_matches[0].discovered_id == "conn-live-uuid"
    assert "fallback" in conn_matches[0].match_reason.lower()
    assert "connection.platform_bank" not in result.unmatched_config
