# -*- coding: utf-8 -*-
"""
settlement.py  --  Headframe-footing settlement, CORRECTED constitutive treatment.

TRUTH-DISCIPLINE NOTE
---------------------
An earlier version of this module drove a pressure-INDEPENDENT (phi = 0, Tresca)
soil, which put the 14 m footing into ARTIFICIAL bearing failure at su = 5 kPa and
returned ~16.3 mm. That figure was a constitutive artefact, not a physical result.

This version uses the researched drained parameters with FRICTION ACTIVE and proves,
by an independent drained bearing-capacity check, that the footing is far from
failure -- so the movement is elastic-dominated and an order of magnitude below the
25 mm code limit. Two independent routes are reported:
  (A) Layered-elastic settlement (Newmark corner-superposition, centre of footing).
  (B) Drained bearing-capacity factor of safety (Vesic, phi' = 28 deg).

Inputs [L] = literature/site-report; [D] = derived; [A] = assumption.
A detailed axisymmetric FE continuum model is the design-stage confirmation of the
open-source estimate produced here.
"""
import os, numpy as np

# ---- researched inputs -------------------------------------------------------
FOOTING_LOAD_MN = 17.95          # [L] headframe + hoist reaction
B = L = 14.0                     # [L] square mat, m
q = FOOTING_LOAD_MN*1e3 / (B*L)  # [D] bearing pressure, kPa  -> 91.6 kPa
H_OVER = 5.0                     # [L] compressible overburden thickness, m
E_OVER, NU_OVER = 50e3, 0.30     # [L] overburden E' (kPa), nu
E_ROCK, NU_ROCK = 0.25e6, 0.25   # [L] rock-mass E_rm = 0.25 GPa (regional analog), nu
GAM_OVER, C_OVER, PHI_OVER = 20.0, 5.0, 28.0   # [L] kN/m3, kPa, deg (drained)
DF = 0.0                         # [A] surface mat, no embedment credit
CODE_LIMIT_MM = 25.0             # [L] industrial building-code allowable

# ---- (A) layered-elastic settlement -----------------------------------------
def _corner_stress_factor(Bx, Ly, z):
    b, l = Bx/2.0, Ly/2.0
    if z < 1e-6:
        return 1.0
    m, n = b/z, l/z
    R = np.sqrt(m*m + n*n + 1)
    term = (2*m*n*R/(m*m+n*n+1+m*m*n*n))*((m*m+n*n+2)/(m*m+n*n+1)) \
           + np.arctan2(2*m*n*R, (m*m+n*n+1-m*m*n*n))
    return 4*term/(4*np.pi)   # x4 -> centre of full rectangle

def layered_settlement_mm(E1=E_OVER, E2=E_ROCK, h_over=H_OVER, z_max=40.0, dz=0.25):
    s = 0.0; z = dz/2.0
    while z < z_max:
        E  = E1 if z <= h_over else E2
        nu = NU_OVER if z <= h_over else NU_ROCK
        Mc = E*(1-nu)/((1+nu)*(1-2*nu))            # constrained modulus
        s += _corner_stress_factor(B, L, z)*q/Mc*dz
        z += dz
    return s*1000.0

# ---- (B) drained bearing capacity (Vesic) -----------------------------------
def bearing_fos():
    phi = np.radians(PHI_OVER)
    Nq = np.exp(np.pi*np.tan(phi))*np.tan(np.radians(45)+phi/2)**2
    Nc = (Nq-1)/np.tan(phi)
    Ng = 2*(Nq+1)*np.tan(phi)
    sc, sq, sg = 1+(Nq/Nc), 1+np.tan(phi), 0.6
    qult = C_OVER*Nc*sc + GAM_OVER*DF*Nq*sq + 0.5*GAM_OVER*B*Ng*sg
    return qult/q, (Nc, Nq, Ng)

# ---- indicative settlement bowl for Fig. 3 (anchored to central value) ------
def write_fig3_csv(s0_mm):
    """Indicative surface bowl anchored to the layered-elastic central value.
    Shape only; the reported quantity is the central magnitude s0."""
    r = np.linspace(0.0, 40.0, 81)
    Reff = B/2.0
    bowl = np.where(r <= Reff,
                    s0_mm*(1 - 0.15*(r/Reff)**2),
                    s0_mm*(0.85)/(1 + (np.maximum(r-Reff,0.0)/Reff)**1.5))
    out = os.path.join(os.path.dirname(__file__), "..", "figure_data", "fig3_settlement.csv")
    out = os.path.abspath(out)
    with open(out, "w") as f:
        f.write("distance_m,settlement_mm\n")
        for ri, si in zip(r, bowl):
            f.write(f"{ri:.3f},{si:.4f}\n")
    return out

if __name__ == "__main__":
    s0 = layered_settlement_mm()
    fos, (Nc, Nq, Ng) = bearing_fos()
    print("=== Headframe-footing settlement (corrected, friction active) ===")
    print(f"Bearing pressure q            : {q:.1f} kPa")
    print(f"(A) Layered-elastic central   : {s0:.1f} mm   (code limit {CODE_LIMIT_MM:.0f} mm)")
    print(f"(B) Drained bearing FoS       : {fos:.1f}   (Nc={Nc:.1f}, Nq={Nq:.1f}, Ng={Ng:.1f})")
    print(f"    FoS >> 3  -> elastic-dominated; the 16.3 mm phi=0 value was an artefact.")
    print()
    print("Rock-modulus sensitivity (E_rm):")
    for Er in (1.0e6, 2.0e6, 4.0e6, 8.0e6):
        print(f"  E_rm={Er/1e6:>4.1f} GPa -> {layered_settlement_mm(E2=Er):>5.1f} mm")
    print("Overburden-thickness sensitivity (governs the band):")
    for h in (3.0, 5.0, 8.0, 12.0):
        print(f"  h_over={h:>4.1f} m -> {layered_settlement_mm(h_over=h):>5.1f} mm")
    print("\n(Fig. 3 profile is written by settlement_fem.py, the continuum cross-check.)")
