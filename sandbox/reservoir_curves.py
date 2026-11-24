"""Calculate the plot grids from the legacy ESRD configuration profiles."""

import numpy as np
import pandas as pd
from scipy.interpolate import griddata, interp1d


def plot_grids(config):
    frame = pd.read_csv(config, skiprows=5)
    rating = frame[["Elev", "Stor", "MaxRel"]].dropna()
    envelope = frame[["Env_Elev", "Release"]].dropna()
    params = frame[["Param", "Values"]].dropna().set_index("Param").Values
    if not rating.MaxRel.min() <= 1000 < rating.MaxRel.max():
        raise ValueError(
            f"Maximum-discharge range {rating.MaxRel.min():,.0f}–{rating.MaxRel.max():,.0f} cfs "
            "does not cover the calculation grid starting at 1,000 cfs"
        )
    releases = np.arange(1000, rating.MaxRel.max(), 1000.0)
    inflows = np.arange(1000, params.Inflow_Max + 1, 1000.0)
    storage = interp1d(rating.Elev, rating.Stor)
    elevation = interp1d(rating.Stor, rating.Elev, bounds_error=False,
                         fill_value=(rating.Elev.min(), rating.Elev.max()))
    surcharge = interp1d(envelope.Release, envelope.Env_Elev)
    capacity = interp1d(rating.MaxRel, rating.Elev)(releases)

    # Legacy surcharge calculation, with rows indexed by release and columns by inflow.
    release = releases[:, None]
    surcharge_elev = surcharge(releases)[:, None]
    recession = frame.TS.iat[0] / 24
    required_storage = (86400 / 43560) * recession * (
        inflows - release * (1 + np.log(inflows / release))
    )
    pool = np.maximum(elevation(storage(surcharge(inflows)) - required_storage), capacity[:, None])
    on_envelope = np.logical_or.accumulate(pool > surcharge_elev - 0.05, axis=0)
    pool = np.where(on_envelope, surcharge_elev, pool)
    inflow_grid = pd.DataFrame(pool, index=releases, columns=inflows)
    levels = np.arange(params.Inflow_Min, params.Inflow_Max + 1, params.Inflow_Step)

    prior_storage = np.interp(pool, rating.Elev, rating.Stor) - (inflows - release) * 0.0826
    prior_elevation = interp1d(rating.Stor, rating.Elev, bounds_error=False, fill_value=0)
    rise = pool - prior_elevation(prior_storage)
    valid = rise > 0
    outflow = np.broadcast_to(release, pool.shape)
    rates = np.arange(0, params.ROC_Max, params.ROC_Step)
    grid_release, grid_rate = np.meshgrid(releases, rates, indexing="ij")
    # Match the old melt order, including the triangulation's input ordering.
    points = np.column_stack((outflow.T[valid.T], rise.T[valid.T]))
    values = griddata(points, pool.T[valid.T], (grid_release, grid_rate), method="linear")
    rate_grid = pd.DataFrame(values, index=releases, columns=rates).dropna(how="all", axis=1)
    for level, curve in rate_grid.items():
        decreasing = curve.diff().lt(0)
        if decreasing.any():
            rate_grid.loc[decreasing.idxmax():, level] = np.nan

    overlays = {}
    for index in range(1, 6):
        column = f"CurveName{index}"
        if column in frame and pd.notna(frame[column].iat[0]):
            overlays[frame[column].iat[0]] = frame[[f"X{index}", f"Y{index}"]].set_axis(
                ["Elev", "Release"], axis=1
            )
    return {
        "dfInflowPlot": inflow_grid.loc[:, levels],
        "dfPlotROC": rate_grid,
        "dfResv": rating,
        "dfSurchargeCurve": envelope,
        "curve_dfs": overlays,
        "param_dict": params,
        "dfTitleBlock": frame[["Line", "Text"]].dropna(),
    }
