"""Aggregated shelter event, state, flow, equity, and audit logging."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pandas as pd

from core.plugin import LoggerPlugin
from core.population import PopulationTemplate
from core.simulator import LodusSimulation

if TYPE_CHECKING:
    from plugins.time_actions.shelter_plugin import ShelterPlugin


class ShelterLogger(LoggerPlugin):
    """Writes analysis-ready shelter tables without per-person records."""

    FILE_COLUMNS = {
        "shelter_events.csv": [
            "Simulation Step", "Cycle Step", "Cycle", "Event", "Population",
            "Origin ID", "Origin", "Origin Region", "Population Origin Region",
            "Shelter ID", "Shelter", "Shelter Region", "Reason",
            "Requested Population", "Mode", "Distance Km",
        ],
        "shelter_step.csv": [
            "Simulation Step", "Cycle Step", "Cycle", "Safe", "In Danger",
            "Sheltered", "Home Demand", "Waitlist", "Enabled Capacity",
            "Disabled Capacity", "Free Beds", "Utilization", "Protection Rate",
            "Arrivals", "Admissions", "Denials", "Reallocations", "Departures",
            "Capacity Constrained", "Total Population", "Status Population",
            "Conservation Difference",
        ],
        "shelter_node_step.csv": [
            "Simulation Step", "Cycle Step", "Cycle", "Shelter ID", "Shelter",
            "Shelter Name", "Shelter Region", "Enabled", "Capacity", "Sheltered",
            "Queue", "Free Beds", "Utilization", "Arrivals", "Admissions",
            "Denials", "Reallocation In", "Reallocation Out",
        ],
        "shelter_region_step.csv": [
            "Simulation Step", "Cycle Step", "Cycle", "Origin Region",
            "Mapped Exposure", "Requested Exposure", "Unresolved Demand",
            "Protected Population", "Protection Rate", "Arrivals",
            "Mean Travel Distance Km",
        ],
        "shelter_group_step.csv": [
            "Simulation Step", "Cycle Step", "Cycle", "Dimension", "Group",
            "Status", "Population", "Rate Within Group",
        ],
        "shelter_locations.csv": [
            "Node ID", "Complete Name", "Display Name", "Region", "Node Type",
            "Longitude", "Latitude", "Is Shelter", "Capacity", "Enabled",
        ],
        "shelter_input_audit.csv": [
            "Audit Type", "Source", "Input Name", "Resolved Name",
            "Alias Version", "Reason", "Requested", "Available", "Applied",
            "Shortfall", "Capacity", "Occupancy", "Details",
        ],
    }

    def __init__(self, export_png: bool = True):
        self.export_png = export_png
        self.events: list[dict] = []
        self.step_rows: list[dict] = []
        self.node_rows: list[dict] = []
        self.region_rows: list[dict] = []
        self.group_rows: list[dict] = []
        self.sim_step = 0
        self.cycle_step = 0

    def load_plugin(self, simulation: LodusSimulation):
        plugins = [
            plugin
            for plugin in simulation.plugin_controller.loaded_action_plugins
            if getattr(plugin, "ACTION_MOVE", None) == "move_to_shelters"
            and callable(getattr(plugin, "add_event_listener", None))
        ]
        if not plugins:
            raise ValueError("ShelterLogger requires ShelterPlugin to load first")
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.shelter_plugin = cast("ShelterPlugin", plugins[0])
        self.cycle_length = simulation.time_status.cycle_length
        self.initial_population = self.env_graph.get_population_size()
        self.base_path = Path("output_logs") / simulation.experiment_name
        self.data_path = self.base_path / "data_frames"
        self.shelter_plugin.add_event_listener(
            self.__class__.__name__, self._log_event
        )

    def setup_logger(self):
        self.data_path.mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.cycle_step = cycle_step
        self.sim_step = simulation_step

    def _log_event(self, event: dict):
        self.events.append(event)

    def _step_events(
        self, event_type: str | None = None, shelter_id=None
    ) -> list[dict]:
        return [
            event
            for event in self.events
            if event.get("simulation_step") == self.sim_step
            and (event_type is None or event.get("event_type") == event_type)
            and (
                shelter_id is None
                or event.get("shelter_id") == shelter_id
            )
        ]

    @staticmethod
    def _population(events: list[dict]) -> int:
        return sum(int(event.get("population", 0)) for event in events)

    def log_simulation_step(self):
        plugin = self.shelter_plugin
        cycle = self.sim_step // self.cycle_length
        safe = self.env_graph.get_population_size(plugin.safe_template)
        danger = self.env_graph.get_population_size(plugin.in_danger_template)
        sheltered = self.env_graph.get_population_size(
            plugin.sheltered_template
        )
        home_demand = sum(
            node.get_population_size(plugin.in_danger_template)
            for node in self.env_graph.get_nodes_by_type("home")
        )
        waitlist = sum(
            node.get_population_size(plugin.in_danger_template)
            for node in plugin.shelters
        )
        enabled_capacity = sum(
            int(node.get_attribute("capacity"))
            for node in plugin.shelters
            if node.is_enabled()
        )
        disabled_capacity = sum(
            int(node.get_attribute("capacity"))
            for node in plugin.shelters
            if not node.is_enabled()
        )
        free_beds = sum(plugin._free_beds(node) for node in plugin.shelters)
        arrivals = self._population(self._step_events("arrived"))
        admissions = self._population(self._step_events("admitted"))
        denials = self._population(self._step_events("admission_denied"))
        reallocations = self._population(self._step_events("reallocated"))
        departures = self._population(self._step_events("departed"))
        mapped_exposure = sum(plugin.exposure_by_region.values())
        status_population = safe + danger + sheltered
        total_population = self.env_graph.get_population_size()

        self.step_rows.append({
            "Simulation Step": self.sim_step,
            "Cycle Step": self.cycle_step,
            "Cycle": cycle,
            "Safe": safe,
            "In Danger": danger,
            "Sheltered": sheltered,
            "Home Demand": home_demand,
            "Waitlist": waitlist,
            "Enabled Capacity": enabled_capacity,
            "Disabled Capacity": disabled_capacity,
            "Free Beds": free_beds,
            "Utilization": sheltered / enabled_capacity if enabled_capacity else 0,
            "Protection Rate": sheltered / mapped_exposure if mapped_exposure else 0,
            "Arrivals": arrivals,
            "Admissions": admissions,
            "Denials": denials,
            "Reallocations": reallocations,
            "Departures": departures,
            "Capacity Constrained": int(waitlist > 0 and free_beds == 0),
            "Total Population": total_population,
            "Status Population": status_population,
            "Conservation Difference": total_population - self.initial_population,
        })

        for node in plugin.shelters:
            capacity = int(node.get_attribute("capacity"))
            occupancy = node.get_population_size(plugin.sheltered_template)
            queue = node.get_population_size(plugin.in_danger_template)
            node_events = self._step_events(shelter_id=node.id)
            self.node_rows.append({
                "Simulation Step": self.sim_step,
                "Cycle Step": self.cycle_step,
                "Cycle": cycle,
                "Shelter ID": node.id,
                "Shelter": node.get_complete_name(),
                "Shelter Name": node.get_attribute("shelter_name"),
                "Shelter Region": node.containing_region_name,
                "Enabled": int(node.is_enabled()),
                "Capacity": capacity,
                "Sheltered": occupancy,
                "Queue": queue,
                "Free Beds": plugin._free_beds(node),
                "Utilization": occupancy / capacity if capacity else 0,
                "Arrivals": self._population(
                    [e for e in node_events if e["event_type"] == "arrived"]
                ),
                "Admissions": self._population(
                    [e for e in node_events if e["event_type"] == "admitted"]
                ),
                "Denials": self._population(
                    [e for e in node_events if e["event_type"] == "admission_denied"]
                ),
                "Reallocation In": self._population(
                    [e for e in node_events if e["event_type"] == "reallocated"]
                ),
                "Reallocation Out": self._population([
                    e for e in self._step_events("reallocated")
                    if e.get("origin_id") == node.id
                ]),
            })

        arrival_events = self._step_events("arrived")
        for region in plugin.affected_regions:
            origin_template = PopulationTemplate()
            origin_template.set_mother_blob_id(region.id)
            danger_template = origin_template.copy()
            danger_template.set_traceable_property(plugin.STATUS, plugin.IN_DANGER)
            protected_template = origin_template.copy()
            protected_template.set_traceable_property(
                plugin.STATUS, plugin.SHELTERED
            )
            unresolved = self.env_graph.get_population_size(danger_template)
            protected = self.env_graph.get_population_size(protected_template)
            region_arrivals = [
                event for event in arrival_events
                if event.get("population_origin_region") == region.name
            ]
            arrived = self._population(region_arrivals)
            distance_total = sum(
                float(event.get("distance_km", 0)) * int(event["population"])
                for event in region_arrivals
            )
            exposure = plugin.exposure_by_region.get(region.name, 0)
            self.region_rows.append({
                "Simulation Step": self.sim_step,
                "Cycle Step": self.cycle_step,
                "Cycle": cycle,
                "Origin Region": region.name,
                "Mapped Exposure": exposure,
                "Requested Exposure": plugin.requested_exposure_by_region.get(
                    region.name, exposure
                ),
                "Unresolved Demand": unresolved,
                "Protected Population": protected,
                "Protection Rate": protected / exposure if exposure else 0,
                "Arrivals": arrived,
                "Mean Travel Distance Km": (
                    distance_total / arrived if arrived else 0
                ),
            })
        self._log_groups(cycle)

    def _log_groups(self, cycle: int):
        plugin = self.shelter_plugin
        dimensions = {
            "age": ["children", "youngs", "adults", "elders"],
            "occupation": ["student", "worker", "other"],
        }
        for dimension, groups in dimensions.items():
            for group in groups:
                populations = {}
                for status in (plugin.SAFE, plugin.IN_DANGER, plugin.SHELTERED):
                    template = PopulationTemplate(
                        sampled_characteristics={dimension: [group]},
                        traceable_characteristics={plugin.STATUS: status},
                    )
                    populations[status] = self.env_graph.get_population_size(
                        template
                    )
                total = sum(populations.values())
                if total == 0:
                    continue
                for status, population in populations.items():
                    if population == 0:
                        continue
                    self.group_rows.append({
                        "Simulation Step": self.sim_step,
                        "Cycle Step": self.cycle_step,
                        "Cycle": cycle,
                        "Dimension": dimension,
                        "Group": group,
                        "Status": status,
                        "Population": population,
                        "Rate Within Group": population / total,
                    })

    def stop_logger(self):
        events = self._events_dataframe()
        steps = pd.DataFrame(
            self.step_rows,
            columns=self.FILE_COLUMNS["shelter_step.csv"],
        )
        nodes = pd.DataFrame(
            self.node_rows,
            columns=self.FILE_COLUMNS["shelter_node_step.csv"],
        )
        regions = pd.DataFrame(
            self.region_rows,
            columns=self.FILE_COLUMNS["shelter_region_step.csv"],
        )
        groups = pd.DataFrame(
            self.group_rows,
            columns=self.FILE_COLUMNS["shelter_group_step.csv"],
        )
        cycles = self._cycle_dataframe(events, steps, nodes)
        flows = self._flow_dataframe(events)
        locations = self._locations_dataframe()
        audit = self._audit_dataframe()
        frames = {
            "shelter_events.csv": events,
            "shelter_step.csv": steps,
            "shelter_node_step.csv": nodes,
            "shelter_region_step.csv": regions,
            "shelter_cycle.csv": cycles,
            "shelter_origin_shelter.csv": flows,
            "shelter_locations.csv": locations,
            "shelter_input_audit.csv": audit,
            "shelter_group_step.csv": groups,
        }
        self.data_path.mkdir(parents=True, exist_ok=True)
        for filename, frame in frames.items():
            frame.to_csv(
                self.data_path / filename,
                sep=";",
                encoding="utf-8-sig",
                index=False,
            )
        self.shelter_plugin.remove_event_listener(self.__class__.__name__)
        from plugins.loggers.visualizations.shelter_visualizations import (
            generate_shelter_visualizations,
        )
        generate_shelter_visualizations(self.base_path, self.export_png)

    def unload_plugin(self):
        self.shelter_plugin.remove_event_listener(self.__class__.__name__)

    def _events_dataframe(self) -> pd.DataFrame:
        rows = [{
            "Simulation Step": event.get("simulation_step", ""),
            "Cycle Step": event.get("cycle_step", ""),
            "Cycle": event.get("cycle", ""),
            "Event": event.get("event_type", ""),
            "Population": event.get("population", 0),
            "Origin ID": event.get("origin_id", ""),
            "Origin": event.get("origin", ""),
            "Origin Region": event.get("origin_region", ""),
            "Population Origin Region": event.get(
                "population_origin_region", event.get("origin_region", "")
            ),
            "Shelter ID": event.get("shelter_id", ""),
            "Shelter": event.get("shelter", ""),
            "Shelter Region": event.get("shelter_region", ""),
            "Reason": event.get("reason", ""),
            "Requested Population": event.get("requested_population", ""),
            "Mode": event.get("mode", ""),
            "Distance Km": event.get("distance_km", ""),
        } for event in self.events]
        columns = self.FILE_COLUMNS["shelter_events.csv"]
        frame = pd.DataFrame(rows, columns=columns)
        if frame.empty:
            return frame
        group_columns = [column for column in columns if column != "Population"]
        return (
            frame.groupby(group_columns, dropna=False, as_index=False)[
                "Population"
            ]
            .sum()
            .loc[:, columns]
        )

    @staticmethod
    def _cycle_dataframe(
        events: pd.DataFrame, steps: pd.DataFrame, nodes: pd.DataFrame
    ) -> pd.DataFrame:
        columns = [
            "Cycle", "Arrivals", "Admissions", "Denials", "Reallocations",
            "Departures", "Waiting Person Steps", "Peak Queue",
            "Peak System Waitlist", "Constrained Steps", "Capacity",
            "Peak Sheltered", "End Sheltered", "End Unresolved Demand",
            "Mean Distance Km", "P95 Distance Km",
        ]
        if steps.empty:
            return pd.DataFrame(columns=columns)
        rows = []
        for cycle, cycle_steps in steps.groupby("Cycle"):
            cycle_events = events[events["Cycle"] == cycle]
            def event_pop(name):
                return int(cycle_events.loc[
                    cycle_events["Event"] == name, "Population"
                ].sum())
            distances = cycle_events.loc[
                cycle_events["Event"].isin(["arrived", "reallocated"])
                & cycle_events["Distance Km"].notna(),
                ["Distance Km", "Population"],
            ]
            weighted_distances = []
            for _, event in distances.iterrows():
                weighted_distances.extend(
                    [float(event["Distance Km"])] * int(event["Population"])
                )
            last = cycle_steps.sort_values("Simulation Step").iloc[-1]
            cycle_nodes = nodes[nodes["Cycle"] == cycle]
            rows.append({
                "Cycle": cycle,
                "Arrivals": event_pop("arrived"),
                "Admissions": event_pop("admitted"),
                "Denials": event_pop("admission_denied"),
                "Reallocations": event_pop("reallocated"),
                "Departures": event_pop("departed"),
                "Waiting Person Steps": int(cycle_steps["Waitlist"].sum()),
                "Peak Queue": int(cycle_nodes["Queue"].max()) if not cycle_nodes.empty else 0,
                "Peak System Waitlist": int(cycle_steps["Waitlist"].max()),
                "Constrained Steps": int(cycle_steps["Capacity Constrained"].sum()),
                "Capacity": int(cycle_steps["Enabled Capacity"].max()),
                "Peak Sheltered": int(cycle_steps["Sheltered"].max()),
                "End Sheltered": int(last["Sheltered"]),
                "End Unresolved Demand": int(last["In Danger"]),
                "Mean Distance Km": (
                    sum(weighted_distances) / len(weighted_distances)
                    if weighted_distances else 0
                ),
                "P95 Distance Km": (
                    pd.Series(weighted_distances).quantile(0.95)
                    if weighted_distances else 0
                ),
            })
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def _flow_dataframe(events: pd.DataFrame) -> pd.DataFrame:
        columns = [
            "Population Origin Region", "Shelter", "Shelter Region",
            "Population", "Mean Distance Km",
        ]
        if events.empty:
            return pd.DataFrame(columns=columns)
        selected = events[
            events["Event"].isin(["arrived", "reallocated"])
            & events["Shelter"].astype(str).ne("")
        ].copy()
        if selected.empty:
            return pd.DataFrame(columns=columns)
        selected["_weighted_distance"] = (
            pd.to_numeric(selected["Distance Km"], errors="coerce").fillna(0)
            * selected["Population"]
        )
        grouped = selected.groupby(
            ["Population Origin Region", "Shelter", "Shelter Region"],
            dropna=False,
            as_index=False,
        ).agg({"Population": "sum", "_weighted_distance": "sum"})
        grouped["Mean Distance Km"] = (
            grouped["_weighted_distance"] / grouped["Population"]
        )
        return grouped.loc[:, columns]

    def _locations_dataframe(self) -> pd.DataFrame:
        rows = []
        for node in self.env_graph.node_list:
            if node.node_type != "shelter" and node.node_type != "home":
                continue
            is_shelter = node.node_type == "shelter"
            rows.append({
                "Node ID": node.id,
                "Complete Name": node.get_complete_name(),
                "Display Name": (
                    node.get_attribute("shelter_name")
                    if is_shelter else node.containing_region_name
                ),
                "Region": node.containing_region_name,
                "Node Type": node.node_type,
                "Longitude": node.long_lat[0],
                "Latitude": node.long_lat[1],
                "Is Shelter": int(is_shelter),
                "Capacity": (
                    int(node.get_attribute("capacity")) if is_shelter else 0
                ),
                "Enabled": int(node.is_enabled()),
            })
        return pd.DataFrame(
            rows, columns=self.FILE_COLUMNS["shelter_locations.csv"]
        )

    def _audit_dataframe(self) -> pd.DataFrame:
        audit_rows = list(self.shelter_plugin.input_audit)
        audit_rows.extend(self._spatial_coverage_audit())
        columns = self.FILE_COLUMNS["shelter_input_audit.csv"]
        rows = [{
            "Audit Type": row.get("audit_type", ""),
            "Source": row.get("source", ""),
            "Input Name": row.get("input_name", ""),
            "Resolved Name": row.get("resolved_name", ""),
            "Alias Version": row.get("alias_version", ""),
            "Reason": row.get("reason", ""),
            "Requested": row.get("requested", ""),
            "Available": row.get("available", ""),
            "Applied": row.get("applied", ""),
            "Shortfall": row.get("shortfall", ""),
            "Capacity": row.get("capacity", ""),
            "Occupancy": row.get("occupancy", ""),
            "Details": row.get("details", ""),
        } for row in audit_rows]
        return pd.DataFrame(rows, columns=columns)

    def _spatial_coverage_audit(self) -> list[dict]:
        affected = self.shelter_plugin.config.get("affected_areas", {})
        filename = affected.get("affected_census_sectors_file")
        if not filename:
            return []
        try:
            import shapefile
            csv_path = self.shelter_plugin._data_file(filename)
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                sector_ids = {
                    str(row["Setores Censitários Preliminares"]).removesuffix("P")
                    for row in csv.DictReader(stream)
                }
            shape_path = (
                Path(__file__).resolve().parents[2]
                / (
                    "data_input/spatial/setores_preliminares_2022/"
                    "porto_alegre_preliminary_mesh_2022.shp"
                )
            )
            reader = shapefile.Reader(str(shape_path))
            fields = [field[0] for field in reader.fields[1:]]
            code_index = fields.index("CD_SETOR")
            geometry_ids = {
                str(record[code_index]).removesuffix("P")
                for record in reader.records()
            }
            unmatched = sorted(sector_ids - geometry_ids)
            return [{
                "audit_type": "spatial_coverage",
                "source": str(csv_path),
                "requested": len(sector_ids),
                "available": len(sector_ids) - len(unmatched),
                "shortfall": len(unmatched),
                "details": "|".join(unmatched),
            }]
        except Exception as error:
            return [{
                "audit_type": "spatial_coverage_unavailable",
                "source": str(filename),
                "reason": type(error).__name__,
                "details": str(error),
            }]
