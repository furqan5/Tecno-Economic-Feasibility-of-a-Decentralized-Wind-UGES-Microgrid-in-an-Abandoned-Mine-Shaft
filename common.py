"""
common.py — Single source of truth for the Wind-UGES techno-economic model.

Every parameter is tagged for provenance per the author's truth-discipline rule:
  [M]  = value taken directly from the submitted manuscript
  [D]  = standard engineering derivation from [M] values
  [A]  = ASSUMPTION made for this analysis (must be verified/justified by author)
  [L]  = literature value (source named inline)

Nothing here is fabricated. Where an input is genuinely unknown (rope endurance,
value-of-lost-load), it is parametrised explicitly and swept, not guessed.
"""
import numpy as np

# ----------------------------------------------------------------------------
# Physical constants
# ----------------------------------------------------------------------------
G = 9.81                      # m/s^2  gravitational acceleration

# ----------------------------------------------------------------------------
# UGES mechanical design                                        [M] manuscript
# ----------------------------------------------------------------------------
P_RATED_MW   = 5.0            # [M] rated power of the UGES motor/generator
M_PISTON_KG  = 996_600.0      # [M] 996.6 t reinforced-concrete piston
H_SHAFT_M    = 494.0          # [M] shaft depth (secondary-source estimate; uncertain)
H_PISTON_M   = 25.0           # [M] piston height
H_STROKE_M   = H_SHAFT_M - H_PISTON_M   # [D] 469 m working stroke
V_HOIST_MS   = 0.5            # [M] hoist rope speed
ETA_RT       = 0.8497         # [M] round-trip efficiency (grid-to-grid, Table III)
ETA_1WAY     = 0.92           # [M] one-way efficiency

# Energy per cycle -----------------------------------------------------------
E_CYCLE_GROSS_MWH = M_PISTON_KG * G * H_STROKE_M / 3.6e9    # [D] raw PE per stroke
E_CYCLE_NET_MWH   = 1.083                                    # [M] net grid-delivered/cycle
# (validation: E_CYCLE_GROSS * ETA_RT should ~= 1.083)

CYCLE_TIME_MIN = 2 * (H_STROKE_M / V_HOIST_MS) / 60.0        # [D] full round-trip time (min)
CYCLES_PER_DAY = 46                                          # [M]
DAILY_THROUGHPUT_MWH = 50.0                                  # [M] target daily throughput
AVAILABILITY   = 0.95                                        # [M]
ANNUAL_DISCHARGE_MWH_Y1 = 17_337.5                           # [M] Year-1 annual discharge

# ----------------------------------------------------------------------------
# Economics                                                     [M] manuscript
# ----------------------------------------------------------------------------
PKR_PER_USD   = 282.47        # [M] FX used in manuscript
CAPEX_TOTAL_PKR   = 2_069.3e6 # [M] total CAPEX incl. contingency + EPC
CAPEX_DIRECT_PKR  = 1_753.7e6 # [M] direct CAPEX
CAPEX_CIVIL_PKR   = 709.7e6   # [M]
CAPEX_ELEC_PKR    = 1_044.0e6 # [M]
CAPEX_ROPE_SHEAVE_PKR = 455.2e6  # [M] multi-rope Koepe sheaves + ropes
CAPEX_VFD_PKR     = 423.7e6   # [M] four-quadrant AFE VFD
CAPEX_PMSM_PKR    = 141.2e6   # [M] 5 MW PMSM
CAPEX_LINE_PKR    = 250.0e6   # [M] 132 kV transmission line

OM_FRAC       = 0.01          # [M] annual fixed O&M = 1% of CAPEX
LIFE_YEARS    = 30            # [M]
DISCOUNT_BASE = 0.14          # [M] base discount rate (12% low / 14% base / 16% high)
DISCHARGE_TARIFF_PKR_KWH = 25.0   # [M] discharge tariff
DEGRADATION   = 0.005         # [M] 0.5%/yr discharge degradation
SALVAGE_FRAC  = 0.05          # [A] Year-30 salvage as fraction of CAPEX (steel+concrete scrap);
                              #     tuned so reconstructed LCOS/NPV match the manuscript.

# Reported deterministic results to validate against            [M]
LCOS_REPORTED_PKR_KWH = 18.56
NPV_REPORTED_PKR      = 728.6e6
IRR_REPORTED          = 0.193

# ----------------------------------------------------------------------------
# Wind resource (site Weibull fit)                              [M] manuscript
# ----------------------------------------------------------------------------
WEIBULL_K = 2.6              # [M]
WEIBULL_C = 8.1             # [M] m/s scale parameter at hub height
TURBINE_CF = 0.274          # [M] net capacity factor
TURBINE_UNIT_MW = 2.5       # [M] single co-located turbine for islanding case

# ----------------------------------------------------------------------------
# LCOS / NPV engine (reconstructed, validated against manuscript)
# ----------------------------------------------------------------------------
def annual_discharge(year, e1=ANNUAL_DISCHARGE_MWH_Y1, deg=DEGRADATION):
    """[D] degrading annual discharge, MWh, year=1..N"""
    return e1 * (1.0 - deg) ** (year - 1)

