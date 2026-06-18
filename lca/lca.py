"""
Cradle-to-Gate Life Cycle Assessment (GWP-100) for the Jhimpir UGES retrofit.

Replaces the OpenLCA workflow with a transparent, editable Python calculation.
Scope: A1-A3 (raw material supply + transport to gate + manufacturing) of the
permanent civil/structural materials of the UGES system only. Wind farm,
transport to site (A4), construction (A5), operation and end-of-life are
excluded, matching a cradle-to-gate boundary.

Characterisation: GWP-100 (IPCC AR5/2013), kg CO2-eq.

Emission factors are cradle-to-gate (A1-A3) embodied carbon coefficients.
Primary source: Inventory of Carbon & Energy (ICE) Database v3.0,
Circular Ecology / Hammond & Jones (2019). https://circularecology.com/embodied-carbon-footprint-database.html
Values are openly published and are the standard UK/EU reference for A1-A3
embodied carbon. Where a process is forging- or drawing-intensive (Koepe
sheave, wire rope) an uplift over plain section steel is applied and noted.

ALL factors and quantities below are editable. After the headframe redesign,
update the QUANTITIES block (masses in tonnes) and re-run.

Author: F. Shakeel
"""

import json
import csv

# ----------------------------------------------------------------------------
# 1. MATERIAL INVENTORY  (tonnes)  -- update these after the headframe redesign
#    Quantities taken from FYDP.xlsx > "Tecno-Economic Analysis" sheet.
# ----------------------------------------------------------------------------
CONCRETE_DENSITY = 2.400  # t/m3 (cell D75)

# Concrete volumes (m3)
V_LINER_CONCRETE      = 1613.2064   # cell I4
V_PISTON_CONCRETE     = 415.265     # cell I5
FOUNDATION_CONC_TONNE = 718.0       # cell I21 (already in tonnes)

# Reinforcement ratios (kg steel / m3 concrete)
LINER_REBAR_RATIO  = 120.0  # cell I19
PISTON_REBAR_RATIO = 150.0  # cell I25

# Discrete steel masses (tonnes)
HEADFRAME_STEEL_TONNE = 76.0    # cell I23  -- UPDATE after redesign
KOEPE_SHEAVE_TONNE    = 222.0   # cell I28 (x2 sheaves, forged AISI 4340)

# Wire rope: 8 x 48 mm ropes over the shaft. 48 mm 6-strand IWRC rope is
# ~9.9 kg/m. Effective suspended length per rope ~ shaft depth (494 m).
ROPE_LINEAR_MASS = 9.9     # kg/m  (48 mm 6x36 IWRC, manufacturer datasheet range 9.5-10.3)
ROPE_COUNT       = 8
ROPE_LENGTH_M    = 494.0
WIRE_ROPE_TONNE  = ROPE_LINEAR_MASS * ROPE_COUNT * ROPE_LENGTH_M / 1000.0

# Derived masses (tonnes)
m_liner_concrete  = V_LINER_CONCRETE  * CONCRETE_DENSITY
m_piston_concrete = V_PISTON_CONCRETE * CONCRETE_DENSITY
m_foundation_conc = FOUNDATION_CONC_TONNE
m_liner_rebar     = LINER_REBAR_RATIO  * V_LINER_CONCRETE  / 1000.0
m_piston_rebar    = PISTON_REBAR_RATIO * V_PISTON_CONCRETE / 1000.0

# ----------------------------------------------------------------------------
# 2. EMISSION FACTOR LIBRARY  (kg CO2-eq / kg material, cradle-to-gate A1-A3)
#    Two scenarios: 'virgin' (primary/BF-BOF route) and 'recycled' (EAF/high
#    recycled content). Pakistani structural steel is predominantly induction-
#    furnace remelt of scrap, so 'recycled' is the more representative default
#    for the local supply chain; 'virgin' is the conservative upper bound.
# ----------------------------------------------------------------------------
EMISSION_FACTORS = {
    # material            : {'virgin': EF, 'recycled': EF, 'source': ...}
    "concrete_C40_50": {
        "virgin":   0.151, "recycled": 0.151,   # concrete EF is route-independent here
        "source": "ICE v3.0, Concrete 40 MPa (RC40), 0.151 kgCO2e/kg",
    },
    "rebar": {
        "virgin":   1.99,  "recycled": 1.40,
        "source": "ICE v3.0, Steel reinforcement bar; virgin world-avg 1.99, recycled-route 1.40",
    },
    "structural_steel": {
        "virgin":   2.45,  "recycled": 1.13,
        "source": "ICE v3.0, Steel section; primary 2.45, recycled-route 1.13 kgCO2e/kg",
    },
    "forged_steel": {
        # plain section steel + forging energy uplift (~0.35 kgCO2e/kg forging,
        # Ashby, Materials & the Environment, 2nd ed., forging process energy)
        "virgin":   2.80,  "recycled": 1.55,
        "source": "ICE v3.0 section steel + forging uplift (Ashby 2013, forging process energy ~0.35 kgCO2e/kg)",
    },
    "wire_rope": {
        # high-carbon drawn wire; drawing + galvanising uplift over section steel
        "virgin":   2.90,  "recycled": 1.75,
        "source": "ICE v3.0 wire (drawn) 2.83-3.02; mid-value with galvanising",
    },
}

