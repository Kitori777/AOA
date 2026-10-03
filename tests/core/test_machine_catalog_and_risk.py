from __future__ import annotations

import pandas as pd
import pytest

from AOA.core.machine_catalog import (
    MachineCapability,
    MachineSpec,
    ReliabilitySpec,
)
from AOA.core.machine_efficiency import build_machine_efficiency, efficiency_summary
from AOA.core.monte_carlo import MonteCarloConfig, simulate_schedule_risk
from AOA.core.optimization.models import Job
from AOA.core.optimization.runner import run_selected_sto_models
from AOA.core.planning import OperationSpec, schedule_operations
from AOA.core.product_routing import ProductRoute, RouteOperation
from AOA.core.production_line import ProductionLineSpec, StationSpec, simulate_production_line
from AOA.core.production_line_designer import PROJECT_SCHEMA_VERSION, ProductionLineDraft
from AOA.core.queue_machine_config import load_queue_machines, save_queue_machines
from AOA.core.scheduling import simulate_schedule


def test_legacy_line_is_migrated_to_individual_machine_profiles() -> None:
    payload = {
        "schema_version": 2,
        "line_id": "legacy",
        "name": "Legacy",
        "stations": [
            {
                "station_id": "cut",
                "name": "Cut",
                "resources": 2,
                "duration_formula": "czas_produkcji_h",
                "cost_formula": "0",
                "waste_formula": "0",
                "quality_formula": "quality",
            }
        ],
    }

    draft = ProductionLineDraft.from_dict(payload)

    assert PROJECT_SCHEMA_VERSION == 3
    assert [machine.machine_id for machine in draft.machines] == ["cut:M1", "cut:M2"]
    assert draft.to_dict()["schema_version"] == 3


def test_machine_catalog_can_bulk_replace_profiles_and_updates_resource_count() -> None:
    draft = ProductionLineDraft(stations=[StationSpec("cut", "Cut", 2)])
    machines = [
        MachineSpec("laser-a", "Laser A", "cut", speed_factor=1.5),
        MachineSpec("laser-b", "Laser B", "cut", speed_factor=0.8),
        MachineSpec("laser-c", "Laser C", "cut", speed_factor=1.1),
    ]

    draft.set_configuration(machines, [])

    assert draft.stations[0].resources == 3
    assert {machine.machine_id for machine in draft.machines} == {
        "laser-a",
        "laser-b",
        "laser-c",
    }


def test_product_route_skips_station_and_restricts_machine() -> None:
    stations = (
        StationSpec("cut", "Cut", 2, "czas_produkcji_h"),
        StationSpec("paint", "Paint", 1, "1"),
        StationSpec("pack", "Pack", 1, "1"),
    )
    machines = (
        MachineSpec("cut:fast", "Fast", "cut", speed_factor=2.0),
        MachineSpec("cut:slow", "Slow", "cut", speed_factor=0.5),
        MachineSpec("paint:M1", "Paint", "paint"),
        MachineSpec("pack:M1", "Pack", "pack"),
    )
    route = ProductRoute(
        "A",
        "Product A",
        (
            RouteOperation("cut", "cut", ("cut:slow",)),
            RouteOperation("pack", "pack", ("pack:M1",)),
        ),
    )
    spec = ProductionLineSpec("line", "Line", stations, machines, (route,))
    jobs = pd.DataFrame(
        {
            "sto_job_id": ["J1"],
            "product_id": ["A"],
            "czas_produkcji_h": [4.0],
            "termin_h": [20.0],
            "quality": [1.0],
        }
    )

    result = simulate_production_line(spec, jobs)

    assert result.machine_events["station_id"].tolist() == ["cut", "pack"]
    assert result.machine_events.iloc[0]["machine_id"] == "cut:slow"
    assert result.machine_events.iloc[0]["czas_produkcji_h"] == 8.0


def test_incompatible_machine_blocks_only_with_clear_reason() -> None:
    machine = MachineSpec(
        "cut:M1",
        "Cotton only",
        "cut",
        capability=MachineCapability(materials=frozenset({"cotton"})),
    )
    spec = ProductionLineSpec(
        "line",
        "Line",
        (StationSpec("cut", "Cut"),),
        (machine,),
    )
    jobs = pd.DataFrame(
        {
            "sto_job_id": ["J1"],
            "material": ["steel"],
            "czas_produkcji_h": [1.0],
            "termin_h": [5.0],
            "quality": [1.0],
        }
    )

    with pytest.raises(ValueError, match="J1.*brak maszyny"):
        simulate_production_line(spec, jobs)


