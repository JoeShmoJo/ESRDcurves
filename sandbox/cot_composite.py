"""Generate the Cottage Grove ESRD pilot from local inputs."""

import argparse
from contextlib import chdir
import os
from pathlib import Path
import runpy
import shutil
import tempfile
from unittest.mock import patch

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MultipleLocator
import numpy as np
import pandas as pd


SOURCE = Path(__file__).resolve().parents[1] / "Script_Folder"
DATA = SOURCE / "data"
LEGACY = SOURCE / "scripts" / "ESRD_Halloween_2.py"


def read_recession_hours():
    workbook = DATA / "Explicit_&_Induced_Surcharge_Function_ESRD_Params.xlsx"
    summary = pd.read_excel(workbook, sheet_name="Summary_IS_Params", header=None)
    block = summary.columns[summary.iloc[0].eq("Final Recommended Parameters")].item()
    reservoir = summary.loc[1, block + 1 : block + 11].eq("COT")
    column = reservoir.index[reservoir].item()
    row = summary.index[summary[block].eq("Time of Recession (hr)")].item()
    return float(summary.at[row, column])


def run_legacy(config, work, hours):
    """Stage the profile under the filename expected by the legacy script."""
    frame = pd.read_csv(config, skiprows=5)
    if float(frame["TS"].iat[0]) != hours:
        raise ValueError(f"{config.name}: recession time differs from the workbook")

    # Preserve the five preamble lines, smoothed storage, and exact CSV values.
    shutil.copyfile(config, work / "config" / "COT_CONFIG.csv")
    with (
        chdir(work / "scripts"),
        plt.rc_context(),
        patch.object(plt, "savefig"),
        patch.object(plt, "show"),
    ):
        try:
            result = runpy.run_path(str(LEGACY))
        finally:
            plt.close("all")
    return result


def sample_line(ax, line):
    """Sample the displayed path densely enough to score label clearance."""
    xy = line.get_xydata()
    weights = np.linspace(0, 1, 24, endpoint=False)[:, None]
    segments = xy[:-1, None] + weights * (xy[1:] - xy[:-1])[:, None]
    points = np.vstack((segments.reshape(-1, 2), xy[-1]))
    return ax.transData.transform(points[np.isfinite(points).all(axis=1)])


def label_curves(ax, curves, bounds):
    """Place labels on the most separated visible portion of each curve."""
    paths = [sample_line(ax, line) for line in (*curves, *bounds)]
    candidates = []
    # Reserve room for the text box, in display pixels at the figure's working DPI.
    for index, path in enumerate(paths[:len(curves)]):
        inside = (
            (path[:, 0] > ax.bbox.x0 + 23) & (path[:, 0] < ax.bbox.x1 - 23)
            & (path[:, 1] > ax.bbox.y0 + 12) & (path[:, 1] < ax.bbox.y1 - 12)
        )
        points = path[inside][::4]
        obstacles = np.concatenate(paths[:index] + paths[index + 1:])
        # Measure clearance in units of the label's half-width and half-height.
        delta = (points[:, None] - obstacles) / [15, 8]
        clearance = np.sqrt(np.min(np.sum(delta ** 2, axis=2), axis=1))
        # Give the physical limits extra clearance where curves approach them.
        boundary_delta = (points[:, None] - np.concatenate(paths[len(curves):])) / [20, 11]
        boundary_clearance = np.sqrt(np.min(np.sum(boundary_delta ** 2, axis=2), axis=1))
        candidates.append((points, np.minimum(clearance, boundary_clearance)))

    placed = []
    # Set the most constrained labels first, then keep later labels clear of them.
    order = sorted(range(len(curves)), key=lambda index: candidates[index][1].max(initial=0))
    for index in order:
        points, scores = candidates[index]
        if not len(points):
            raise ValueError(f"No visible segment for curve {curves[index].get_label()}")
        if placed:
            delta = (points[:, None] - placed) / [31, 17]
            label_clearance = np.min(np.max(np.abs(delta), axis=2), axis=1)
            scores = np.where(label_clearance >= 1, scores, -np.inf)
        if not np.isfinite(scores).any():
            raise ValueError(f"No clear label position for curve {curves[index].get_label()}")
        point = points[scores.argmax()]
        placed.append(point)
        line = curves[index]
        ax.annotate(
            line.get_label(), ax.transData.inverted().transform(point),
            ha="center", va="center", color=line.get_color(), fontsize=9, fontweight="bold",
            path_effects=[path_effects.withStroke(linewidth=3, foreground="white")],
        )


