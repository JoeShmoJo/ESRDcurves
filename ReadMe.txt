Josh Roach
ENC-HY
ENC-HR Detail
30Sep2024

Script reads CONFIG files and calculates Emergency Spillway Release Diagram (ESRD), otherwise known as special curves, using methodology outlined in EM 1110-2-3600 (2017 version), section 4.5.4
There are 3 CONFIG files for each reservoir; one for the full size plot starting not far below the spillway and extending to the top of the dam and out to the maximum release capacity at full pool, a XXX_Small_CONFIG file that is focused on the upper left and corner of the curve most likely to be used by regulators, and a 3rd XXX_Table_CONFIG file that that serves to produce lookup tables at the highest possible resolution. 

For proper plotting of of curves, script needs the correct TS, maximum reservoir elevation, and an accurate storage elevation curve.

TS and maximum elevation are taken from the WCM. These parameters have been collected from each WCM and placed in the Explicit_&_Induced_Surcharge_Function_ESRD_Params.xlsx .

Storage capacities were taken from  https://nwp-wmops.nwp.usace.army.mil/nwp/ratings/www/rating_links/ [ 3 letter reservoir abbreviation ].txt  . These storage curves were smoothed to faciliated production of the Elevation Rate of Change plots. The resulting storage curve is visually indistinguishable from the original, but the elevation rate of change (ROC) calculations are extremely sensative to the rate of change of the slope of the storage rating curve. This smoothing process greatly improves the readability of the ROC ESRD curves and is appropriate when the pool rate of change used is the average of the past 3 or 6 hours as outlined by the project's WCM. 

Maximum free flow (spillway) and full gate opening (RO) outlet capacity curves were taken from spreadsheets found at https://team.usace.army.mil/sites/NWP/EC/H/water_mgmt/Outlet%20Rating%20Tables/Forms/AllItems.aspx . 

The bottom curve on the ESRD represents the maximum design capacity of the regulating outlet and the greater of the spillway or penstock capacity. This assumes penstocks can be used when below the spillway but that the penstock flow will be shut off once the spillway begins being used.Penstock capacity is negligable compared to spillway capacity soon after rising above the spillway. RO capacity is shown for the entire curve provided in the HR rating curves. For reservoirs where regulating outlets are not defined above a given elevation, the maximum capacity curve is smoothed to show a transition from the RO to the Spillway that does not show a reduction in capacity. A seperate capacity curve representing only the spillway is shown as well. 

Capacity curves may not represent all limitations, expecially RO curves at DOR, COT, FRN, and other RO limitations at DET and LOP. 

The maximum capacities shown on the curves are design capacities and may not indicate all project limitations assocatied with gate openings or the concurant use of the RO and Spillway at high discharges. 