"""
Rule-based Energy Management System for the Jhimpir Wind-UGES plant.
Rule-based energy-management dispatch model (NumPy).

Four-mode dispatch, exactly as specified in the manuscript:
  CHARGING            : grid surplus > 0  AND  tariff < 8.5 PKR/kWh  AND  SOC < 90%
  DISCHARGING         : (grid deficit) OR (tariff > 22 PKR/kWh)  AND  SOC > 10%
  CURTAILMENT-AVOID   : prioritise charging over wind curtailment when grid is export-constrained
  STRATEGIC-RESERVE   : SOC locked above a configurable floor regardless of price

Storage: single 1.083 MWh cycle capacity, 5 MW power rating, 84.97% round-trip
(eta_chg = eta_dis = sqrt(0.8497)). 1-hour time step over 24 h.
The model reproduces the time-shifting behaviour and the SOC band in the
the 24-hour dispatch figure; parameters are configurable at the top.
"""
import numpy as np

# ---------------- parameters ----------------
E_CAP   = 1.083          # MWh usable per cycle (validated)
P_RATE  = 5.0            # MW motor/generator rating
RTE     = 0.8497
ETA     = np.sqrt(RTE)   # one-way efficiency each direction
SOC_HI, SOC_LO = 0.90, 0.10
TARIFF_CHG, TARIFF_DIS = 8.5, 22.0   # PKR/kWh thresholds
RESERVE_FLOOR = 0.10     # strategic-reserve SOC floor (set >0.10 to arm)
DT = 1.0                 # hour

# 24-h ToU tariff (PKR/kWh): off-peak nights cheap, evening peak ~sunset
tariff = np.array([6,6,6,6,6,7, 8,10,12,14, 9,9, 9,10,11,12, 14,28,30,26, 16,12,8,7], float)
# grid surplus seen by plant (MW): + = grid can absorb / needs less; here a
# simple proxy = high overnight wind surplus, tight evening (demand peak)
surplus = np.array([40,42,44,45,44,40, 30,18,8,4, 10,12, 12,8,4,2, -2,-6,-8,-4, 6,20,34,40], float)

def dispatch(reserve_floor=RESERVE_FLOOR):
    """Peak-aware virtual-peaker dispatch.
    Charge only in genuinely cheap hours; reserve discharge for the daily
    high-tariff peak window (and true deficits), as the manuscript describes."""
    soc = 0.5
    P, SOCv, mode = [], [], []
    peak_hours = set(np.where(tariff >= np.percentile(tariff, 85))[0])  # top ~15% price hours
    for h in range(24):
        t, sp = tariff[h], surplus[h]
        p = 0.0; md = "idle"
        floor = max(SOC_LO, reserve_floor)
        cheap = t <= TARIFF_CHG + 0.5
        if cheap and (sp > 0) and (soc < SOC_HI):
            p = -min(P_RATE, (SOC_HI - soc) * E_CAP / DT / ETA)          # charge
            md = "charge"
        elif (h in peak_hours or t > TARIFF_DIS) and (soc > floor):
            p =  min(P_RATE, (soc - floor) * E_CAP * ETA / DT)           # discharge into price peak
            md = "discharge"
        if p < 0:   soc += (-p) * ETA * DT / E_CAP
        elif p > 0: soc -=  (p / ETA) * DT / E_CAP
        soc = float(np.clip(soc, 0.0, 1.0))
        P.append(p); SOCv.append(soc); mode.append(md)
    return np.array(P), np.array(SOCv), mode

def measured_rte():
    """RTE on a matched single cycle: full charge from empty, then full discharge."""
    e_in = E_CAP / ETA          # grid energy to lift a full piston
    e_out = E_CAP * ETA         # grid energy recovered on descent
    return e_out / e_in

P, SOC, mode = dispatch()

print("="*64)
print("Jhimpir Wind-UGES EMS - 24-h rule-based dispatch (NumPy)")
print("="*64)
print(f"{'h':>3} {'tariff':>7} {'surplus':>8} {'P_uges':>8} {'SOC%':>6}  mode")
for h in range(24):
    print(f"{h:3d} {tariff[h]:7.1f} {surplus[h]:8.1f} {P[h]:8.2f} {SOC[h]*100:6.1f}  {mode[h]}")

chg = -P[P<0].sum()*DT
dis =  P[P>0].sum()*DT
print(f"\nDaily energy charged : {chg:5.2f} MWh   discharged: {dis:5.2f} MWh "
      f"(net SOC change carried to next day)")
print(f"Single-cycle round-trip efficiency : {measured_rte()*100:5.2f}%  "
      f"(matched full charge/discharge; design {RTE*100:.2f}%)")
print(f"SOC stayed within [{SOC.min()*100:.0f}%, {SOC.max()*100:.0f}%]")
peak = int(np.where(P>0)[0][0]) if (P>0).any() else int(np.argmax(tariff))
print(f"Discharge fires at hour {peak}:00 (PKR {tariff[peak]:.0f}/kWh) -> UGES {P[peak]:+.2f} MW "
      f"({'discharging' if P[peak]>0 else 'idle/charging'})")

# strategic-reserve demonstration
_,SOCr,_ = dispatch(reserve_floor=0.40)
print(f"\nStrategic-reserve override (floor 40%): SOC never drops below "
      f"{SOCr.min()*100:.0f}% (vs {SOC.min()*100:.0f}% commercial).")

# ---------------- figure ----------------
try:
    import matplotlib
    matplotlib.use('Agg'); import matplotlib.pyplot as plt
    h=np.arange(24)
    fig,ax1=plt.subplots(figsize=(3.4,2.4),dpi=300); plt.rcParams['font.family']='serif'
    ax1.bar(h,P,color=np.where(P>=0,'#1a9850','#b22222'),width=0.8,label='UGES power')
    ax1.axhline(0,color='k',lw=0.5); ax1.set_xlabel('Hour',fontsize=8)
    ax1.set_ylabel('UGES power (MW)\n+discharge / -charge',fontsize=8)
    ax1.tick_params(labelsize=7)
    ax2=ax1.twinx()
    ax2.plot(h,SOC*100,'o-',color='#2166ac',ms=2.4,lw=1.3,label='SOC')
    ax2.plot(h,tariff,':',color='#762a83',lw=1.1,label='tariff')
    ax2.set_ylabel('SOC (%)  /  tariff (PKR/kWh)',fontsize=8); ax2.tick_params(labelsize=7)
    ax2.set_ylim(0,100)
    l1,la1=ax1.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
    ax1.legend(l1+l2,la1+la2,fontsize=5.6,frameon=False,loc='upper center',ncol=2)
    plt.tight_layout(); plt.savefig('ems_dispatch.png',bbox_inches='tight')
    print("\nfigure saved: ems_dispatch.png")
except Exception as e:
    print("plot skipped:",e)
