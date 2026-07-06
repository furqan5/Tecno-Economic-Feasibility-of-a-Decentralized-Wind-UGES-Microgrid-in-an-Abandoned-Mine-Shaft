# Techno-Economic Feasibility of a Decentralized Wind–UGES Microgrid in an Abandoned Mine Shaft

Reproducible analysis code for the feasibility study of a 50 MW wind farm
paired with a 5 MW Underground Gravity Energy Storage (UGES) retrofit in a
494 m abandoned coal shaft at Jhimpir, Pakistan.

This repository contains the open-source models behind the manuscript's
quantitative results: grid load flow, energy-management dispatch, shaft-and-
foundation settlement, structural verification, wire-rope sizing, strike
survivability, and life-cycle embodied carbon. Every figure and headline number
in the paper can be regenerated from these scripts. Numerical results come
from the Python modules; the publication figures are drawn in MATLAB from the
CSV files the modules export (see **Figures** below).

## Repository layout

```
jhimpir_wind_uges/
├── loadflow/       Steady-state grid load flow (pandapower, Newton–Raphson)
│   └── loadflow.py
├── ems/            24-hour rule-based energy-management dispatch (NumPy)
│   └── ems_dispatch.py
├── settlement/     Headframe-foundation settlement (OpenSeesPy, plane strain)
│   └── settlement.py
├── structural/     Closed-form structural checks + wire-rope factor of safety
│   ├── structural.py
│   └── rope_fos.py
├── resilience/     Monte-Carlo strike-survivability and islanding endurance
│   └── resilience.py
├── lca/            Cradle-to-gate embodied-carbon life-cycle assessment
│   └── lca.py
├── figure_data/    CSVs written by the modules, read by the MATLAB figures
├── make_mpce_figures.m   Publication figures 3–7 (MATLAB; reads figure_data/)
├── requirements.txt
├── LICENSE
└── README.md
```

## What each module computes

**loadflow/** — Builds the 50 MW farm + 5 MW UGES interconnection on a 33 kV
collector bus, a 33/132 kV step-up, and a 132 kV double-circuit line to the
220/132 kV grid station modelled as the slack bus. Solves charging and
discharging scenarios and reports net export, point-of-common-coupling voltage,
transformer loading, and losses. Transformer and line impedances are standard
IEC 60076 class values; results are reproducible to within solver tolerance.

**ems/** — Four-mode rule-based dispatch (charge below a price threshold while
the state of charge has headroom; discharge into the daily price peak;
curtailment avoidance; strategic-reserve floor). Reports the daily dispatch
trajectory, the state-of-charge band, and the single-cycle round-trip
efficiency. All thresholds and the tariff/surplus profiles are configurable at
the top of the file.

**settlement/** — Plane-strain finite-element model of the headframe footing on
a two-layer profile: a Mohr–Coulomb overburden (E′ = 50 MPa, c′ = 5 kPa,
φ′ = 28°) over a stiffer sandstone-shale rock mass (E_rm = 4.0 GPa), with the
200 mm concrete shaft liner represented as an elastic ring. Returns the maximum
surface settlement under the headframe load and the settlement profile.

**structural/** — Closed-form strength-of-materials verification of the
four-column RHS headframe (axial + frame bending, factor of safety against
yield), the concrete piston (lifting-interface tension, self-weight
compression, Euler column buckling), and the forged sheave. `rope_fos.py`
computes the wire-rope factor of safety from the ISO 2408 minimum-breaking-force
relation for a multi-rope friction winder and the resulting sheave tread
pressure.

**resilience/** — Parametric Monte-Carlo model comparing the surviving energy
inventory of above-ground battery storage against single and dispersed
underground shafts under multi-strike salvos, plus an islanding-endurance
calculation for representative critical loads (telecom, hospital, forward
operating base).

**lca/** — Cradle-to-gate embodied-carbon estimate for the dominant materials
(structural steel, cement) using IPCC GWP-100a characterization factors.

## Requirements

Python 3.10 or later. Install dependencies with:

```
pip install -r requirements.txt
```

Note: `openseespy` (used only by `settlement/`) ships as a binary wheel for
mainstream Linux, macOS, and Windows builds. The modules depend only on NumPy,
pandapower, OpenSeesPy, and openpyxl — there is no Python plotting dependency.
The publication figures are produced separately in **MATLAB R2020a or later**
(`make_mpce_figures.m`); MATLAB is not required to reproduce any number.

## Running the full suite

A master script at the repository root runs every analysis module in sequence
and prints a pass/fail summary:

```
python run_simulation.py
```

Each module is executed as a standalone process from its own folder, so it
behaves exactly as it does when run individually — there are no shared-state
or import-order effects, and results are identical either way. The script exits
with status `0` only if every module completes successfully, which makes it
suitable for a continuous-integration check.

To list the modules without running them:

```
python run_simulation.py --list
```

## Running individual modules

Each script is self-contained and runs from its own folder with no
configuration or environment variables:

```
python loadflow/loadflow.py
python ems/ems_dispatch.py
python settlement/settlement.py
python structural/structural.py
python structural/rope_fos.py
python resilience/resilience.py
python lca/lca.py
```

Scripts print their key results to standard output and write the data behind
their figure into `figure_data/*.csv` (see **Figures**).

## Figures

Figures 3–7 in the manuscript are drawn in MATLAB, not Python, and follow a
single-source-of-truth data bridge so a figure can never disagree with the
number it plots:

1. `python run_simulation.py` runs the models and writes one CSV per figure
   into `figure_data/` (e.g. `fig4_loadflow.csv`, `fig6_structural.csv`).
2. Open `make_mpce_figures.m` in MATLAB R2020a+, run the top cell once, then
   run any figure cell. It reads the CSVs and exports 300-dpi TIFF (LZW) at
   IEEE column widths (8.9 cm single / 18.2 cm double).

The CSVs are regenerated on every run, so editing a model input and re-running
the Python propagates straight into the figures. To restyle a figure without
touching the analysis, edit only the `.m`.

| CSV | Figure | Produced by |
|-----|--------|-------------|
| `fig3_settlement.csv` | 3 – foundation settlement bowl | `settlement/settlement.py` |
| `fig4_loadflow.csv` | 4 – load-flow steady state | `loadflow/loadflow.py` |
| `fig5_ems.csv` | 5 – 24-h EMS dispatch | `ems/ems_dispatch.py` |
| `fig6_structural.csv` | 6 – factors of safety | `structural/structural.py` |
| `fig7a_survivability.csv`, `fig7b_islanding.csv` | 7 – resilience | `resilience/resilience.py` |

`settlement/settlement.py` also writes `settlement_opensees_profile.csv` (the
raw plane-strain FE profile, kept for the record). The published Fig-3 curve in
`fig3_settlement.csv` is a representative bowl anchored to the PLAXIS 3D maximum;
replace its two columns with the PLAXIS settlement path for the final figure.

## Notes on reproducibility

- Model inputs (geometry, material properties, tariffs, discount rate) are set
  as named constants at the top of each script so they can be inspected and
  varied.
- The settlement model's overburden thickness is the one fitted parameter; all
  other geotechnical inputs are taken from the site material set.
- The Monte-Carlo resilience model uses a fixed random seed for repeatable
  output.

## Citation

If you use this code, please cite the associated manuscript and this
repository's archived release on Zenodo (cite the v1.0.1 version DOI).

## License

Released under the MIT License. See `LICENSE`.
