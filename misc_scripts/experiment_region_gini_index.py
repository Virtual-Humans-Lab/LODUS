from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import pandas as pd
from plotly.subplots import make_subplots
import numpy as np

# Y-axis range constants for Gini plots
GINI_Y_MIN = 0.0
GINI_Y_MAX = 1.0

# X-axis tick interval for time-series plots
X_TICK_INTERVAL = 6

# filepath: c/LODUS/misc_scripts/experiment_region_gini_index.py
"""
WARNING: This script is mostly AI-generated and may require adjustments.

Plot Gini index time-series from experiment gini_region.csv.

CSV expected columns:
- Simulation_Step (x-axis)
- Region
- one or more "characteristics" columns (e.g., age, occupation)

Outputs:
- show (interactive window for matplotlib; browser window for plotly)
- html (plotly only)
- png (plotly or matplotlib)

Examples:

1) Plot a single region and multiple characteristics:
   
    python misc_scripts/experiment_region_gini_index.py 
        --csv "output_logs/large_scale_event/Baseline/gini_region.csv" 
        --output show 
        region --region "Farroupilha" --cols age occupation    

    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend plotly --output html --out plots/farroupilha.html
        region --region "Farroupilha" --cols age occupation

    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend matplotlib --output png --out plots/farroupilha.png
        region --region "Farroupilha" --cols age occupation

    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend plotly --output html --out plots/farroupilha.html --also-show
        region --region "Farroupilha" --cols age occupation


2) Compare multiple regions for one or more characteristics:
    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --output show
        compare --regions "Farroupilha" "Centro Histórico" "Restinga" --cols age occupation

    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend plotly --output png --out plots/compare_age.png
        compare --regions "Farroupilha" "Centro Histórico" "Restinga" --cols age

3) Plot one characteristic for all regions (many lines; use --top-n to reduce clutter):
    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --output show
        all --col age --top-n 20

    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend plotly --output html --out plots/all_regions_occupation.html
        all --col occupation

Recommended additional visualizations:

4) Heatmap (region x Simulation_Step) for a characteristic:
    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend plotly --output html --out plots/heatmap_age.html
        heatmap --col age

    Filtered heatmap (only selected regions):
    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend plotly --output html --out plots/heatmap_age_subset.html
        heatmap --col age --regions "Farroupilha" "Centro Histórico"

5) Mean Gini per region (bar chart), for a characteristic:
    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend matplotlib --output png --out plots/mean_age.png
        meanbar --col age

    Filtered mean Gini (only selected regions):
    python misc_scripts/experiment_region_gini_index.py
        --csv output_logs/large_scale_event/Baseline/gini_region.csv
        --backend matplotlib --output png --out plots/mean_age_subset.png
        meanbar --col age --regions "Farroupilha" "Centro Histórico"
"""





@dataclass(frozen=True)
class PlotConfig:
    backend: str  # "plotly" | "matplotlib"
    output: str  # "show" | "html" | "png"
    out: Optional[Path] = None
    also_show: bool = False  # Show plot in addition to saving
    width: int = 1200
    height: int = 650
    dpi: int = 160


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"Simulation_Step", "Region"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    # Ensure x-axis sorted and numeric
    df["Simulation_Step"] = pd.to_numeric(df["Simulation_Step"], errors="coerce")
    df = df.dropna(subset=["Simulation_Step"])
    df["Simulation_Step"] = df["Simulation_Step"].astype(int)
    df = df.sort_values(["Simulation_Step", "Region"], kind="mergesort")
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


def _make_color_map(names: Iterable[str]) -> dict:
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
        except Exception as exc:  # kaleido missing, etc.
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


