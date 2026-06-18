# Techno-Economic Feasibility of a Decentralized Wind–UGES Microgrid in an Abandoned Mine Shaft

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20742345.svg)](https://doi.org/10.5281/zenodo.20742345)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Reproducible analysis code for the feasibility study of a 50 MW wind farm
paired with a 5 MW Underground Gravity Energy Storage (UGES) retrofit in a
494 m abandoned coal shaft at Jhimpir, Pakistan.

This repository contains the open-source models behind the manuscript's
quantitative results: grid load flow, energy-management dispatch, shaft-and-
foundation settlement, structural verification, wire-rope sizing, strike
survivability, and life-cycle embodied carbon. Every figure and headline number
in the paper can be regenerated from these scripts.

## Citation

If you use this code, please cite the archived release:

> Shakeel, F. (2026). *Techno-Economic Feasibility of a Decentralized Wind-UGES
> Microgrid in an Abandoned Mine Shaft* (v1.0.0). Zenodo.
> https://doi.org/10.5281/zenodo.20742345

A `CITATION.cff` file is included so GitHub and Zenodo can generate citation
text automatically.

## Repository layout

```
.
├── run_simulation.py   Master script: runs every module in sequence
├── loadflow/           Steady-state grid load flow (pandapower, Newton–Raphson)
│   └── loadflow.py
├── ems/                24-hour rule-based energy-management dispatch (NumPy)
│   └── ems_dispatch.py
├── settlement/         Headframe-foundation settlement (OpenSeesPy, plane strain)
│   └── settlement.py
├── structural/         Closed-form structural checks + wire-rope factor of safety
│   ├── structural.py
│   └── rope_fos.py
├── resilience/         Monte-Carlo strike-survivability and islanding endurance
│   └── resilience.py
├── lca/                Cradle-to-gate embodied-carbon life-cycle assessment
│   └── lca.py
├── requirements.txt
├── CITATION.cff
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
mainstream Linux, macOS, and Windows builds. All other modules depend only on
NumPy, matplotlib, pandapower, and Pillow.

## Running the full suite

A master script at the repository root runs every analysis module in sequence
and prints a pass/fail summary:

```
python run_simulation.py
```

Each module is executed as a standalone process from its own folder, so it
behaves exactly as it does when run individually — there are no shared-state or
import-order effects, and results are identical either way. The script exits
with status `0` only if every module completes successfully, which makes it
suitable for a continuous-integration check.

To list the modules without running them:

```
python run_simulation.py --list
```

The `settlement/` module uses OpenSeesPy and takes noticeably longer than the
others; this is expected, not a failure. Modules that produce figures write
them into the folder they run from.

## Running modules individually

Each script is self-contained and can also be run on its own from its folder:

```
python loadflow/loadflow.py
python ems/ems_dispatch.py
python settlement/settlement.py
python structural/structural.py
python structural/rope_fos.py
python resilience/resilience.py
python lca/lca.py
```

## Notes on reproducibility

- Model inputs (geometry, material properties, tariffs, discount rate) are set
  as named constants at the top of each script so they can be inspected and
  varied.
- The settlement model's overburden thickness is the one fitted parameter; all
  other geotechnical inputs are taken from the site material set.
- The Monte-Carlo resilience model uses a fixed random seed for repeatable
  output.

## License

Released under the MIT License. See `LICENSE`.
