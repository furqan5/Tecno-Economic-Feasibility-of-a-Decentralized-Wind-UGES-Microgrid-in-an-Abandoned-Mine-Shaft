"""
04_probabilistic_lcos.py

Turns the deterministic point-estimate economics into a probabilistic result:
  - Monte-Carlo distribution of LCOS and NPV (P10/P50/P90, Pr(NPV>0))
  - Sobol global sensitivity indices (which inputs drive LCOS variance)

Open-source: numpy (MC) + SALib (Sobol). Uses the validated common.py engine, so
the deterministic centre reproduces the manuscript's 18.82 PKR/kWh.

Input uncertainty ranges are engineering judgement [A] and flagged; the point of
the analysis is the RANKING of drivers and the spread, both robust to the exact
bounds.
"""
import numpy as np, json, os
os.makedirs("../results", exist_ok=True); os.makedirs("../figures", exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from SALib.sample import saltelli
from SALib.analyze import sobol
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C

T = np.arange(1, C.LIFE_YEARS + 1)

def lcos_vec(capex, r, om_frac, e1, deg, salv):
    df   = (1 + r[:, None]) ** (-T[None, :])
    e_t  = e1[:, None] * (1 - deg[:, None]) ** (T[None, :] - 1)
    den  = (e_t * df).sum(1)
    om   = om_frac * capex
    num  = capex + om * df.sum(1) - salv * capex * (1 + r) ** (-C.LIFE_YEARS)
    return num / den / 1000.0

def npv_vec(capex, r, om_frac, e1, deg, tariff, salv):
    df   = (1 + r[:, None]) ** (-T[None, :])
    e_t  = e1[:, None] * (1 - deg[:, None]) ** (T[None, :] - 1)
    om   = om_frac * capex
    cf   = e_t * tariff[:, None] * 1000 - om[:, None]
    return -capex + (cf * df).sum(1) + salv * capex * (1 + r) ** (-C.LIFE_YEARS)

# --- parameter ranges [A] ---------------------------------------------------
names  = ["capex","r","tariff","avail","deg","om_frac","depth_scale"]
bounds = [[0.80*C.CAPEX_TOTAL_PKR, 1.20*C.CAPEX_TOTAL_PKR],  # CAPEX +/-20%
          [0.12, 0.16],                                       # discount rate
          [0.80*C.DISCHARGE_TARIFF_PKR_KWH, 1.20*C.DISCHARGE_TARIFF_PKR_KWH],
          [0.92, 0.98],                                       # availability (centred on the 0.95 design point)
          [0.003, 0.008],                                     # degradation
          [0.008, 0.015],                                     # O&M fraction
          [0.85, 1.15]]                                       # depth->E1 scaling +/-15%
problem = {"num_vars": len(names), "names": names, "bounds": bounds}

def unpack(X):
    capex=X[:,0]; r=X[:,1]; tariff=X[:,2]; avail=X[:,3]; deg=X[:,4]; om=X[:,5]; dscale=X[:,6]
    e1 = C.ANNUAL_DISCHARGE_MWH_Y1 * (avail/C.AVAILABILITY) * dscale
    return capex,r,tariff,avail,deg,om,e1

# --- Sobol (structured sample) ----------------------------------------------
X = saltelli.sample(problem, 2048, calc_second_order=False)
capex,r,tariff,avail,deg,om,e1 = unpack(X)
Y_lcos = lcos_vec(capex,r,om,e1,deg,np.full_like(r,C.SALVAGE_FRAC))
Si = sobol.analyze(problem, Y_lcos, calc_second_order=False, print_to_console=False)

# --- pure Monte-Carlo (independent uniform draws) for distributions ---------
rng = np.random.default_rng(42); Nmc = 60000
U = rng.uniform(size=(Nmc, len(names)))
Xmc = np.array(bounds)[:,0] + U*(np.array(bounds)[:,1]-np.array(bounds)[:,0])
capex,r,tariff,avail,deg,om,e1 = unpack(Xmc)
salv = np.full(Nmc, C.SALVAGE_FRAC)
lcos_mc = lcos_vec(capex,r,om,e1,deg,salv)
npv_mc  = npv_vec(capex,r,om,e1,deg,tariff,salv)

p10,p50,p90 = np.percentile(lcos_mc,[10,50,90])
pr_npv_pos  = float((npv_mc>0).mean())
np10,np50,np90 = np.percentile(npv_mc/1e6,[10,50,90])

print("=== PROBABILISTIC LCOS / NPV (Monte-Carlo, N=60000) ===")
print(f"LCOS  P10/P50/P90 : {p10:.2f} / {p50:.2f} / {p90:.2f} PKR/kWh (det. 18.82)")
print(f"NPV   P10/P50/P90 : {np10:.0f} / {np50:.0f} / {np90:.0f} M PKR")
print(f"Pr(NPV > 0)       : {pr_npv_pos*100:.1f}%")
print("\n=== SOBOL SENSITIVITY (LCOS) ===")
order = np.argsort(Si['ST'])[::-1]
for i in order:
    print(f"  {names[i]:<12} S1={Si['S1'][i]:+.3f}  ST={Si['ST'][i]:+.3f}")

# --- figures ----------------------------------------------------------------
fig, ax = plt.subplots(1,2, figsize=(12,4.4))
ax[0].hist(lcos_mc, bins=60, color="#4C78A8", alpha=0.85, edgecolor="w", linewidth=0.2)
for p,l,c in [(p10,"P10","#59A14F"),(p50,"P50","#000000"),(p90,"P90","#E15759")]:
    ax[0].axvline(p, color=c, ls="--", lw=1.3, label=f"{l}={p:.1f}")
ax[0].axvline(C.LCOS_REPORTED_PKR_KWH, color="orange", lw=1.6,
              label=f"deterministic {C.LCOS_REPORTED_PKR_KWH:.2f}")
ax[0].set_xlabel("LCOS (PKR/kWh)"); ax[0].set_ylabel("frequency")
ax[0].set_title("Monte-Carlo LCOS distribution"); ax[0].legend(fontsize=8)

yb = np.arange(len(names))
ax[1].barh(yb, Si['ST'][order], color="#B07AA1", label="ST (total)")
ax[1].barh(yb, Si['S1'][order], color="#4C78A8", height=0.5, label="S1 (first)")
ax[1].set_yticks(yb); ax[1].set_yticklabels([names[i] for i in order]); ax[1].invert_yaxis()
ax[1].set_xlabel("Sobol index"); ax[1].set_title("LCOS variance drivers"); ax[1].legend(fontsize=8)
plt.tight_layout(); plt.savefig("../figures/fig_probabilistic_lcos.png", dpi=150); plt.close()

json.dump({"LCOS_P10_P50_P90":[round(p10,2),round(p50,2),round(p90,2)],
           "NPV_P10_P50_P90_MPKR":[round(np10,0),round(np50,0),round(np90,0)],
           "Pr_NPV_positive":round(pr_npv_pos,3),
           "sobol_ST":{names[i]:round(float(Si['ST'][i]),3) for i in order},
           "sobol_S1":{names[i]:round(float(Si['S1'][i]),3) for i in order},
           "N_mc":Nmc,"ranges":dict(zip(names,bounds))},
          open("../results/probabilistic_lcos.json","w"), indent=2)
print("\nWrote figures/fig_probabilistic_lcos.png")
