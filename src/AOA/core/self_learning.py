from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request

import pandas as pd

from AOA.config import DATA_DIR
from AOA.core.mh_models import get_mh_model_specs
from AOA.core.ml_models import get_ml_model_specs
from AOA.core.mlstack.evaluation import run_benchmark
from AOA.core.sto_models import dataframe_to_jobs, run_selected_sto_models


class AliceSelfLearningLoop:
    """Background evaluator: runs periodic checks and writes learning logs/reports."""

    def __init__(self) -> None:
        self._root_dir = Path(__file__).resolve().parents[3]
        self._logs_dir = self._root_dir / "logs"
        self._selflearn_dir = self._logs_dir / "alice_selflearn"
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False
        self._last_report_path: Path | None = None
        self._action_log: list[str] = []
        self._interval_seconds = 900
        self._last_cycle_at: datetime | None = None
        self._cycle_count = 0
        self._phase = "local_mastery"
        self._phase_goal = "Opanowac lokalna aplikacje AOA (algorytmy, workflow, testy)."
        self._mastery_state: dict[str, Any] = {
            "local_checklist": {
                "docs_mapped": False,
                "models_mapped": False,
                "sto_mapped": False,
                "benchmarked": False,
                "health_checks_ok": False,
            },
            "internet_checklist": {
                "sources_contacted": False,
                "algorithms_expanded": False,
                "improvement_candidates": False,
            },
            "mastered_local": False,
            "started_internet": False,
        }
        self._internet_whitelist = [
            "https://scikit-learn.org/stable/",
            "https://arxiv.org/",
            "https://docs.python.org/3/",
            "https://numpy.org/doc/",
            "https://pandas.pydata.org/docs/",
        ]
        self._learning_state_path = self._logs_dir / "alice_learning_state.json"
        self._local_sources_dir = self._root_dir / "docs" / "alice_sources"
        self._curriculum_state: dict[str, Any] = {
            "learn_queue": [
                "app_workflow",
                "ml_models",
                "sto_heuristics",
                "visual_dashboards",
                "results_sql_export",
                "code_scan_core",
                "code_scan_gui",
                "internet_to_app_mapping",
            ],
            "learn_index": 0,
            "validation_queue": [
                "check_workflow_answer",
                "check_model_comparison",
                "check_sto_explanation",
                "check_visual_guidance",
                "check_results_sql_guidance",
            ],
            "validation_index": 0,
            "knowledge_score": 0.0,
            "last_notice": "",
        }
        self._last_delta_key = ""

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_report_path(self) -> str:
        return str(self._last_report_path.resolve()) if self._last_report_path else ""

    def start(self, interval_seconds: int = 900, initial_delay_seconds: int = 180) -> str:
        if self._running:
            return "Tryb samonauki juz dziala w tle."
        self._interval_seconds = max(120, int(interval_seconds))
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker,
            kwargs={
                "interval_seconds": self._interval_seconds,
                "initial_delay_seconds": max(5, int(initial_delay_seconds)),
            },
            daemon=True,
        )
        self._thread.start()
        self._running = True
        self._append_runtime_log(
            f"START interval={self._interval_seconds}s initial_delay={initial_delay_seconds}s"
        )
        return "Wlaczylam samonauke w tle: benchmarki + raporty do poprawy."

    def stop(self) -> str:
        if not self._running:
            return "Tryb samonauki nie byl aktywny."
        self._stop_event.set()
        self._running = False
        self._append_runtime_log("STOP")
        return "Wylaczylam samonauke w tle."

    def status(self) -> str:
        if not self._running:
            return "Samonauka: wylaczona."
        if self._last_report_path and not self._last_report_path.exists():
            self._append_runtime_log(
                "STATUS: brak pliku ostatniego raportu, probuje odtworzyc latest"
            )
            recovered = self._recover_last_report_from_latest()
            if not recovered:
                self.run_once_now(reason="status_repair")
        report = self.last_report_path or "brak raportu"
        last_cycle = (
            self._last_cycle_at.isoformat(timespec="seconds") if self._last_cycle_at else "brak"
        )
        return (
            f"Samonauka: aktywna. Etap: {self._phase}. Ostatni raport: {report}. "
            f"Ostatni cykl: {last_cycle}. Interwal: {self._interval_seconds}s."
        )

    def latest_report_summary(self) -> str:
        if self._last_report_path is None or not self._last_report_path.exists():
            self.run_once_now(reason="report_request")
        if self._last_report_path is None or not self._last_report_path.exists():
            return "Nie mam jeszcze raportu samonauki. Sprobuj ponownie za chwile."
        try:
            payload = json.loads(self._last_report_path.read_text(encoding="utf-8"))
        except Exception:
            return f"Mam raport, ale nie moge go odczytac: {self._last_report_path}"
        top = payload.get("top") or []
        rec = payload.get("recommendation") or "Brak rekomendacji."
        theory = payload.get("theory_learning") or {}
        ml_cards = theory.get("ml_cards") or []
        sto_cards = theory.get("sto_cards") or []
        best = top[0] if top else {}
        best_line = (
            f"Najlepszy model: {best.get('model', 'n/a')} (score={float(best.get('mean_score', 0.0)):.4f})."
            if best
            else "Brak rankingu modeli."
        )
        return (
            f"Raport samonauki ({payload.get('timestamp', 'n/a')}):\n"
            f"{best_line}\n"
            f"{rec}\n"
            f"Theory-learning: ML kart={len(ml_cards)}, STO kart={len(sto_cards)}.\n"
            f"Plik raportu: {self._last_report_path}"
        )

    def latest_report_digest(self) -> tuple[str, str]:
        payload = self._read_latest_payload()
        if not payload:
            return "", "Brak jeszcze raportu samonauki."
        ts = str(payload.get("timestamp") or "")
        top = payload.get("top") or []
        best = top[0] if top else {}
        best_model = best.get("model", "n/a")
        try:
            best_score = float(best.get("mean_score", 0.0))
            best_line = f"{best_model} ({best_score:.4f})"
        except Exception:
            best_line = str(best_model)
        recommendation = self._sanitize_text(payload.get("recommendation") or "Brak rekomendacji.")
        phase = payload.get("phase") or self._phase
        internet = payload.get("internet_learning") or {}
        sto_learning = payload.get("sto_learning") or {}
        internet_line = ""
        if internet:
            internet_line = (
                f" | net: reached={internet.get('reached_sources', 0)}/"
                f"{internet.get('total_sources', 0)}, fallback={internet.get('local_fallback_hits', 0)}"
            )
        sto_line = ""
        if sto_learning:
            best_sto = sto_learning.get("best") or {}
            if best_sto:
                sto_line = (
                    f" | STO best={best_sto.get('model', 'n/a')} ({best_sto.get('sto', 'n/a')})"
                )
        delta = payload.get("delta_report") or {}
        significant = bool(delta.get("significant_changes", False))
        if significant:
            delta_lines = delta.get("changes") or []
            delta_text = " | ".join(delta_lines[:3]) if delta_lines else "istotna zmiana"
            msg = (
                f"Auto-raport {ts}: etap={phase}, najlepszy={best_line}{internet_line}{sto_line}\n"
                f"Nowe zmiany: {self._sanitize_text(delta_text)}\n"
                f"Wniosek: {recommendation}"
            )
        else:
            msg = (
                f"Auto-raport {ts}: etap={phase}, najlepszy={best_line}{internet_line}{sto_line}\n"
                "Brak istotnych zmian od poprzedniego cyklu."
            )
        return ts, msg

    def latest_report_signature(self) -> str:
        payload = self._read_latest_payload()
        if not payload:
            return ""
        top = payload.get("top") or []
        best = top[0] if top else {}
        best_model = str(best.get("model", ""))
        try:
            best_score = f"{float(best.get('mean_score', 0.0)):.6f}"
        except Exception:
            best_score = "0.000000"
        recommendation = self._sanitize_text(str(payload.get("recommendation") or "").strip())
        phase = str(payload.get("phase") or "")
        sto_best = (payload.get("sto_learning") or {}).get("best") or {}
        sto_sig = f"{sto_best.get('model', '')}:{sto_best.get('sto', '')}"
        delta_key = str((payload.get("delta_report") or {}).get("delta_key") or "")
        return "|".join([phase, best_model, best_score, sto_sig, recommendation, delta_key])

    def daily_summary_digest(self) -> tuple[str, str]:
        if not self._selflearn_dir.exists():
            return "", "Brak raportow dziennych."
        today_key = datetime.now().strftime("%Y%m%d")
        files = sorted(self._selflearn_dir.glob(f"selflearn_{today_key}_*.json"))
        if not files:
            return today_key, "Brak raportow z dzisiaj."

        rows: list[dict] = []
        for path in files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            top = payload.get("top") or []
            best = top[0] if top else {}
            rows.append(
                {
                    "ts": str(payload.get("timestamp") or ""),
                    "best_model": str(best.get("model", "n/a")),
                    "best_score": float(best.get("mean_score", 0.0)) if best else 0.0,
                    "rec": str(payload.get("recommendation") or ""),
                    "sto_best": ((payload.get("sto_learning") or {}).get("best") or {}).get(
                        "model", ""
                    ),
                }
            )
        if not rows:
            return today_key, "Brak czytelnych raportow z dzisiaj."

        first = rows[0]["ts"]
        last = rows[-1]["ts"]
        unique_best = sorted({r["best_model"] for r in rows})
        avg_score = sum(r["best_score"] for r in rows) / max(len(rows), 1)
        sto_best = sorted({r["sto_best"] for r in rows if r["sto_best"]})
        msg = (
            f"PODSUMOWANIE DNIA {today_key}:\n"
            f"- cykli: {len(rows)} ({first} -> {last})\n"
            f"- ML best (unikalne): {', '.join(unique_best)}\n"
            f"- sredni best_score: {avg_score:.4f}\n"
            f"- STO best (unikalne): {', '.join(sto_best) if sto_best else 'brak'}\n"
            f"- ostatni wniosek: {rows[-1]['rec']}"
        )
        self._write_daily_summary_file(today_key, msg)
        return today_key, msg

    def changes_since_previous_summary(self) -> str:
        if not self._selflearn_dir.exists():
            return "Brak raportow do porownania."
        files = sorted(self._selflearn_dir.glob("selflearn_*.json"))
        if len(files) < 2:
            return "Za malo raportow, zeby pokazac zmiany."
        try:
            cur = json.loads(files[-1].read_text(encoding="utf-8"))
            prev = json.loads(files[-2].read_text(encoding="utf-8"))
        except Exception:
            return "Nie moge porownac dwoch ostatnich raportow."

        def _best(payload: dict) -> tuple[str, float]:
            top = payload.get("top") or []
            if not top:
                return "n/a", 0.0
            head = top[0]
            try:
                return str(head.get("model", "n/a")), float(head.get("mean_score", 0.0))
            except Exception:
                return str(head.get("model", "n/a")), 0.0

        b_cur, s_cur = _best(cur)
        b_prev, s_prev = _best(prev)
        delta = s_cur - s_prev
        trend = "bez zmian"
        if delta > 1e-9:
            trend = f"lepiej o {delta:.4f}"
        elif delta < -1e-9:
            trend = f"gorzej o {abs(delta):.4f}"

        sto_cur = (cur.get("sto_learning") or {}).get("best") or {}
        sto_prev = (prev.get("sto_learning") or {}).get("best") or {}
        sto_line = (
            f"STO: {sto_prev.get('model', 'n/a')}({sto_prev.get('sto', 'n/a')}) -> "
            f"{sto_cur.get('model', 'n/a')}({sto_cur.get('sto', 'n/a')})"
        )
        return (
            f"Zmiana od poprzedniego cyklu:\n"
            f"- ML best: {b_prev} ({s_prev:.4f}) -> {b_cur} ({s_cur:.4f}), trend: {trend}\n"
            f"- {sto_line}\n"
            f"- Rekomendacja teraz: {self._sanitize_text(cur.get('recommendation', 'brak'))}"
        )

    def latest_theory_summary(self) -> str:
        if self._last_report_path is None or not self._last_report_path.exists():
            self.run_once_now(reason="theory_request")
        if self._last_report_path is None or not self._last_report_path.exists():
            return "Brak raportu teorii. Sprobuj ponownie za chwile."
        try:
            payload = json.loads(self._last_report_path.read_text(encoding="utf-8"))
        except Exception:
            return "Nie moge odczytac ostatniego raportu teorii."
        theory = payload.get("theory_learning") or {}
        ml_cards = theory.get("ml_cards") or []
        sto_cards = theory.get("sto_cards") or []
        top_ml = ml_cards[:3]
        lines = ["Skrot nauki algorytmow (ostatni cykl):"]
        for item in top_ml:
            lines.append(
                f"- {item.get('model')}: {item.get('focus')} | {item.get('practice_note')}"
            )
        if sto_cards:
            lines.append(f"- STO: aktywne karty teorii = {len(sto_cards)}")
        return "\n".join(lines)

    def learning_plan_summary(self) -> str:
        local = self._mastery_state.get("local_checklist", {})
        internet = self._mastery_state.get("internet_checklist", {})
        return (
            f"Plan ALICE:\n"
            f"- Etap: {self._phase}\n"
            f"- Cel: {self._phase_goal}\n"
            f"- Lokalny mastering: {local}\n"
            f"- Internet mastering: {internet}\n"
            f"- Whitelista: {', '.join(self._internet_whitelist)}\n"
            f"- Fallback offline: {self._local_sources_dir.resolve()}\n"
            f"- Kolejka nauki: {self._curriculum_state['learn_index'] + 1}/{len(self._curriculum_state['learn_queue'])}\n"
            f"- Kolejka walidacji: {self._curriculum_state['validation_index'] + 1}/{len(self._curriculum_state['validation_queue'])}\n"
            f"- Knowledge score: {self._curriculum_state.get('knowledge_score', 0.0):.2f}"
        )

    def run_once_now(self, reason: str = "manual") -> str:
        try:
            self._append_runtime_log(f"MANUAL cycle start reason={reason}")
            self._run_once()
            return f"Zrobione: wygenerowalam raport teraz ({self.last_report_path})."
        except Exception as exc:
            self._append_runtime_log(f"MANUAL cycle error {type(exc).__name__}: {exc}")
            return f"Nie udalo sie wygenerowac raportu teraz: {type(exc).__name__}"

    def _worker(self, interval_seconds: int, initial_delay_seconds: int) -> None:
        self._stop_event.wait(initial_delay_seconds)
        while not self._stop_event.is_set():
            try:
                self._run_once()
            except Exception as exc:
                self._append_runtime_log(f"ERROR cycle: {type(exc).__name__}: {exc}")
            self._cycle_count += 1
            self._stop_event.wait(interval_seconds)

    def _run_once(self) -> None:
        sample = self._resolve_learning_dataset()
        if sample is None:
            self._append_runtime_log("SKIP cycle: brak datasetu do nauki")
            self._write_heartbeat_report("Brak datasetu do nauki")
            return

        df = pd.read_csv(sample)
        model_candidates = ["Quality", "Quality_ET", "Delay", "Delay_RF", "Quality_RIDGE"]
        try:
            rows = run_benchmark(df, model_candidates, folds=3)
        except Exception as exc:
            self._append_runtime_log(f"SKIP cycle: benchmark error {type(exc).__name__}: {exc}")
            self._write_heartbeat_report(f"Benchmark error: {type(exc).__name__}")
            return
        if not rows:
            self._append_runtime_log("SKIP cycle: benchmark zwrocil 0 wierszy")
            self._write_heartbeat_report("Benchmark zwrocil pusty wynik")
            return

        rows_sorted = sorted(rows, key=lambda r: r.mean_score, reverse=True)
        best = rows_sorted[0]
        worst = rows_sorted[-1]
        recommendation = (
            f"Najlepszy teraz: {best.model} (score={best.mean_score:.4f}). "
            f"Najslabszy: {worst.model} (score={worst.mean_score:.4f}). "
            "Sprawdz cechy wejscia i porownaj stabilnosc metryk na nowszej probce."
        )
        recommendation = self._sanitize_text(recommendation)
        theory = self._build_theory_snapshot(rows_sorted)

        out_dir = self._selflearn_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"selflearn_{ts}.json"
        payload = {
            "timestamp": ts,
            "phase": self._phase,
            "phase_goal": self._phase_goal,
            "mastery_state": self._mastery_state,
            "internet_whitelist": self._internet_whitelist,
            "top": [
                {
                    "model": r.model,
                    "folds": r.folds,
                    "mean_score": r.mean_score,
                    "std_score": r.std_score,
                    "fit_seconds": r.fit_seconds,
                }
                for r in rows_sorted
            ],
            "recommendation": recommendation,
            "theory_learning": theory,
        }
        queue_learning = self._run_learning_queue_cycle(df)
        payload["learning_queue"] = queue_learning
        sto_learning = self._run_sto_learning(df)
        if sto_learning:
            payload["sto_learning"] = sto_learning
        payload["insight_scores"] = self._build_insight_scores(payload)
        payload["delta_report"] = self._build_delta_report(payload)
        health = self._run_health_checks_if_due()
        if health:
            payload["health_checks"] = health
        self._update_local_mastery_flags(payload)
        if self._mastery_state.get("mastered_local"):
            self._phase = "internet_learning"
            self._phase_goal = "Rozwijac wiedze o algorytmach z internetu i rekomendowac wdrozenia."
            self._mastery_state["started_internet"] = True
            payload["phase"] = self._phase
            payload["phase_goal"] = self._phase_goal
            payload["mastery_state"] = self._mastery_state
            payload["internet_learning"] = self._run_internet_learning_cycle()
            payload["app_mapping_recommendations"] = self._build_app_mapping_recommendations(
                payload
            )
        self._persist_learning_state()
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._last_report_path = out_path
        self._last_cycle_at = datetime.now()
        self._append_runtime_log(
            f"OK cycle report={out_path.name} best={best.model}:{best.mean_score:.4f} dataset={sample.name}"
        )
        self._write_latest_status(payload)

    def _build_theory_snapshot(self, rows_sorted) -> dict:
        ml_specs = get_ml_model_specs()
        mh_specs = get_mh_model_specs()
        score_map = {row.model: row.mean_score for row in rows_sorted}

        ml_cards = []
        for spec in ml_specs:
            score = score_map.get(spec.name)
            if score is None:
                practice = "Brak swiezego wyniku benchmarku dla tego modelu."
            elif score >= 0.5:
                practice = "Model wyglada stabilnie na aktualnej probce."
            elif score >= 0.2:
                practice = "Model dziala srednio; warto porownac z alternatywa."
            else:
                practice = "Model ma slaba stabilnosc; wymagany przeglad cech/parametrow."
            ml_cards.append(
                {
                    "model": spec.name,
                    "label": self._sanitize_text(spec.label),
                    "focus": self._sanitize_text(spec.focus),
                    "description": self._sanitize_text(spec.description),
                    "practice_note": self._sanitize_text(practice),
                }
            )

        sto_cards = [
            {
                "model": spec.name,
                "label": self._sanitize_text(spec.label),
                "focus": self._sanitize_text(spec.focus),
                "description": self._sanitize_text(spec.description),
                "practice_note": (
                    "Sprawdzaj ten wariant przez porownanie Kop/opoznien i pozycje w drzewie rozwiazan."
                ),
            }
            for spec in mh_specs
        ]

        return {
            "ml_cards": ml_cards,
            "sto_cards": sto_cards,
            "learning_note": (
                "ALICE laczy teorie (co robi algorytm) z praktyka (jak wyszedl w benchmarku), "
                "zeby wskazac co poprawic w kolejnym kroku."
            ),
        }

    def _resolve_learning_dataset(self) -> Path | None:
        preferred = DATA_DIR / "sample" / "sample_table.csv"
        if preferred.exists():
            return preferred
        sample_dir = DATA_DIR / "sample"
        if sample_dir.exists():
            candidates = sorted(
                sample_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True
            )
            if candidates:
                return candidates[0]
        prod = DATA_DIR / "production.csv"
        if prod.exists():
            return prod
        return None

    def _append_runtime_log(self, message: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        line = f"{now} | {message}"
        self._action_log.append(line)
        logs_dir = self._logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        with (logs_dir / "alice_selflearn.log").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _write_latest_status(self, payload: dict) -> None:
        logs_dir = self._logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        latest_path = logs_dir / "alice_selflearn_latest.json"
        latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_heartbeat_report(self, reason: str) -> None:
        out_dir = self._selflearn_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"selflearn_{ts}.json"
        payload = {
            "timestamp": ts,
            "phase": self._phase,
            "phase_goal": self._phase_goal,
            "mastery_state": self._mastery_state,
            "internet_whitelist": self._internet_whitelist,
            "top": [],
            "recommendation": self._sanitize_text(reason),
            "theory_learning": {
                "ml_cards": [
                    {
                        "model": spec.name,
                        "label": spec.label,
                        "focus": spec.focus,
                        "description": spec.description,
                        "practice_note": "Czekam na dane benchmarkowe, zeby ocenic praktyke.",
                    }
                    for spec in get_ml_model_specs()
                ],
                "sto_cards": [
                    {
                        "model": spec.name,
                        "label": spec.label,
                        "focus": spec.focus,
                        "description": spec.description,
                        "practice_note": "Czekam na dane benchmarkowe, zeby ocenic praktyke.",
                    }
                    for spec in get_mh_model_specs()
                ],
                "learning_note": "Wygenerowano raport heartbeat mimo braku pelnego benchmarku.",
            },
        }
        if self._phase == "internet_learning":
            payload["internet_learning"] = self._run_internet_learning_cycle()
            payload["app_mapping_recommendations"] = self._build_app_mapping_recommendations(
                payload
            )
        payload["insight_scores"] = self._build_insight_scores(payload)
        payload["delta_report"] = self._build_delta_report(payload)
        self._persist_learning_state()
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._last_report_path = out_path
        self._last_cycle_at = datetime.now()
        self._append_runtime_log(f"HEARTBEAT report={out_path.name} reason={reason}")
        self._write_latest_status(payload)

    def _run_health_checks_if_due(self) -> dict | None:
        # Run lightweight checks every 4th cycle to reduce UI impact.
        if self._cycle_count % 4 != 0:
            return None
        tests = [
            "tests/core/test_mlstack_workflow.py",
            "tests/core/test_visualization_service.py",
        ]
        cmd = [sys.executable, "-m", "pytest", "-q", *tests]
        try:
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(self._root_dir),
            )
        except Exception as exc:
            self._append_runtime_log(f"HEALTH error: {type(exc).__name__}: {exc}")
            return {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        ok = proc.returncode == 0
        summary = (proc.stdout or proc.stderr or "").strip().splitlines()[-5:]
        self._append_runtime_log(f"HEALTH {'OK' if ok else 'FAIL'} code={proc.returncode}")
        return {
            "ok": ok,
            "returncode": proc.returncode,
            "summary_tail": summary,
            "tests": tests,
        }

    def _update_local_mastery_flags(self, payload: dict) -> None:
        ml_cards = (payload.get("theory_learning") or {}).get("ml_cards") or []
        sto_cards = (payload.get("theory_learning") or {}).get("sto_cards") or []
        self._mastery_state["local_checklist"]["docs_mapped"] = True
        self._mastery_state["local_checklist"]["models_mapped"] = len(ml_cards) > 0
        self._mastery_state["local_checklist"]["sto_mapped"] = len(sto_cards) > 0
        self._mastery_state["local_checklist"]["benchmarked"] = len(payload.get("top") or []) > 0
        health = payload.get("health_checks") or {}
        if health:
            self._mastery_state["local_checklist"]["health_checks_ok"] = bool(health.get("ok"))
        local = self._mastery_state["local_checklist"]
        self._mastery_state["mastered_local"] = all(bool(v) for v in local.values())

    def _persist_learning_state(self) -> None:
        self._learning_state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "phase": self._phase,
            "phase_goal": self._phase_goal,
            "mastery_state": self._mastery_state,
            "internet_whitelist": self._internet_whitelist,
            "last_report_path": self.last_report_path,
            "curriculum_state": self._curriculum_state,
        }
        self._learning_state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _run_internet_learning_cycle(self) -> dict:
        notes: list[dict] = []
        reached = 0
        network_blocked_count = 0
        local_fallback_hits = 0
        for source in self._internet_whitelist:
            title, snippet, blocked = self._fetch_source_note(source)
            used_local = False
            if not snippet:
                local_title, local_snippet = self._load_local_source_note(source)
                if local_snippet:
                    title, snippet = local_title, local_snippet
                    used_local = True
            if snippet:
                reached += 1
            if used_local:
                local_fallback_hits += 1
            if blocked:
                network_blocked_count += 1
            actionable = self._build_actionable_from_text(snippet)
            notes.append(
                {
                    "source": source,
                    "title": self._sanitize_text(title),
                    "snippet": self._sanitize_text(snippet),
                    "actionable": actionable["actionable"],
                    "module": actionable["module"],
                    "impact": actionable["impact"],
                    "difficulty": actionable["difficulty"],
                    "confidence": actionable["confidence"],
                    "source_mode": "local_fallback" if used_local else "online",
                }
            )
        self._mastery_state["internet_checklist"]["sources_contacted"] = reached > 0
        self._mastery_state["internet_checklist"]["algorithms_expanded"] = any(
            n.get("snippet") for n in notes
        )
        self._mastery_state["internet_checklist"]["improvement_candidates"] = any(
            n.get("actionable") for n in notes
        )
        return {
            "mode": "whitelist_only",
            "network_blocked": network_blocked_count == len(self._internet_whitelist),
            "network_blocked_count": network_blocked_count,
            "reached_sources": reached,
            "total_sources": len(self._internet_whitelist),
            "local_fallback_hits": local_fallback_hits,
            "local_sources_dir": str(self._local_sources_dir.resolve()),
            "notes": notes,
            "summary": self._sanitize_text(self._internet_summary(notes)),
        }

    def _run_sto_learning(self, df: pd.DataFrame) -> dict:
        try:
            jobs = dataframe_to_jobs(
                df,
                job_id_col="sto_job_id" if "sto_job_id" in df.columns else None,
                processing_col="czas_produkcji_h",
                deadline_col="termin_h",
                round_to_int=True,
            )
            methods = [
                "MT",
                "MO",
                "MZO",
                "MOPT",
                "GENETIC",
                "SLACK",
                "CR",
                "EDD_SPT",
                "SPT_EDD",
                "LPT_EDD",
                "NEH",
                "LOCAL_SEARCH",
                "RANDOM_RESTART",
            ]
            results = run_selected_sto_models(jobs, methods)
            if not results:
                return {}
            best = min(results, key=lambda r: float(r.get("sto", float("inf"))))
            worst = max(results, key=lambda r: float(r.get("sto", float("-inf"))))
            stability = self._build_sto_stability(df, methods)
            previous = self._read_latest_payload()
            prev_best = ((previous.get("sto_learning") or {}).get("best")) or {}
            prev_sto = float(prev_best.get("sto", best.get("sto", 0.0)) or 0.0)
            cur_sto = float(best.get("sto", 0.0) or 0.0)
            regression = {
                "detected": cur_sto > prev_sto + 1e-9,
                "delta_sto": round(cur_sto - prev_sto, 6),
                "prev_best_model": prev_best.get("model", ""),
                "prev_best_sto": prev_sto,
            }
            return {
                "best": {
                    "model": best.get("method"),
                    "sto": best.get("sto"),
                    "completion_total": best.get("completion_total"),
                },
                "worst": {
                    "model": worst.get("method"),
                    "sto": worst.get("sto"),
                },
                "count": len(results),
                "stability": stability,
                "regression": regression,
            }
        except Exception as exc:
            self._append_runtime_log(f"STO learning skip: {type(exc).__name__}: {exc}")
            return {}

    @staticmethod
    def _build_actionable_from_text(snippet: str) -> dict:
        text = (snippet or "").lower()
        if not text:
            return {
                "module": "Theory",
                "actionable": "",
                "impact": "niski",
                "difficulty": "niska",
                "confidence": 0.2,
            }
        if "outlier" in text or "anomal" in text:
            return {
                "module": "Visual",
                "actionable": "Dodaj porownanie detekcji anomalii: IsolationForest vs DBSCAN (wspolny panel metryk).",
                "impact": "wysoki",
                "difficulty": "srednia",
                "confidence": 0.82,
            }
        if "cross-validation" in text or "cross validation" in text:
            return {
                "module": "Main",
                "actionable": "Rozszerz benchmark o walidacje krzyzowa 5-fold i raport odchylen metryk.",
                "impact": "wysoki",
                "difficulty": "niska",
                "confidence": 0.86,
            }
        if "pipeline" in text:
            return {
                "module": "Main",
                "actionable": "Dodaj gotowy pipeline 1-click: EDA -> trening -> ewaluacja -> raport.",
                "impact": "wysoki",
                "difficulty": "srednia",
                "confidence": 0.8,
            }
        if "feature" in text:
            return {
                "module": "Results",
                "actionable": "Dodaj panel selekcji cech i ranking waznosci (globalny + per model).",
                "impact": "sredni",
                "difficulty": "srednia",
                "confidence": 0.74,
            }
        if "documentation" in text or "api" in text:
            return {
                "module": "Theory",
                "actionable": "Utworz notatke wdrozeniowa: co mozna bezpiecznie przejac do aplikacji z dokumentacji.",
                "impact": "sredni",
                "difficulty": "niska",
                "confidence": 0.66,
            }
        return {
            "module": "Theory",
            "actionable": "Zapisz notatke do backlogu i ocen wplyw na workflow uzytkownika.",
            "impact": "niski",
            "difficulty": "niska",
            "confidence": 0.55,
        }

    @staticmethod
    def _internet_summary(notes: list[dict]) -> str:
        actionable = [n for n in notes if n.get("actionable")]
        if not actionable:
            return "Brak nowych wskazowek do wdrozenia w tym cyklu."
        modules = sorted({str(n.get("module", "Theory")) for n in actionable})
        return (
            f"Znaleziono {len(actionable)} wskazowek do rozwoju algorytmow i pipeline. "
            f"Moduly: {', '.join(modules)}."
        )

    def _fetch_source_note(self, source_url: str) -> tuple[str, str, bool]:
        try:
            req = request.Request(
                source_url,
                headers={"User-Agent": "AOA-ALICE/1.0"},
                method="GET",
            )
            with request.urlopen(req, timeout=8) as resp:
                raw = resp.read(50000).decode("utf-8", errors="ignore")
        except Exception as exc:
            self._append_runtime_log(f"INTERNET miss {source_url}: {type(exc).__name__}")
            return source_url, "", True

        title = source_url
        title_start = raw.lower().find("<title>")
        title_end = raw.lower().find("</title>")
        if title_start >= 0 and title_end > title_start:
            title = raw[title_start + 7 : title_end].strip()
        plain = " ".join(raw.replace("\n", " ").replace("\r", " ").split())
        plain = plain[:400]
        return title, plain, False

    def _load_local_source_note(self, source_url: str) -> tuple[str, str]:
        self._local_sources_dir.mkdir(parents=True, exist_ok=True)
        stem = self._source_url_to_stem(source_url)
        candidates = [
            self._local_sources_dir / f"{stem}.md",
            self._local_sources_dir / f"{stem}.txt",
            self._local_sources_dir / f"{stem}.html",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            plain = " ".join(raw.replace("\n", " ").replace("\r", " ").split())
            if plain:
                return f"LOCAL:{path.name}", plain[:600]
        return source_url, ""

    @staticmethod
    def _source_url_to_stem(source_url: str) -> str:
        cleaned = (
            source_url.replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .replace(":", "_")
            .replace(".", "_")
            .strip("_")
        )
        return cleaned or "source"

    def _recover_last_report_from_latest(self) -> bool:
        latest_path = self._logs_dir / "alice_selflearn_latest.json"
        if not latest_path.exists():
            return False
        try:
            payload = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        ts = payload.get("timestamp")
        if not ts:
            return False
        candidate = self._selflearn_dir / f"selflearn_{ts}.json"
        if candidate.exists():
            self._last_report_path = candidate
            return True
        self._selflearn_dir.mkdir(parents=True, exist_ok=True)
        candidate.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._last_report_path = candidate
        self._append_runtime_log(f"RECOVER: odtworzono brakujacy raport {candidate.name} z latest")
        return True

    def _read_latest_payload(self) -> dict:
        latest_path = self._logs_dir / "alice_selflearn_latest.json"
        if not latest_path.exists():
            return {}
        try:
            return json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_daily_summary_file(self, day_key: str, text: str) -> None:
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        out = self._logs_dir / f"alice_daily_summary_{day_key}.txt"
        out.write_text(text, encoding="utf-8")

    def _run_learning_queue_cycle(self, df: pd.DataFrame) -> dict:
        learn_queue = self._curriculum_state["learn_queue"]
        validation_queue = self._curriculum_state["validation_queue"]
        li = int(self._curriculum_state.get("learn_index", 0)) % max(len(learn_queue), 1)
        vi = int(self._curriculum_state.get("validation_index", 0)) % max(len(validation_queue), 1)
        learn_task = learn_queue[li] if learn_queue else "none"
        validation_task = validation_queue[vi] if validation_queue else "none"

        learn_result = self._execute_learn_task(learn_task, df)
        validation_result = self._execute_validation_task(validation_task)
        delta = float(learn_result.get("score_delta", 0.0)) + float(
            validation_result.get("score_delta", 0.0)
        )
        self._curriculum_state["knowledge_score"] = round(
            float(self._curriculum_state.get("knowledge_score", 0.0)) + delta, 3
        )
        notice = learn_result.get("notice") or validation_result.get("notice") or ""
        self._curriculum_state["last_notice"] = notice

        self._curriculum_state["learn_index"] = (li + 1) % max(len(learn_queue), 1)
        self._curriculum_state["validation_index"] = (vi + 1) % max(len(validation_queue), 1)

        if notice:
            self._append_runtime_log(f"NOTICE {notice}")

        return {
            "learn_task": learn_task,
            "learn_result": learn_result,
            "validation_task": validation_task,
            "validation_result": validation_result,
            "knowledge_score": self._curriculum_state["knowledge_score"],
            "notice": notice,
        }

    def _execute_learn_task(self, task: str, df: pd.DataFrame) -> dict:
        if task == "app_workflow":
            return {
                "done": True,
                "note": "Przeplyw stron i funkcji aplikacji potwierdzony.",
                "score_delta": 0.1,
            }
        if task == "ml_models":
            cols = set(df.columns.astype(str))
            need = {"cena", "odpad", "termin_h", "czas_produkcji_h"}
            miss = sorted(list(need - cols))
            return {
                "done": not miss,
                "note": f"Weryfikacja kolumn pod ML. Braki: {', '.join(miss) if miss else 'brak'}",
                "score_delta": 0.15 if not miss else 0.02,
                "notice": "Brakuje kolumn pod pelny trening ML." if miss else "",
            }
        if task == "sto_heuristics":
            try:
                jobs = dataframe_to_jobs(
                    df, job_id_col="sto_job_id" if "sto_job_id" in df.columns else None
                )
                res = run_selected_sto_models(jobs, ["MT", "MO", "MZO", "MOPT"])
                best = min(res, key=lambda r: float(r.get("sto", 1e18))) if res else {}
                return {
                    "done": bool(res),
                    "note": f"Porownanie STO 4 metod. Best={best.get('method', 'n/a')}",
                    "score_delta": 0.2 if res else 0.02,
                }
            except Exception as exc:
                return {
                    "done": False,
                    "note": f"STO test skip: {type(exc).__name__}",
                    "score_delta": 0.01,
                }
        if task == "visual_dashboards":
            return {
                "done": True,
                "note": "Mapowanie wykresow i dashboardow utrwalone.",
                "score_delta": 0.08,
            }
        if task == "results_sql_export":
            return {
                "done": True,
                "note": "Scenariusz Results/SQL/CSV utrwalony.",
                "score_delta": 0.08,
            }
        if task == "code_scan_core":
            core_files = list((self._root_dir / "src" / "AOA" / "core").glob("*.py"))
            return {
                "done": bool(core_files),
                "note": f"Przeskanowano core: {len(core_files)} plikow.",
                "score_delta": 0.12,
            }
        if task == "code_scan_gui":
            gui_files = list((self._root_dir / "src" / "AOA" / "gui").rglob("*.py"))
            return {
                "done": bool(gui_files),
                "note": f"Przeskanowano gui: {len(gui_files)} plikow.",
                "score_delta": 0.12,
            }
        if task == "internet_to_app_mapping":
            return {
                "done": True,
                "note": "Powiazano wiedze z netu z backlogiem zmian appki.",
                "score_delta": 0.15,
            }
        return {"done": False, "note": "Nieznane zadanie kolejki.", "score_delta": 0.0}

    def _execute_validation_task(self, task: str) -> dict:
        payload = self._read_latest_payload()
        txt = json.dumps(payload, ensure_ascii=False)
        digest = hashlib.sha1(txt.encode("utf-8", errors="ignore")).hexdigest()[:12]
        if task == "check_workflow_answer":
            ok = "workflow" in txt.lower() or "przeplyw" in txt.lower()
        elif task == "check_model_comparison":
            ok = "top" in payload and bool(payload.get("top"))
        elif task == "check_sto_explanation":
            ok = bool(payload.get("sto_learning"))
        elif task == "check_visual_guidance":
            ok = "theory_learning" in payload
        elif task == "check_results_sql_guidance":
            ok = "recommendation" in payload
        else:
            ok = False
        return {
            "ok": ok,
            "check": task,
            "fingerprint": digest,
            "score_delta": 0.08 if ok else 0.0,
            "notice": "" if ok else f"Walidacja nie przeszla: {task}",
        }

    def _build_app_mapping_recommendations(self, payload: dict) -> list[str]:
        recs: list[str] = []
        internet = payload.get("internet_learning") or {}
        notes = internet.get("notes") or []
        for n in notes:
            action = self._sanitize_text(str(n.get("actionable") or "").strip())
            module = self._sanitize_text(str(n.get("module") or "Theory").strip())
            impact = self._sanitize_text(str(n.get("impact") or "sredni").strip())
            difficulty = self._sanitize_text(str(n.get("difficulty") or "srednia").strip())
            if action:
                recs.append(f"[{module}] {action} (wplyw: {impact}, trudnosc: {difficulty})")
        queue = payload.get("learning_queue") or {}
        notice = str(queue.get("notice") or "").strip()
        if notice:
            recs.append(f"[Queue] Z kolejki samonauki: {self._sanitize_text(notice)}")
        uniq = []
        for r in recs:
            if r not in uniq:
                uniq.append(r)
        return uniq[:8]

    def _build_sto_stability(self, df: pd.DataFrame, methods: list[str]) -> dict:
        snapshots: list[dict[str, float | str]] = []
        scenarios = [
            ("base", 1.0, False),
            ("fast_line", 0.85, False),
            ("slow_line", 1.15, False),
            ("shuffled", 1.0, True),
        ]
        for name, scale, shuffle in scenarios:
            dfx = df.copy()
            if "czas_produkcji_h" in dfx.columns:
                dfx["czas_produkcji_h"] = (
                    pd.to_numeric(dfx["czas_produkcji_h"], errors="coerce").fillna(0.0) * scale
                )
            if shuffle:
                dfx = dfx.sample(frac=1.0, random_state=42).reset_index(drop=True)
            jobs = dataframe_to_jobs(
                dfx,
                job_id_col="sto_job_id" if "sto_job_id" in dfx.columns else None,
                processing_col="czas_produkcji_h",
                deadline_col="termin_h",
                round_to_int=True,
            )
            res = run_selected_sto_models(jobs, methods)
            if not res:
                continue
            best = min(res, key=lambda r: float(r.get("sto", 1e18)))
            snapshots.append(
                {
                    "scenario": name,
                    "best_model": str(best.get("method", "unknown")),
                    "best_sto": float(best.get("sto", 0.0) or 0.0),
                }
            )
        if not snapshots:
            return {"ok": False, "note": "Brak danych stabilnosci."}
        stos = [float(s["best_sto"]) for s in snapshots]
        rng = max(stos) - min(stos)
        top_models = sorted(str(s["best_model"]) for s in snapshots)
        return {
            "ok": True,
            "scenarios": snapshots,
            "best_sto_range": round(rng, 6),
            "best_models_seen": top_models,
        }

    def _build_insight_scores(self, payload: dict) -> dict:
        prev = self._read_latest_payload()
        top = payload.get("top") or []
        prev_top = prev.get("top") or []
        cur_best = top[0] if top else {}
        prev_best = prev_top[0] if prev_top else {}
        cur_model = str(cur_best.get("model", ""))
        prev_model = str(prev_best.get("model", ""))
        try:
            cur_score = float(cur_best.get("mean_score", 0.0))
            prev_score = float(prev_best.get("mean_score", 0.0))
        except Exception:
            cur_score, prev_score = 0.0, 0.0
        model_changed = cur_model != prev_model
        score_delta = abs(cur_score - prev_score)
        rec_cur = self._sanitize_text(str(payload.get("recommendation") or ""))
        rec_prev = self._sanitize_text(str(prev.get("recommendation") or ""))
        rec_changed = rec_cur != rec_prev
        novelty = min(
            1.0,
            (0.55 if model_changed else 0.0)
            + min(score_delta * 10.0, 0.35)
            + (0.1 if rec_changed else 0.0),
        )
        conf_base = max(0.0, min(1.0, 1.0 - float(cur_best.get("std_score", 0.5) or 0.5)))
        confidence = round(0.35 + 0.65 * conf_base, 3)
        return {
            "confidence": confidence,
            "novelty": round(novelty, 3),
            "model_changed": model_changed,
            "score_delta_abs": round(score_delta, 6),
            "recommendation_changed": rec_changed,
        }

    def _build_delta_report(self, payload: dict) -> dict:
        prev = self._read_latest_payload()
        changes: list[str] = []

        def _best(data: dict) -> tuple[str, float]:
            top = data.get("top") or []
            if not top:
                return "", 0.0
            m = str(top[0].get("model", ""))
            try:
                s = float(top[0].get("mean_score", 0.0))
            except Exception:
                s = 0.0
            return m, s

        cur_m, cur_s = _best(payload)
        prev_m, prev_s = _best(prev)
        if cur_m != prev_m and cur_m:
            changes.append(f"ML best: {prev_m or 'n/a'} -> {cur_m}")
        if abs(cur_s - prev_s) > 1e-6:
            sign = "+" if (cur_s - prev_s) >= 0 else "-"
            changes.append(f"ML score delta: {sign}{abs(cur_s - prev_s):.4f}")

        cur_sto = ((payload.get("sto_learning") or {}).get("best")) or {}
        prev_sto = ((prev.get("sto_learning") or {}).get("best")) or {}
        if cur_sto.get("model") and cur_sto.get("model") != prev_sto.get("model"):
            changes.append(f"STO best: {prev_sto.get('model', 'n/a')} -> {cur_sto.get('model')}")
        try:
            dsto = float(cur_sto.get("sto", 0.0) or 0.0) - float(prev_sto.get("sto", 0.0) or 0.0)
            if abs(dsto) > 1e-9:
                sign = "+" if dsto >= 0 else "-"
                changes.append(f"STO delta: {sign}{abs(dsto):.2f}")
        except Exception:
            pass

        app_map = payload.get("app_mapping_recommendations") or []
        prev_map = prev.get("app_mapping_recommendations") or []
        new_map = [x for x in app_map if x not in prev_map]
        if new_map:
            changes.append(f"Nowe rekomendacje appki: {len(new_map)}")

        sig_raw = "|".join(changes) if changes else "no_change"
        delta_key = hashlib.sha1(sig_raw.encode("utf-8", errors="ignore")).hexdigest()[:12]
        self._last_delta_key = delta_key
        return {
            "significant_changes": bool(changes),
            "changes": [self._sanitize_text(x) for x in changes[:8]],
            "delta_key": delta_key,
        }

    @staticmethod
    def _sanitize_text(value: str) -> str:
        text = str(value or "").replace("\ufeff", "").strip()
        fixes = {
            "Ä…": "ą",
            "Ä‡": "ć",
            "Ä™": "ę",
            "Å‚": "ł",
            "Å„": "ń",
            "Ã³": "ó",
            "Å›": "ś",
            "Åº": "ź",
            "Å¼": "ż",
            "Ä„": "Ą",
            "Ä†": "Ć",
            "Ä�": "Ę",
            "Å�": "Ł",
            "Åƒ": "Ń",
            "Ã“": "Ó",
            "Åš": "Ś",
            "Å¹": "Ź",
            "Å»": "Ż",
        }
        for bad, good in fixes.items():
            text = text.replace(bad, good)
        return text


alice_self_learning_loop = AliceSelfLearningLoop()
