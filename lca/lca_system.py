"""
06_lca_system.py

Full-system life-cycle carbon: Wind+UGES vs Wind+BESS over 30 years, on an
identical basis. This closes the manuscript's stated LCA limitation (UGES was
only cradle-to-gate; no full-system BESS comparison).

Provenance of factors:
  wind      : [L] IPCC AR6 onshore-wind lifecycle median ~11 gCO2eq/kWh
  UGES       : [M] manuscript cradle-to-gate 2,850 (recycled) / 4,210 (virgin) tCO2eq
  BESS (LFP): [L] embodied ~40-100 kgCO2eq/kWh pack (LFP; e.g. Nat. Commun. 2024) - VERIFY
The storage-only ratio (BESS/UGES) is the robust claim; system totals depend on
the wind factor, which dominates and is common to both architectures.
"""
import numpy as np, json, os
os.makedirs("../results", exist_ok=True); os.makedirs("../figures", exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C

YEARS = C.LIFE_YEARS
NET_AEP_GWH_YR = 89.7                   # [D] IEC 61400-12-1 normalised curve x measured Weibull [18]
WIND_G_PER_KWH = 11.0                   # [L] IPCC AR6 onshore wind median

# --- wind farm embodied (common to both) ------------------------------------
wind_t = WIND_G_PER_KWH * (NET_AEP_GWH_YR*1e6) * YEARS / 1e6   # gCO2 -> tCO2e
# gCO2/kWh * kWh = gCO2; kWh = GWh*1e6; /1e6 -> t

# --- UGES storage embodied [M] ----------------------------------------------
UGES_RECYCLED_T = 2850.0
UGES_VIRGIN_T   = 4210.0

# --- BESS storage embodied (sized to equivalent daily energy service) -------
BESS_NAMEPLATE_MWH = C.DAILY_THROUGHPUT_MWH / 0.90    # ~55.6 MWh to deliver 50 MWh/day @90% DoD [A]
BESS_LIFE_YR       = 12                                # [L] typical LFP calendar/cycle life
n_builds           = int(np.ceil(YEARS / BESS_LIFE_YR))  # replacements incl. initial (3 over 30 yr)
EF_range           = np.array([40, 60, 80, 100.0])    # [L] kgCO2eq/kWh pack - VERIFY

print("=== FULL-SYSTEM LCA (30 yr) ===")
print(f"Wind farm embodied (common)     : {wind_t:,.0f} tCO2e "
      f"({WIND_G_PER_KWH} g/kWh x {NET_AEP_GWH_YR} GWh/yr x {YEARS})")
print(f"UGES storage (recycled/virgin)  : {UGES_RECYCLED_T:,.0f} / {UGES_VIRGIN_T:,.0f} tCO2e")
print(f"Wind+UGES total (recycled)      : {wind_t+UGES_RECYCLED_T:,.0f} tCO2e")
print(f"\nBESS nameplate {BESS_NAMEPLATE_MWH:.1f} MWh, {n_builds} builds over {YEARS} yr")
print(f"{'EF kg/kWh':>9} | {'BESS store (t)':>14} | {'Wind+BESS (t)':>14} | {'BESS/UGES x':>11}")
bess_store=[]; sys_bess=[]
for ef in EF_range:
    b = ef * BESS_NAMEPLATE_MWH*1e3 * n_builds / 1e3       # kg -> t
    bess_store.append(b); sys_bess.append(wind_t+b)
    print(f"{ef:>9} | {b:>14,.0f} | {wind_t+b:>14,.0f} | {b/UGES_RECYCLED_T:>11.1f}")

ratio_lo = min(bess_store)/UGES_VIRGIN_T
ratio_hi = max(bess_store)/UGES_RECYCLED_T
print(f"\nStorage-only BESS/UGES ratio across sweep: {ratio_lo:.1f}x - {ratio_hi:.1f}x  (ROBUST CLAIM)")
print(f"Wind+UGES = {wind_t+UGES_RECYCLED_T:,.0f} t ; Wind+BESS = {min(sys_bess):,.0f}-{max(sys_bess):,.0f} t")

# --- figure -----------------------------------------------------------------
fig, ax = plt.subplots(1,2, figsize=(12,4.4))
# storage-only
labels=["UGES\nrecycled","UGES\nvirgin"]+[f"BESS\nEF={int(e)}" for e in EF_range]
vals=[UGES_RECYCLED_T,UGES_VIRGIN_T]+bess_store
cols=["#59A14F","#8Cb369"]+["#E15759"]*len(EF_range)
ax[0].bar(labels,vals,color=cols,edgecolor="k",linewidth=0.5)
ax[0].set_ylabel("Storage embodied carbon (tCO2e)")
ax[0].set_title(f"Storage only, 30 yr ({n_builds} BESS builds)")
ax[0].tick_params(axis='x',labelsize=8)
# system totals (stacked)
x=np.arange(2); wind_bar=[wind_t,wind_t]
store_bar=[UGES_RECYCLED_T, np.mean(bess_store)]
ax[1].bar(x,wind_bar,color="#4C78A8",label="Wind farm (common)")
ax[1].bar(x,store_bar,bottom=wind_bar,color=["#59A14F","#E15759"],label="Storage")
ax[1].set_xticks(x); ax[1].set_xticklabels(["Wind+UGES","Wind+BESS\n(mean EF)"])
ax[1].set_ylabel("System embodied carbon (tCO2e)")
ax[1].set_title("Full-system total, 30 yr")
for i,(w,s) in enumerate(zip(wind_bar,store_bar)):
    ax[1].text(i,w+s+700,f"{w+s:,.0f}",ha="center",fontsize=9)
ax[1].legend(fontsize=8); ax[1].set_ylim(0,max(sys_bess)*1.15)
plt.tight_layout(); plt.savefig("../figures/fig_lca_system.png", dpi=150); plt.close()

json.dump({"wind_t":round(wind_t,0),"uges_recycled_t":UGES_RECYCLED_T,"uges_virgin_t":UGES_VIRGIN_T,
           "wind_uges_total_t":round(wind_t+UGES_RECYCLED_T,0),
           "bess_nameplate_MWh":round(BESS_NAMEPLATE_MWH,1),"bess_builds":n_builds,
           "EF_kg_per_kWh":EF_range.tolist(),"bess_store_t":[round(b,0) for b in bess_store],
           "wind_bess_total_t":[round(s,0) for s in sys_bess],
           "storage_ratio_range":[round(ratio_lo,1),round(ratio_hi,1)],
           "factors":["wind 11 gCO2/kWh [L IPCC AR6]","UGES [M]","BESS EF [L] VERIFY Nat Commun 2024"]},
          open("../results/lca_system.json","w"), indent=2)
print("\nWrote figures/fig_lca_system.png")