def plot_region(
    df: pd.DataFrame,
    region: str,
    characteristics: List[str],
    cfg: PlotConfig,
) -> None:
    characteristics = validate_characteristics(df, characteristics)
    dfr = df[df["Region"] == region].copy()
    if dfr.empty:
        raise ValueError(f"Region not found: {region}")

    title = f"Gini over time - {region}"
    default_name = f"gini_region_{region.replace(' ', '_')}.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.graph_objects as go

        fig = go.Figure()
        for c in characteristics:
            fig.add_trace(
                go.Scatter(
                    x=dfr["Simulation_Step"],
                    y=dfr[c],
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
            ax.plot(dfr["Simulation_Step"], dfr[c], marker="o", linewidth=2, label=c)
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


def plot_compare_regions(
    df: pd.DataFrame,
    regions: List[str],
    characteristics: List[str],
    cfg: PlotConfig,
) -> None:
    characteristics = validate_characteristics(df, characteristics)
    regions = list(regions)

    color_map = _make_color_map(regions)

    dfc = df[df["Region"].isin(regions)].copy()
    if dfc.empty:
        raise ValueError("No data after filtering by regions. Check region names.")

    title = "Region comparison (Gini over time)"
    default_name = f"gini_compare_regions.{cfg.output}"

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

        for r in regions:
            dfr = dfc[dfc["Region"] == r]
            for i, c in enumerate(characteristics, start=1):
                fig.add_trace(
                    go.Scatter(
                        x=dfr["Simulation_Step"],
                        y=dfr[c],
                        mode="lines",
                        name=r,
                        legendgroup=r,
                        line=dict(color=color_map[r]),
                        showlegend=(i == 1),
                    ),
                    row=i,
                    col=1,
                )

        fig.update_layout(
            title=title,
            width=cfg.width,
            height=max(cfg.height, 250 * rows),
            legend_title_text="Region",
        )
        # Apply Y-axis range and labels to all subplots
        for i in range(1, rows + 1):
            fig.update_yaxes(title_text="Gini", range=[GINI_Y_MIN, GINI_Y_MAX], row=i, col=1)
            fig.update_xaxes(dtick=X_TICK_INTERVAL, row=i, col=1)
        # Set x-axis title only on bottom subplot
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
            for r in regions:
                dfr = dfc[dfc["Region"] == r]
                ax.plot(
                    dfr["Simulation_Step"],
                    dfr[c],
                    linewidth=2,
                    label=r,
                    color=color_map[r],
                )
            ax.set_title(c)
            ax.set_ylabel("Gini")
            ax.set_ylim(GINI_Y_MIN, GINI_Y_MAX)
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Simulation_Step")
        axes[-1].xaxis.set_major_locator(MultipleLocator(X_TICK_INTERVAL))
        axes[0].legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
        fig.suptitle(title, y=1.02)
        fig.tight_layout()
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def plot_all_regions_for_characteristic(
    df: pd.DataFrame,
    characteristic: str,
    cfg: PlotConfig,
    top_n: Optional[int] = None,
) -> None:
    validate_characteristics(df, [characteristic])

    title = f"All regions - {characteristic}"
    default_name = f"gini_all_regions_{characteristic}.{cfg.output}"

    # Optional reduction: top_n regions by mean gini (for readability)
    regions = df["Region"].unique().tolist()
    if top_n is not None:
        means = df.groupby("Region")[characteristic].mean().sort_values(ascending=False)
        regions = means.head(int(top_n)).index.tolist()

    dfa = df[df["Region"].isin(regions)].copy()

    if cfg.backend == "plotly":
        import plotly.graph_objects as go

        fig = go.Figure()
        for r in regions:
            dfr = dfa[dfa["Region"] == r]
            fig.add_trace(
                go.Scatter(
                    x=dfr["Simulation_Step"],
                    y=dfr[characteristic],
                    mode="lines",
                    name=r,
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
            legend_title_text="Region",
        )
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MultipleLocator

        fig, ax = plt.subplots(figsize=(cfg.width / 100, cfg.height / 100))
        for r in regions:
            dfr = dfa[dfa["Region"] == r]
            ax.plot(dfr["Simulation_Step"], dfr[characteristic], linewidth=1.5, label=r)
        ax.set_title(title)
        ax.set_xlabel("Simulation_Step")
        ax.set_ylabel("Gini")
        ax.set_ylim(GINI_Y_MIN, GINI_Y_MAX)
        ax.xaxis.set_major_locator(MultipleLocator(X_TICK_INTERVAL))
        ax.grid(True, alpha=0.3)

        # Keep legend reasonable
        if len(regions) <= 15:
            ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def plot_heatmap_region_step(
    df: pd.DataFrame,
    characteristic: str,
    cfg: PlotConfig,
    top_n: Optional[int] = None,
    regions: Optional[List[str]] = None,
) -> None:
    """
    Heatmap of Gini by (Region x Simulation_Step) for a single characteristic.
    plotly recommended (html output).
    """
    validate_characteristics(df, [characteristic])
    title = f"Heatmap: {characteristic} (Region x Simulation_Step)"
    default_name = f"gini_heatmap_{characteristic}.{cfg.output}"

    dfx = df[["Region", "Simulation_Step", characteristic]].copy()
    if regions:
        dfx = dfx[dfx["Region"].isin(regions)]
        if dfx.empty:
            raise ValueError("No data after filtering by regions. Check region names.")
    if top_n is not None:
        means = dfx.groupby("Region")[characteristic].mean().sort_values(ascending=False)
        keep = means.head(int(top_n)).index
        dfx = dfx[dfx["Region"].isin(keep)]
        if dfx.empty:
            raise ValueError("No data after applying top-n filter. Relax filters or check data.")

    pivot = dfx.pivot_table(
        index="Region",
        columns="Simulation_Step",
        values=characteristic,
        aggfunc="mean",
    ).sort_index()

    if cfg.backend == "plotly":
        import plotly.express as px

        fig = px.imshow(
            pivot,
            aspect="auto",
            color_continuous_scale="Viridis",
            labels={"x": "Simulation_Step", "y": "Region", "color": "Gini"},
            title=title,
        )
        fig.update_layout(width=cfg.width, height=max(cfg.height, 25 * len(pivot.index)))
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(cfg.width / 100, max(cfg.height / 100, len(pivot.index) / 4)))
        im = ax.imshow(pivot.values, aspect="auto")
        ax.set_title(title)
        ax.set_xlabel("Simulation_Step")
        ax.set_ylabel("Region")
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)

        # Avoid too many xtick labels
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


def plot_mean_gini_bar(
    df: pd.DataFrame,
    characteristic: str,
    cfg: PlotConfig,
    top_n: Optional[int] = None,
    regions: Optional[List[str]] = None,
) -> None:
    """Bar chart of mean Gini per region for a characteristic (summarizes the time-series)."""
    validate_characteristics(df, [characteristic])

    dfm = df
    if regions:
        dfm = dfm[dfm["Region"].isin(regions)]
        if dfm.empty:
            raise ValueError("No data after filtering by regions. Check region names.")

    means = dfm.groupby("Region")[characteristic].mean().sort_values(ascending=False)
    if top_n is not None:
        means = means.head(int(top_n))
        if means.empty:
            raise ValueError("No data after applying top-n filter. Relax filters or check data.")

    title = f"Mean Gini per region - {characteristic}"
    default_name = f"gini_meanbar_{characteristic}.{cfg.output}"

    if cfg.backend == "plotly":
        import plotly.express as px

        fig = px.bar(
            means.reset_index(name="mean_gini"),
            x="Region",
            y="mean_gini",
            title=title,
            labels={"mean_gini": "Mean Gini"},
        )
        fig.update_layout(width=cfg.width, height=max(cfg.height, 30 * len(means)))
        fig.update_xaxes(tickangle=45)
        _dispatch_plotly(fig, cfg, default_name)
        return

    if cfg.backend == "matplotlib":
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(cfg.width / 100, max(cfg.height / 100, len(means) / 4)))
        ax.barh(means.index[::-1], means.values[::-1]) # pyright: ignore[reportArgumentType]
        ax.set_title(title)
        ax.set_xlabel("Mean Gini")
        ax.set_ylabel("Region")
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        _dispatch_matplotlib(fig, cfg, default_name)
        return

    raise ValueError(f"Unknown backend: {cfg.backend}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Plot region gini index time-series from gini_region.csv.",
    )
    p.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to gini_region.csv",
    )
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
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file path (required for html/png).",
    )
    p.add_argument(
        "--also-show",
        action="store_true",
        help="Also show plot interactively when saving to file (html/png).",
    )
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--height", type=int, default=650)
    p.add_argument("--dpi", type=int, default=160, help="Used by matplotlib PNG export.")

    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("region", help="Plot a single region with multiple characteristics.")
    s1.add_argument("--region", required=True, help="Region name to filter (exact match).")
    s1.add_argument("--cols", nargs="+", required=True, help="Characteristic columns to plot.")

    s2 = sub.add_parser("compare", help="Compare multiple regions for one or more characteristics.")
    s2.add_argument("--regions", nargs="+", required=True, help="Region names (exact matches).")
    s2.add_argument("--cols", nargs="+", required=True, help="Characteristic columns to compare.")

    s3 = sub.add_parser("all", help="Plot one characteristic for all regions (many lines).")
    s3.add_argument("--col", required=True, help="Characteristic column.")
    s3.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Optional: only plot top N regions by mean Gini (reduces clutter).",
    )

    s4 = sub.add_parser("heatmap", help="Heatmap: Region x Simulation_Step for a characteristic.")
    s4.add_argument("--col", required=True, help="Characteristic column.")
    s4.add_argument("--top-n", type=int, default=None, help="Optional: keep top N regions by mean.")
    s4.add_argument("--regions", nargs="+", default=None, help="Optional: only include these regions.")

    s5 = sub.add_parser("meanbar", help="Bar chart: mean Gini per region for a characteristic.")
    s5.add_argument("--col", required=True, help="Characteristic column.")
    s5.add_argument("--top-n", type=int, default=None, help="Optional: keep top N regions by mean.")
    s5.add_argument("--regions", nargs="+", default=None, help="Optional: only include these regions.")

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

    if args.cmd == "region":
        plot_region(df, region=args.region, characteristics=args.cols, cfg=cfg)
        return

    if args.cmd == "compare":
        plot_compare_regions(df, regions=args.regions, characteristics=args.cols, cfg=cfg)
        return

    if args.cmd == "all":
        plot_all_regions_for_characteristic(df, characteristic=args.col, cfg=cfg, top_n=args.top_n)
        return

    if args.cmd == "heatmap":
        plot_heatmap_region_step(
            df,
            characteristic=args.col,
            cfg=cfg,
            top_n=args.top_n,
            regions=args.regions,
        )
        return

    if args.cmd == "meanbar":
        plot_mean_gini_bar(
            df,
            characteristic=args.col,
            cfg=cfg,
            top_n=args.top_n,
            regions=args.regions,
        )
        return

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()