#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arrest_anchorage.py
Shaft arrest system: engagement dynamics, pawl design load, and first-order
anchorage verification of the bearing ledges through the shaft liner.

Companion to: "Beyond Lithium and Above Ground ..."  (Section 3.6)

SCOPE / LIMITS
  Closed-form and elastic-distribution checks only. This does NOT replace a
  local finite-element bearing analysis of the ledge-liner-rock load path,
  which is carried in the paper as an unresolved item.
Units: SI throughout (N, m, Pa, s).
"""
import os, json, numpy as np
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import common as C
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

# ----------------------------------------------------------------------
# 1. INPUTS  (all traceable to the manuscript)
# ----------------------------------------------------------------------
M_PISTON   = C.M_PISTON_KG    # [M] kg  piston mass (from common.py)
G          = C.G              # [M] m/s2
W_PISTON   = M_PISTON * G     # N     static weight  = 9.78 MN

D_INNER    = 5.00             # [M] m  shaft internal diameter
T_LINER    = 0.200            # [M] m  C40/50 liner thickness
D_OUTER    = D_INNER + 2*T_LINER

N_PAWLS    = 4                # -     pawls per set

# Concrete C40/50 to EN 1992-1-1
F_CK       = 40e6             # Pa    characteristic cylinder strength
GAMMA_C    = 1.5
F_CD       = F_CK / GAMMA_C   # Pa    design compressive strength  = 26.7 MPa
F_CTK005   = 2.5e6            # Pa    5% fractile tensile strength (C40/50)
F_CTD      = F_CTK005 / GAMMA_C

# EN 1992-1-1 6.7 partially loaded areas: FRdu <= 3.0 fcd Ac0
BEARING_CAP = 3.0 * F_CD      # Pa    = 80.0 MPa  upper bound on concrete bearing

# EN 1992-1-1 6.2.5 interface shear, rough surface (conservative: cohesion only)
C_ROUGH    = 0.45
MU_ROUGH   = 0.70
V_RDI_COH  = C_ROUGH * F_CTD  # Pa    cohesion-only interface shear   = 0.75 MPa

# Regulatory deceleration envelope for shaft safety catches (mining practice):
# not less than 9 m/s2, not more than 20 m/s2
A_MIN, A_MAX = 9.0, 20.0      # m/s2

# ----------------------------------------------------------------------
# 2. ENGAGEMENT DYNAMICS
# ----------------------------------------------------------------------
def engagement(t_delay):
    """Free-fall state at the instant the pawls bite."""
    v = G * t_delay
    drop = 0.5 * G * t_delay**2
    ke = 0.5 * M_PISTON * v**2
    return v, drop, ke

def arrest_force(v, stroke):
    """
    Energy balance over the progressive arrest stroke, gravity still acting:
        F*s = KE + W*s   ->   F = KE/s + W
    Net deceleration of the mass a_net = (F - W)/m = v^2/(2s)
    """
    ke = 0.5 * M_PISTON * v**2
    F = ke / stroke + W_PISTON
    a_net = v**2 / (2*stroke)
    return F, a_net

def stroke_for_decel(v, a):
    """Arrest stroke that produces a given net deceleration."""
    return v**2 / (2*a)

# ----------------------------------------------------------------------
# 3. ANCHORAGE CHECKS
# ----------------------------------------------------------------------
def pawl_bearing_area(F_total):
    """Contact area per pawl on the concrete ledge, EN 1992-1-1 6.7 bound."""
    F_pawl = F_total / N_PAWLS
    return F_pawl / BEARING_CAP, F_pawl

def shear_transfer_length(F_total, v_rdi=V_RDI_COH):
    """
    Vertical shear transfer from liner into rock over the liner-rock interface.
    Treated as uniform shear on the outer cylindrical surface.
    """
    return F_total / (np.pi * D_OUTER * v_rdi)

def liner_axial_stress(F_total):
    """Mean axial compressive stress in the liner annulus."""
    area = np.pi * ((D_OUTER/2)**2 - (D_INNER/2)**2)
    return F_total / area, area

def rock_radial_confinement(depth, gamma_rock=26e3, k0=0.5):
    """Horizontal in-situ stress used as normal stress on the interface."""
    return k0 * gamma_rock * depth

# ----------------------------------------------------------------------
# 4. RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("="*74)
    print("SHAFT ARREST SYSTEM - ENGAGEMENT DYNAMICS AND LEDGE ANCHORAGE")
    print("="*74)
    print(f"Piston mass            {M_PISTON:,.0f} kg")
    print(f"Static weight W        {W_PISTON/1e6:.2f} MN")
    print(f"Concrete C40/50: fcd   {F_CD/1e6:.1f} MPa,  bearing bound 3fcd = {BEARING_CAP/1e6:.1f} MPa")
    print(f"Interface shear (coh)  {V_RDI_COH/1e6:.2f} MPa")

    # --- 4.1 design load vs engagement delay, at the regulatory decel band ---
    print("\n" + "-"*74)
    print("4.1  DESIGN LOAD AT THE 9-20 m/s2 SAFETY-CATCH DECELERATION BAND")
    print("-"*74)
    print(f"{'t_delay':>8} {'v':>7} {'drop':>7} {'KE':>8} | "
          f"{'s@9':>7} {'F@9':>7} | {'s@20':>7} {'F@20':>7}")
    print(f"{'(s)':>8} {'(m/s)':>7} {'(m)':>7} {'(MJ)':>8} | "
          f"{'(m)':>7} {'(MN)':>7} | {'(m)':>7} {'(MN)':>7}")
    rows = []
    for td in (0.25, 0.50, 0.75, 1.00):
        v, drop, ke = engagement(td)
        s9  = stroke_for_decel(v, A_MIN);  F9,_  = arrest_force(v, s9)
        s20 = stroke_for_decel(v, A_MAX);  F20,_ = arrest_force(v, s20)
        rows.append((td, v, drop, ke, s9, F9, s20, F20))
        print(f"{td:8.2f} {v:7.2f} {drop:7.2f} {ke/1e6:8.2f} | "
              f"{s9:7.2f} {F9/1e6:7.1f} | {s20:7.2f} {F20/1e6:7.1f}")

    # design case adopted: 0.5 s delay
    v_d, drop_d, ke_d = engagement(0.50)
    s_lo = stroke_for_decel(v_d, A_MAX)     # short stroke -> high force
    s_hi = stroke_for_decel(v_d, A_MIN)     # long stroke  -> low force
    F_hi, _ = arrest_force(v_d, s_lo)
    F_lo, _ = arrest_force(v_d, s_hi)
    print(f"\nAdopted engagement delay 0.50 s -> v = {v_d:.2f} m/s, "
          f"free drop {drop_d:.2f} m, KE = {ke_d/1e6:.1f} MJ")
    print(f"Compliant arrest stroke  {s_lo:.2f} - {s_hi:.2f} m")
    print(f"Design load envelope     {F_lo/1e6:.1f} - {F_hi/1e6:.1f} MN "
          f"({F_lo/W_PISTON:.2f} - {F_hi/W_PISTON:.2f} x static weight)")

    # --- 4.2 anchorage at the governing (upper) design load ---
    F_DES = F_hi
    print("\n" + "-"*74)
    print(f"4.2  ANCHORAGE CHECKS AT GOVERNING DESIGN LOAD {F_DES/1e6:.1f} MN")
    print("-"*74)

    A_pawl, F_pawl = pawl_bearing_area(F_DES)
    side = np.sqrt(A_pawl)
    print(f"Load per pawl ({N_PAWLS} pawls)      {F_pawl/1e6:.2f} MN")
    print(f"Bearing area required        {A_pawl*1e4:.0f} cm2  "
          f"(square pad {side*1e3:.0f} x {side*1e3:.0f} mm)")
    print(f"  -> governed by concrete at {BEARING_CAP/1e6:.0f} MPa, NOT by steel at 200 MPa")
    A_steel = F_pawl / 200e6
    print(f"  steel-only pad would be    {A_steel*1e4:.0f} cm2  "
          f"({A_pawl/A_steel:.1f}x smaller - the earlier basis was unconservative)")

    L_shear = shear_transfer_length(F_DES)
    print(f"\nShear transfer length (cohesion only)   {L_shear:.2f} m")
    for depth in (100, 250, 469):
        sig_n = rock_radial_confinement(depth)
        v_rdi = V_RDI_COH + MU_ROUGH * sig_n
        L = shear_transfer_length(F_DES, v_rdi)
        print(f"  at {depth:3d} m depth: sigma_n {sig_n/1e6:5.2f} MPa, "
              f"v_Rdi {v_rdi/1e6:5.2f} MPa -> L = {L:.2f} m")

    sig_ax, area = liner_axial_stress(F_DES)
    print(f"\nLiner annulus area           {area:.3f} m2")
    print(f"Mean axial stress in liner   {sig_ax/1e6:.2f} MPa  "
          f"({sig_ax/F_CD*100:.1f}% of fcd)  -> {'OK' if sig_ax < F_CD else 'FAIL'}")

    # --- 4.3 what the paper should report ---
    print("\n" + "="*74)
    print("SUMMARY FOR MANUSCRIPT")
    print("="*74)
    print(f"  Engagement delay        0.50 s")
    print(f"  Impact velocity         {v_d:.2f} m/s")
    print(f"  Kinetic energy          {ke_d/1e6:.1f} MJ")
    print(f"  Compliant stroke        {s_lo:.2f}-{s_hi:.2f} m (9-20 m/s2 band)")
    print(f"  Design load             {F_lo/1e6:.0f}-{F_hi/1e6:.0f} MN total")
    print(f"  Per pawl                {F_lo/N_PAWLS/1e6:.1f}-{F_hi/N_PAWLS/1e6:.1f} MN")
    print(f"  Bearing pad (concrete)  {pawl_bearing_area(F_lo)[0]*1e4:.0f}-{A_pawl*1e4:.0f} cm2")
    print(f"  Shear length, no confin {shear_transfer_length(F_lo):.1f}-{L_shear:.1f} m")
    print(f"  Liner axial stress      {liner_axial_stress(F_lo)[0]/1e6:.1f}-{sig_ax/1e6:.1f} MPa "
          f"vs fcd {F_CD/1e6:.1f} MPa")

    # ------------------------------------------------------------------
    # export the design envelope for the figure pipeline
    # ------------------------------------------------------------------
    OUT = os.path.join(ROOT, "figure_data")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    rec = []
    for td in np.linspace(0.1, 1.5, 29):
        v, drop, ke = engagement(td)
        for a in (A_MIN, A_MAX):
            s_ = stroke_for_decel(v, a)
            F_, _ = arrest_force(v, s_)
            rec.append([td, v, drop, ke/1e6, a, s_, F_/1e6])
    np.savetxt(os.path.join(OUT, "arrest_design_envelope.csv"),
               np.array(rec), delimiter=",",
               header="t_delay_s,v_ms,free_drop_m,KE_MJ,decel_ms2,stroke_m,force_MN",
               comments="")
    print("\nwrote figure_data/arrest_design_envelope.csv")

    with open(os.path.join(ROOT, "results", "arrest_anchorage.json"), "w") as fh:
        json.dump(dict(
            static_weight_MN=W_PISTON/1e6,
            engagement_delay_s=0.50,
            impact_velocity_ms=v_d,
            kinetic_energy_MJ=ke_d/1e6,
            stroke_range_m=[s_lo, s_hi],
            design_load_MN=[F_lo/1e6, F_hi/1e6],
            per_pawl_MN=[F_lo/N_PAWLS/1e6, F_hi/N_PAWLS/1e6],
            bearing_pad_cm2=[pawl_bearing_area(F_lo)[0]*1e4, A_pawl*1e4],
            shear_length_m=[shear_transfer_length(F_lo), L_shear],
            liner_axial_MPa=[liner_axial_stress(F_lo)[0]/1e6, sig_ax/1e6],
        ), fh, indent=2)
    print("Wrote results/arrest_anchorage.json")