def draw_curves(ax, result, kind, colors, zoom=False):
    inflow = kind == "Inflow"
    curves = result["dfInflowPlot" if inflow else "dfPlotROC"]
    config = result["param_dict"]
    envelope = result["dfSurchargeCurve"]
    capacity = result["dfResv"]
    x_min, x_max = (1000, 12000) if zoom else (config["X_Min"], config["X_Max"])
    if zoom and inflow:
        curves = result["dfInOutElev"].loc[x_min:x_max, curves.columns]
    curve_lines = []
    for value, curve in curves.items():
        label = f"{float(value) / 1000:g}" if inflow else f"{float(value):g}"
        line, = ax.plot(curve.index, curve, color=colors[float(value)], linewidth=1.2, label=label)
        curve_lines.append(line)
    ax.plot(capacity["MaxRel"], capacity["Elev"], color="#202a33", lw=1.8, label="Maximum discharge")
    envelope_top = envelope["Env_Elev"].max()
    ax.plot(envelope["Release"], envelope["Env_Elev"], color="#9c492e", lw=1.55,
            label=f"Surcharge envelope ({envelope_top:g} ft)")
    overlays = result["curve_dfs"]
    if isinstance(overlays, dict):
        for name, curve in overlays.items():
            if name != "None":
                ax.plot(curve["Release"], curve["Elev"], "--", lw=1.1, color="#676b73", label=name.capitalize())
    ax.set(
        xlim=(x_min, x_max),
        ylim=(config["Y_Min"], config["Y_Max"]),
        xlabel="Reservoir release (1,000 cfs)",
        ylabel="Pool elevation (ft, project datum)",
    )
    ax.xaxis.set_major_locator(MultipleLocator(config["X_Step"]))
    ax.set_yticks(np.arange(config["Y_Min"], config["Y_Max"] + 0.001, config["Y_Step"]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:g}"))
    ax.xaxis.set_minor_locator(MultipleLocator(1000 if zoom else 2500))
    ax.yaxis.set_minor_locator(MultipleLocator(0.5 if zoom else 1))
    ax.grid(which="major", color="#c7d0d7", linewidth=0.7)
    ax.grid(which="minor", color="#e5eaee", linewidth=0.5)
    for spine in ax.spines.values():
        spine.set(color="#586772", linewidth=0.75)
    ax.tick_params(which="major", width=0.75, length=4, colors="#344552")
    ax.tick_params(which="minor", width=0.55, length=2.5, colors="#62717d")
    ax.xaxis.label.set_color("#344552")
    ax.yaxis.label.set_color("#344552")
    ax.set_axisbelow(True)
    return curve_lines, ax.lines[len(curve_lines):]


def write_composite(full, zoom, kind, output):
    label = "Inflow ESRD" if kind == "Inflow" else "Rate-of-rise ESRD"
    fig, (main_ax, zoom_ax) = plt.subplots(
        1, 2, figsize=(13, 6.4), width_ratios=(1.55, 1)
    )
    fig.subplots_adjust(left=0.072, right=0.975, bottom=0.205, top=0.765, wspace=0.23)
    ink = "#182d3a"
    secondary = "#405461"
    fig.text(0.072, 0.945, "Cottage Grove Reservoir", fontsize=21, fontweight="bold",
             color=ink, va="top")
    fig.text(0.072, 0.881, label, fontsize=13, color=secondary, va="top")
    units = "Inflow (1,000 cfs)" if kind == "Inflow" else "Pool rise (ft/hr)"
    fig.text(0.975, 0.881, f"Curve labels · {units}", ha="right", va="top",
             fontsize=10, color=secondary)
    for y in (0.826, 0.119):
        fig.add_artist(Line2D([0.072, 0.975], [y, y], transform=fig.transFigure,
                              color="#bac7cf", lw=0.7))
    key = "dfInflowPlot" if kind == "Inflow" else "dfPlotROC"
    levels = sorted({float(value) for result in (full, zoom) for value in result[key]})
    colors = dict(zip(levels, plt.colormaps["viridis"](np.linspace(0.05, 0.73, len(levels)))))
    main_lines, main_bounds = draw_curves(main_ax, full, kind, colors)
    zoom_lines, zoom_bounds = draw_curves(zoom_ax, zoom, kind, colors, zoom=True)
    main_ax.set_title("Full range", loc="left", fontsize=11, fontweight="bold", color=ink, pad=9)
    zoom_ax.set_title("Low-release detail", loc="left", fontsize=11, fontweight="bold",
                      color=ink, pad=9)
    fig.legend(handles=main_bounds, loc="lower center", bbox_to_anchor=(0.5, 0.066),
               ncol=len(main_bounds), frameon=False, fontsize=9, labelcolor=secondary)
    fig.text(0.5, 0.037, "From pool elevation, trace across to the labeled curve, "
             "then down to read release.", ha="center", fontsize=9, color=secondary)
    fig.canvas.draw()
    label_curves(main_ax, main_lines, main_bounds)
    label_curves(zoom_ax, zoom_lines, zoom_bounds)
    for extension in ("png", "pdf"):
        fig.savefig(output / f"COT_{kind}_composite.{extension}", dpi=240)
    plt.close(fig)


def write_capacity_comparison(full, output):
    """Keep source outlet ratings visible for review alongside the legacy curve."""
    raw = pd.read_csv(DATA / "ReleaseCapacity.csv")
    source = raw.loc[raw["Reservoir"].eq("Cottage Grove")]
    comparison = full["dfResv"].rename(columns={
        "Elev": "Elevation (ft)", "Stor": "Legacy smoothed storage (acre-ft)",
        "MaxRel": "Legacy maximum release (cfs)",
    }).copy()
    elevation = comparison["Elevation (ft)"]
    for name, outlet in source.groupby("Outlet"):
        outlet = outlet.sort_values("Elevation")
        comparison[f"{name} source rating (cfs)"] = np.interp(
            elevation, outlet["Elevation"], outlet["Release Capacity"], left=np.nan, right=np.nan,
        )
    comparison.to_csv(output / "COT_capacity_comparison.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("out"))
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    hours = read_recession_hours()
    with tempfile.TemporaryDirectory(prefix="esrd-cot-") as directory:
        work = Path(directory)
        for child in ("config", "scripts", "out"):
            (work / child).mkdir()
        full = run_legacy(SOURCE / "config" / "COT_CONFIG.csv", work, hours)
        zoom = run_legacy(SOURCE / "config" / "COT_Small_CONFIG.csv", work, hours)
        for kind in ("Inflow", "ElevROC"):
            write_composite(full, zoom, kind, output)
        for table in (work / "out").glob("*ESRD.csv"):
            shutil.copyfile(table, output / table.name)
        write_capacity_comparison(full, output)
    print(f"COT pilot written to {output} (recession time: {hours:g} hr)")


if __name__ == "__main__":
    main()
