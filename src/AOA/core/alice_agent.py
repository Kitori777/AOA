from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class AgentStep:
    task: str
    status: str
    observation: str


@dataclass(frozen=True)
class AgentRun:
    prompt: str
    context: str
    plan: tuple[str, ...]
    steps: tuple[AgentStep, ...]
    started_at: str

    @property
    def successful(self) -> bool:
        return bool(self.steps) and all(step.status in {"DONE", "SKIPPED"} for step in self.steps)

    def format_polish(self) -> str:
        plan_text = ", ".join(self.plan)
        execution = "\n".join(
            f"{index}. [{step.status}] {step.task}: {step.observation}"
            for index, step in enumerate(self.steps, start=1)
        )
        if self.successful:
            result = "Plan zakonczony. Sprawdzilam odpowiedzi wykonanych operacji."
        else:
            result = "Plan zakonczyl sie z bledem; dalsze bezpieczne kroki zostaly zatrzymane."
        return (
            f"Cel: {self.prompt}\n"
            f"Kontekst: {self.context}\n"
            f"Plan: {plan_text}\n"
            f"Wykonanie:\n{execution}\n"
            f"Wynik: {result}"
        )


class AliceAgent:
    """Bounded local agent that can only invoke explicitly mapped AOA actions."""

    def __init__(
        self,
        *,
        task_collector: Callable[[str], list[str]],
        task_runner: Callable[[str], str],
        heavy_predicate: Callable[[str], bool],
        confirm_heavy: Callable[[str], bool],
        context_provider: Callable[[], str],
        memory_size: int = 8,
    ) -> None:
        self.task_collector = task_collector
        self.task_runner = task_runner
        self.heavy_predicate = heavy_predicate
        self.confirm_heavy = confirm_heavy
        self.context_provider = context_provider
        self.memory: deque[AgentRun] = deque(maxlen=max(1, memory_size))

    def run(self, prompt: str) -> AgentRun | None:
        plan = tuple(self.task_collector(prompt))
        if not plan:
            return None
        context = self.context_provider() or "nieznany widok"
        steps: list[AgentStep] = []
        heavy_tasks = tuple(task for task in plan if self.heavy_predicate(task))
        heavy_allowed = True
        if heavy_tasks:
            heavy_allowed = self.confirm_heavy(" + ".join(heavy_tasks))
        for task in plan:
            if self.heavy_predicate(task) and not heavy_allowed:
                steps.append(AgentStep(task, "SKIPPED", "anulowane przez uzytkownika"))
                continue
            try:
                reply = str(self.task_runner(task)).strip() or "operacja zakonczona bez komunikatu"
            except Exception as exc:
                steps.append(AgentStep(task, "ERROR", str(exc)))
                break
            steps.append(AgentStep(task, "DONE", reply))
        run = AgentRun(
            prompt=prompt,
            context=context,
            plan=plan,
            steps=tuple(steps),
            started_at=datetime.now(UTC).isoformat(),
        )
        self.memory.append(run)
        return run

    def recent_summary(self) -> str:
        if not self.memory:
            return "Brak wykonanych planow."
        latest = self.memory[-1]
        done = sum(step.status == "DONE" for step in latest.steps)
        return f"Ostatni plan: {latest.prompt}; wykonano {done}/{len(latest.plan)} krokow."
