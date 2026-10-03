from __future__ import annotations

from dataclasses import replace
from tkinter import messagebox

import customtkinter as ctk

from AOA.core.machine_catalog import MachineCapability, MachineSpec, ReliabilitySpec
from AOA.core.product_routing import ProductRoute, RouteOperation
from AOA.core.production_line_designer import ProductionLineDraft


def _items(value: str) -> frozenset[str]:
    return frozenset(
        item.strip()
        for item in value.replace(";", "|").replace(",", "|").split("|")
        if item.strip()
    )


class MachineConfigurationDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        draft: ProductionLineDraft,
        on_save=None,
        *,
        show_routes: bool = True,
    ):
        super().__init__(parent)
        self.draft = draft
        self.on_save = on_save
        self.machines = list(draft.machines)
        self.routes = list(draft.product_routes)
        self.machine_vars: dict[str, ctk.BooleanVar] = {}
        self.route_var = ctk.StringVar(value="")
        self.title("Maszyny, możliwości i trasy produktów")
        self.geometry("1320x820")
        self.minsize(1050, 680)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Konfiguracja fizycznych maszyn i tras produktów",
            font=("Segoe UI", 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=8)
        machine_tab = self.tabs.add("Maszyny")
        self._build_machine_tab(machine_tab)
        if show_routes:
            route_tab = self.tabs.add("Trasy produktów")
            self._build_route_tab(route_tab)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="Puste pole przy edycji wielu maszyn pozostawia daną wartość bez zmian.",
            text_color="#94a3b8",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(footer, text="Anuluj", command=self.destroy, width=110).grid(
            row=0, column=1, padx=6
        )
        ctk.CTkButton(
            footer,
            text="Zapisz konfigurację",
            command=self._save_all,
            width=180,
            fg_color="#16a34a",
        ).grid(row=0, column=2, padx=(6, 0))
        self._refresh_machine_list()
        if show_routes:
            self._refresh_route_menu()

    def _build_machine_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=3)
        tab.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(actions, text="+ Dodaj", command=self._add_machine, width=90).pack(
            side="left", padx=3
        )
        ctk.CTkButton(
            actions,
            text="Usuń wybrane",
            command=self._delete_machines,
            width=120,
            fg_color="#991b1b",
        ).pack(side="left", padx=3)
        self.machine_list = ctk.CTkScrollableFrame(left, label_text="Zaznacz jedną lub wiele")
        self.machine_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.machine_list.grid_columnconfigure(0, weight=1)

        right = ctk.CTkScrollableFrame(tab, label_text="Parametry zaznaczonych maszyn")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)
        right.grid_columnconfigure(1, weight=1)
        fields = (
            ("ID maszyny", "machine_id"),
            ("Nazwa", "name"),
            ("Stanowisko", "station_id"),
            ("Prędkość (1,0 = standard)", "speed_factor"),
            ("Odpad (1,0 = standard)", "waste_factor"),
            ("Energia [kWh/h]", "energy_kwh_per_hour"),
            ("Koszt [zł/h]", "cost_per_hour"),
            ("Przezbrojenie [h]", "setup_time_h"),
            ("Planowany czas [h]", "planned_hours_h"),
            ("Produkty (|)", "products"),
            ("Materiały (|)", "materials"),
            ("Operacje (|)", "operations"),
            ("MTBF [h]", "mtbf_h"),
            ("MTTR [h]", "mttr_h"),
            ("Ryzyko po zmianie [0..1]", "post_probability"),
            ("Okno ryzyka [h]", "risk_window_h"),
            ("Przestój po zmianie [h]", "post_downtime_h"),
        )
        self.machine_fields: dict[str, ctk.StringVar] = {}
        for row, (label, key) in enumerate(fields):
            ctk.CTkLabel(right, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            variable = ctk.StringVar(value="")
            self.machine_fields[key] = variable
            ctk.CTkEntry(right, textvariable=variable).grid(
                row=row, column=1, sticky="ew", padx=10, pady=5
            )
        ctk.CTkButton(
            right,
            text="Zastosuj do zaznaczonych",
            command=self._apply_machine_fields,
            height=40,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="ew", padx=10, pady=12)

    def _build_route_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        body = ctk.CTkFrame(tab, corner_radius=14)
        body.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        body.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(body, text="Trasa").grid(row=0, column=0, sticky="w", padx=12, pady=8)
        self.route_menu = ctk.CTkOptionMenu(
            body,
            values=["(nowa)"],
            variable=self.route_var,
            command=lambda _value: self._load_route(),
        )
        self.route_menu.grid(row=0, column=1, sticky="ew", padx=12, pady=8)
        self.route_fields: dict[str, ctk.StringVar] = {
            "product_id": ctk.StringVar(),
            "name": ctk.StringVar(),
            "stations": ctk.StringVar(),
            "machines": ctk.StringVar(),
        }
        route_fields = (
            ("ID produktu", "product_id"),
            ("Nazwa produktu", "name"),
            ("Kolejność stanowisk", "stations"),
            ("Ograniczenia maszyn", "machines"),
        )
        for row, (label, key) in enumerate(route_fields, start=1):
            ctk.CTkLabel(body, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=8)
            ctk.CTkEntry(body, textvariable=self.route_fields[key]).grid(
                row=row, column=1, sticky="ew", padx=12, pady=8
            )
        ctk.CTkLabel(
            body,
            text=(
                "Stanowiska: S1 > S2 > S3\n"
                "Maszyny: S1=S1:M1|S1:M2; S2=S2:M1\n"
                "Puste ograniczenie oznacza wszystkie zgodne maszyny stanowiska."
            ),
            justify="left",
            text_color="#93c5fd",
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=10)
        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ctk.CTkButton(buttons, text="Nowa", command=self._new_route, width=100).pack(
            side="left", padx=4
        )
        ctk.CTkButton(buttons, text="Zapisz trasę", command=self._save_route, width=130).pack(
            side="left", padx=4
        )
        ctk.CTkButton(
            buttons,
            text="Usuń trasę",
            command=self._delete_route,
            width=120,
            fg_color="#991b1b",
        ).pack(side="left", padx=4)

    def _selected_machine_ids(self) -> list[str]:
        return [machine_id for machine_id, variable in self.machine_vars.items() if variable.get()]

    def _refresh_machine_list(self, selected: set[str] | None = None) -> None:
        selected = selected if selected is not None else set(self._selected_machine_ids())
        for child in self.machine_list.winfo_children():
            child.destroy()
        self.machine_vars = {}
        for row, machine in enumerate(self.machines):
            variable = ctk.BooleanVar(value=machine.machine_id in selected)
            self.machine_vars[machine.machine_id] = variable
            ctk.CTkCheckBox(
                self.machine_list,
                text=f"{machine.name}\n{machine.machine_id} • {machine.station_id}",
                variable=variable,
                command=self._load_machine_fields,
            ).grid(row=row, column=0, sticky="ew", padx=8, pady=6)

    def _load_machine_fields(self) -> None:
        selected = [
            machine for machine in self.machines if machine.machine_id in self._selected_machine_ids()
        ]
        if not selected:
            for variable in self.machine_fields.values():
                variable.set("")
            return
        first = selected[0]
        values = {
            "machine_id": first.machine_id,
            "name": first.name,
            "station_id": first.station_id,
            "speed_factor": first.speed_factor,
            "waste_factor": first.waste_factor,
            "energy_kwh_per_hour": first.energy_kwh_per_hour,
            "cost_per_hour": first.cost_per_hour,
            "setup_time_h": first.setup_time_h,
            "planned_hours_h": first.planned_hours_h,
            "products": "|".join(sorted(first.capability.products)),
            "materials": "|".join(sorted(first.capability.materials)),
            "operations": "|".join(sorted(first.capability.operations)),
            "mtbf_h": first.reliability.mtbf_h,
            "mttr_h": first.reliability.mttr_h,
            "post_probability": first.reliability.post_changeover_failure_probability,
            "risk_window_h": first.reliability.post_changeover_risk_window_h,
            "post_downtime_h": first.reliability.post_changeover_downtime_h,
        }
        for key, value in values.items():
            same = all(self._machine_value(machine, key) == value for machine in selected)
            self.machine_fields[key].set(str(value) if same else "")
        if len(selected) > 1:
            for key in ("machine_id", "name", "station_id"):
                self.machine_fields[key].set("")

    @staticmethod
    def _machine_value(machine: MachineSpec, key: str):
        mapping = {
            "products": "|".join(sorted(machine.capability.products)),
            "materials": "|".join(sorted(machine.capability.materials)),
            "operations": "|".join(sorted(machine.capability.operations)),
            "mtbf_h": machine.reliability.mtbf_h,
            "mttr_h": machine.reliability.mttr_h,
            "post_probability": machine.reliability.post_changeover_failure_probability,
            "risk_window_h": machine.reliability.post_changeover_risk_window_h,
            "post_downtime_h": machine.reliability.post_changeover_downtime_h,
        }
        return mapping.get(key, getattr(machine, key, None))

    def _apply_machine_fields(self) -> None:
        selected_ids = self._selected_machine_ids()
        if not selected_ids:
            messagebox.showerror("Brak wyboru", "Zaznacz przynajmniej jedną maszynę.", parent=self)
            return
        try:
            updated = []
            rename: tuple[str, str] | None = None
            for machine in self.machines:
                if machine.machine_id not in selected_ids:
                    updated.append(machine)
                    continue
                single = len(selected_ids) == 1
                machine_id = self.machine_fields["machine_id"].get().strip() if single else ""
                name = self.machine_fields["name"].get().strip() if single else ""
                station_id = self.machine_fields["station_id"].get().strip() if single else ""
                capability = MachineCapability(
                    products=self._set_or_existing("products", machine.capability.products),
                    materials=self._set_or_existing("materials", machine.capability.materials),
                    operations=self._set_or_existing("operations", machine.capability.operations),
                )
                reliability = ReliabilitySpec(
                    mtbf_h=self._float_or_existing("mtbf_h", machine.reliability.mtbf_h),
                    mttr_h=self._float_or_existing("mttr_h", machine.reliability.mttr_h),
                    post_changeover_failure_probability=self._float_or_existing(
                        "post_probability",
                        machine.reliability.post_changeover_failure_probability,
                    ),
                    post_changeover_risk_window_h=self._float_or_existing(
                        "risk_window_h", machine.reliability.post_changeover_risk_window_h
                    ),
                    post_changeover_downtime_h=self._float_or_existing(
                        "post_downtime_h", machine.reliability.post_changeover_downtime_h
                    ),
                )
                replacement = MachineSpec(
                    machine_id or machine.machine_id,
                    name or machine.name,
                    station_id or machine.station_id,
                    self._float_or_existing("speed_factor", machine.speed_factor),
                    self._float_or_existing("waste_factor", machine.waste_factor),
                    self._float_or_existing(
                        "energy_kwh_per_hour", machine.energy_kwh_per_hour
                    ),
                    self._float_or_existing("cost_per_hour", machine.cost_per_hour),
                    self._float_or_existing("setup_time_h", machine.setup_time_h),
                    self._float_or_existing("planned_hours_h", machine.planned_hours_h),
                    capability,
                    reliability,
                ).normalized()
                if replacement.machine_id != machine.machine_id:
                    rename = (machine.machine_id, replacement.machine_id)
                updated.append(replacement)
            if rename:
                self.routes = self._renamed_routes(*rename)
            self.machines = updated
            chosen = {rename[1] if rename and item == rename[0] else item for item in selected_ids}
            self._refresh_machine_list(chosen)
            self._load_machine_fields()
        except Exception as exc:
            messagebox.showerror("Błąd parametrów", str(exc), parent=self)

    def _float_or_existing(self, key: str, existing: float) -> float:
        raw = self.machine_fields[key].get().strip().replace(",", ".")
        return existing if not raw else float(raw)

    def _set_or_existing(self, key: str, existing: frozenset[str]) -> frozenset[str]:
        raw = self.machine_fields[key].get().strip()
        return existing if not raw else _items(raw)

    def _add_machine(self) -> None:
        if not self.draft.stations:
            return
        station = self.draft.stations[0]
        used = {machine.machine_id for machine in self.machines}
        index = 1
        while f"{station.station_id}:M{index}" in used:
            index += 1
        machine = MachineSpec(
            f"{station.station_id}:M{index}",
            f"{station.name} — maszyna {index}",
            station.station_id,
            capability=MachineCapability(operations=frozenset({station.station_id})),
        ).normalized(index)
        self.machines.append(machine)
        self._refresh_machine_list({machine.machine_id})
        self._load_machine_fields()

    def _delete_machines(self) -> None:
        selected = set(self._selected_machine_ids())
        if not selected:
            return
        remaining = [machine for machine in self.machines if machine.machine_id not in selected]
        counts = {station.station_id: 0 for station in self.draft.stations}
        for machine in remaining:
            counts[machine.station_id] = counts.get(machine.station_id, 0) + 1
        if any(count == 0 for count in counts.values()):
            messagebox.showerror(
                "Nie można usunąć",
                "Każde stanowisko musi mieć przynajmniej jedną maszynę.",
                parent=self,
            )
            return
        self.machines = remaining
        self.routes = [
            ProductRoute(
                route.product_id,
                route.name,
                tuple(
                    replace(
                        operation,
                        allowed_machine_ids=tuple(
                            item for item in operation.allowed_machine_ids if item not in selected
                        ),
                    )
                    for operation in route.operations
                ),
            )
            for route in self.routes
        ]
        self._refresh_machine_list()
        self._load_machine_fields()

    def _renamed_routes(self, old: str, new: str) -> list[ProductRoute]:
        return [
            ProductRoute(
                route.product_id,
                route.name,
                tuple(
                    replace(
                        operation,
                        allowed_machine_ids=tuple(
                            new if item == old else item for item in operation.allowed_machine_ids
                        ),
                    )
                    for operation in route.operations
                ),
            )
            for route in self.routes
        ]

    def _refresh_route_menu(self) -> None:
        values = ["(nowa)", *[route.product_id for route in self.routes]]
        self.route_menu.configure(values=values)
        if self.route_var.get() not in values:
            self.route_var.set("(nowa)")
        self._load_route()

    def _new_route(self) -> None:
        self.route_var.set("(nowa)")
        for variable in self.route_fields.values():
            variable.set("")
        self.route_fields["stations"].set(" > ".join(self.draft.ordered_station_ids()))

    def _load_route(self) -> None:
        selected = next(
            (route for route in self.routes if route.product_id == self.route_var.get()), None
        )
        if selected is None:
            self._new_route()
            return
        self.route_fields["product_id"].set(selected.product_id)
        self.route_fields["name"].set(selected.name)
        self.route_fields["stations"].set(
            " > ".join(operation.station_id for operation in selected.operations)
        )
        restrictions = []
        for operation in selected.operations:
            if operation.allowed_machine_ids:
                restrictions.append(
                    f"{operation.station_id}={'|'.join(operation.allowed_machine_ids)}"
                )
        self.route_fields["machines"].set("; ".join(restrictions))

    def _save_route(self) -> None:
        try:
            product_id = self.route_fields["product_id"].get().strip()
            stations = [
                item.strip()
                for item in self.route_fields["stations"].get().replace("→", ">").split(">")
                if item.strip()
            ]
            restrictions: dict[str, tuple[str, ...]] = {}
            raw_restrictions = self.route_fields["machines"].get().strip()
            if raw_restrictions:
                for part in raw_restrictions.split(";"):
                    station_id, separator, raw_ids = part.partition("=")
                    if not separator:
                        raise ValueError("Ograniczenie maszyny musi miec postac S1=M1|M2.")
                    restrictions[station_id.strip()] = tuple(sorted(_items(raw_ids)))
            route = ProductRoute(
                product_id,
                self.route_fields["name"].get(),
                tuple(
                    RouteOperation(station_id, station_id, restrictions.get(station_id, ()))
                    for station_id in stations
                ),
            ).normalized()
            selected_id = self.route_var.get()
            self.routes = [item for item in self.routes if item.product_id != selected_id]
            self.routes = [item for item in self.routes if item.product_id != route.product_id]
            self.routes.append(route)
            self.route_var.set(route.product_id)
            self._refresh_route_menu()
        except Exception as exc:
            messagebox.showerror("Błąd trasy", str(exc), parent=self)

    def _delete_route(self) -> None:
        selected = self.route_var.get()
        self.routes = [route for route in self.routes if route.product_id != selected]
        self.route_var.set("(nowa)")
        self._refresh_route_menu()

    def _save_all(self) -> None:
        try:
            self.draft.set_configuration(self.machines, self.routes)
            if callable(self.on_save):
                self.on_save()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Błąd konfiguracji", str(exc), parent=self)


def open_machine_configuration(
    parent,
    draft: ProductionLineDraft,
    on_save=None,
    *,
    show_routes: bool = True,
):
    return MachineConfigurationDialog(
        parent,
        draft,
        on_save=on_save,
        show_routes=show_routes,
    )