def test_monte_carlo_is_repeatable_and_reports_lost_time() -> None:
    events = pd.DataFrame(
        {
            "sto_job_id": ["J1", "J2"],
            "machine_id": ["M1", "M1"],
            "setup_start": [0.0, 4.0],
            "setup_h": [0.0, 1.0],
            "t_start": [0.0, 5.0],
            "t_end": [4.0, 9.0],
            "czas_produkcji_h": [4.0, 4.0],
            "termin_h": [10.0, 10.0],
        }
    )
    machines = (
        MachineSpec(
            "M1",
            "Machine 1",
            "S1",
            reliability=ReliabilitySpec(
                mtbf_h=2.0,
                mttr_h=1.0,
                post_changeover_failure_probability=1.0,
                post_changeover_risk_window_h=4.0,
                post_changeover_downtime_h=2.0,
            ),
        ),
    )
    config = MonteCarloConfig(iterations=100, seed=7)

    first = simulate_schedule_risk(events, machines, config)
    second = simulate_schedule_risk(events, machines, config)

    pd.testing.assert_frame_equal(first.runs, second.runs)
    assert first.summary["mean_downtime_h"] > 0
    assert first.summary["p90_makespan_h"] >= first.summary["mean_makespan_h"]
    assert first.machine_summary.iloc[0]["downtime_probability"] == 1.0


def test_efficiency_report_contains_operational_and_risk_metrics() -> None:
    events = pd.DataFrame(
        {
            "machine_id": ["M1", "M1"],
            "machine_name": ["Machine 1", "Machine 1"],
            "station_id": ["S1", "S1"],
            "t_start": [0.0, 3.0],
            "t_end": [2.0, 5.0],
            "czas_produkcji_h": [2.0, 2.0],
            "base_duration_h": [2.0, 2.0],
            "setup_h": [0.0, 1.0],
            "lateness_h": [0.0, 1.0],
            "quality": [0.98, 0.96],
            "cost": [10.0, 12.0],
            "waste": [0.1, 0.2],
            "energy_kwh": [4.0, 4.0],
        }
    )

    report = build_machine_efficiency(events)
    summary = efficiency_summary(report)

    assert report.iloc[0]["productive_h"] == 4.0
    assert report.iloc[0]["setup_h"] == 1.0
    assert report.iloc[0]["late_jobs"] == 1
    assert 0 < report.iloc[0]["estimated_oee_pct"] <= 100
    assert summary["machines"] == 1


def test_robust_mc_is_registered_repeatable_and_exposes_risk_summary() -> None:
    jobs = [
        Job("A", 3.0, 4.0, setup_time=0.5),
        Job("B", 2.0, 8.0, setup_time=0.5),
        Job("C", 1.0, 6.0, setup_time=0.5),
    ]

    first = run_selected_sto_models(jobs, ["ROBUST_MC"], n_machines=2)[0]
    second = run_selected_sto_models(jobs, ["ROBUST_MC"], n_machines=2)[0]

    assert first["order"] == second["order"]
    assert first["risk_summary"] == second["risk_summary"]
    assert first["risk_summary"]["iterations"] == 1000
    assert first["risk_summary"]["p90_makespan_h"] >= first["makespan_h"]


def test_auto_queue_machine_profiles_are_persisted_and_affect_dispatch(tmp_path) -> None:
    queue_path = tmp_path / "queue.csv"
    queue_path.write_text("zlecenie_id,czas_produkcji_h,termin_h\n", encoding="utf-8")
    machines = [
        MachineSpec(
            "fast-cotton",
            "Fast cotton",
            "QUEUE",
            speed_factor=2.0,
            capability=MachineCapability(materials=frozenset({"cotton"})),
        ),
        MachineSpec(
            "slow-steel",
            "Slow steel",
            "QUEUE",
            speed_factor=0.5,
            capability=MachineCapability(materials=frozenset({"steel"})),
        ),
    ]
    path = save_queue_machines(queue_path, machines)
    restored = load_queue_machines(queue_path, 2)
    jobs = pd.DataFrame(
        {
            "sto_job_id": ["A", "B"],
            "material": ["cotton", "steel"],
            "czas_produkcji_h": [4.0, 4.0],
            "termin_h": [20.0, 20.0],
        }
    )

    scheduled = simulate_schedule(jobs, n_machines=2, machine_specs=restored)

    assert path.exists()
    assert scheduled["machine_external_id"].tolist() == ["fast-cotton", "slow-steel"]
    assert scheduled["t_end"].tolist() == [2.0, 8.0]


def test_operation_scheduler_uses_machine_capability_and_speed() -> None:
    machines = (
        MachineSpec(
            "M1",
            "Cotton fast",
            "QUEUE",
            speed_factor=2.0,
            capability=MachineCapability(materials=frozenset({"cotton"})),
        ),
        MachineSpec(
            "M2",
            "Steel",
            "QUEUE",
            capability=MachineCapability(materials=frozenset({"steel"})),
        ),
    )
    operation = OperationSpec(
        "OP1",
        "A",
        4.0,
        10.0,
        material="cotton",
        product_id="P1",
    )

    result = schedule_operations([operation], machine_count=2, machine_specs=machines)

    assert result.steps[0].machine_id == 1
    assert result.steps[0].end_h == 2.0
