# ESRD review sheets

Open the [stacked PNG folder](png/) or the [inset PNG folder](inset/) in an
image viewer to cycle through the sheets. Each layout has inflow and
rate-of-rise versions, with directly labeled contours, a boxed project title
block, and notes. Worked examples label the result in cfs of release. Insets retain
tick marks and values, with axis titles on the main plot. The prior PDF
edition remains in this directory.

| Reservoir | Inflow | Rate of rise | Profiles |
| --- | --- | --- | --- |
| Applegate | [Stacked](png/APP_inflow_reference.png) · [Inset](inset/APP_inflow_inset.png) | [Stacked](png/APP_rate_of_rise_reference.png) · [Inset](inset/APP_rate_of_rise_inset.png) | `APP_CONFIG.csv` + derived zoom |
| Blue River | [Stacked](png/BLU_inflow_reference.png) · [Inset](inset/BLU_inflow_inset.png) | [Stacked](png/BLU_rate_of_rise_reference.png) · [Inset](inset/BLU_rate_of_rise_inset.png) | `BLU_CONFIG.csv` + `BLU_Small_CONFIG.csv` |
| Cougar | [Stacked](png/CGR_inflow_reference.png) · [Inset](inset/CGR_inflow_inset.png) | [Stacked](png/CGR_rate_of_rise_reference.png) · [Inset](inset/CGR_rate_of_rise_inset.png) | `CGR_CONFIG.csv` + `CGR_Small_CONFIG.csv` |
| Cottage Grove | [Stacked](png/COT_inflow_reference.png) · [Inset](inset/COT_inflow_inset.png) | [Stacked](png/COT_rate_of_rise_reference.png) · [Inset](inset/COT_rate_of_rise_inset.png) | `COT_CONFIG.csv` + `COT_Small_CONFIG.csv` |
| Detroit | [Stacked](png/DET_inflow_reference.png) · [Inset](inset/DET_inflow_inset.png) | [Stacked](png/DET_rate_of_rise_reference.png) · [Inset](inset/DET_rate_of_rise_inset.png) | `Script_Folder/out/DET_CONFIG.csv` + derived zoom |
| Dorena | [Stacked](png/DOR_inflow_reference.png) · [Inset](inset/DOR_inflow_inset.png) | [Stacked](png/DOR_rate_of_rise_reference.png) · [Inset](inset/DOR_rate_of_rise_inset.png) | `DOR_CONFIG.csv` + `DOR_Small_CONFIG.csv` |
| Fall Creek | [Stacked](png/FAL_inflow_reference.png) · [Inset](inset/FAL_inflow_inset.png) | [Stacked](png/FAL_rate_of_rise_reference.png) · [Inset](inset/FAL_rate_of_rise_inset.png) | `FAL_CONFIG.csv` + `FAL_Small_CONFIG.csv` |
| Foster | [Stacked](png/FOS_inflow_reference.png) · [Inset](inset/FOS_inflow_inset.png) | [Stacked](png/FOS_rate_of_rise_reference.png) · [Inset](inset/FOS_rate_of_rise_inset.png) | `FOS_CONFIG.csv` + `FOS_Small_CONFIG.csv` |
| Fern Ridge | [Stacked](png/FRN_inflow_reference.png) · [Inset](inset/FRN_inflow_inset.png) | [Stacked](png/FRN_rate_of_rise_reference.png) · [Inset](inset/FRN_rate_of_rise_inset.png) | `FRN_CONFIG_2.csv` + `FRN_Small_CONFIG_2.csv` |
| Green Peter | [Stacked](png/GPR_inflow_reference.png) · [Inset](inset/GPR_inflow_inset.png) | [Stacked](png/GPR_rate_of_rise_reference.png) · [Inset](inset/GPR_rate_of_rise_inset.png) | `GPR_CONFIG.csv` + `GPR_Small_CONFIG.csv` |
| Hills Creek | [Stacked](png/HCR_inflow_reference.png) · [Inset](inset/HCR_inflow_inset.png) | [Stacked](png/HCR_rate_of_rise_reference.png) · [Inset](inset/HCR_rate_of_rise_inset.png) | `HCR_CONFIG.csv` + `HCR_Small_CONFIG.csv` |
| Lookout Point | [Stacked](png/LOP_inflow_reference.png) · [Inset](inset/LOP_inflow_inset.png) | [Stacked](png/LOP_rate_of_rise_reference.png) · [Inset](inset/LOP_rate_of_rise_inset.png) | `LOP_CONFIG.csv` + `LOP_Small_CONFIG.csv` |
| Lost Creek | [Stacked](png/LOS_inflow_reference.png) · [Inset](inset/LOS_inflow_inset.png) | [Stacked](png/LOS_rate_of_rise_reference.png) · [Inset](inset/LOS_rate_of_rise_inset.png) | `LOS_CONFIG.csv` + derived zoom |
| Mossyrock | — | — | `MOS_Table_CONFIG.csv` only |

Inset placement uses the open areas of the full-range chart to keep the main
curves visible. The zoom uses the checked-in small profile where available. Applegate, Detroit,
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

To regenerate both layouts from the repository root, run
`/workspace/.esrd-venv/bin/python sandbox/reservoir_review.py`.
Use `--layout inset` or `--layout stacked` for one layout,
`--reservoir COT` for one reservoir, or `--output DIRECTORY` to write both
layout folders to another location.
