from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, cast
import pandas as pd
from plotly.subplots import make_subplots
import numpy as np

"""
WARNING: This script is mostly AI-generated and may require adjustments.

Plot Gini index time-series from experiment gini_node.csv.

CSV expected columns:
- Simulation_Step (x-axis)
- Node (format: "Region//NodeType", e.g. "Farroupilha//home")
- one or more "characteristics" columns (e.g., age, occupation)

This script derives:
- Region: part before "//"
- Node_Type: part after "//"

Commands:
- node: plot a particular node (exact match)
- compare: compare multiple nodes (exact matches)
- region: plot all nodes in a region (optionally filter by node-type)
- nodetype: plot nodes with a certain node-type across all regions (optionally filter regions)
- heatmap: Node x Simulation_Step heatmap for a characteristic (filters available)
- meanbar: mean Gini per node (summarizes the time-series; filters available)
- typebox: distribution per node-type (box plot; filters available)

Examples:

1) Plot a single node:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        --output show
        node --node "Farroupilha//home" --cols age occupation

2) Compare multiple nodes:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        compare --nodes "Farroupilha//home" "Centro Histórico//home" --cols age occupation

3) All nodes in a region:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        region --region "Farroupilha" --cols age occupation

4) All "home" nodes across all regions:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        nodetype --node-type home --cols age

5) Heatmap of all "work" nodes:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        --backend plotly --output html --out plots/heatmap_work_age.html
        heatmap --col age --node-type work

    Heatmap filtered to specific regions:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        --backend plotly --output html --out plots/heatmap_work_age_subset.html
        heatmap --col age --node-type work --regions "Farroupilha" "Centro Histórico"

6) Mean bar chart of top nodes by mean age Gini:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        meanbar --col age --top-n 30

    Mean bar chart filtered to specific regions:
    python misc_scripts/experiment_node_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_node.csv
        meanbar --col age --top-n 30 --regions "Farroupilha" "Centro Histórico"

Notes:
- Many Node/characteristic entries may be NaN (e.g., nodes not present). Plots handle NaNs.
"""

# Y-axis range constants for Gini plots
GINI_Y_MIN = 0.0
GINI_Y_MAX = 1.0

# X-axis tick interval for time-series plots
X_TICK_INTERVAL = 6


@dataclass(frozen=True)
class PlotConfig:
    backend: str  # "plotly" | "matplotlib"
    output: str  # "show" | "html" | "png"
    out: Optional[Path] = None
    also_show: bool = False
    width: int = 1200
    height: int = 650
    dpi: int = 160


def _split_node(node: str) -> Tuple[str, str]:
    if not isinstance(node, str):
        return ("", "")
    parts = node.split("//", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), ""


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"Simulation_Step", "Node"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    df["Simulation_Step"] = pd.to_numeric(df["Simulation_Step"], errors="coerce")
    df = df.dropna(subset=["Simulation_Step"])
    df["Simulation_Step"] = df["Simulation_Step"].astype(int)

    # Derive Region and Node_Type from Node field: "Region//NodeType"
    region_type = df["Node"].apply(_split_node)
    df["Region"] = [rt[0] for rt in region_type]
    df["Node_Type"] = [rt[1] for rt in region_type]

    df = df.sort_values(["Simulation_Step", "Region", "Node_Type", "Node"], kind="mergesort")
    return df


def validate_characteristics(df: pd.DataFrame, cols: Iterable[str]) -> List[str]:
    cols = list(cols)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Unknown characteristic columns: {missing}. Available: {list(df.columns)}")
    return cols


def _ensure_out_path(cfg: PlotConfig, default_name: str) -> Path:
    if cfg.output == "show":
        return Path(default_name)
    if cfg.out is None:
        raise ValueError("--out is required when --output is html or png")
    cfg.out.parent.mkdir(parents=True, exist_ok=True)
    return cfg.out


def _dispatch_plotly(fig, cfg: PlotConfig, default_name: str) -> None:
    if cfg.output == "show":
        fig.show()
        return

    out = _ensure_out_path(cfg, default_name)
    if cfg.output == "html":
        fig.write_html(str(out))
        if cfg.also_show:
            fig.show()
        return

    if cfg.output == "png":
        try:
            fig.write_image(str(out), width=cfg.width, height=cfg.height)
            if cfg.also_show:
                fig.show()
        except Exception as exc:
            raise RuntimeError(
                "Failed to export PNG with plotly. Install kaleido:\n"
                "  pip install -U kaleido"
            ) from exc
        return

    raise ValueError(f"Unknown output mode: {cfg.output}")