# ----------------------------------------------------------------------------
# 3. ASSEMBLE INVENTORY  -> (material_key, mass_tonnes, component_label)
# ----------------------------------------------------------------------------
INVENTORY = [
    ("concrete_C40_50", m_liner_concrete,  "Shaft liner concrete"),
    ("concrete_C40_50", m_piston_concrete, "Piston concrete"),
    ("concrete_C40_50", m_foundation_conc, "Headframe foundation concrete"),
    ("rebar",           m_liner_rebar,     "Liner reinforcement"),
    ("rebar",           m_piston_rebar,    "Piston reinforcement"),
    ("structural_steel",HEADFRAME_STEEL_TONNE, "Headframe structural steel"),
    ("forged_steel",    KOEPE_SHEAVE_TONNE,    "Koepe sheave (x2, forged)"),
    ("wire_rope",       WIRE_ROPE_TONNE,       "Hoist wire rope (8 x 48 mm)"),
]

# ----------------------------------------------------------------------------
# 4. CALCULATE
# ----------------------------------------------------------------------------
def run_lca(scenario="recycled"):
    rows = []
    total = 0.0
    for key, mass_t, label in INVENTORY:
        ef = EMISSION_FACTORS[key][scenario]          # kgCO2e/kg
        gwp_t = mass_t * 1000.0 * ef / 1000.0          # tonnes CO2e
        total += gwp_t
        rows.append({
            "component": label,
            "material": key,
            "mass_t": round(mass_t, 1),
            "ef_kgco2e_per_kg": ef,
            "gwp_tco2e": round(gwp_t, 1),
        })
    for r in rows:
        r["share_pct"] = round(100.0 * r["gwp_tco2e"] / total, 1)
    return rows, total


def material_rollup(rows):
    agg = {}
    for r in rows:
        agg.setdefault(r["material"], 0.0)
        agg[r["material"]] += r["gwp_tco2e"]
    return agg


if __name__ == "__main__":
    print("=" * 78)
    print("CRADLE-TO-GATE LCA (GWP-100) - Jhimpir UGES structure")
    print("=" * 78)

    for scenario in ("recycled", "virgin"):
        rows, total = run_lca(scenario)
        print(f"\n--- Scenario: {scenario.upper()} steel route ---")
        print(f"{'Component':<34}{'Mass (t)':>10}{'EF':>7}{'GWP (tCO2e)':>14}{'%':>7}")
        print("-" * 78)
        for r in rows:
            print(f"{r['component']:<34}{r['mass_t']:>10.1f}{r['ef_kgco2e_per_kg']:>7.2f}"
                  f"{r['gwp_tco2e']:>14.1f}{r['share_pct']:>7.1f}")
        print("-" * 78)
        print(f"{'TOTAL':<34}{'':>10}{'':>7}{total:>14.1f}{100.0:>7.1f}")

        roll = material_rollup(rows)
        print(f"\n  By material class:")
        for mat, g in sorted(roll.items(), key=lambda x: -x[1]):
            print(f"    {mat:<22}{g:>10.1f} tCO2e ({100*g/total:>5.1f}%)")

    # Export the representative (recycled-route) result
    rows, total = run_lca("recycled")
    with open("uges_lca_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["component", "material", "mass_t",
                                          "ef_kgco2e_per_kg", "gwp_tco2e", "share_pct"])
        w.writeheader()
        w.writerows(rows)
        w.writerow({"component": "TOTAL", "material": "", "mass_t": "",
                    "ef_kgco2e_per_kg": "", "gwp_tco2e": round(total, 1), "share_pct": 100.0})

    summary = {
        "scope": "Cradle-to-gate (A1-A3), UGES civil/structural materials only",
        "method": "GWP-100 (IPCC AR5/2013)",
        "ef_database": "ICE v3.0 (Circular Ecology / Hammond & Jones, 2019) + forging/drawing uplifts",
        "total_recycled_route_tco2e": round(run_lca("recycled")[1], 1),
        "total_virgin_route_tco2e": round(run_lca("virgin")[1], 1),
        "note": "Original manuscript figure of 290,309 tCO2e is ~130x this result and is a scale/units error.",
    }
    with open("uges_lca_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\nWrote: uges_lca_results.csv, uges_lca_summary.json")


def make_chart():
    """Generate a publication-quality stacked breakdown chart (both scenarios)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mats = ["concrete_C40_50", "rebar", "structural_steel", "forged_steel", "wire_rope"]
    labels = ["Concrete C40/50", "Rebar", "Structural steel", "Forged steel (sheave)", "Wire rope"]
    colors = ["#6E7B8B", "#C44E52", "#4C72B0", "#8C8C00", "#55A868"]

    data = {}
    for sc in ("recycled", "virgin"):
        rows, _ = run_lca(sc)
        roll = material_rollup(rows)
        data[sc] = [roll.get(m, 0.0) for m in mats]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = [0, 1]
    bottoms = [0.0, 0.0]
    for i, m in enumerate(mats):
        vals = [data["recycled"][i], data["virgin"][i]]
        ax.bar(x, vals, bottom=bottoms, width=0.55, label=labels[i], color=colors[i],
               edgecolor="white", linewidth=0.6)
        bottoms = [bottoms[0] + vals[0], bottoms[1] + vals[1]]

    for xi, sc in zip(x, ("recycled", "virgin")):
        tot = sum(data[sc])
        ax.text(xi, tot + 30, f"{tot:,.0f}", ha="center", va="bottom",
                fontsize=11, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(["Recycled steel\nroute (local mix)", "Virgin steel\nroute (upper bound)"])
    ax.set_ylabel("Embodied carbon, cradle-to-gate (t CO$_2$-eq)")
    ax.set_title("UGES structure embodied carbon by material (GWP-100, A1\u2013A3)")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(sum(data["virgin"]), sum(data["recycled"])) * 1.18)
    fig.tight_layout()
    fig.savefig("uges_lca_breakdown.png", dpi=300, bbox_inches="tight")
    print("Wrote: uges_lca_breakdown.png")


make_chart()
