# ESRD review sheets

Each reservoir has a letter-size inflow and rate-of-rise sheet. Both include
the full range, a zoomed view, directly labeled contours, and a worked example
where a unique crossing is available. The dashed guide shows how to read the
example from the chart. These sheets are for review.

| Reservoir | Inflow | Rate of rise | Profiles |
| --- | --- | --- | --- |
| Applegate | [PDF](APP_inflow_reference.pdf) | [PDF](APP_rate_of_rise_reference.pdf) | `APP_CONFIG.csv` + derived zoom |
| Blue River | [PDF](BLU_inflow_reference.pdf) | [PDF](BLU_rate_of_rise_reference.pdf) | `BLU_CONFIG.csv` + `BLU_Small_CONFIG.csv` |
| Cougar | [PDF](CGR_inflow_reference.pdf) | [PDF](CGR_rate_of_rise_reference.pdf) | `CGR_CONFIG.csv` + `CGR_Small_CONFIG.csv` |
| Cottage Grove | [PDF](COT_inflow_reference.pdf) | [PDF](COT_rate_of_rise_reference.pdf) | `COT_CONFIG.csv` + `COT_Small_CONFIG.csv` |
| Detroit | [PDF](DET_inflow_reference.pdf) | [PDF](DET_rate_of_rise_reference.pdf) | `Script_Folder/out/DET_CONFIG.csv` + derived zoom |
| Dorena | [PDF](DOR_inflow_reference.pdf) | [PDF](DOR_rate_of_rise_reference.pdf) | `DOR_CONFIG.csv` + `DOR_Small_CONFIG.csv` |
| Fall Creek | [PDF](FAL_inflow_reference.pdf) | [PDF](FAL_rate_of_rise_reference.pdf) | `FAL_CONFIG.csv` + `FAL_Small_CONFIG.csv` |
| Foster | [PDF](FOS_inflow_reference.pdf) | [PDF](FOS_rate_of_rise_reference.pdf) | `FOS_CONFIG.csv` + `FOS_Small_CONFIG.csv` |
| Fern Ridge | [PDF](FRN_inflow_reference.pdf) | [PDF](FRN_rate_of_rise_reference.pdf) | `FRN_CONFIG_2.csv` + `FRN_Small_CONFIG_2.csv` |
| Green Peter | [PDF](GPR_inflow_reference.pdf) | [PDF](GPR_rate_of_rise_reference.pdf) | `GPR_CONFIG.csv` + `GPR_Small_CONFIG.csv` |
| Hills Creek | [PDF](HCR_inflow_reference.pdf) | [PDF](HCR_rate_of_rise_reference.pdf) | `HCR_CONFIG.csv` + `HCR_Small_CONFIG.csv` |
| Lookout Point | [PDF](LOP_inflow_reference.pdf) | [PDF](LOP_rate_of_rise_reference.pdf) | `LOP_CONFIG.csv` + `LOP_Small_CONFIG.csv` |
| Lost Creek | [PDF](LOS_inflow_reference.pdf) | [PDF](LOS_rate_of_rise_reference.pdf) | `LOS_CONFIG.csv` + derived zoom |
| Mossyrock | — | — | `MOS_Table_CONFIG.csv` only |

The zoom uses the checked-in small profile where available. Applegate, Detroit,
and Lost Creek use a narrower window of their full profile. Detroit uses the
full CONFIG archived with the old outputs. Fern Ridge uses the matching
revision 2 pair. On sheets marked “Selected contours shown,” the renderer
omitted crowded contours where the labels could not share a readable line.

Mossyrock is blocked. Its only CONFIG is a table profile with 9,999,999 cfs
in every maximum-discharge row. A usable rating and plot profile are needed
to render it.

To regenerate the PDFs from the repository root, run
`/workspace/.esrd-venv/bin/python sandbox/reservoir_review.py`.
Use `--reservoir COT` for one reservoir or `--output DIRECTORY` for a
separate output location.
