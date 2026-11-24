"""Render an alternate Cottage Grove ESRD reference sheet."""

import argparse
from pathlib import Path
import tempfile

from cot_composite import SOURCE, read_recession_hours, run_legacy

import matplotlib.patheffects as effects
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np


INK = "#102e43"
CURVE = "#176179"
CAPACITY = "#20262c"
ENVELOPE = "#aa462c"
EXAMPLE = "#ac570e"


def plot_panel(ax, result, inflow, detail, code):
    curves = result["dfInflowPlot" if inflow else "dfPlotROC"]
    config = result["param_dict"]
    if code == "COT":
        if inflow and detail:
            curves = result.get("dfInOutElev", curves).loc[1000:12000, curves.columns]
        x_limits, y_limits = ((1, 12), (794, 803)) if detail else ((0, 45), (790, 804))
    else:
        x_limits = (config["X_Min"] / 1000, config["X_Max"] / 1000)
        y_limits = (config["Y_Min"], config["Y_Max"])
    lines = []
    for level, curve in curves.items():
        value = float(level) / (1000 if inflow else 1)
        visible = curve.index.to_series().between(*(1000 * x for x in x_limits))
        if curve[visible].between(*y_limits, inclusive="neither").sum() < 2:
            continue
        label = f"{value:.8g}"
        line, = ax.plot(curve.index / 1000, curve, color=CURVE, lw=1.35, label=label)
        lines.append(line)

    rating = result["dfResv"]
    envelope = result["dfSurchargeCurve"]
    limits = []
    line, = ax.plot(rating.MaxRel / 1000, rating.Elev, color=CAPACITY, lw=2,
                    label="Maximum discharge")
    limits.append(line)
    line, = ax.plot(envelope.Release / 1000, envelope.Env_Elev, color=ENVELOPE,
                    lw=1.55, label=f"Surcharge envelope · {envelope.Env_Elev.max():g} ft")
    limits.append(line)
    if isinstance(result["curve_dfs"], dict):
        for name, curve in result["curve_dfs"].items():
            if name != "None":
                line, = ax.plot(curve.Release / 1000, curve.Elev, "--", lw=1.1,
                                color="#657582", label=name.capitalize())
                limits.append(line)

    ax.set(xlim=x_limits, ylim=y_limits)
    x_step, y_step = config["X_Step"] / 1000, config["Y_Step"]
    if code == "COT":
        x_step, y_step = (2, 1) if detail else (5, 2)
    ax.xaxis.set_major_locator(MultipleLocator(x_step))
    ax.xaxis.set_minor_locator(MultipleLocator(x_step / (5 if code == "COT" and not detail else 2)))
    ax.yaxis.set_major_locator(MultipleLocator(y_step))
    ax.yaxis.set_minor_locator(MultipleLocator(y_step / 2))
    ax.grid(which="major", color="#c6d3da", lw=0.65)
    ax.grid(which="minor", color="#e8edf0", lw=0.4)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=8.5, colors=INK, width=0.7)
    for spine in ax.spines.values():
        spine.set(color="#8799a4", linewidth=0.7)
    ax.set_xlabel("Reservoir release (1,000 cfs)", color=INK, fontsize=9.5)
    ax.set_ylabel("Pool elevation (ft, project datum)", color=INK, fontsize=9.5)
    return lines, limits


def spaced_subset(anchors, offsets, clearances):
    """Choose the straight guide that fits the most ordered, readable labels."""
    count = anchors.shape[1]
    offsets = np.asarray(offsets).T
    clearances = np.asarray(clearances).T
    weights = count * 4 + np.minimum(clearances, 4)
    weights = np.where((offsets <= 2) & (clearances >= 0.35), weights, -np.inf)
    scores = weights.copy()
    previous = np.full(scores.shape, -1, dtype=int)
    for end in range(1, count):
        separated = anchors[:, end, 0, None] - anchors[:, :end, 0] >= 16
        predecessors = np.where(separated, scores[:, :end], -np.inf)
        best = predecessors.argmax(axis=1)
        best_score = predecessors[np.arange(len(best)), best]
        valid = np.isfinite(best_score)
        scores[valid, end] += best_score[valid]
        previous[valid, end] = best[valid]
    guide, index = np.unravel_index(scores.argmax(), scores.shape)
    if not np.isfinite(scores[guide, index]):
        raise ValueError("No readable curve labels in this view")
    kept = []
    while index >= 0:
        kept.append(index)
        index = previous[guide, index]
    return guide, kept[::-1]