def _dispatch_matplotlib(fig, cfg: PlotConfig, default_name: str) -> None:
    import matplotlib.pyplot as plt

    if cfg.output == "html":
        raise ValueError("matplotlib backend does not support --output html. Use --backend plotly.")

    if cfg.output == "show":
        plt.show()
        return

    out = _ensure_out_path(cfg, default_name)
    fig.savefig(out, dpi=cfg.dpi, bbox_inches="tight")
    if cfg.also_show:
        plt.show()
    else:
        plt.close(fig)


def _default_name_safe(s: str) -> str:
    return (
        s.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("'", "")
        .replace('"', "")
    )


def _filter_df(
    df: pd.DataFrame,
    *,
    nodes: Optional[Sequence[str]] = None,
    region: Optional[str] = None,
    node_type: Optional[str] = None,
    regions: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    out = df
    if nodes:
        out = out[out["Node"].isin(list(nodes))]
    if region:
        out = out[out["Region"] == region]
    if node_type is not None:
        out = out[out["Node_Type"] == node_type]
    if regions:
        out = out[out["Region"].isin(list(regions))]
    return out


def _make_color_map(names: Sequence[str]) -> dict:
    """Consistent color assignment across subplots for the same series labels."""
    palette = [
        "#636EFA",
        "#EF553B",
        "#00CC96",
        "#AB63FA",
        "#FFA15A",
        "#19D3F3",
        "#FF6692",
        "#B6E880",
        "#FF97FF",
        "#FECB52",
    ]
    return {name: palette[i % len(palette)] for i, name in enumerate(names)}


def plot_node(
    df: pd.DataFrame,
    node: str,
    characteristics: List[str],
    cfg: PlotConfig,
) -> None:
    characteristics = validate_characteristics(df, characteristics)
    dfn = _filter_df(df, nodes=[node]).copy()
    if dfn.empty:
        raise ValueError(f"Node not found: {node}")

    title = f"Gini over time - {node}"
    default_name = f"gini_node_{_default_name_safe(node)}.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.graph_objects as go

        fig = go.Figure()
        for c in characteristics:
            fig.add_trace(
                go.Scatter(
                    x=dfn["Simulation_Step"],
                    y=dfn[c],
                    mode="lines+markers",
                    name=c,
                )
            )
        fig.update_layout(
            title=title,
            xaxis_title="Simulation_Step",
            yaxis_title="Gini",
            yaxis=dict(range=[GINI_Y_MIN, GINI_Y_MAX]),
            xaxis=dict(dtick=X_TICK_INTERVAL),
            width=cfg.width,
            height=cfg.height,
            legend_title_text="Characteristic",
        )
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MultipleLocator

        fig, ax = plt.subplots(figsize=(cfg.width / 100, cfg.height / 100))
        for c in characteristics:
            ax.plot(dfn["Simulation_Step"], dfn[c], marker="o", linewidth=2, label=c)
        ax.set_title(title)
        ax.set_xlabel("Simulation_Step")
        ax.set_ylabel("Gini")
        ax.set_ylim(GINI_Y_MIN, GINI_Y_MAX)
        ax.xaxis.set_major_locator(MultipleLocator(X_TICK_INTERVAL))
        ax.grid(True, alpha=0.3)
        ax.legend(title="Characteristic")
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def plot_compare_nodes(
    df: pd.DataFrame,
    nodes: List[str],
    characteristics: List[str],
    cfg: PlotConfig,
) -> None:
    characteristics = validate_characteristics(df, characteristics)
    nodes = list(nodes)

    color_map = _make_color_map(nodes)

    dfc = _filter_df(df, nodes=nodes).copy()
    if dfc.empty:
        raise ValueError("No data after filtering by nodes. Check node names (exact matches).")

    title = "Node comparison (Gini over time)"
    default_name = f"gini_compare_nodes.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.graph_objects as go

        rows = len(characteristics)
        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            subplot_titles=[f"{c}" for c in characteristics],
            vertical_spacing=0.07,
        )

        for n in nodes:
            dfn = dfc[dfc["Node"] == n]
            for i, c in enumerate(characteristics, start=1):
                fig.add_trace(
                    go.Scatter(
                        x=dfn["Simulation_Step"],
                        y=dfn[c],
                        mode="lines",
                        name=n,
                        legendgroup=n,
                        line=dict(color=color_map[n]),
                        showlegend=(i == 1),
                    ),
                    row=i,
                    col=1,
                )

        fig.update_layout(
            title=title,
            width=cfg.width,
            height=max(cfg.height, 250 * rows),
            legend_title_text="Node",
        )
        for i in range(1, rows + 1):
            fig.update_yaxes(title_text="Gini", range=[GINI_Y_MIN, GINI_Y_MAX], row=i, col=1)
            fig.update_xaxes(dtick=X_TICK_INTERVAL, row=i, col=1)
        fig.update_xaxes(title_text="Simulation_Step", row=rows, col=1)
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MultipleLocator

        rows = len(characteristics)
        fig, axes = plt.subplots(
            nrows=rows,
            ncols=1,
            figsize=(cfg.width / 100, max(cfg.height / 100, 2.5 * rows)),
            sharex=True,
        )
        if rows == 1:
            axes = [axes]

        for ax, c in zip(axes, characteristics):
            for n in nodes:
                dfn = dfc[dfc["Node"] == n]
                ax.plot(
                    dfn["Simulation_Step"],
                    dfn[c],
                    linewidth=2,
                    label=n,
                    color=color_map[n],
                )
            ax.set_title(c)
            ax.set_ylabel("Gini")
            ax.set_ylim(GINI_Y_MIN, GINI_Y_MAX)
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Simulation_Step")
        axes[-1].xaxis.set_major_locator(MultipleLocator(X_TICK_INTERVAL))
        axes[0].legend(title="Node", bbox_to_anchor=(1.02, 1), loc="upper left")
        fig.suptitle(title, y=1.02)
        fig.tight_layout()
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def plot_region_nodes(
    df: pd.DataFrame,
    region: str,
    characteristics: List[str],
    cfg: PlotConfig,
    node_type: Optional[str] = None,
    top_n: Optional[int] = None,
) -> None:
    """
    Plot all nodes in a given region (optionally restricting to a node-type).
    Optionally keep only top N nodes by mean Gini (using the first characteristic).
    """
    characteristics = validate_characteristics(df, characteristics)
    dfr = _filter_df(df, region=region, node_type=node_type).copy()
    if dfr.empty:
        msg = f"No data for region={region!r}"
        if node_type is not None:
            msg += f" and node_type={node_type!r}"
        raise ValueError(msg)

    nodes = dfr["Node"].dropna().unique().tolist()
    if top_n is not None and len(nodes) > 0:
        base_c = characteristics[0]
        means = dfr.groupby("Node")[base_c].mean().sort_values(ascending=False)
        nodes = means.head(int(top_n)).index.tolist()
        dfr = dfr[dfr["Node"].isin(nodes)]

    label = f"{region}" + (f" ({node_type})" if node_type else "")
    title = f"Nodes in region - {label}"
    default_name = f"gini_region_nodes_{_default_name_safe(label)}.{cfg.output}"

    # Reuse compare-like plot where legend is node and subplots are characteristics
    plot_compare_nodes(dfr, nodes=nodes, characteristics=characteristics, cfg=cfg)


