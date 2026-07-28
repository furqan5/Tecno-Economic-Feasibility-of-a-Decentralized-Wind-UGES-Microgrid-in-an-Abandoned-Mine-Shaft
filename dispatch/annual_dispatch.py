"""
annual_dispatch.py

Representative-day-per-month dispatch of the 5 MW / ~13-min UGES store, the
extended-horizon answer to the review request to show charge-discharge behaviour
and peak-load handling across seasons (not just one week).

Model of record: the store runs at its RATED daily duty every day (46 strokes,
50 MWh/day throughput -> 17.3 GWh/yr at 95% availability), the duty that
underwrites the arbitrage economics. The seasonal variable is the CHARGE SOURCE:
wind surplus to concurrent demand (otherwise exported) vs off-peak grid. Grid-
connected, so surplus beyond the store's intake is EXPORTED, not curtailed.

Provenance:  [M] manuscript  [D] derived  [A] assumption (verify)  [L] literature
Representative-year, not a measured 8760-h record. Shape assumptions are stated.
Outputs: ../results/annual_dispatch.json, ../figures/fig_annual_dispatch.png
"""
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C
import numpy as np, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
_os.makedirs("../results", exist_ok=True); _os.makedirs("../figures", exist_ok=True)
rng = np.random.default_rng(20260722)

# ---- store constants from common (single source of truth) ----
E_STROKE = 1.083                        # [M] MWh per full stroke
assert abs(C.DAILY_THROUGHPUT_MWH/E_STROKE - 46) < 1.0, "stroke/throughput mismatch"
RTE      = C.ETA_RT                      # [M]
THRU_DAY = C.DAILY_THROUGHPUT_MWH        # [M] 50 MWh/day
CHG_DAY  = THRU_DAY/RTE                  # [D] ~58.8 MWh/day input
CYC_DAY  = THRU_DAY/E_STROKE             # [D] ~46 strokes/day
AVAIL    = 0.95                          # [M]

# ---- wind farm [M] ----
N_TURB=20; P_TURB=2.5; ARRAY_LOSS=0.215; AVAIL_W=0.95
# Measured turbine power curve, QBlade CE v2.0.9 export [M] (figure_data/qblade_power_curve.csv):
# cut-in 3.0 m/s, 2.5 MW reached at 13.0 m/s, cut-out 25 m/s. Convolved with the measured
# Weibull of Khan et al. 2021 carried to 100 m it returns net AEP 96.5 GWh (CF 22.0%).
def pcurve(v):
    return C.turbine_MW(v)*N_TURB*(1-ARRAY_LOSS)*AVAIL_W

MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
WMEAN =np.array([5.13,5.34,5.56,6.69,8.36,8.54,9.36,8.34,7.04,5.19,4.92,5.19])  # [L] Khan et al. 2021 V80 -> 100 m hub (alpha=0.14)
DAYS  =np.array([31,28,31,30,31,30,31,31,30,31,30,31])

NS=96; t=np.arange(NS)*0.25
diurnal_w=1.0+0.18*np.sin(2*np.pi*(t-9)/24)      # [A] afternoon sea-breeze max
TI=0.13                                           # [A] turbulence intensity
def wind_day(mm):
    mu=mm*diurnal_w; e=rng.normal(0,1,NS); a=0.82
    z=np.zeros(NS); z[0]=e[0]
    for i in range(1,NS): z[i]=a*z[i-1]+np.sqrt(1-a*a)*e[i]
    return pcurve(np.clip(mu*(1+TI*z),0,None))
def load_day(summer):
    base=0.55; morning=0.16*np.exp(-0.5*((t-10)/2.0)**2)
    pk=22.0 if summer else 18.5; amp=0.45 if summer else 0.34
    evening=amp*np.exp(-0.5*((t-pk)/1.6)**2); night=-0.06*np.exp(-0.5*((t-3)/2.5)**2)
    return (base+morning+evening+night)*(1.32 if summer else 0.92)
LPEAK_MW=10.0     # [A] representative local feeder peak served by the microgrid

def day_split(W,L):
    dt=0.25; Lm=L*LPEAK_MW
    surplus=np.maximum(0,W-Lm).sum()*dt
    wind_chg=min(surplus, CHG_DAY); grid_chg=CHG_DAY-wind_chg; exported=surplus-wind_chg
    return dict(surplus=surplus,wind_chg=wind_chg,grid_chg=grid_chg,exported=exported,wind=W.sum()*dt)

rows=[]
for m in range(12):
    summer=m in (4,5,6,7,8)
    agg={k:0.0 for k in ['surplus','wind_chg','grid_chg','exported','wind']}
    for _ in range(12):
        r=day_split(wind_day(WMEAN[m]),load_day(summer))
        for k in agg: agg[k]+=r[k]/12
    rows.append((m,summer,agg))

