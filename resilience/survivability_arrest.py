#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
survivability_arrest.py
Strike-survivability of buried energy inventory, re-derived so that the
per-node loss probability decomposes explicitly into shaft collapse and
failure of the shaft arrest system.

    p_sh_eff = p_collapse + (1 - p_collapse) * (1 - R_arrest)

Companion to: "Beyond Lithium and Above Ground ..."  (Sections 3.6, 9.4)
"""
import os, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import common as C
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

RNG = np.random.default_rng(20260729)

P_AG_REF   = 0.80    # per-strike destruction probability, above-ground node
P_COLL_REF = 0.05    # per-strike shaft-collapse probability
N_MC       = 100_000

def p_eff(p_collapse, R):
    """Effective per-strike inventory-loss probability for a gravity node."""
    return p_collapse + (1.0 - p_collapse)*(1.0 - R)

def expected_fraction(n_nodes, M, p):
    """
    Analytical expectation. M strikes spread as evenly as possible over
    n_nodes; node i receives m_i strikes; f = (1/n) * sum (1-p)^m_i
    """
    base, rem = divmod(M, n_nodes)
    m = np.full(n_nodes, base)
    m[:rem] += 1
    return np.mean((1.0 - p)**m)

def mc_fraction(n_nodes, M, p, n_trials=N_MC):
    """Monte-Carlo with strikes allocated at random across nodes."""
    idx = RNG.integers(0, n_nodes, size=(n_trials, M))
    counts = np.zeros((n_trials, n_nodes), dtype=np.int32)
    for j in range(M):
        np.add.at(counts, (np.arange(n_trials), idx[:, j]), 1)
    surv = (1.0 - p)**counts
    return surv.mean(axis=1)

if __name__ == "__main__":
    print("="*74)
    print("SURVIVABILITY WITH EXPLICIT ARREST-SYSTEM RELIABILITY")
    print("="*74)
    print(f"p_AG (above-ground)   {P_AG_REF}")
    print(f"p_collapse (shaft)    {P_COLL_REF}")

    # ---- reproduce the published reference case (perfect arrest) ----
    print("\n" + "-"*74)
    print("VERIFICATION AGAINST PUBLISHED FIGURES (R_arrest = 1.0)")
    print("-"*74)
    p0 = p_eff(P_COLL_REF, 1.0)
    for M in (2, 4):
        bat = expected_fraction(1, M, P_AG_REF)
        g1  = expected_fraction(1, M, p0)
        g5  = expected_fraction(5, M, p0)
        print(f"  M={M}: battery {bat*100:5.1f}%   1 shaft {g1*100:5.1f}%   "
              f"5 shafts {g5*100:5.1f}%")

    # ---- sensitivity to arrest reliability ----
    print("\n" + "-"*74)
    print("SENSITIVITY OF THE HEADLINE RESULT TO ARREST RELIABILITY (M = 2)")
    print("-"*74)
    print(f"{'R_arrest':>9} {'p_sh_eff':>10} {'1 shaft':>9} {'5 shafts':>10} "
          f"{'vs battery':>11}")
    bat2 = expected_fraction(1, 2, P_AG_REF)
    rows = []
    for R in (1.000, 0.999, 0.99, 0.95, 0.90, 0.80, 0.50, 0.0):
        pe = p_eff(P_COLL_REF, R)
        g1 = expected_fraction(1, 2, pe)
        g5 = expected_fraction(5, 2, pe)
        rows.append((R, pe, g1, g5))
        print(f"{R:9.3f} {pe:10.4f} {g1*100:8.1f}% {g5*100:9.1f}% "
              f"{g1/bat2:10.1f}x")

    # ---- reliability needed to hold specific claims ----
    print("\n" + "-"*74)
    print("REQUIRED ARREST RELIABILITY")
    print("-"*74)
    Rs = np.linspace(0.0, 1.0, 200_001)
    g1s = np.array([(1.0 - p_eff(P_COLL_REF, R))**2 for R in Rs])
    for target in (0.90, 0.85, 0.80, 0.50):
        ok = Rs[g1s >= target]
        if len(ok):
            print(f"  single shaft retains >= {target*100:.0f}%  ->  "
                  f"R_arrest >= {ok.min():.4f}")
    # break-even against the battery
    be = Rs[g1s >= bat2]
    print(f"  single shaft beats battery ({bat2*100:.1f}%)  ->  "
          f"R_arrest >= {be.min():.4f}")

    # ---- Monte-Carlo confirmation at a degraded reliability ----
    print("\n" + "-"*74)
    print("MONTE-CARLO CHECK, RANDOM STRIKE ALLOCATION (N = 100,000)")
    print("-"*74)
    for R in (1.0, 0.95, 0.90):
        pe = p_eff(P_COLL_REF, R)
        s5 = mc_fraction(5, 2, pe)
        print(f"  R={R:.2f}  5 shafts: mean {s5.mean()*100:5.1f}%  "
              f"P5 {np.percentile(s5,5)*100:5.1f}%")

    # ---- figure ----
    Rg = np.linspace(0.5, 1.0, 400)
    f1 = np.array([(1-p_eff(P_COLL_REF,R))**2 for R in Rg])*100
    f5 = np.array([expected_fraction(5,2,p_eff(P_COLL_REF,R)) for R in Rg])*100

    OUT = os.path.join(ROOT, "figure_data")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "figures"), exist_ok=True)
    np.savetxt(os.path.join(OUT, "fig12_arrest_reliability.csv"),
               np.column_stack([Rg*100, f1, f5,
                                np.full_like(Rg, bat2*100)]),
               delimiter=",",
               header="R_arrest_pct,one_shaft_pct,five_shafts_pct,battery_pct",
               comments="")
    print("wrote figure_data/fig12_arrest_reliability.csv")

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.plot(Rg*100, f5, lw=2.0, label="5 dispersed shafts")
    ax.plot(Rg*100, f1, lw=2.0, label="1 shaft (Jhimpir, as designed)")
    ax.axhline(bat2*100, ls="--", lw=1.6, color="crimson",
               label=f"above-ground battery ({bat2*100:.1f}%)")
    ax.axvline(99.86, ls=":", lw=1.4, color="grey")
    ax.annotate("R = 99.9% holds the\n90% headline result",
                xy=(99.86, 90), xytext=(88, 62), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8, color="grey"))
    ax.set_xlabel("arrest-system reliability $R$ (%)")
    ax.set_ylabel("expected surviving\ninventory (%)")
    ax.set_xlim(50, 100); ax.set_ylim(0, 100)
    ax.legend(fontsize=8, loc="lower left", framealpha=0.9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "figures", "fig_arrest_reliability.png"),
                dpi=155, bbox_inches="tight")
    with open(os.path.join(ROOT, "results", "survivability_arrest.json"), "w") as fh:
        json.dump(dict(
            p_AG=P_AG_REF, p_collapse=P_COLL_REF,
            battery_M2_pct=bat2*100,
            reliability_table=[dict(R=R, p_sh_eff=pe,
                                    one_shaft_pct=g1*100, five_shafts_pct=g5*100)
                               for R, pe, g1, g5 in rows],
        ), fh, indent=2)
    print("Wrote results/survivability_arrest.json")
    print("Wrote figures/fig_arrest_reliability.png")