def label_panel(ax, lines, limits):
    """Choose label anchors by comparing clear space in display coordinates."""
    if not lines:
        raise ValueError("No visible contours in this view")
    left, right = ax.get_xlim()
    x = np.linspace(left, right, 460)

    def sample(line):
        return np.interp(x, line.get_xdata(), line.get_ydata(), left=np.nan, right=np.nan)

    paths = [ax.transData.transform(np.column_stack((x, sample(line)))) for line in lines]
    # The capacity and envelope may have repeated x values. Sample their actual
    # segments in drawing order so the clearance check sees vertical sections.
    for line in limits:
        xy = line.get_xydata()
        t = np.linspace(0, 1, 90, endpoint=True)
        segments = xy[:-1, None] + t[:, None] * np.diff(xy, axis=0)[:, None]
        paths.append(ax.transData.transform(segments.reshape(-1, 2)))

    options, active = [], []
    for index, path in enumerate(paths[:len(lines)]):
        points = path[
            (path[:, 0] > ax.bbox.x0 + 17) & (path[:, 0] < ax.bbox.x1 - 17)
            & (path[:, 1] > ax.bbox.y0 + 10) & (path[:, 1] < ax.bbox.y1 - 10)
        ][::3]
        if not len(points):
            lines[index].set_visible(False)
            continue
        active.append(lines[index])
        others = np.concatenate(paths[:index] + paths[index + 1:])
        others = others[np.isfinite(others).all(axis=1)]
        distances = (points[:, None] - others) / [12, 7]
        clearance = np.sqrt((distances ** 2).sum(axis=2).min(axis=1))
        options.append((points, clearance))

    # Find a common straight guide in panel coordinates. Score it against the
    # tightest curve clearance and reject guides that bunch consecutive labels.
    if not active:
        raise ValueError("No visible label anchors in this view")
    slopes, intercepts = np.meshgrid(
        np.linspace(-1.2, 1.2, 97), np.linspace(0.13, 0.87, 75)
    )
    slopes, intercepts = slopes.ravel(), intercepts.ravel()
    anchors, clearances, offsets = [], [], []
    for points, clearance in options:
        x = (points[:, 0] - ax.bbox.x0) / ax.bbox.width - 0.5
        y = (points[:, 1] - ax.bbox.y0) / ax.bbox.height
        error = np.abs(y - (intercepts[:, None] + slopes[:, None] * x))
        nearest = error.argmin(axis=1)
        anchors.append(points[nearest])
        clearances.append(clearance[nearest])
        offsets.append(error[np.arange(len(nearest)), nearest] * ax.bbox.height)

    anchors = np.stack(anchors, axis=1)
    separation = np.diff(anchors, axis=1)
    spaced = (separation[:, :, 0] >= 16).all(axis=1)
    aligned = np.max(offsets, axis=0) <= 2.5
    score = np.min(clearances, axis=0) + 0.25 * np.mean(clearances, axis=0)
    score = np.where(spaced & aligned, score, -np.inf)
    if np.isfinite(score).any():
        guide, kept = score.argmax(), list(range(len(active)))
    else:
        guide, kept = spaced_subset(anchors, offsets, clearances)
    for index in kept:
        point = anchors[guide, index]
        ax.annotate(active[index].get_label(), ax.transData.inverted().transform(point),
                    ha="center", va="center", color=INK, fontsize=9, fontweight="bold",
                    zorder=7, path_effects=[effects.withStroke(linewidth=3, foreground="white")])

    for index, line in enumerate(active):
        line.set_visible(index in kept)
    return [active[index] for index in kept]


