"""Generate the portrait ESRD review sheets for the checked-in reservoir profiles."""

import argparse
from pathlib import Path

from cot_reference_sheet import SOURCE, write_sheet
from reservoir_curves import plot_grids

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


RESERVOIRS = {
    "APP": "Applegate", "BLU": "Blue River", "CGR": "Cougar", "COT": "Cottage Grove",
    "DET": "Detroit", "DOR": "Dorena", "FAL": "Fall Creek", "FOS": "Foster",
    "FRN": "Fern Ridge", "GPR": "Green Peter", "HCR": "Hills Creek",
    "LOP": "Lookout Point", "LOS": "Lost Creek", "MOS": "Mossyrock",
}


def profiles(code):
    directory = SOURCE / "config"
    if code == "DET":
        return SOURCE / "out" / "DET_CONFIG.csv", None
    if code == "MOS":
        return directory / "MOS_Table_CONFIG.csv", None
    revision = "_2" if code == "FRN" else ""
    full = directory / f"{code}_CONFIG{revision}.csv"
    zoom = directory / f"{code}_Small_CONFIG{revision}.csv"
    return full, zoom if zoom.is_file() else None


def derive_zoom(full):
    """Use the upper part of the full chart when no zoom profile exists."""
    detail = full.copy()
    params = full["param_dict"].copy()
    top = full["dfSurchargeCurve"].Env_Elev.max()
    params.Y_Min = round(top - (params.Y_Max - params.Y_Min) * 0.38)
    params.Y_Max = max(top + 0.5, min(params.Y_Max, top + 2))
    params.X_Max = params.X_Min + (params.X_Max - params.X_Min) * 0.52
    for axis, unit in (("X", 1000), ("Y", 1)):
        ticks = MaxNLocator(nbins=7).tick_values(params[f"{axis}_Min"] / unit,
                                                  params[f"{axis}_Max"] / unit)
        params[f"{axis}_Step"] = (ticks[1] - ticks[0]) * unit
    detail["param_dict"] = params
    return detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SOURCE.parent / "review" / "esrd")
    parser.add_argument("--reservoir", choices=RESERVOIRS, action="append")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    for code in args.reservoir or RESERVOIRS:
        full_path, zoom_path = profiles(code)
        try:
            full = plot_grids(full_path)
            detail = plot_grids(zoom_path) if zoom_path else derive_zoom(full)
        except (KeyError, ValueError) as error:
            print(f"{code} inputs: {error}", flush=True)
            continue

        for inflow in (True, False):
            kind = "inflow" if inflow else "rate of rise"
            try:
                counts = write_sheet(full, detail, inflow, output, code=code,
                            title=f"{RESERVOIRS[code]} Reservoir", formats=("pdf",))
                print(f"{code} {kind}: saved (full {counts[0]}/{counts[1]}, zoom {counts[2]}/{counts[3]})", flush=True)
            except ValueError as error:
                print(f"{code} {kind}: {error}", flush=True)
            finally:
                plt.close("all")


if __name__ == "__main__":
    main()