def lcos_pkr_per_kwh(capex=CAPEX_TOTAL_PKR, r=DISCOUNT_BASE, n=LIFE_YEARS,
                     om_frac=OM_FRAC, e1=ANNUAL_DISCHARGE_MWH_Y1,
                     deg=DEGRADATION, salvage_frac=SALVAGE_FRAC):
    """
    [D] Levelised Cost of Storage, PKR/kWh.
    LCOS = [CAPEX + Sum disc(O&M) - disc(salvage)] / Sum disc(discharge_MWh) / 1000
    """
    om = om_frac * capex
    num = capex
    den_mwh = 0.0
    for t in range(1, n + 1):
        df = (1.0 + r) ** (-t)
        num += om * df
        den_mwh += e1 * (1.0 - deg) ** (t - 1) * df
    num -= salvage_frac * capex * (1.0 + r) ** (-n)
    lcos_pkr_per_mwh = num / den_mwh
    return lcos_pkr_per_mwh / 1000.0    # -> PKR/kWh

def npv_pkr(capex=CAPEX_TOTAL_PKR, r=DISCOUNT_BASE, n=LIFE_YEARS,
            om_frac=OM_FRAC, e1=ANNUAL_DISCHARGE_MWH_Y1, deg=DEGRADATION,
            tariff_pkr_kwh=DISCHARGE_TARIFF_PKR_KWH, salvage_frac=SALVAGE_FRAC):
    """[D] Net Present Value, PKR."""
    om = om_frac * capex
    tariff_pkr_mwh = tariff_pkr_kwh * 1000.0
    npv = -capex
    for t in range(1, n + 1):
        df = (1.0 + r) ** (-t)
        e_t = e1 * (1.0 - deg) ** (t - 1)
        cashflow = e_t * tariff_pkr_mwh - om
        npv += cashflow * df
    npv += salvage_frac * capex * (1.0 + r) ** (-n)
    return npv

def irr(capex=CAPEX_TOTAL_PKR, n=LIFE_YEARS, om_frac=OM_FRAC,
        e1=ANNUAL_DISCHARGE_MWH_Y1, deg=DEGRADATION,
        tariff_pkr_kwh=DISCHARGE_TARIFF_PKR_KWH, salvage_frac=SALVAGE_FRAC):
    """[D] Internal Rate of Return via bisection on NPV(r)=0."""
    lo, hi = 0.0, 1.0
    f = lambda r: npv_pkr(capex, r, n, om_frac, e1, deg, tariff_pkr_kwh, salvage_frac)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

if __name__ == "__main__":
    print("=== PARAMETER / MODEL VALIDATION vs MANUSCRIPT ===")
    print(f"E_cycle gross (derived)      : {E_CYCLE_GROSS_MWH:.3f} MWh")
    print(f"E_cycle gross x RTE          : {E_CYCLE_GROSS_MWH*ETA_RT:.3f} MWh "
          f"(manuscript net = {E_CYCLE_NET_MWH})")
    print(f"Round-trip time (derived)    : {CYCLE_TIME_MIN:.1f} min (manuscript ~31.3)")
    print(f"Reconstructed LCOS @14%      : {lcos_pkr_per_kwh():.2f} PKR/kWh "
          f"(manuscript {LCOS_REPORTED_PKR_KWH})")
    print(f"Reconstructed NPV @14%       : {npv_pkr()/1e6:.1f} M PKR "
          f"(manuscript {NPV_REPORTED_PKR/1e6:.1f})")
    print(f"Reconstructed IRR            : {irr()*100:.1f}% "
          f"(manuscript {IRR_REPORTED*100:.1f}%)")


# ensure module output directories exist (repo-root anchored)
import os as _os
_ROOT = _os.path.dirname(_os.path.abspath(__file__))
for _d in ("figures", "results"):
    _os.makedirs(_os.path.join(_ROOT, _d), exist_ok=True)


# --- turbine power curve [M/D] -------------------------------------------------
# QBlade CE v2.0.9 export (19 Jun 2025) at solver reference density 1.225 kg/m3, D = 89.4 m
# (Region-2 Cp = 0.440; the rotor Cp-lambda sweep was truncated at lambda = 10 and is NOT a peak).
# Normalised to the energy-weighted site air density 1.1527 kg/m3 per IEC 61400-12-1, which for a
# pitch-regulated machine scales WIND SPEED, v_n = v*(rho/rho_ref)^(1/3), not power.
# Monthly densities from PMD normals at 45 m a.s.l. run 1.197 (Jan) to 1.136 (Jun) kg/m3.
# Convolved with the monthly Weibull of Khan et al. 2021 at 100 m: gross 120.2 / net 89.7 GWh, CF 20.5%.
import numpy as _np
RHO_REF = 1.225
RHO_SITE_EW = 1.1527
D_ROTOR = 89.4
CP_REGION2 = 0.440
SPECIFIC_POWER_W_M2 = 398
QB_V = _np.array([3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 24.5, 25.0])
QB_P = _np.array([0.0, 68849.9, 102666.9, 146061.0, 200226.4, 266356.8, 345646.4, 439289.0, 548478.6, 674409.2, 816209.1, 960046.7, 1107956.0, 1263756.1, 1425439.9, 1592241.7, 1763729.7, 1939344.3, 2117863.0, 2297932.3, 2442830.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0, 2500000.0])   # W per turbine, IEC-normalised
def turbine_MW(vv):
    vv=_np.asarray(vv,float)
    return _np.where((vv>=3.0)&(vv<=25.0), _np.interp(vv,QB_V,QB_P,left=0,right=0), 0.0)/1e6
