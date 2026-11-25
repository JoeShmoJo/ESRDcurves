"""Render an alternate Cottage Grove ESRD reference sheet."""

import argparse
from pathlib import Path
import tempfile
from textwrap import fill

from cot_composite import SOURCE, read_recession_hours, run_legacy

import matplotlib.patheffects as effects
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator
from matplotlib.transforms import Bbox
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
    return f"{elevation:g} ft with {measurement} → {round(release * 10) * 100:,} cfs release"


def add_title_block(fig, full, inflow, code, title, *, landscape):
    """Set the source title-block text beside the interpretation notes."""
    source = full["dfTitleBlock"]
    lines = [" ".join(str(value).split()) for value in source.Text]
    lines = [line for line in lines if line and "Reservoir" not in line]
    if not lines:
        envelope = full["dfSurchargeCurve"].Env_Elev.max()
        dam_crest = {"DET": 1579, "HCR": 1548}.get(code)
        lines = [f"Plotted surcharge envelope – {envelope:g} ft", "All elevations in project datum"]
        if dam_crest:
            lines.extend([f"Top of dam – {dam_crest:g} ft", "U.S. Army Corps of Engineers",
                          "Portland District", "August 2024 draft"])
        else:
            lines.append("Legacy title block unavailable")

    # Draft_Curve.pdf repeats the inflow wording on several rate-of-rise pages.
    # Carry over the verified periods only for the corresponding measurement.
    draft_hours = {"BLU": 3, "CGR": 3, "COT": 3, "DET": 3, "DOR": 3,
                   "FAL": 3, "FOS": 2, "FRN": 3, "GPR": 3, "HCR": 3, "LOP": 2}
    verified_rise = {"FAL", "FOS", "GPR", "LOP"}
    if code in draft_hours:
        heading = "NOTES FROM THE DRAFT CURVE"
        if inflow or code in verified_rise:
            measurement = "inflow" if inflow else "pool elevation rate of change"
            basis = f"Use the preceding {draft_hours[code]}-hour average {measurement} and current pool elevation."
        else:
            basis = "Use current pool elevation and the pool-rise averaging period in the water control manual."
        notes = [
            "1. Follow the regular flood-control schedule until the chart indicates a larger release.",
            f"2. {basis}",
            "3. At maximum pool elevation, release inflow until downstream stages fall below bankfull. Then keep releases at or below bankfull until the flood pool is evacuated.",
        ]
    else:
        heading = "NOTES"
        notes = [
            "Method: EM 1110-2-3600 (2017), section 4.5.4.",
            "Maximum-discharge curves show design capacity. Project limits may apply to gate openings and concurrent outlet use.",
            "Use the averaging period specified in the project's water control manual.",
        ]
    left = 0.075 if landscape else 0.125
    width = 0.27 if landscape else 0.32
    bottom, top = 0.027, 0.182
    fig.add_artist(Rectangle((left, bottom), width, top - bottom,
                             transform=fig.transFigure, facecolor="white",
                             edgecolor=INK, linewidth=1.15))
    center = left + width / 2
    fig.text(center, top - 0.014, title, color=INK, fontsize=9.3,
             weight="bold", ha="center", va="top")
    fig.text(center, top - 0.036, "\n".join(lines), color=INK, fontsize=8,
             ha="center", va="top", linespacing=1.16)

    notes_left = left + width + 0.035
    fig.text(notes_left, top - 0.014, heading.capitalize(), color=INK,
             fontsize=9, weight="bold", va="top")
    body = "\n".join(fill(note, width=88 if landscape else 60,
                          subsequent_indent="   " if note[:1].isdigit() else "")
                     for note in notes)
    fig.text(notes_left, top - 0.036, body, color=INK,
             fontsize=8.3, va="top", linespacing=1.22)


