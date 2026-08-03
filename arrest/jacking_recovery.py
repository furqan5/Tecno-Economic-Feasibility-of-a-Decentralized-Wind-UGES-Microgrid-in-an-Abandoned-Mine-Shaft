#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jacking_recovery.py
Emergency discharge by in-shaft regenerative hydraulic jacking after loss of
the headframe. Replaces the assumed ~80% conversion with a component chain
plus Monte-Carlo propagation.

Companion to: "Beyond Lithium and Above Ground ..."  (Section 9.5)
Units: SI (N, m, Pa, s, W, J).
"""
import os, json, numpy as np
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import common as C
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

RNG = np.random.default_rng(20260729)

# ---------------------------------------------------------------- inputs
M_PISTON = C.M_PISTON_KG      # [M]
G        = C.G                # [M]
W        = M_PISTON * G          # 9.78 MN
STROKE   = C.H_STROKE_M       # [D] m  operating stroke (common.py)
E_MECH   = W * STROKE            # J   = 4.587 GJ = 1.274 MWh

P_WORK   = 70e6                  # Pa  700 bar heavy-lift circuit
N_JACKS  = 4
LEDGE_SP = 3.0                   # m   ledge spacing = jack stroke

# hydraulic fluid, ISO VG 46 at 40 C
RHO_OIL  = 870.0                 # kg/m3
NU_OIL   = 46e-6                 # m2/s

D_PIPE   = 0.032                 # m   DN32 bore
L_PIPE   = 500.0                 # m   worst-case run, piston to bottom chamber

# ------------------------------------------------------- circuit sizing
def circuit(load_kW):
    """Size the jack circuit for a given delivered mechanical power."""
    A_tot  = W / P_WORK                      # total effective piston area
    A_jack = A_tot / N_JACKS
    bore   = np.sqrt(4*A_jack/np.pi)
    v_desc = load_kW*1e3 / W                 # descent rate, m/s
    Q      = A_tot * v_desc                  # m3/s
    return dict(A_tot=A_tot, A_jack=A_jack, bore=bore, v_desc=v_desc, Q=Q)

def line_loss(Q):
    """Darcy-Weisbach pressure drop in the return line."""
    A = np.pi*D_PIPE**2/4
    v = Q/A
    Re = v*D_PIPE/NU_OIL
    f  = 64/Re if Re < 2300 else 0.316*Re**-0.25
    dp = f*(L_PIPE/D_PIPE)*(RHO_OIL*v**2/2)
    return dp, v, Re, ('laminar' if Re < 2300 else 'turbulent')

# ------------------------------------------------- Monte-Carlo efficiency
def sample_chain(n):
    """
    Component efficiencies. Triangular distributions over ranges typical of
    heavy-lift hydraulic equipment; these are engineering estimates, not
    measurements, and are the dominant uncertainty in the delivered energy.
    """
    eta_cyl = RNG.triangular(0.93, 0.955, 0.97,  n)   # cylinder mech-hyd
    eta_mot = RNG.triangular(0.86, 0.905, 0.93,  n)   # axial-piston motor
    eta_gen = RNG.triangular(0.93, 0.950, 0.965, n)   # generator
    aux     = RNG.triangular(0.01, 0.020, 0.04,  n)   # parasitic fraction
    return eta_cyl, eta_mot, eta_gen, aux

def run_mc(load_kW=100.0, n=200_000):
    c  = circuit(load_kW)
    dp, v_pipe, Re, regime = line_loss(c['Q'])
    eta_line = 1.0 - dp/P_WORK

    eta_cyl, eta_mot, eta_gen, aux = sample_chain(n)
    eta_tot = eta_cyl * eta_line * eta_mot * eta_gen * (1.0 - aux)

    E_del = E_MECH * eta_tot                      # J delivered
    hours = E_del / (load_kW*1e3) / 3600.0
    return c, dp, v_pipe, Re, regime, eta_line, eta_tot, E_del, hours

# ---------------------------------------------------------------- report
if __name__ == "__main__":
    J2MWH = 1/3.6e9
    print("="*74)
    print("IN-SHAFT REGENERATIVE JACKING - RECOVERY EFFICIENCY AND ENDURANCE")
    print("="*74)
    print(f"Piston weight              {W/1e6:.2f} MN")
    print(f"Operating stroke           {STROKE:.0f} m")
    print(f"Mechanical energy stored   {E_MECH/1e9:.3f} GJ = {E_MECH*J2MWH:.3f} MWh")
    print(f"Ledge spacing / jack strk  {LEDGE_SP:.1f} m")
    print(f"Energy per increment       {W*LEDGE_SP/1e6:.1f} MJ")
    print(f"Number of increments       {STROKE/LEDGE_SP:.0f}")

    c, dp, v_pipe, Re, regime, eta_line, eta_tot, E_del, hours = run_mc(100.0)
    print("\n" + "-"*74)
    print("CIRCUIT SIZING AT 0.1 MW PROTECTED LOAD")
    print("-"*74)
    print(f"Working pressure           {P_WORK/1e5:.0f} bar")
    print(f"Total piston area          {c['A_tot']:.4f} m2 "
          f"({N_JACKS} jacks x {c['A_jack']:.4f} m2)")
    print(f"Jack bore                  {c['bore']*1e3:.0f} mm")
    print(f"Descent rate               {c['v_desc']*1e3:.2f} mm/s")
    print(f"Flow                       {c['Q']*6e4:.1f} L/min")
    print(f"Line velocity (DN{D_PIPE*1e3:.0f})       {v_pipe:.2f} m/s, Re = {Re:.0f} ({regime})")
    print(f"Line pressure drop         {dp/1e6:.2f} MPa = {dp/P_WORK*100:.1f}% of working pressure")
    print(f"Time per increment         {LEDGE_SP/c['v_desc']/60:.1f} min")

    print("\n" + "-"*74)
    print("MONTE-CARLO CONVERSION EFFICIENCY  (N = 200,000)")
    print("-"*74)
    p = np.percentile(eta_tot, [10, 50, 90])
    print(f"Line efficiency (determ.)  {eta_line:.4f}")
    print(f"Overall eta  P10/P50/P90   {p[0]:.3f} / {p[1]:.3f} / {p[2]:.3f}")
    pe = np.percentile(E_del*J2MWH, [10, 50, 90])
    print(f"Delivered energy (MWh)     {pe[0]:.3f} / {pe[1]:.3f} / {pe[2]:.3f}")
    ph = np.percentile(hours, [10, 50, 90])
    print(f"Endurance at 0.1 MW (h)    {ph[0]:.1f} / {ph[1]:.1f} / {ph[2]:.1f}")

    print("\n" + "-"*74)
    print("ENDURANCE BY PROTECTED LOAD (median chain)")
    print("-"*74)
    print(f"{'load (MW)':>10} {'bore (mm)':>10} {'flow (L/min)':>13} "
          f"{'dp (%)':>8} {'E_del (MWh)':>12} {'hours':>8}")
    for L in (0.01, 0.05, 0.10, 0.25, 0.50):
        cc, ddp, _, _, _, el, et, Ed, hh = run_mc(L*1e3, n=20_000)
        print(f"{L:10.2f} {cc['bore']*1e3:10.0f} {cc['Q']*6e4:13.1f} "
              f"{ddp/P_WORK*100:8.2f} {np.median(Ed)*J2MWH:12.3f} {np.median(hh):8.1f}")

    print("\n" + "="*74)
    print("SUMMARY FOR MANUSCRIPT")
    print("="*74)
    print(f"  Conversion efficiency   {p[1]*100:.0f}% (P10-P90 {p[0]*100:.0f}-{p[2]*100:.0f}%)")
    print(f"  Delivered energy        {pe[1]:.2f} MWh (P10-P90 {pe[0]:.2f}-{pe[2]:.2f})")
    print(f"  Endurance at 0.1 MW     {ph[1]:.1f} h (P10-P90 {ph[0]:.1f}-{ph[2]:.1f})")
    print(f"  Compare Table 10 calm buffer for 0.1 MW load: 10.8 h")

    # ------------------------------------------------------------------
    # export for the figure pipeline
    # ------------------------------------------------------------------
    OUT = os.path.join(ROOT, "figure_data")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    rec = []
    for L in np.linspace(0.01, 0.60, 40):
        cc, ddp, _, _, _, el, et, Ed, hh = run_mc(L*1e3, n=5000)
        rec.append([L, cc['Q']*6e4, ddp/P_WORK*100,
                    np.median(et), np.median(Ed)*J2MWH, np.median(hh)])
    np.savetxt(os.path.join(OUT, "jacking_recovery.csv"),
               np.array(rec), delimiter=",",
               header="load_MW,flow_Lmin,line_loss_pct,eta_median,E_delivered_MWh,endurance_h",
               comments="")
    print("wrote figure_data/jacking_recovery.csv")

    with open(os.path.join(ROOT, "results", "jacking_recovery.json"), "w") as fh:
        json.dump(dict(
            mechanical_energy_MWh=E_MECH*J2MWH,
            jack_bore_mm=c['bore']*1e3,
            n_jacks=N_JACKS,
            working_pressure_bar=P_WORK/1e5,
            line_loss_pct=dp/P_WORK*100,
            eta_P10_P50_P90=list(np.percentile(eta_tot, [10, 50, 90])),
            delivered_MWh_P10_P50_P90=list(np.percentile(E_del*J2MWH, [10, 50, 90])),
            endurance_h_at_0p1MW=list(np.percentile(hours, [10, 50, 90])),
        ), fh, indent=2)
    print("Wrote results/jacking_recovery.json")
