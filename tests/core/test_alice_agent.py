from __future__ import annotations

from AOA.core.alice_agent import AliceAgent


def test_agent_observes_plans_acts_and_remembers_in_order() -> None:
    calls: list[str] = []

    def runner(task: str) -> str:
        calls.append(task)
        return f"ok {task}"

    agent = AliceAgent(
        task_collector=lambda _prompt: ["queue:open", "queue:refresh"],
        task_runner=runner,
        heavy_predicate=lambda _task: False,
        confirm_heavy=lambda _task: True,
        context_provider=lambda: "aktywny widok: MainPage",
    )

    run = agent.run("otworz i przelicz kolejke")

    assert run is not None
    assert calls == ["queue:open", "queue:refresh"]
    assert run.successful
    assert "Kontekst: aktywny widok: MainPage" in run.format_polish()
    assert "wykonano 2/2" in agent.recent_summary()


def test_agent_confirms_heavy_task_and_stops_after_failure() -> None:
    calls: list[str] = []

    def runner(task: str) -> str:
        calls.append(task)
        if task == "broken":
            raise RuntimeError("kontrola nie przeszla")
        return "ok"

    agent = AliceAgent(
        task_collector=lambda _prompt: ["heavy", "broken", "after"],
        task_runner=runner,
        heavy_predicate=lambda task: task == "heavy",
        confirm_heavy=lambda _task: False,
        context_provider=lambda: "Auto Queue",
    )

    run = agent.run("wykonaj plan")

    assert run is not None
    assert [step.status for step in run.steps] == ["SKIPPED", "ERROR"]
    assert calls == ["broken"]
    assert not run.successful


def test_agent_asks_once_for_all_heavy_steps() -> None:
    confirmations: list[str] = []
    calls: list[str] = []

    def runner(task: str) -> str:
        calls.append(task)
        return "ok"

    def confirm(plan: str) -> bool:
        confirmations.append(plan)
        return True

    agent = AliceAgent(
        task_collector=lambda _prompt: ["heavy-a", "light", "heavy-b"],
        task_runner=runner,
        heavy_predicate=lambda task: task.startswith("heavy"),
        confirm_heavy=confirm,
        context_provider=lambda: "Auto Queue",
    )

    run = agent.run("wykonaj")

    assert run is not None and run.successful
    assert confirmations == ["heavy-a + heavy-b"]
    assert calls == ["heavy-a", "light", "heavy-b"]