def make_inset(fig, main, lines):
    """Place the zoom only where its panel and tick labels clear the plotted data."""
    fig.canvas.draw()
    paths = [line.get_path().transformed(main.transData + main.transAxes.inverted())
             for line in lines]
    sizes = ((0.49, 0.42), (0.46, 0.39), (0.43, 0.35))
    placements = [(width, height, x, y)
                  for width, height in sizes
                  for x in (0.97 - width, 0.91 - width, 0.08)
                  for y in (0.11, 0.18, 0.55)]
    placements.extend((width, height, x, y)
                      for width, height in (*sizes, (0.43, 0.32), (0.40, 0.31))
                      for x in (0.97 - width, 0.91 - width, 0.08)
                      for y in (0.075, 0.11, 0.18, 0.55))
    for width, height, x, y in placements:
        padded = Bbox.from_extents(x - 0.043, y - 0.057,
                                   x + width + 0.006, y + height + 0.045)
        if not any(path.intersects_bbox(padded, filled=False) for path in paths):
            return main.inset_axes([x, y, width, height]), True

    # Keep the zoom legible beside the main panel when an inset would cover data.
    main.set_position([0.075, 0.289, 0.51, 0.56])
    return fig.add_axes([0.635, 0.40, 0.315, 0.39]), False


def write_sheet(full, detail, inflow, output, code="COT", title="Cottage Grove Reservoir",
                formats=("pdf", "png"), inset=False):
    if inset:
        fig, main = plt.subplots(figsize=(13, 9))
        fig.subplots_adjust(left=0.075, right=0.95, top=0.859, bottom=0.289)
    else:
        fig, (main, zoom) = plt.subplots(2, 1, figsize=(8.5, 11))
        fig.subplots_adjust(left=0.125, right=0.95, top=0.859, bottom=0.278, hspace=0.36)
    left = 0.075 if inset else 0.125
    fig.text(left, 0.96, title, fontsize=21, color=INK, weight="bold")
    heading = "Inflow" if inflow else "Rate of rise"
    units = "1,000 cfs" if inflow else "ft/hr"
    fig.text(left, 0.923, f"{heading} ({units}) · Emergency Spillway Release Diagram",
             fontsize=12, color=INK)

    full_lines, bounds = plot_panel(main, full, inflow, detail=False, code=code)
    embedded = False
    if inset:
        zoom, embedded = make_inset(fig, main, [*full_lines, *bounds])
    zoom_lines, zoom_bounds = plot_panel(zoom, detail, inflow, detail=True, code=code)
    if inset:
        zoom.set(xlabel=None, ylabel=None)
    main.set_title("Full release range", loc="left", fontsize=11, weight="bold", color=INK)
    zoom.set_title("Zoomed view", loc="left", fontsize=11, weight="bold", color=INK)
    fig.legend(handles=bounds, loc="lower left", bbox_to_anchor=(left - 0.01, 0.192),
               ncol=len(bounds), fontsize=8, frameon=False, labelcolor=INK)
    fig.canvas.draw()
    shown_main = label_panel(main, full_lines, bounds)
    shown_zoom = label_panel(zoom, zoom_lines, zoom_bounds)
    reduced = len(shown_main) < len(full_lines) or len(shown_zoom) < len(zoom_lines)
    if reduced:
        fig.text(0.95, 0.901, "Selected contours shown", ha="right", fontsize=8.5, color=INK)
    example = add_example(zoom, shown_zoom, inflow, code)
    if example:
        fig.text(left, 0.222, f"Worked example   {example}",
                 fontsize=9.5, color=EXAMPLE, weight="bold")
    add_title_block(fig, full, inflow, code, title, landscape=inset)
    name = f"{code}_{'inflow' if inflow else 'rate_of_rise'}_{'inset' if inset else 'reference'}"
    for extension in formats:
        fig.savefig(output / f"{name}.{extension}", dpi=240)
    plt.close(fig)
    return len(shown_main), len(full_lines), len(shown_zoom), len(zoom_lines), embedded


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