def add_example(ax, lines, inflow, code):
    left, right = ax.get_xlim()
    bottom, top = ax.get_ylim()
    candidates = []
    for line in lines:
        level = line.get_label()
        x, y = line.get_xydata().T
        for elevation in ([800] if code == "COT" else range(int(bottom) + 1, int(top))):
            if code == "COT" and level != ("12" if inflow else "0.4"):
                continue
            crosses = np.flatnonzero((y[:-1] < elevation) & (y[1:] >= elevation))
            if len(crosses) != 1:
                continue
            i = crosses.item()
            release = np.interp(elevation, y[i:i + 2], x[i:i + 2])
            if left < release < right:
                distance = abs((release - left) / (right - left) - 0.55)
                distance += abs((elevation - bottom) / (top - bottom) - 0.66)
                candidates.append((distance, elevation, level, release))
    if not candidates:
        return None
    _, elevation, level, release = min(candidates)
    ax.plot([left, release, release], [elevation, elevation, ax.get_ylim()[0]],
            color=EXAMPLE, lw=1.25, linestyle=(0, (4, 3)), zorder=3)
    ax.scatter([release], [elevation], s=23, color=EXAMPLE, edgecolor="white",
               linewidth=0.6, zorder=6)
    measurement = f"{float(level) * 1000:,.0f} cfs inflow" if inflow else f"{level} ft/hr pool rise"
    return f"{elevation:g} ft with {measurement} → about {round(release * 10) * 100:,} cfs"


def write_sheet(full, detail, inflow, output, code="COT", title="Cottage Grove Reservoir",
                formats=("pdf", "png")):
    fig, (main, zoom) = plt.subplots(2, 1, figsize=(8.5, 11))
    fig.subplots_adjust(left=0.125, right=0.95, top=0.825, bottom=0.126, hspace=0.29)
    fig.text(0.125, 0.96, title, fontsize=21, color=INK, weight="bold")
    heading = "Inflow" if inflow else "Rate of rise"
    units = "inflow in 1,000 cfs" if inflow else "pool rise in ft/hr"
    fig.text(0.125, 0.923, f"{heading} · Emergency Spillway Release Diagram",
             fontsize=12, color=INK)
    fig.text(0.125, 0.890, f"Curve labels show {units}. From pool elevation, trace across to",
             fontsize=9.5, color=INK)
    fig.text(0.125, 0.872, "the matching curve, then down to read reservoir release.",
             fontsize=9.5, color=INK)

    full_lines, bounds = plot_panel(main, full, inflow, detail=False, code=code)
    zoom_lines, zoom_bounds = plot_panel(zoom, detail, inflow, detail=True, code=code)
    main.set_title("Full release range", loc="left", fontsize=11, weight="bold", color=INK)
    zoom.set_title("Zoomed view", loc="left", fontsize=11, weight="bold", color=INK)
    fig.legend(handles=bounds, loc="lower left", bbox_to_anchor=(0.115, 0.017),
               ncol=len(bounds), fontsize=8, frameon=False, labelcolor=INK)
    fig.canvas.draw()
    shown_main = label_panel(main, full_lines, bounds)
    shown_zoom = label_panel(zoom, zoom_lines, zoom_bounds)
    reduced = len(shown_main) < len(full_lines) or len(shown_zoom) < len(zoom_lines)
    if reduced:
        fig.text(0.95, 0.872, "Selected contours shown", ha="right", fontsize=8.5, color=INK)
    example = add_example(zoom, shown_zoom, inflow, code)
    if example:
        fig.text(0.125, 0.060, f"Worked example   {example}",
                 fontsize=9.5, color=EXAMPLE, weight="bold")
    name = f"{code}_{'inflow' if inflow else 'rate_of_rise'}_reference"
    for extension in formats:
        fig.savefig(output / f"{name}.{extension}", dpi=240)
    plt.close(fig)
    return len(shown_main), len(full_lines), len(shown_zoom), len(zoom_lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("out") / "reference")
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    hours = read_recession_hours()
    with tempfile.TemporaryDirectory(prefix="esrd-reference-") as directory:
        work = Path(directory)
        for subdirectory in ("config", "scripts", "out"):
            (work / subdirectory).mkdir()
        full = run_legacy(SOURCE / "config" / "COT_CONFIG.csv", work, hours)
        detail = run_legacy(SOURCE / "config" / "COT_Small_CONFIG.csv", work, hours)
        write_sheet(full, detail, True, output)
        write_sheet(full, detail, False, output)


if __name__ == "__main__":
    main()
