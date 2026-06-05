# mypy: disable-error-code=attr-defined
import customtkinter as ctk


class MainPageResultsPanelMixin:
    def _build_sto_results_section(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=8)
        ctk.CTkLabel(frame, text="Wyniki STO", font=("Arial", 18, "bold")).pack(
            anchor="w", padx=15, pady=(12, 8)
        )
        self.sto_box = ctk.CTkTextbox(frame, height=260)
        self.sto_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.sto_box.configure(state="disabled")

    def _log_sto_results(self, sto_result: dict):
        results = sto_result.get("results", [])
        best = sto_result.get("best_result")
        saved_paths = sto_result.get("saved_paths", [])
        best_path = sto_result.get("best_path")
        all_path = sto_result.get("all_path")

        self._safe_log("===== WYNIKI STO =====")
        if best is not None:
            self._safe_log(
                f"🏆 Najlepszy model: {best['method']} | STO={best['sto']:.3f} | Kolejność: {', '.join(best['order'])}"
            )
        for index, result in enumerate(results, start=1):
            self._safe_log("")
            self._safe_log(f"[{index}] MODEL: {result['method']}")
            self._safe_log(f"    STO: {result['sto']:.3f}")
            self._safe_log(f"    Kolejność: {', '.join(result['order'])}")
            self._safe_log(f"    Czas całkowity: {result['completion_total']:.3f}")
            self._safe_log(f"    Max T+: {result['max_positive_delay']:.3f}")
        if saved_paths:
            self._safe_log("")
            self._safe_log("===== ZAPISANE PLIKI STO =====")
            for item in saved_paths:
                self._safe_log(
                    f"- {item['method']} | STO={item['sto']:.3f} | drzewo: SolutionTree | {item['path']}"
                )
        if all_path:
            self._safe_log(f"- WSZYSTKIE MODELE | wybieraj model drzewa w Visual | {all_path}")
        if best_path:
            self._safe_log(f"- BEST | {best_path}")

    def _sto_saved_files_text(self, sto_result: dict) -> str:
        saved_paths = sto_result.get("saved_paths", [])
        best_path = sto_result.get("best_path")
        all_path = sto_result.get("all_path")
        if not saved_paths and not best_path and not all_path:
            return ""

        lines = [
            "",
            "ZAPISANE WYNIKI I DRZEWA",
            "========================",
        ]
        if all_path:
            lines.extend(
                [
                    f"Zbiorczy CSV: {all_path}",
                    "W Visual wczytaj ten plik, wybierz SolutionTree i wskaz model w polu modelu drzewa.",
                    "",
                ]
            )
        for item in saved_paths:
            lines.append(
                f"- {item['method']}: STO={item['sto']:.3f} | CSV: {item['path']} | wykres: SolutionTree"
            )
        if best_path:
            lines.append(f"- BEST: {best_path}")
        return "\n".join(lines)