def plot_nodes_with_type_across_regions(
    df: pd.DataFrame,
    node_type: str,
    characteristics: List[str],
    cfg: PlotConfig,
    regions: Optional[List[str]] = None,
    top_n: Optional[int] = None,
) -> None:
    """
    Plot all nodes with a specific node-type across regions (e.g., all '//home' nodes).
    Optionally restrict to a subset of regions and/or keep top N nodes by mean
    (using the first characteristic).
    """
    characteristics = validate_characteristics(df, characteristics)
    dfx = _filter_df(df, node_type=node_type, regions=regions).copy()
    if dfx.empty:
        raise ValueError("No data after filtering by node-type/regions. Check inputs.")

    nodes = dfx["Node"].dropna().unique().tolist()
    if top_n is not None and len(nodes) > 0:
        base_c = characteristics[0]
        means = dfx.groupby("Node")[base_c].mean().sort_values(ascending=False)
        nodes = means.head(int(top_n)).index.tolist()
        dfx = dfx[dfx["Node"].isin(nodes)]

    title = f"Nodes by type across regions - {node_type}"
    default_name = f"gini_nodetype_{_default_name_safe(node_type)}.{cfg.output}"

    # Use compare-like plot with nodes as legend
    if cfg.backend == "plotly":
        # Override title/default in a single place by building the figure directly
        import plotly.graph_objects as go

        rows = len(characteristics)
        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            subplot_titles=[f"{c}" for c in characteristics],
            vertical_spacing=0.07,
        )

        for n in nodes:
            dfn = dfx[dfx["Node"] == n]
            for i, c in enumerate(characteristics, start=1):
                fig.add_trace(
                    go.Scatter(
                        x=dfn["Simulation_Step"],
                        y=dfn[c],
                        mode="lines",
                        name=n,
                        legendgroup=n,
                        showlegend=(i == 1),
                    ),
                    row=i,
                    col=1,
                )

        fig.update_layout(
            title=title,
            width=cfg.width,
            height=max(cfg.height, 250 * rows),
            legend_title_text="Node (Region//Type)",
        )
        for i in range(1, rows + 1):
            fig.update_yaxes(title_text="Gini", range=[GINI_Y_MIN, GINI_Y_MAX], row=i, col=1)
            fig.update_xaxes(dtick=X_TICK_INTERVAL, row=i, col=1)
        fig.update_xaxes(title_text="Simulation_Step", row=rows, col=1)
        _dispatch_plotly(fig, cfg, default_name)
        return

    # matplotlib: reuse compare implementation then retitle by rebuilding (simple)
    plot_compare_nodes(dfx, nodes=nodes, characteristics=characteristics, cfg=cfg)


