# v2.0.0 — Measured-resource rebuild

**Release title:** `v2.0.0 — Measured resource, measured rotor: site wind record, QBlade power curve, and IEC 61400-12-1 density normalisation`

**Tag:** `v2.0.0`  ·  **Date:** 2026-07-28  ·  **Supersedes:** v1.0.1 (2026-07-06)

---

## Why this is a major version

Every headline result in this package changed. Anyone who ran v1.0.1 and quoted its
outputs will get different numbers here, and one entry point (`gen_figs.py`) no longer
runs. Under semantic versioning both are breaking changes, so this is `2.0.0` rather
than a minor bump.

**Do not mix outputs across versions.** Results from v1.x should be regarded as
superseded, not as an alternative scenario.

---

## What changed and why

### The wind resource is now measured, not modelled

v1.x used Weibull parameters `k ≈ 2.6, c ≈ 8.1 m s⁻¹`, which do not appear in the cited
mast study. They are close to Global Wind Atlas mesoscale values. The complete-record
fit in the cited source is `k = 2.17, c = 7.48 m s⁻¹` at 80 m (mean 6.50 m s⁻¹), carried
to 100 m as `c = 7.72 m s⁻¹` with `k` unchanged, since a constant shear factor rescales
the scale parameter alone.

### The power curve is the exported rotor, not an assumed one

v1.x reported a peak power coefficient of 0.4821 at λ = 7. The blade-element sweep does
not support that: Cp rises monotonically to **0.383 at λ = 10**, the truncation point,
and never peaks within the swept range. Modern three-bladed rotors peak near λ = 7–8, so
a curve still climbing at λ = 10 has not resolved its own maximum. That figure is now
reported as a **truncated lower bound, not peak Cp**, and energy capture is taken from
the exported power curve directly (Region-2 efficiency 0.440 at the solver reference
density).

### Air density follows IEC 61400-12-1

For a pitch-regulated machine the standard normalises **wind speed**, not power:
`v_n = v(ρ/ρ_ref)^(1/3)`. Monthly densities were computed from climate normals at 45 m
elevation and run from 1.197 kg m⁻³ (January) to 1.136 kg m⁻³ (June). Because the windy
months are also the hottest, the **energy-weighted density (1.1527 kg m⁻³) sits below the
annual arithmetic mean (1.1601)**; the energy-weighted value is the one used.

### Geotechnical constitutive correction

Rock-mass modulus corrected from 4.0 GPa to a regional-analog **0.25 GPa**, with a
friction-consistent Drucker–Prager treatment replacing the pressure-independent
idealisation that was driving artificial bearing failure.

---

## Results: v1.0.1 → v2.0.0

| Quantity | v1.0.1 | v2.0.0 |
|---|---|---|
| Gross farm AEP | 153.3 GWh | **120.2 GWh** |
| Net farm AEP | 120.23 GWh | **89.7 GWh** |
| Net capacity factor | 27.4% | **20.5%** |
| Weibull (80 m) | k 2.6, c 8.1 m s⁻¹ | **k 2.17, c 7.48 m s⁻¹** |
| Air density | 1.074 kg m⁻³ (declared) | **1.1527 kg m⁻³ (energy-weighted)** |
| Rotor Cp | 0.4821 "peak" at λ = 7 | **0.383 truncated at λ = 10; Region-2 0.440** |
| Rated wind speed | 12 m s⁻¹ | **13.0 m s⁻¹** |
| Footing settlement | 7.5 mm | **11.1 mm** (band 9.2–16.5 mm) |
| Rock-mass modulus | 4.0 GPa | **0.25 GPa** |
| Bearing factor of safety | 17.5 | **≈ 39** |
| 30-yr system carbon | 42,526 tCO₂e | **32,451 tCO₂e** |
| BESS comparator | 46,343–56,343 tCO₂e | **36,268–46,268 tCO₂e** |
| Islanding, shed hospital core | 85.3% | **77.7%** |
| LCOS P10/P50/P90 (PKR kWh⁻¹) | 15.4 / 19.2 / 23.8 | **15.3 / 19.0 / 23.5** |
| NPV P10/P50/P90 (M PKR) | −8 / 657 / 1,402 | **+19 / 688 / 1,437** |
| Pr(NPV > 0) | 89.7% | **90.8%** |

### Unchanged

The storage results do not depend on wind yield and are carried through intact:
round-trip efficiency **84.97%**, **17,337.5 MWh** discharged per year, **46 strokes/day**
on a **1.083 MWh** cycle, deterministic base-case **NPV +722 M PKR**, **IRR 19.3%**. The
storage-only embodied-carbon ratio against an equal-service battery remains **1.6–5.8×**,
and the critical-mineral result is unchanged: **zero lithium and zero graphite** against
roughly 17 t and 180 t for the LFP equivalent.

---

## Added

- `dispatch/annual_dispatch.py` — representative-year seasonal dispatch at fixed rated
  duty; reports the charge-source split (52% wind-sourced annually; 97% across the
  monsoon; 1–15% in the low-wind months) and 16.1 GWh yr⁻¹ of exported surplus.
- `lca/lca_resource.py` — abiotic depletion and critical-mineral bill against an
  equal-service battery.
- `make_figures.py` — single source of truth for figure generation.
- `figure_data/qblade_power_curve.csv` — power curve as exported, at the solver
  reference density.
- `figure_data/power_curve_site_density.csv` — same curve normalised to site density.
- `common.py` — `turbine_MW()`, `QB_V`, `QB_P`, `RHO_REF`, `RHO_SITE_EW`, `D_ROTOR`,
  `CP_REGION2`, `SPECIFIC_POWER_W_M2`.

## Changed

- Monte-Carlo availability sampled **0.92–0.98**, centred on the 0.95 design point
  (previously 0.90–0.98, which biased the median low).
- `resilience/islanding_arma.py` and `dispatch/annual_dispatch.py` now call the shared
  measured power curve instead of local analytic approximations.
- Figures regenerated; legends moved clear of plotted data and code-limit lines.

## Removed / breaking

- `gen_figs.py` raises on import. It would overwrite corrected figures with stale
  versions. Use `make_figures.py`.

---

## Known limitations

These are open by nature of the available data, not deferred work:

1. **Rope bending-fatigue capacity** has no published endurance curve at this rope
   diameter and sheave ratio. Demand is exact from hoist kinematics; capacity remains an
   assumption pending a full-scale endurance test.
2. **Piston–air-column aeroelastic coupling** sets a liner overpressure for which no
   validated model exists at this shaft aspect ratio.
3. **No harmonised life-cycle method** places gravity and electrochemical storage on a
   common element-depletion basis, so the abiotic depletion ratio is order-of-magnitude.
   The critical-mineral mass comparison is method-independent and is the durable claim.
4. **Shaft depth, stratigraphy, and residual gas** require borehole logging, site
   investigation, and in-situ desorption sampling respectively.
5. **Specific power of 398 W m⁻²** is high for a 6.6 m s⁻¹ hub-height resource. A
   110–117 m rotor on the same generator would raise capacity factor materially; the
   89.4 m rotor is retained because it is the geometry actually modelled.

## Reproducing

```bash
python run_simulation.py     # all modules; writes results/*.json and figures/*.png
python make_figures.py       # regenerates manuscript figures
```

Requires NumPy, SciPy, matplotlib, PuLP, SALib. Air-density inputs derive from published
climate normals for the nearest first-order station, not on-site metering; substitute
mast-station temperature and humidity where available.