ann=dict(dis=0.0,windc=0.0,gridc=0.0,exp=0.0,wind=0.0); monthly=[]
for (m,summer,a) in rows:
    tot=a['wind_chg']+a['grid_chg']; wpct=100*a['wind_chg']/tot
    monthly.append(dict(month=MONTHS[m],wind_MWh_day=round(a['wind'],1),
        surplus_MWh_day=round(a['surplus'],1),wind_charge_pct=round(wpct,0),
        exported_MWh_day=round(a['exported'],1)))
    d=DAYS[m]*AVAIL
    ann['dis']+=THRU_DAY*d; ann['windc']+=a['wind_chg']*d; ann['gridc']+=a['grid_chg']*d
    ann['exp']+=a['exported']*DAYS[m]; ann['wind']+=a['wind']*DAYS[m]
wind_frac=100*ann['windc']/(ann['windc']+ann['gridc'])
mons=[a for m,s,a in rows if s]; wint=[a for m,s,a in rows if not s]
fw=lambda L:100*sum(x['wind_chg'] for x in L)/sum(x['wind_chg']+x['grid_chg'] for x in L)

print(f"annual discharge        : {ann['dis']:,.0f} MWh (manuscript 17,337.5)")
print(f"rated duty              : {CYC_DAY:.0f} strokes/day, {THRU_DAY:.0f} MWh/day")
print(f"wind-charge fraction    : {wind_frac:.0f}%  (monsoon {fw(mons):.0f}%, winter {fw(wint):.0f}%)")
print(f"exported surplus        : {ann['exp']/1000:,.1f} GWh/yr (not curtailed)")

json.dump(dict(annual_discharge_MWh=round(ann['dis'],0), strokes_per_day=round(CYC_DAY,0),
    throughput_MWh_day=THRU_DAY, wind_charge_fraction_pct=round(wind_frac,0),
    monsoon_wind_pct=round(fw(mons),0), winter_wind_pct=round(fw(wint),0),
    charge_from_wind_GWh=round(ann['windc']/1000,1), charge_from_grid_GWh=round(ann['gridc']/1000,1),
    exported_surplus_GWh=round(ann['exp']/1000,1), monthly=monthly,
    notes=["representative-year; monthly means measured (Khan et al. 2021, V80) [L]",
           "national double-hump demand shape, LPEAK 10 MW [A]",
           "rep-day under-samples windiest hours; 96.5 GWh net AEP (QBlade curve x measured Weibull) is figure of record"]),
    open("../results/annual_dispatch.json","w"), indent=2)

# ---- figure ----
wc=np.array([a['wind_chg'] for _,_,a in rows]); gc=np.array([a['grid_chg'] for _,_,a in rows])
wp=100*wc/(wc+gc); x=np.arange(12)
Wj=wind_day(WMEAN[6]); Lj=load_day(True)*LPEAK_MW
Wd=wind_day(WMEAN[11]); Ld=load_day(False)*LPEAK_MW
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12.4,4.5))
ax1.bar(x,wc,color='#2b8cbe',label='surplus wind'); ax1.bar(x,gc,bottom=wc,color='#bdbdbd',label='off-peak grid')
ax1.axhline(CHG_DAY,color='k',ls='--',lw=1,label=f'daily charge duty {CHG_DAY:.1f} MWh')
ax1.set_xticks(x); ax1.set_xticklabels(MONTHS); ax1.set_ylabel('store charge (MWh / rep. day)')
ax1.set_title('(a) Seasonal charge source at fixed 46-stroke duty')
axb=ax1.twinx(); axb.plot(x,wp,'o-',color='#e6550d',lw=1.8,ms=4); axb.set_ylim(0,105)
axb.set_ylabel('wind-sourced (%)',color='#e6550d'); axb.tick_params(axis='y',labelcolor='#e6550d')
ax1.legend(loc='upper left',fontsize=8,framealpha=0.9)
ax2.plot(t,Wj,color='#2b8cbe',lw=1.6,label='wind, Jul'); ax2.plot(t,Wd,color='#2b8cbe',ls='--',lw=1.4,label='wind, Dec')
ax2.plot(t,Lj,color='#e6550d',lw=1.6,label='demand, summer'); ax2.plot(t,Ld,color='#e6550d',ls='--',lw=1.4,label='demand, winter')
ax2.fill_between(t,Lj,Wj,where=Wj>Lj,color='#2b8cbe',alpha=0.15)
ax2.set_xlim(0,24); ax2.set_xticks(range(0,25,4)); ax2.set_xlabel('hour'); ax2.set_ylabel('power (MW)')
ax2.set_title('(b) Representative dispatch day: wind vs served demand'); ax2.legend(fontsize=8,loc='upper left',framealpha=0.9)
plt.tight_layout(); plt.savefig("../figures/fig_annual_dispatch.png",dpi=155,bbox_inches='tight')
print("wrote ../figures/fig_annual_dispatch.png and ../results/annual_dispatch.json")