def plot_heatmap_node_step(
    df: pd.DataFrame,
    characteristic: str,
    cfg: PlotConfig,
    region: Optional[str] = None,
    node_type: Optional[str] = None,
    regions: Optional[List[str]] = None,
    nodes: Optional[List[str]] = None,
    top_n: Optional[int] = None,
) -> None:
    """
    Heatmap of Gini by (Node x Simulation_Step) for a single characteristic.
    plotly recommended (html output).
    """
    validate_characteristics(df, [characteristic])

    dfx = _filter_df(df, nodes=nodes, region=region, node_type=node_type, regions=regions)
    if dfx.empty:
        raise ValueError("No data after filters. Relax filters or check names.")

    # Optional: keep top N nodes by mean gini (for readability)
    if top_n is not None:
        means = dfx.groupby("Node")[characteristic].mean().sort_values(ascending=False)
        keep = means.head(int(top_n)).index
        dfx = dfx[dfx["Node"].isin(keep)]
        if dfx.empty:
            raise ValueError("No data after applying top-n filter. Relax filters or check data.")

    pivot = dfx.pivot_table(
        index="Node",
        columns="Simulation_Step",
        values=characteristic,
        aggfunc="mean",
    ).sort_index()

    title_bits = [f"Heatmap: {characteristic} (Node x Simulation_Step)"]
    if region:
        title_bits.append(f"region={region}")
    if node_type:
        title_bits.append(f"type={node_type}")
    title = " | ".join(title_bits)
    default_name = f"gini_heatmap_node_{_default_name_safe(characteristic)}.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.express as px

        fig = px.imshow(
            pivot,
            aspect="auto",
            color_continuous_scale="Viridis",
            labels={"x": "Simulation_Step", "y": "Node", "color": "Gini"},
            title=title,
        )
        fig.update_layout(width=cfg.width, height=max(cfg.height, 22 * len(pivot.index)))
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(cfg.width / 100, max(cfg.height / 100, len(pivot.index) / 4)))
        im = ax.imshow(pivot.values, aspect="auto")
        ax.set_title(title)
        ax.set_xlabel("Simulation_Step")
        ax.set_ylabel("Node")
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)

        cols = list(pivot.columns)
        step = max(1, len(cols) // 15)
        xticks = list(range(0, len(cols), step))
        ax.set_xticks(xticks)
        ax.set_xticklabels([str(cols[i]) for i in xticks], rotation=0)

        fig.colorbar(im, ax=ax, label="Gini")
        fig.tight_layout()
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def plot_mean_gini_bar_nodes(
    df: pd.DataFrame,
    characteristic: str,
    cfg: PlotConfig,
    region: Optional[str] = None,
    node_type: Optional[str] = None,
    regions: Optional[List[str]] = None,
    nodes: Optional[List[str]] = None,
    top_n: Optional[int] = None,
) -> None:
    """Bar chart of mean Gini per node for a characteristic (summarizes the time-series)."""
    validate_characteristics(df, [characteristic])

    dfm = _filter_df(df, nodes=nodes, region=region, node_type=node_type, regions=regions)
    if dfm.empty:
        raise ValueError("No data after filters. Relax filters or check names.")

    means = dfm.groupby("Node")[characteristic].mean().sort_values(ascending=False)
    if top_n is not None:
        means = means.head(int(top_n))
        if means.empty:
            raise ValueError("No data after applying top-n filter. Relax filters or check data.")

    title_bits = [f"Mean Gini per node - {characteristic}"]
    if region:
        title_bits.append(f"region={region}")
    if node_type:
        title_bits.append(f"type={node_type}")
    title = " | ".join(title_bits)
    default_name = f"gini_meanbar_node_{_default_name_safe(characteristic)}.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.express as px

        fig = px.bar(
            means.reset_index(name="mean_gini"),
            x="Node",
            y="mean_gini",
            title=title,
            labels={"mean_gini": "Mean Gini"},
        )
        fig.update_layout(width=cfg.width, height=max(cfg.height, 28 * len(means)))
        fig.update_xaxes(tickangle=45)
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(cfg.width / 100, max(cfg.height / 100, len(means) / 4)))
        y = means.index[::-1].tolist()
        x = np.asarray(means.iloc[::-1].to_numpy(dtype=float))
        ax.barh(y, x)
        ax.set_title(title)
        ax.set_xlabel("Mean Gini")
        ax.set_ylabel("Node")
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def plot_box_by_node_type(
    df: pd.DataFrame,
    characteristic: str,
    cfg: PlotConfig,
    regions: Optional[List[str]] = None,
    region: Optional[str] = None,
) -> None:
    """
    Recommended visualization:
    Box plot of the distribution of a characteristic by Node_Type (aggregating all steps/nodes).
    Useful to compare "home/work/school/..." variability.
    """
    validate_characteristics(df, [characteristic])
    dfx = _filter_df(df, region=region, regions=regions).copy()
    if dfx.empty:
        raise ValueError("No data after region filters.")

    title_bits = [f"Distribution by node-type - {characteristic}"]
    if region:
        title_bits.append(f"region={region}")
    title = " | ".join(title_bits)
    default_name = f"gini_typebox_{_default_name_safe(characteristic)}.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.express as px

        fig = px.box(
            dfx,
            x="Node_Type",
            y=characteristic,
            points="outliers",
            title=title,
            labels={"Node_Type": "Node Type", characteristic: "Gini"},
        )
        fig.update_layout(width=cfg.width, height=cfg.height)
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt

        # Keep only non-null values for the characteristic
        dfx = dfx.dropna(subset=[characteristic])
        if dfx.empty:
            raise ValueError("No non-NaN values for selected characteristic after filtering.")

        gb = list(dfx.groupby("Node_Type", sort=True))
        groups = [np.asarray(g[characteristic].to_numpy(dtype=float)) for _, g in gb]
        labels = [str(k) for k, _ in gb]

        fig, ax = plt.subplots(figsize=(cfg.width / 100, cfg.height / 100))
        try:
            ax.boxplot(cast(Sequence[np.ndarray], groups), vert=True, showfliers=True, tick_labels=labels)
        except TypeError:
            ax.boxplot(cast(Sequence[np.ndarray], groups), vert=True, showfliers=True)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels)
        ax.set_title(title)
        ax.set_xlabel("Node Type")
        ax.set_ylabel("Gini")
        ax.set_ylim(GINI_Y_MIN, GINI_Y_MAX)
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Plot node gini index time-series from gini_node.csv.",
    )
    p.add_argument("--csv", type=Path, required=True, help="Path to gini_node.csv")
    p.add_argument(
        "--backend",
        choices=["plotly", "matplotlib"],
        default="plotly",
        help="Plotting backend. Use plotly for html output.",
    )
    p.add_argument(
        "--output",
        choices=["show", "html", "png"],
        default="show",
        help="Output mode.",
    )
    p.add_argument("--out", type=Path, default=None, help="Output file path (required for html/png).")
    p.add_argument(
        "--also-show",
        action="store_true",
        help="Also show plot interactively when saving to file (html/png).",
    )
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--height", type=int, default=650)
    p.add_argument("--dpi", type=int, default=160, help="Used by matplotlib PNG export.")

    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("node", help="Plot a single node (exact match) with multiple characteristics.")
    s1.add_argument("--node", required=True, help='Node string, e.g. "Farroupilha//home" (exact match).')
    s1.add_argument("--cols", nargs="+", required=True, help="Characteristic columns to plot.")

    s2 = sub.add_parser("compare", help="Compare multiple nodes for one or more characteristics.")
    s2.add_argument("--nodes", nargs="+", required=True, help="Node strings (exact matches).")
    s2.add_argument("--cols", nargs="+", required=True, help="Characteristic columns to compare.")

    s3 = sub.add_parser("region", help="Plot all nodes in a region (optionally filter by node-type).")
    s3.add_argument("--region", required=True, help="Region name (exact match; part before //).")
    s3.add_argument("--cols", nargs="+", required=True, help="Characteristic columns to plot.")
    s3.add_argument("--node-type", default=None, help="Optional: only include nodes with this type (after //).")
    s3.add_argument("--top-n", type=int, default=None, help="Optional: keep top N nodes by mean of first col.")

    s4 = sub.add_parser(
        "nodetype",
        help="Plot nodes with a certain node-type in all regions (optionally filter regions).",
    )
    s4.add_argument("--node-type", required=True, help="Node type (part after //), e.g. home, work, school.")
    s4.add_argument("--cols", nargs="+", required=True, help="Characteristic columns to plot.")
    s4.add_argument("--regions", nargs="+", default=None, help="Optional: only include these regions.")
    s4.add_argument("--top-n", type=int, default=None, help="Optional: keep top N nodes by mean of first col.")

    s5 = sub.add_parser("heatmap", help="Heatmap: Node x Simulation_Step for a characteristic.")
    s5.add_argument("--col", required=True, help="Characteristic column.")
    s5.add_argument("--region", default=None, help="Optional: only include this region.")
    s5.add_argument("--regions", nargs="+", default=None, help="Optional: only include these regions.")
    s5.add_argument("--node-type", default=None, help="Optional: only include this node-type.")
    s5.add_argument("--nodes", nargs="+", default=None, help="Optional: only include these nodes.")
    s5.add_argument("--top-n", type=int, default=None, help="Optional: keep top N nodes by mean.")

    s6 = sub.add_parser("meanbar", help="Bar chart: mean Gini per node for a characteristic.")
    s6.add_argument("--col", required=True, help="Characteristic column.")
    s6.add_argument("--region", default=None, help="Optional: only include this region.")
    s6.add_argument("--regions", nargs="+", default=None, help="Optional: only include these regions.")
    s6.add_argument("--node-type", default=None, help="Optional: only include this node-type.")
    s6.add_argument("--nodes", nargs="+", default=None, help="Optional: only include these nodes.")
    s6.add_argument("--top-n", type=int, default=None, help="Optional: keep top N nodes by mean.")

    s7 = sub.add_parser("typebox", help="Box plot: distribution of a characteristic by node-type.")
    s7.add_argument("--col", required=True, help="Characteristic column.")
    s7.add_argument("--region", default=None, help="Optional: only include this region.")
    s7.add_argument("--regions", nargs="+", default=None, help="Optional: only include these regions.")

    return p


