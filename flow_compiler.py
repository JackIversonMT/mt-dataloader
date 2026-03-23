"""Funds Flow DSL compiler.

Pipeline: FundsFlowConfig[] → resolve_actors → compile_flows → FlowIR[]
          → emit_dataloader_config → DataLoaderConfig

All compilation logic lives in this single module. The engine, handlers,
and main.py are unchanged — the emitted DataLoaderConfig feeds directly
into the existing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models import DataLoaderConfig, FundsFlowConfig, FundsFlowStepConfig

__all__ = ["maybe_compile"]

# ---------------------------------------------------------------------------
# Resource type → DataLoaderConfig section name
# ---------------------------------------------------------------------------

_RESOURCE_TYPE_TO_SECTION: dict[str, str] = {
    "payment_order": "payment_orders",
    "incoming_payment_detail": "incoming_payment_details",
    "ledger_transaction": "ledger_transactions",
    "expected_payment": "expected_payments",
    "return": "returns",
    "reversal": "reversals",
}

_NEEDS_PAYMENT_TYPE: frozenset[str] = frozenset({
    "incoming_payment_detail",
    "payment_order",
})

# ---------------------------------------------------------------------------
# FlowIR dataclasses (internal — not Pydantic)
# ---------------------------------------------------------------------------


@dataclass
class LedgerGroup:
    """One set of ledger entries that emits as a standalone LT or inline LT."""

    group_id: str
    inline: bool
    entries: list[dict]
    metadata: dict[str, str]


@dataclass
class FlowIRStep:
    """One step in the FlowIR — compiles to one resource in DataLoaderConfig."""

    step_id: str
    flow_ref: str
    instance_id: str
    depends_on: list[str]
    resource_type: str
    payload: dict
    ledger_groups: list[LedgerGroup]
    trace_metadata: dict[str, str]

    @property
    def emitted_ref(self) -> str:
        return f"{self.flow_ref}__{self.instance_id}__{self.step_id}"


@dataclass
class FlowIR:
    """Complete IR for one flow instance."""

    flow_ref: str
    instance_id: str
    pattern_type: str
    trace_key: str
    trace_value: str
    trace_metadata: dict[str, str]
    steps: list[FlowIRStep] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_ref_segment(segment: str) -> None:
    if "__" in segment:
        raise ValueError(
            f"Ref segment '{segment}' must not contain '__' "
            f"(reserved as instance separator)"
        )


def resolve_actors(obj: Any, actors: dict[str, str]) -> Any:
    """Replace ``@actor:<alias>`` references with concrete ``$ref:`` values."""
    if isinstance(obj, str) and obj.startswith("@actor:"):
        alias = obj[7:]
        if alias not in actors:
            raise ValueError(
                f"Unknown actor alias '{alias}' — "
                f"available: {sorted(actors.keys())}"
            )
        return actors[alias]
    if isinstance(obj, dict):
        return {k: resolve_actors(v, actors) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_actors(v, actors) for v in obj]
    return obj


def expand_trace_value(template: str, ref: str, instance: int) -> str:
    try:
        return template.format_map({"ref": ref, "instance": instance})
    except KeyError as e:
        raise ValueError(
            f"Unknown placeholder {e} in trace_value_template '{template}'"
        ) from e


def _auto_derive_lifecycle_refs(
    step: FundsFlowStepConfig,
    step_dict: dict,
    step_ref_map: dict[str, str],
    all_steps: list[FundsFlowStepConfig],
) -> None:
    """Auto-set returnable_id / payment_order_id from depends_on targets."""
    if step.type == "return" and "returnable_id" not in step_dict:
        for dep_id in step.depends_on:
            dep_step = next(s for s in all_steps if s.step_id == dep_id)
            if dep_step.type == "incoming_payment_detail":
                step_dict["returnable_id"] = step_ref_map[dep_id]
                break

    if step.type == "reversal" and "payment_order_id" not in step_dict:
        for dep_id in step.depends_on:
            dep_step = next(s for s in all_steps if s.step_id == dep_id)
            if dep_step.type == "payment_order":
                step_dict["payment_order_id"] = step_ref_map[dep_id]
                break


def _inject_lifecycle_depends_on(step: FlowIRStep) -> None:
    """Add depends_on edges for lifecycle ordering the engine can't infer
    from data refs alone."""
    if step.resource_type == "return":
        ipd_ref = step.payload.get("returnable_id", "")
        if ipd_ref.startswith("$ref:") and ipd_ref not in step.depends_on:
            step.depends_on.append(ipd_ref)
    elif step.resource_type == "reversal":
        po_ref = step.payload.get("payment_order_id", "")
        if po_ref.startswith("$ref:") and po_ref not in step.depends_on:
            step.depends_on.append(po_ref)


# ---------------------------------------------------------------------------
# Compiler: DSL → FlowIR
# ---------------------------------------------------------------------------


def compile_flows(
    flows: list[FundsFlowConfig],
    base_config: DataLoaderConfig,
) -> list[FlowIR]:
    """Compile FundsFlowConfig DSL entries into FlowIR instances."""
    result: list[FlowIR] = []

    for flow in flows:
        _validate_ref_segment(flow.ref)
        instance_id = "0000"
        trace_value = expand_trace_value(
            flow.trace_value_template, flow.ref, 0
        )
        trace_meta = {flow.trace_key: trace_value, **flow.trace_metadata}

        # --- Pass 1: build ref map for ALL steps ---
        step_ref_map: dict[str, str] = {}
        for step in flow.steps:
            _validate_ref_segment(step.step_id)
            emitted_ref = f"{flow.ref}__{instance_id}__{step.step_id}"
            typed_ref = f"$ref:{step.type}.{emitted_ref}"
            step_ref_map[step.step_id] = typed_ref

        # --- Pass 2: process step payloads ---
        ir_steps: list[FlowIRStep] = []
        for step in flow.steps:
            emitted_ref = f"{flow.ref}__{instance_id}__{step.step_id}"

            step_dict = step.model_dump(
                exclude={"step_id", "type", "depends_on", "ledger_entries"},
                exclude_none=True,
            )

            if "payment_type" in step_dict:
                step_dict["type"] = step_dict.pop("payment_type")
            elif step.type in _NEEDS_PAYMENT_TYPE:
                raise ValueError(
                    f"Step '{step.step_id}' (type={step.type}) requires "
                    f"'payment_type' (e.g., 'ach', 'wire'). The DSL 'type' "
                    f"field is the resource type; use 'payment_type' for the "
                    f"payment method."
                )

            step_dict = resolve_actors(step_dict, flow.actors)

            step_dict["metadata"] = {
                **step_dict.get("metadata", {}),
                **trace_meta,
            }

            # depends_on: direct index — Pydantic already validated targets
            ir_depends = [step_ref_map[dep] for dep in step.depends_on]

            # Auto-derive lifecycle data-field refs
            _auto_derive_lifecycle_refs(
                step, step_dict, step_ref_map, flow.steps
            )

            ledger_groups: list[LedgerGroup] = []
            if step.ledger_entries:
                entries_resolved = resolve_actors(
                    [e.model_dump(exclude_none=True) for e in step.ledger_entries],
                    flow.actors,
                )
                ledger_groups.append(LedgerGroup(
                    group_id=f"{step.step_id}_lg0",
                    inline=False,
                    entries=entries_resolved,
                    metadata=trace_meta.copy(),
                ))

            ir_steps.append(FlowIRStep(
                step_id=step.step_id,
                flow_ref=flow.ref,
                instance_id=instance_id,
                depends_on=ir_depends,
                resource_type=step.type,
                payload=step_dict,
                ledger_groups=ledger_groups,
                trace_metadata=trace_meta,
            ))

        result.append(FlowIR(
            flow_ref=flow.ref,
            instance_id=instance_id,
            pattern_type=flow.pattern_type,
            trace_key=flow.trace_key,
            trace_value=trace_value,
            trace_metadata=trace_meta,
            steps=ir_steps,
        ))

    return result


# ---------------------------------------------------------------------------
# Emitter: FlowIR → DataLoaderConfig
# ---------------------------------------------------------------------------


def emit_dataloader_config(
    flow_irs: list[FlowIR],
    base_config: DataLoaderConfig,
) -> DataLoaderConfig:
    """Emit FlowIR steps into DataLoaderConfig resource sections.

    The emitted config passes through ``DataLoaderConfig.model_validate()``
    which runs every existing Pydantic validator as a safety net.
    """
    data = base_config.model_dump(exclude_none=True)
    data["funds_flows"] = []

    for flow_ir in flow_irs:
        for step in flow_ir.steps:
            _inject_lifecycle_depends_on(step)

            ref = step.emitted_ref
            resource_type = step.resource_type
            section = _RESOURCE_TYPE_TO_SECTION[resource_type]

            resource_dict: dict[str, Any] = {
                "ref": ref,
                **step.payload,
            }
            if step.depends_on:
                resource_dict["depends_on"] = step.depends_on

            for lg in step.ledger_groups:
                if not lg.inline:
                    if resource_type == "ledger_transaction":
                        resource_dict["ledger_entries"] = lg.entries
                        resource_dict["metadata"] = {
                            **resource_dict.get("metadata", {}),
                            **lg.metadata,
                        }
                    else:
                        lt_ref = f"{ref}__{lg.group_id}"
                        lt_dict: dict[str, Any] = {
                            "ref": lt_ref,
                            "ledger_entries": lg.entries,
                            "metadata": lg.metadata,
                            "depends_on": [f"$ref:{resource_type}.{ref}"],
                        }
                        if step.payload.get("description"):
                            lt_dict["description"] = step.payload["description"]
                        data.setdefault("ledger_transactions", []).append(lt_dict)
                else:
                    inline_lt: dict[str, Any] = {
                        "ledger_entries": lg.entries,
                        "metadata": lg.metadata,
                    }
                    if step.payload.get("description"):
                        inline_lt["description"] = step.payload["description"]
                    resource_dict["ledger_transaction"] = inline_lt

            data.setdefault(section, []).append(resource_dict)

    return DataLoaderConfig.model_validate(data)


# ---------------------------------------------------------------------------
# Public gate (wired into main.py at step 1s)
# ---------------------------------------------------------------------------


def maybe_compile(config: DataLoaderConfig) -> DataLoaderConfig:
    """If funds_flows is populated, compile to FlowIR and emit back into
    the config's resource sections.  Otherwise return the config unchanged.
    """
    if not config.funds_flows:
        return config

    flow_irs = compile_flows(config.funds_flows, config)
    return emit_dataloader_config(flow_irs, base_config=config)
