# Cottage Grove ESRD sandbox

From the repository root, run with the cloud Python environment:

```bash
mkdir -p /workspace/scratch/esrd-cache
MPLCONFIGDIR=/workspace/scratch/esrd-cache XDG_CACHE_HOME=/workspace/scratch/esrd-cache \
  /workspace/.esrd-venv/bin/python sandbox/cot_composite.py
```

The command writes PNG and vector PDF composites for inflow and elevation rate
of change, full and small lookup CSVs, and a capacity comparison to
`sandbox/out/`. Use `--output DIRECTORY` to save another run separately.

The full and zoomed panels use their respective COT CONFIG profiles. Both use
existing smoothed elevation–storage points and the legacy maximum-release
curve and surcharge envelope. The profiles have different curve settings, so
the zoomed panel is computed separately. The pilot checks that both profiles
agree with the recommended recession time in the surcharge workbook (30 hr).
It runs the existing calculation in a temporary directory.

The capacity comparison interpolates the two Cottage Grove outlet ratings in
`ReleaseCapacity.csv` onto the full CONFIG elevation grid. Blank values are
outside an outlet's data range. The comparison keeps each outlet separate and
retains the existing maximum-release curve alongside them. Substituting a
combined curve would require reconciling outlet transitions and the legacy
limit at maximum pool. The high-resolution table profile and server refresh
are outside this pilot.

The full-range lookup CSVs match a fresh run of the legacy script byte for
byte. The full-range rate-of-change lookup reproduces a legacy interpolation
defect at elevation 803 ft, above the 802.6 ft surcharge envelope. That row
contains infinite and implausibly large values. Treat the outputs as
development artifacts pending numerical review.

## Alternate portrait reference sheets

Run `/workspace/.esrd-venv/bin/python sandbox/cot_reference_sheet.py` from the
repository root. The alternate renderer writes letter-size PDFs and PNGs to
`sandbox/out/reference/`. Each page has a full-range chart, a zoomed
view, and one worked reading example interpolated from the plotted curve.