def main() -> None:
    args = build_parser().parse_args()

    cfg = PlotConfig(
        backend=args.backend,
        output=args.output,
        out=args.out,
        also_show=args.also_show,
        width=args.width,
        height=args.height,
        dpi=args.dpi,
    )

    df = load_data(args.csv)

    if cfg.output == "html" and cfg.backend != "plotly":
        raise SystemExit("For --output html, use --backend plotly.")

    if args.cmd == "node":
        plot_node(df, node=args.node, characteristics=args.cols, cfg=cfg)
        return

    if args.cmd == "compare":
        plot_compare_nodes(df, nodes=args.nodes, characteristics=args.cols, cfg=cfg)
        return

    if args.cmd == "region":
        plot_region_nodes(
            df,
            region=args.region,
            characteristics=args.cols,
            cfg=cfg,
            node_type=args.node_type,
            top_n=args.top_n,
        )
        return

    if args.cmd == "nodetype":
        plot_nodes_with_type_across_regions(
            df,
            node_type=args.node_type,
            characteristics=args.cols,
            cfg=cfg,
            regions=args.regions,
            top_n=args.top_n,
        )
        return

    if args.cmd == "heatmap":
        plot_heatmap_node_step(
            df,
            characteristic=args.col,
            cfg=cfg,
            region=args.region,
            regions=args.regions,
            node_type=args.node_type,
            nodes=args.nodes,
            top_n=args.top_n,
        )
        return

    if args.cmd == "meanbar":
        plot_mean_gini_bar_nodes(
            df,
            characteristic=args.col,
            cfg=cfg,
            region=args.region,
            regions=args.regions,
            node_type=args.node_type,
            nodes=args.nodes,
            top_n=args.top_n,
        )
        return

    if args.cmd == "typebox":
        plot_box_by_node_type(
            df,
            characteristic=args.col,
            cfg=cfg,
            regions=args.regions,
            region=args.region,
        )
        return

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()