# ESRD review sheets

Open the [PNG folder](png/) in an image viewer to cycle through the
letter-size inflow and rate-of-rise sheets. Both include
the full range, a zoomed view, directly labeled contours, and a worked example
where a unique crossing is available. The dashed guide shows how to read the
example from the chart. These sheets are for review. The
prior PDF edition remains in this directory.

Cottage Grove also has two landscape inset trials. The zoom sits in the open
area below the main curves. [Inflow inset](inset/COT_inflow_inset.png) ·
[Rate-of-rise inset](inset/COT_rate_of_rise_inset.png).

| Reservoir | Inflow | Rate of rise | Profiles |
| --- | --- | --- | --- |
| Applegate | [PNG](png/APP_inflow_reference.png) | [PNG](png/APP_rate_of_rise_reference.png) | `APP_CONFIG.csv` + derived zoom |
| Blue River | [PNG](png/BLU_inflow_reference.png) | [PNG](png/BLU_rate_of_rise_reference.png) | `BLU_CONFIG.csv` + `BLU_Small_CONFIG.csv` |
| Cougar | [PNG](png/CGR_inflow_reference.png) | [PNG](png/CGR_rate_of_rise_reference.png) | `CGR_CONFIG.csv` + `CGR_Small_CONFIG.csv` |
| Cottage Grove | [PNG](png/COT_inflow_reference.png) | [PNG](png/COT_rate_of_rise_reference.png) | `COT_CONFIG.csv` + `COT_Small_CONFIG.csv` |
| Detroit | [PNG](png/DET_inflow_reference.png) | [PNG](png/DET_rate_of_rise_reference.png) | `Script_Folder/out/DET_CONFIG.csv` + derived zoom |
| Dorena | [PNG](png/DOR_inflow_reference.png) | [PNG](png/DOR_rate_of_rise_reference.png) | `DOR_CONFIG.csv` + `DOR_Small_CONFIG.csv` |
| Fall Creek | [PNG](png/FAL_inflow_reference.png) | [PNG](png/FAL_rate_of_rise_reference.png) | `FAL_CONFIG.csv` + `FAL_Small_CONFIG.csv` |
| Foster | [PNG](png/FOS_inflow_reference.png) | [PNG](png/FOS_rate_of_rise_reference.png) | `FOS_CONFIG.csv` + `FOS_Small_CONFIG.csv` |
| Fern Ridge | [PNG](png/FRN_inflow_reference.png) | [PNG](png/FRN_rate_of_rise_reference.png) | `FRN_CONFIG_2.csv` + `FRN_Small_CONFIG_2.csv` |
| Green Peter | [PNG](png/GPR_inflow_reference.png) | [PNG](png/GPR_rate_of_rise_reference.png) | `GPR_CONFIG.csv` + `GPR_Small_CONFIG.csv` |
| Hills Creek | [PNG](png/HCR_inflow_reference.png) | [PNG](png/HCR_rate_of_rise_reference.png) | `HCR_CONFIG.csv` + `HCR_Small_CONFIG.csv` |
| Lookout Point | [PNG](png/LOP_inflow_reference.png) | [PNG](png/LOP_rate_of_rise_reference.png) | `LOP_CONFIG.csv` + `LOP_Small_CONFIG.csv` |
| Lost Creek | [PNG](png/LOS_inflow_reference.png) | [PNG](png/LOS_rate_of_rise_reference.png) | `LOS_CONFIG.csv` + derived zoom |
| Mossyrock | — | — | `MOS_Table_CONFIG.csv` only |

The zoom uses the checked-in small profile where available. Applegate, Detroit,
and Lost Creek use a narrower window of their full profile. Detroit uses the
full CONFIG archived with the old outputs. Fern Ridge uses the matching
revision 2 pair. On sheets marked “Selected contours shown,” the renderer
omitted crowded contours where the labels could not share a readable line.

Mossyrock is blocked. Its only CONFIG is a table profile with 9,999,999 cfs
in every maximum-discharge row. A usable rating and plot profile are needed
to render it.

Title blocks use the source CONFIG text. Detroit and Hills Creek have blank
CONFIG title blocks. Their sheets show the plotted surcharge elevation and
use the draft PDF for dam-crest elevation and attribution. The notes summarize
`Draft_Curve.pdf` where available. Some draft rate-of-rise sheets repeat the
inflow note. In those cases the sheet refers to the water control manual for
the averaging period. Applegate and Lost Creek use method and interpretation
notes because the draft PDF does not include those projects.

To regenerate the PNGs from the repository root, run
`/workspace/.esrd-venv/bin/python sandbox/reservoir_review.py`.
Use `--reservoir COT` for one reservoir or `--output DIRECTORY` for a
separate output location. For the inset trial, add `--inset --output review/esrd/inset`.
