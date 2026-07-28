"""
03_dispatch_milp.py

Wear-aware dispatch optimisation for a quantized-cycle UGES, formulated as a MILP
(PuLP / CBC, open source). This replaces the manuscript's rule-based EMS and is
the primary answer to the "contributions insufficient / no optimisation" review.

NOVELTY: a per-cycle rope-bending-fatigue cost term (Miner-rule marginal damage x
rope-set replacement cost) is embedded in the objective, coupling dispatch to a
mechanical fatigue model. This transfers battery cycle-aging-cost dispatch into a
mechanical-fatigue domain for gravity storage.

Objective (maximise, PKR over the representative day):
   sum_k [ price_k * eta_d * d_k * dt        (discharge revenue)
         - pcharge_k * c_k * dt ]            (charge cost; 0 when curtailed wind)
         - c_wear * (sum_k d_k*dt / E_cyc)   (rope-fatigue cost, per equiv. cycle)

Store: single-cycle buffer E_max = E_cyc_net; power <= P_rated; binary no
simultaneous charge/discharge. Compared against the manuscript rule-based policy.
All price/curtailment profiles are representative [A] and clearly flagged.
"""
import numpy as np, json, os
os.makedirs("../results", exist_ok=True); os.makedirs("../figures", exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import pulp
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C

# --- horizon ----------------------------------------------------------------
DT = 0.25                       # h, 15-min resolution
K  = int(24/DT)                 # 96 steps
t  = np.arange(K)*DT
P  = C.P_RATED_MW
EMAX = C.E_CYCLE_NET_MWH        # single-cycle buffer, MWh
ETA_C = ETA_D = np.sqrt(C.ETA_RT)

# --- representative Time-of-Use price, PKR/kWh [A] --------------------------
# Stylised to the manuscript's own thresholds (charge<8.5, discharge>22).
price = np.full(K, 12.0)
for k in range(K):
    hr = t[k]
    if 0 <= hr < 6:      price[k] = 7.0      # overnight off-peak
    elif 6 <= hr < 17:   price[k] = 12.0     # daytime shoulder
    elif 18 <= hr < 22:  price[k] = 27.0     # evening peak
    else:                price[k] = 15.0     # late evening

# --- curtailed-wind availability (free charging when True) [A] --------------
# Jhimpir summer surplus: overnight + a midday window feed otherwise-curtailed wind.
curtailed = np.array([(0 <= hr < 7) or (11 <= hr < 15) for hr in t])
pcharge = np.where(curtailed, 0.0, price)    # charge cost PKR/kWh

# --- rope-fatigue cost per equivalent cycle ---------------------------------
# c_wear = rope_set_replacement_cost / endurance_cycles  (PKR per full cycle)
ROPE_SET_COST_PKR = 50e6         # [A] rope-set replacement (subset of Koepe CAPEX) - VERIFY
def c_wear_of(Ncyc):             # PKR per equivalent cycle
    return ROPE_SET_COST_PKR / Ncyc
N_CYC_BASE = 3.0e6               # [A] rope endurance in cycles (fatigue MC ~3e6 bends, SF~3)

def solve_milp(c_wear):
    m = pulp.LpProblem("uges_dispatch", pulp.LpMaximize)
    c = [pulp.LpVariable(f"c{k}", 0, P) for k in range(K)]   # charge MW
    d = [pulp.LpVariable(f"d{k}", 0, P) for k in range(K)]   # discharge MW
    u = [pulp.LpVariable(f"u{k}", cat="Binary") for k in range(K)]
    v = [pulp.LpVariable(f"v{k}", cat="Binary") for k in range(K)]
    soc = [pulp.LpVariable(f"s{k}", 0, EMAX) for k in range(K+1)]
    m += soc[0] == 0.5*EMAX
    for k in range(K):
        m += c[k] <= P*u[k]; m += d[k] <= P*v[k]; m += u[k]+v[k] <= 1
        m += soc[k+1] == soc[k] + ETA_C*c[k]*DT - d[k]*DT/ETA_D
    m += soc[K] == 0.5*EMAX      # cyclic-ish boundary
    disch_energy = pulp.lpSum(d[k]*DT for k in range(K))
    rev = pulp.lpSum(price[k]*1000*ETA_D*d[k]*DT - pcharge[k]*1000*c[k]*DT for k in range(K))
    m += rev - c_wear*(disch_energy/EMAX)
    m.solve(pulp.PULP_CBC_CMD(msg=0))
    cv = np.array([c[k].value() for k in range(K)])
    dv = np.array([d[k].value() for k in range(K)])
    sv = np.array([soc[k].value() for k in range(K+1)])
    e_dis = float(np.sum(dv*DT))
    cycles = e_dis/EMAX
    revenue = float(np.sum(price*1000*ETA_D*dv*DT - pcharge*1000*cv*DT))
    return dict(c=cv,d=dv,soc=sv,e_dis=e_dis,cycles=cycles,revenue=revenue,
                wear_cost=c_wear*(e_dis/EMAX))

def rule_based():
    """Manuscript rule-based EMS: charge if price<8.5 (& curtailed pref), discharge if price>22."""
    soc = 0.5*EMAX; cv=np.zeros(K); dv=np.zeros(K); s=[soc]
    for k in range(K):
        if (price[k] < 8.5 or curtailed[k]) and soc < EMAX:
            c = min(P, (EMAX-soc)/(ETA_C*DT)); cv[k]=c; soc += ETA_C*c*DT
        elif price[k] > 22 and soc > 0:
            d = min(P, soc*ETA_D/DT); dv[k]=d; soc -= d*DT/ETA_D
        s.append(soc)
    e_dis=float(np.sum(dv*DT))
    revenue=float(np.sum(price*1000*ETA_D*dv - pcharge*1000*cv)*DT)
    return dict(c=cv,d=dv,soc=np.array(s),e_dis=e_dis,cycles=e_dis/EMAX,revenue=revenue)

# --- runs -------------------------------------------------------------------
rb   = rule_based()
opt0 = solve_milp(0.0)                       # optimal, no wear penalty
optw = solve_milp(c_wear_of(N_CYC_BASE))     # optimal, wear-aware

ANNUALISE = 365 * C.AVAILABILITY
ppa_rev_yr = C.ANNUAL_DISCHARGE_MWH_Y1 * C.DISCHARGE_TARIFF_PKR_KWH * 1000  # manuscript basis

print("=== DISPATCH: representative day (merchant ToU mode) ===")
def row(n,r): print(f"{n:<28} revenue={r['revenue']:>11,.0f} PKR/day  cycles={r['cycles']:>5.1f}  "
                    f"E_dis={r['e_dis']:>5.2f} MWh")
row("Naive threshold (heuristic)", rb)
row("MILP optimal (no wear)",  opt0)
row("MILP wear-aware (base)",  optw)
uplift = 100*(opt0['revenue']-rb['revenue'])/max(rb['revenue'],1)
print(f"\nOptimal captures curtailment-conversion value the naive price-threshold")
print(f"rule leaves on the table (baseline-sensitive; naive rule = {rb['cycles']:.1f} cyc/day).")
print(f"\n--- REVENUE BASIS RECONCILIATION (flag for author) ---")
print(f"MILP merchant-mode, annualised : {optw['revenue']*ANNUALISE/1e6:>7.1f} M PKR/yr")
print(f"Manuscript PPA-mode (flat tariff): {ppa_rev_yr/1e6:>7.1f} M PKR/yr")
print(f"Ratio merchant/PPA             : {optw['revenue']*ANNUALISE/ppa_rev_yr:>7.2f}")
print("  -> The manuscript's 433 M/yr assumes a FIRM 25 PKR/kWh offtake on 50 MWh/day")
print("     with free (curtailed) charging. Merchant ToU arbitrage yields far less.")
print("     Both are legitimate under different market framings; state which applies.")
print(f"\nWear-aware cost at N_cyc={N_CYC_BASE:.0e}: {optw['wear_cost']:,.0f} PKR/day "
      f"({100*optw['wear_cost']/max(opt0['revenue'],1):.2f}% of daily revenue)")
print("  -> Rope-fatigue cost is SECOND-ORDER vs price margin at plausible endurance;")
print("     cycling is margin-limited, not fatigue-limited, until endurance collapses.")

# --- endurance sensitivity of wear term -------------------------------------
Ns = np.logspace(4.7, 7, 25)
cyc_vs_N=[]; rev_vs_N=[]
for Ncyc in Ns:
    r = solve_milp(c_wear_of(Ncyc)); cyc_vs_N.append(r['cycles']); rev_vs_N.append(r['revenue'])
cyc_vs_N=np.array(cyc_vs_N); rev_vs_N=np.array(rev_vs_N)

# --- figures ----------------------------------------------------------------
fig, ax = plt.subplots(2,1, figsize=(9,6.5), sharex=True,
                       gridspec_kw={"height_ratios":[2,1.3]})
ax[0].step(t, optw['d']-optw['c'], where="post", color="#4C78A8", lw=1.6, label="UGES power (+dis / -chg)")
ax[0].fill_between(t, 0, np.where(curtailed, P, 0), step="post", color="#59A14F", alpha=0.12, label="curtailed-wind window")
ax[0].axhline(0, color="k", lw=0.6); ax[0].set_ylabel("Power (MW)")
ax[0].legend(fontsize=8, loc="upper left"); ax[0].set_title("Wear-aware MILP dispatch (representative day)")
ax2 = ax[0].twinx(); ax2.step(t, price, where="post", color="#E15759", lw=1.2, alpha=0.8)
ax2.set_ylabel("ToU price (PKR/kWh)", color="#E15759")
ax[1].step(t, optw['soc'][:-1], where="post", color="#B07AA1", lw=1.6)
ax[1].set_ylabel("Store SOC (MWh)"); ax[1].set_xlabel("Hour of day"); ax[1].set_ylim(0, EMAX*1.05)
plt.tight_layout(); plt.savefig("../figures/fig_dispatch_milp.png", dpi=160); plt.close()

fig, ax = plt.subplots(figsize=(7,4.2))
ax.semilogx(Ns, cyc_vs_N, "o-", color="#4C78A8")
ax.axvline(N_CYC_BASE, ls="--", color="k", lw=0.8)
ax.set_xlabel("Rope-set endurance $N_{cyc}$ (cycles to failure)")
ax.set_ylabel("Optimal cycles / day", color="#4C78A8")
ax.set_title("Wear-aware dispatch: cycling backs off as endurance falls")
axb=ax.twinx(); axb.semilogx(Ns, np.array(rev_vs_N)/1e3, "s-", color="#E15759", alpha=0.7)
axb.set_ylabel("Daily revenue (k PKR)", color="#E15759")
plt.tight_layout(); plt.savefig("../figures/fig_dispatch_wear_sensitivity.png", dpi=160); plt.close()

json.dump({"naive_threshold":{k:rb[k] for k in ("revenue","cycles","e_dis")},
           "milp_no_wear":{k:opt0[k] for k in ("revenue","cycles","e_dis")},
           "milp_wear_aware":{k:optw[k] for k in ("revenue","cycles","e_dis","wear_cost")},
           "milp_merchant_annual_MPKR":round(optw['revenue']*ANNUALISE/1e6,1),
           "manuscript_ppa_annual_MPKR":round(ppa_rev_yr/1e6,1),
           "merchant_to_ppa_ratio":round(optw['revenue']*ANNUALISE/ppa_rev_yr,2),
           "N_cyc_base":N_CYC_BASE,
           "assumptions":["ToU price profile [A]","curtailment windows [A]",
                          "rope-set cost 50M PKR [A]","endurance 3e6 cycles [A]"],
           "flag":"merchant ToU value << manuscript flat-tariff PPA value; state market framing"},
          open("../results/dispatch_milp.json","w"), indent=2)
print("Wrote figures/fig_dispatch_milp.png, fig_dispatch_wear_sensitivity.png")
