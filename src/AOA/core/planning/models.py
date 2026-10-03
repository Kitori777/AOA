from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OperationSpec:
    operation_id: str
    order_id: str
    processing_time_h: float
    deadline_h: float
    predecessors: tuple[str, ...] = ()
    eligible_machines: tuple[int, ...] = ()
    components_ready_h: float = 0.0
    setup_time_h: float = 0.0
    waste_kg: float = 0.0
    energy_kwh: float = 0.0
    priority: int = 0
    frozen: bool = False
    started: bool = False
    fixed_machine_id: int | None = None
    fixed_start_h: float | None = None
    station_type: str = ""
    product_id: str = ""
    material: str = ""


@dataclass(frozen=True)
class OperationStep:
    operation_id: str
    order_id: str
    machine_id: int
    start_h: float
    end_h: float
    deadline_h: float
    tardiness_h: float
    components_ready_h: float
    predecessor_ready_h: float
    frozen: bool
    started: bool
    reason: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()
    topological_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanningResult:
    steps: tuple[OperationStep, ...]
    violations: tuple[str, ...]
    unscheduled: tuple[str, ...]
    machine_count: int
    total_tardiness_h: float
    makespan_h: float
    total_waste_kg: float
    total_energy_kwh: float
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def feasible(self) -> bool:
        return not self.violations and not self.unscheduled
