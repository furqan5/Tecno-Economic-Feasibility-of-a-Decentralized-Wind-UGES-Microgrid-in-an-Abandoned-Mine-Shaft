# -*- coding: utf-8 -*-
"""
Islanding endurance with a Billinton-framework ARMA time-series wind model
(Billinton, Chen & Ghajar, IEEE TEC 11(4):728-734, 1996; Microelectron. Reliab.
36(9):1253-1261, 1996). Reduced to AR(2) and calibrated to the Jhimpir Weibull
moments (k=2.17, c=7.72 at 100 m, from [18] extrapolated) plus a representative hourly lag-1 autocorrelation r1=0.90
(r2=0.79) documented for hourly wind. Sequential Monte-Carlo over a 72 h grid
outage; co-located 2.5 MW turbine feeds the protected load, 1.083 MWh store buffers.
"""
import numpy as np
import os as _os, sys as _sys
_sys.path.insert(0,_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import common as C
from math import gamma
rng = np.random.default_rng(11)

k, c = 2.17, 7.72   # [L] Khan et al. 2021 complete-data fit, 80 m -> 100 m (alpha=0.14)
mu = c*gamma(1+1/k)
sd = c*np.sqrt(gamma(1+2/k)-gamma(1+1/k)**2)
print(f"Weibull -> mean={mu:.2f} m/s, std={sd:.2f} m/s")

# AR(2) Yule-Walker from target ACF (Billinton ARMA reduced form)
r1, r2 = 0.90, 0.79
phi1 = r1*(1-r2)/(1-r1**2)
phi2 = (r2-r1**2)/(1-r1**2)
sig_a = sd*np.sqrt(max(1e-6, 1 - phi1*r1 - phi2*r2))
print(f"AR(2): phi1={phi1:.3f}, phi2={phi2:.3f}, sigma_a={sig_a:.3f}")

E_INV = 1.083   # MWh store
def turbine(v):
    """Measured QBlade power curve [M] (common.QB_V/QB_P), single 2.5 MW machine."""
    return float(C.turbine_MW(np.clip(v,0,60)))

def sim(load_mw, hours=72, trials=6000):
    ok=0
    for _ in range(trials):
        y=np.zeros(hours); y[0]=rng.normal(0,sd); y[1]=phi1*y[0]+rng.normal(0,sig_a)
        v=np.zeros(hours); v[0]=max(0,mu+y[0]); v[1]=max(0,mu+y[1])
        soc=E_INV; served=True
        for h in range(2,hours):
            y[h]=phi1*y[h-1]+phi2*y[h-2]+rng.normal(0,sig_a)
            v[h]=max(0.0, mu+y[h])
        for h in range(hours):
            net=turbine(v[h])-load_mw
            soc = min(E_INV, soc+net) if net>=0 else soc+net
            if soc<0: served=False; break
        ok+=served
    return E_INV/load_mw, ok/trials

print("\n=== ISLANDING (Billinton ARMA/AR2 wind, 72 h, N=6000) ===")
print(f"{'Application':<20}{'Load MW':>8}{'calm h':>9}{'P(72h)':>9}")
rows=[]
for name,L in [("Hospital, full",0.50),("Hospital, shed core",0.10),
               ("Forward operating base",1.50),("Telecom node",0.01)]:
    calm,p = sim(L)
    rows.append((name,L,round(calm,1),round(p*100,1)))
    print(f"{name:<20}{L:>8}{calm:>9.1f}{p*100:>8.1f}%")
print("\n(prior Table VI, ad-hoc AR(1): 1.6 / 85.3 / <0.1 / >99.9 %)")

import os as _os
_csv = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                     "figure_data", "fig7b_islanding.csv")
with open(_csv, "w") as _f:
    _f.write("load,P72_pct,buffer_h\n")
    for _n, _L, _c, _p in rows:
        _q = f'"{_n}"' if "," in _n else _n
        _f.write(f"{_q},{_p:.2f},{_c}\n")
print("Wrote", _csv)
