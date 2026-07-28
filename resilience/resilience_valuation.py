"""
05_resilience_valuation.py

Three linked pieces that turn the manuscript's resilience narrative into numbers:
  (A) Strike-survivability Monte Carlo  (reproduces the 4.0 / 90.2 / 98.0% result)
  (B) Islanding endurance from the site Weibull wind fit (Table VI style)
  (C) MONETISED resilience: Value of Resilience VoR = EENS_avoided x VoLL, with
      VoLL swept over the international range and the Pakistan value flagged unknown,
      plus a resilience-adjusted LCOS.

Open-source: numpy only. VoLL and grid-outage exposure are the only non-manuscript
inputs; both are swept and clearly labelled [A]/[L].
"""
import numpy as np, json, os
os.makedirs("../results", exist_ok=True); os.makedirs("../figures", exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C
rng = np.random.default_rng(7)

# =====================================================================
# (A) STRIKE-SURVIVABILITY MONTE CARLO
# =====================================================================
def survive_fraction(n_nodes, M_strikes, p_loss, trials=100000):
    """Mean + 5th-pct surviving inventory fraction: strikes ~ multinomial over nodes,
       node keeps (1-p_loss)^m of its share. f = mean_i (1-p_loss)^{m_i}."""
    hits = rng.multinomial(M_strikes, np.full(n_nodes, 1/n_nodes), size=trials)
    f = ((1 - p_loss) ** hits).mean(axis=1)
    return f.mean(), np.percentile(f, 5)

P_AG, P_SH = 0.8, 0.05          # [A] reference per-strike loss probs (manuscript)
print("=== (A) STRIKE SURVIVABILITY (p_AG=0.8, p_sh=0.05) ===")
for M in (2, 4):
    ag,_   = survive_fraction(1, M, P_AG)
    u1,_   = survive_fraction(1, M, P_SH)
    u5,u5p = survive_fraction(5, M, P_SH)
    print(f"  M={M}: BESS(1)={ag*100:5.1f}%  UGES(1)={u1*100:5.1f}%  "
          f"UGES(5)={u5*100:5.1f}% (5th pct {u5p*100:.1f}%)")
print("  (manuscript: M=2 -> 4.0 / 90.2 / 98.0 ; M=4 -> 0.2 / 81.5 / 96.0)")

# survivability curve vs salvo size
Ms = np.arange(1, 9)
ag_curve = [survive_fraction(1,M,P_AG)[0] for M in Ms]
u1_curve = [survive_fraction(1,M,P_SH)[0] for M in Ms]
u5_curve = [survive_fraction(5,M,P_SH)[0] for M in Ms]

# =====================================================================
# (B) ISLANDING ENDURANCE from site Weibull wind
# =====================================================================
E_INV = C.E_CYCLE_NET_MWH               # 1.083 MWh single-cycle inventory
def turbine_power(v, rated=C.TURBINE_UNIT_MW, vin=3, vr=12, vout=25):
    p = np.zeros_like(v)
    ramp = (v>=vin)&(v<vr); p[ramp] = rated*((v[ramp]-vin)/(vr-vin))**3
    p[(v>=vr)&(v<vout)] = rated
    return p

from math import gamma as _gamma
_MU  = C.WEIBULL_C*_gamma(1+1/C.WEIBULL_K)
_SD  = C.WEIBULL_C*np.sqrt(_gamma(1+2/C.WEIBULL_K)-_gamma(1+1/C.WEIBULL_K)**2)
_R1, _R2 = 0.90, 0.79                       # [A] representative hourly-wind ACF
_PHI1 = _R1*(1-_R2)/(1-_R1**2)
_PHI2 = (_R2-_R1**2)/(1-_R1**2)
_SIGA = _SD*np.sqrt(max(1e-6, 1 - _PHI1*_R1 - _PHI2*_R2))

def islanding_stats(load_mw, hours=72, trials=4000):
    """Billinton-framework ARMA (reduced to AR(2)) time-series wind, calibrated to
       the site Weibull moments and a representative hourly autocorrelation; a
       co-located turbine feeds the load with the store buffering E_INV. Returns
       the calm-buffer hours (E/L) and P(load served for the full window).
       Ref: Billinton, Chen & Ghajar, IEEE TEC 11(4):728-734, 1996."""
    ok = 0
    for _ in range(trials):
        y = np.zeros(hours); y[0]=rng.normal(0,_SD); y[1]=_PHI1*y[0]+rng.normal(0,_SIGA)
        for h in range(2, hours):
            y[h] = _PHI1*y[h-1] + _PHI2*y[h-2] + rng.normal(0,_SIGA)
        gen = turbine_power(np.clip(np.maximum(0.0, _MU+y), 0, 40))
        soc = E_INV; served = True
        for h in range(hours):
            net = gen[h] - load_mw
            soc = min(E_INV, soc + net) if net>=0 else soc + net
            if soc < 0: served=False; break
        ok += served
    return E_INV/load_mw, ok/trials

print("\n=== (B) ISLANDING ENDURANCE (1.083 MWh inventory + 2.5 MW turbine) ===")
loads = [("Hospital full",0.50),("Hospital shed",0.10),("Forward base",1.50),("Telecom",0.01)]
island_rows=[]
for name,L in loads:
    calm,p72 = islanding_stats(L)
    island_rows.append((name,L,round(calm,1),round(p72*100,1)))
    print(f"  {name:<15} L={L:>4} MW  calm buffer={calm:>5.1f} h  P(72h)={p72*100:5.1f}%")

# =====================================================================
# (C) MONETISED RESILIENCE  VoR = EENS_avoided x VoLL
# =====================================================================
# EENS_avoided: energy the store supplies to a protected load during grid outages
# that would otherwise be unserved.
L_PROT   = 0.10                         # [A] protected critical load, MW (shed-hospital core)
OUTAGE_H = np.array([50,100,200,400])   # [A] grid-outage exposure, h/yr (sweep)
COVERAGE = 0.85                         # [A] fraction of outage energy actually covered (from B)
VOLL_USD = np.array([1,2,5,10.0])       # [L] international VoLL range, USD/kWh (PK value unknown)
r = C.DISCOUNT_BASE; N = C.LIFE_YEARS
annuity = (1-(1+r)**(-N))/r

print("\n=== (C) MONETISED RESILIENCE  VoR = EENS_avoided x VoLL ===")
print(f"Protected load {L_PROT} MW, coverage {COVERAGE}, annuity(14%,30yr)={annuity:.2f}")
print(f"{'VoLL$/kWh':>9} | " + " | ".join(f"{h}h/yr NPV(MPKR)" for h in OUTAGE_H))
vor_grid=np.zeros((len(VOLL_USD),len(OUTAGE_H)))
for i,voll in enumerate(VOLL_USD):
    voll_pkr = voll*C.PKR_PER_USD*1000   # PKR/MWh
    row=[]
    for j,H in enumerate(OUTAGE_H):
        eens = L_PROT*H*COVERAGE          # MWh/yr avoided unserved energy
        vor_yr = eens*voll_pkr            # PKR/yr
        vor_npv = vor_yr*annuity/1e6      # M PKR
        vor_grid[i,j]=vor_npv; row.append(f"{vor_npv:>14.1f}")
    print(f"{voll:>9} | " + " | ".join(row))

# reference point tying to manuscript "~PKR 10M/yr -> ~70-80M NPV"
ref_npv = 10e6*annuity/1e6
print(f"\nReference: a flat PKR 10 M/yr security credit -> {ref_npv:.0f} M PKR NPV "
      f"(manuscript stated ~70-80 M).")

# resilience-adjusted LCOS at a mid VoR
vor_mid = vor_grid[2,2]*1e6              # VoLL=5, 200 h/yr
lcos_base = C.lcos_pkr_per_kwh()
# subtract VoR PV from lifecycle cost numerator
disc_mwh = sum(C.ANNUAL_DISCHARGE_MWH_Y1*(1-C.DEGRADATION)**(t-1)*(1+r)**(-t) for t in range(1,N+1))
lcos_resadj = lcos_base - (vor_mid/disc_mwh)/1000
print(f"Resilience-adjusted LCOS (VoLL=5$/kWh,200h/yr): "
      f"{lcos_resadj:.2f} vs {lcos_base:.2f} PKR/kWh base")

# --- figures ----------------------------------------------------------------
fig, ax = plt.subplots(1,2, figsize=(12,4.4))
ax[0].plot(Ms, np.array(ag_curve)*100, "o-", color="#E15759", label="Single BESS (above-ground)")
ax[0].plot(Ms, np.array(u1_curve)*100, "s-", color="#4C78A8", label="Single UGES shaft")
ax[0].plot(Ms, np.array(u5_curve)*100, "^-", color="#59A14F", label="Five dispersed UGES")
ax[0].set_xlabel("Salvo size (independent strikes)"); ax[0].set_ylabel("Surviving inventory (%)")
ax[0].set_title("(A) Strike survivability\n$p_{AG}$=0.8, $p_{sh}$=0.05"); ax[0].legend(fontsize=8); ax[0].set_ylim(0,105)

im = ax[1].imshow(vor_grid, origin="lower", aspect="auto", cmap="viridis")
ax[1].set_xticks(range(len(OUTAGE_H))); ax[1].set_xticklabels([f"{h}" for h in OUTAGE_H])
ax[1].set_yticks(range(len(VOLL_USD))); ax[1].set_yticklabels([f"{v:g}" for v in VOLL_USD])
ax[1].set_xlabel("Grid-outage exposure (h/yr)"); ax[1].set_ylabel("VoLL (USD/kWh)")
ax[1].set_title("(C) Value of Resilience NPV (M PKR)")
for i in range(len(VOLL_USD)):
    for j in range(len(OUTAGE_H)):
        ax[1].text(j,i,f"{vor_grid[i,j]:.0f}",ha="center",va="center",color="w",fontsize=8)
fig.colorbar(im, ax=ax[1], shrink=0.85)
plt.tight_layout(); plt.savefig("../figures/fig_resilience.png", dpi=150); plt.close()

json.dump({"survivability_M2":{"BESS_1":round(survive_fraction(1,2,P_AG)[0],3),
                               "UGES_1":round(survive_fraction(1,2,P_SH)[0],3),
                               "UGES_5":round(survive_fraction(5,2,P_SH)[0],3)},
           "islanding":island_rows,
           "VoR_NPV_MPKR_grid":vor_grid.round(1).tolist(),
           "VoLL_USD":VOLL_USD.tolist(),"outage_h_yr":OUTAGE_H.tolist(),
           "ref_10M_per_yr_NPV_MPKR":round(ref_npv,0),
           "lcos_base":round(lcos_base,2),"lcos_resilience_adjusted":round(lcos_resadj,2),
           "assumptions":["p_AG=0.8,p_sh=0.05 [A]","protected load 0.1 MW [A]",
                          "coverage 0.85 [A]","VoLL 1-10 USD/kWh [L]; PK value UNKNOWN",
                          "outage exposure 50-400 h/yr [A]"]},
          open("../results/resilience.json","w"), indent=2)
print("\nWrote figures/fig_resilience.png")
