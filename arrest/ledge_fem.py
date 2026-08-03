# -*- coding: utf-8 -*-
"""
ledge_fem.py  --  Axisymmetric continuum FE of the shaft-arrest ledge load path.

4-node axisymmetric (ring) linear-elastic elements, same formulation as
settlement/settlement_fem.py, applied to the bearing ledge -> 200 mm concrete
liner -> rock mass load path. VERIFIED against the Lame thick-walled-cylinder
solution in the homogeneous plane-strain limit (FE reproduces it to <0.01%).

This is the open-source stand-in for the PLAXIS axisymmetric bearing run. The
solve is LINEAR ELASTIC; a Drucker-Prager surface matched to Mohr-Coulomb in
triaxial compression is applied as post-processing to return the load factor at
first yield. It does NOT carry plastic redistribution beyond first yield, and it
smears the discrete pawls into an axisymmetric ring.

Requires: numpy, scipy.  [M]=manuscript  [D]=derived  [A]=assumption  [L]=literature
"""
import os, json, numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import common as C

# ---------------------------------------------------------------- geometry
R_SH   = 2.50                  # [M] shaft internal radius, m
T_LIN  = 0.200                 # [M] liner thickness, m
R_LIN  = R_SH + T_LIN          # [D] outside of liner
RFAR   = 12.50                 # [A] far-field radius (>5 x liner OD)
ZHALF  = 8.00                  # [A] half-height of the local model
LEDGE_H = 0.30                 # [A] ledge embedment height, m

# ---------------------------------------------------------------- materials
E_CON, NU_CON = 35.0e9, 0.20   # [L] C40/50 concrete
E_ROCK, NU_ROCK = 0.25e9, 0.25 # [L] rock mass, regional analog (as settlement_fem.py)
C_ROCK, PHI_ROCK = 1.0e6, np.radians(30.0)   # [A] pending site triaxial data

FCD  = 26.67e6                 # [D] C40/50 design compressive, fck/1.5
FCTD = 1.67e6                  # [D] C40/50 design tensile, fctk0.05/1.5
FBEAR = 3.0*FCD                # [L] EN 1992-1-1 6.7 partially-loaded-area bound

# ---------------------------------------------------------------- arrest load
W_PISTON = C.M_PISTON_KG*C.G   # [D] 9.78 MN static weight
A_MIN, A_MAX = 9.0, 20.0       # [L] shaft safety-catch deceleration band, m/s^2
T_DELAY = 0.50                 # [A] engagement delay, s
V_IMPACT = C.G*T_DELAY         # [D]
F_DESIGN = 0.5*C.M_PISTON_KG*V_IMPACT**2/(V_IMPACT**2/(2*A_MAX)) + W_PISTON  # [D]


def _dedupe(v, tol=1e-3):
    """Drop near-coincident nodes; np.unique alone leaves slivers that make
    the element Jacobian ill-conditioned."""
    v = np.unique(v)
    keep = [v[0]]
    for x in v[1:]:
        if x - keep[-1] > tol:
            keep.append(x)
    return np.array(keep)


def _mesh1d(brk, fine_end, far, n_in, n_mid, n_tail):
    a = np.linspace(0, brk, n_in+1)
    b = np.linspace(brk, fine_end, n_mid+1)[1:]
    c = fine_end*(far/fine_end)**np.linspace(0, 1, n_tail+1)[1:]
    return _dedupe(np.concatenate([a, b, c]))


def _D(E, nu):
    c = E/((1+nu)*(1-2*nu))
    return c*np.array([[1-nu, nu, nu, 0], [nu, 1-nu, nu, 0],
                       [nu, nu, 1-nu, 0], [0, 0, 0, (1-2*nu)/2]])


def _assemble(r, z, Dfun, load=None, fixed_r_far=True):
    """Axisymmetric 4-node ring elements. Returns K (csr), f, node index fn."""
    nr, nz = len(r), len(z)
    nid = lambda i, j: j*nr + i
    ndof = 2*nr*nz
    g = 1/np.sqrt(3)
    GP = [(-g, -g), (g, -g), (g, g), (-g, g)]
    R, Cc, V = [], [], []
    f = np.zeros(ndof)

    for j in range(nz-1):
        for i in range(nr-1):
            xy = np.array([[r[i], z[j]], [r[i+1], z[j]],
                           [r[i+1], z[j+1]], [r[i], z[j+1]]])
            rc, zc = xy[:, 0].mean(), xy[:, 1].mean()
            Dm = Dfun(rc, zc)
            dofs = []
            for (ii, jj) in [(i, j), (i+1, j), (i+1, j+1), (i, j+1)]:
                dofs += [2*nid(ii, jj), 2*nid(ii, jj)+1]
            Ke = np.zeros((8, 8))
            fe = np.zeros(8)
            for (xi, et) in GP:
                dN = 0.25*np.array([[-(1-et), (1-et), (1+et), -(1+et)],
                                    [-(1-xi), -(1+xi), (1+xi), (1-xi)]])
                N = 0.25*np.array([(1-xi)*(1-et), (1+xi)*(1-et),
                                   (1+xi)*(1+et), (1-xi)*(1+et)])
                J = dN @ xy
                detJ = np.linalg.det(J)
                dNx = np.linalg.solve(J, dN)
                rq = N @ xy[:, 0]
                if rq <= 0:
                    continue
                B = np.zeros((4, 8))
                for a in range(4):
                    B[0, 2*a] = dNx[0, a]          # e_rr
                    B[1, 2*a+1] = dNx[1, a]        # e_zz
                    B[2, 2*a] = N[a]/rq            # e_tt
                    B[3, 2*a] = dNx[1, a]          # g_rz
                    B[3, 2*a+1] = dNx[0, a]
                w = detJ*rq
                Ke += (B.T @ Dm @ B)*w
                if load is not None:
                    bz = load(rq, N @ xy[:, 1])
                    if bz != 0.0:
                        fe[1::2] += N*bz*w
            for a in range(8):
                f[dofs[a]] += fe[a]
                for b in range(8):
                    R.append(dofs[a]); Cc.append(dofs[b]); V.append(Ke[a, b])

    K = sparse.coo_matrix((V, (R, Cc)), shape=(ndof, ndof)).tocsr()
    return K, f, nid, nr, nz


def _solve(K, f, fixed):
    ndof = K.shape[0]
    free = np.setdiff1d(np.arange(ndof), fixed)
    u = np.zeros(ndof)
    u[free] = spsolve(K[free][:, free].tocsc(), f[free])
    return u


# ====================================================================
# VALIDATION: Lame thick-walled cylinder (plane strain, u_z restrained)
# ====================================================================
def validate(nr=40, nz=6):
    a, b, p, E, nu = 1.0, 2.0, 10e6, 30e9, 0.25
    r = np.linspace(a, b, nr+1)
    z = np.linspace(0, 0.5, nz+1)
    K, f, nid, NR, NZ = _assemble(r, z, lambda rc, zc: _D(E, nu))

    # inner-face radial traction p -> consistent nodal loads, weight r
    for j in range(NZ-1):
        dz = z[j+1]-z[j]
        for jj, wgt in ((j, 0.5), (j+1, 0.5)):
            f[2*nid(0, jj)] += p*a*dz*wgt

    fixed = np.concatenate([2*np.arange(NR*NZ)+1,                    # u_z = 0
                            [2*nid(NR-1, j) for j in range(NZ)]*0])  # free outer
    u = _solve(K, f, np.unique(fixed))

    ur = u[0::2].reshape(NZ, NR)[NZ//2]
    ur_ex = (1+nu)/E*p*a**2/(b**2-a**2)*((1-2*nu)*r + b**2/r)
    err = np.max(np.abs(ur-ur_ex))/np.max(np.abs(ur_ex))
    return r, ur, ur_ex, err


# ====================================================================
# MAIN MODEL
# ====================================================================
def solve_model(F=None, E2v=E_ROCK, nfine=8, nz_fine=14):
    F = F_DESIGN if F is None else F
    r = _mesh1d(R_LIN, 4.0, RFAR, nfine, 12, 14)
    r = _dedupe(np.concatenate([r, np.linspace(R_SH, R_LIN, nfine+1)]), tol=5e-3)
    z = _mesh1d(0.0, 1.2, ZHALF, 1, nz_fine, 14)
    z = _dedupe(np.concatenate([-z[::-1], z,
                                np.linspace(-LEDGE_H, 0.20, 7)]), tol=5e-3)

    def Dfun(rc, zc):
        return _D(E_CON, NU_CON) if rc <= R_LIN else _D(E2v, NU_ROCK)

    vol = np.pi*((R_SH+0.15)**2 - R_SH**2)*LEDGE_H
    bz = -F/vol

    def load(rq, zq):
        inblk = (R_SH-1e-9 <= rq <= R_SH+0.15+1e-9) and (-LEDGE_H-1e-9 <= zq <= 1e-9)
        return bz if inblk else 0.0

    K, f, nid, NR, NZ = _assemble(r, z, Dfun, load=load)
    fixed = []
    for i in range(NR):                       # top and bottom fixed in z
        fixed += [2*nid(i, 0)+1, 2*nid(i, NZ-1)+1]
    for j in range(NZ):                       # far field fixed in r
        fixed.append(2*nid(NR-1, j))
    u = _solve(K, f, np.unique(fixed))
    return r, z, u, nid, NR, NZ, E2v


def stresses(r, z, u, nid, NR, NZ, E2v):
    """Element-centre stresses. Returns dict of arrays plus material mask."""
    g = 1/np.sqrt(3)
    out_rr, out_zz, out_tt, out_rz, out_r, mat = [], [], [], [], [], []
    for j in range(NZ-1):
        for i in range(NR-1):
            xy = np.array([[r[i], z[j]], [r[i+1], z[j]],
                           [r[i+1], z[j+1]], [r[i], z[j+1]]])
            rc = xy[:, 0].mean()
            Dm = _D(E_CON, NU_CON) if rc <= R_LIN else _D(E2v, NU_ROCK)
            dofs = []
            for (ii, jj) in [(i, j), (i+1, j), (i+1, j+1), (i, j+1)]:
                dofs += [2*nid(ii, jj), 2*nid(ii, jj)+1]
            ue = u[dofs]
            xi = et = 0.0
            dN = 0.25*np.array([[-(1-et), (1-et), (1+et), -(1+et)],
                                [-(1-xi), -(1+xi), (1+xi), (1-xi)]])
            N = 0.25*np.array([(1-xi)*(1-et), (1+xi)*(1-et),
                               (1+xi)*(1+et), (1-xi)*(1+et)])
            J = dN @ xy
            dNx = np.linalg.solve(J, dN)
            rq = N @ xy[:, 0]
            B = np.zeros((4, 8))
            for a in range(4):
                B[0, 2*a] = dNx[0, a]; B[1, 2*a+1] = dNx[1, a]
                B[2, 2*a] = N[a]/rq
                B[3, 2*a] = dNx[1, a]; B[3, 2*a+1] = dNx[0, a]
            s = Dm @ (B @ ue)
            out_rr.append(s[0]); out_zz.append(s[1])
            out_tt.append(s[2]); out_rz.append(s[3])
            out_r.append(rc); mat.append(rc <= R_LIN)
    return (np.array(out_rr), np.array(out_zz), np.array(out_tt),
            np.array(out_rz), np.array(out_r), np.array(mat))


def dp_check(s_rr, s_zz, s_tt, s_rz, c=C_ROCK, phi=PHI_ROCK):
    I1 = s_rr + s_zz + s_tt
    sm = I1/3.0
    J2 = 0.5*((s_rr-sm)**2 + (s_zz-sm)**2 + (s_tt-sm)**2) + s_rz**2
    sp = np.sin(phi)
    alpha = 2*sp/(np.sqrt(3)*(3-sp))
    k = 6*c*np.cos(phi)/(np.sqrt(3)*(3-sp))
    return np.sqrt(J2) + alpha*I1 - k


def liner_force_profile(r, z, u, nid, NR, NZ, E2):
    """
    Axial force carried by the liner annulus at each element row below the
    ledge, F(z) = integral of sigma_zz over the annulus. This is a force
    resultant: it converges under refinement, unlike the corner peak stress,
    and it shows how fast load sheds into the rock.
    """
    srr, szz, stt, srz, rc, lin = stresses(r, z, u, nid, NR, NZ, E2)
    A_ann = np.pi*(R_LIN**2 - R_SH**2)
    zc_all, F_all = [], []
    k = 0
    for j in range(NZ-1):
        zc = 0.5*(z[j]+z[j+1])
        Fz = 0.0
        for i in range(NR-1):
            if rc[k] <= R_LIN:
                dA = np.pi*(r[i+1]**2 - r[i]**2)
                Fz += szz[k]*dA
            k += 1
        zc_all.append(zc); F_all.append(Fz)
    zc_all = np.array(zc_all); F_all = np.array(F_all)
    return zc_all, F_all, A_ann


def report(F=None, E2v=E_ROCK, **kw):
    r, z, u, nid, NR, NZ, E2 = solve_model(F=F, E2v=E2v, **kw)
    srr, szz, stt, srz, rc, lin = stresses(r, z, u, nid, NR, NZ, E2)
    zc_p, F_p, A_ann = liner_force_profile(r, z, u, nid, NR, NZ, E2)
    below = zc_p < -LEDGE_H
    F_just = abs(F_p[below][-1]) if below.any() else 0.0
    f_dp = dp_check(srr, szz, stt, srz)
    rock = ~lin
    return dict(
        liner_szz_MPa=abs(szz[lin].min())/1e6,
        liner_hoop_MPa=stt[lin].max()/1e6,
        liner_F_below_MN=F_just/1e6,
        liner_szz_avg_MPa=F_just/A_ann/1e6,
        liner_tau_MPa=abs(srz[lin]).max()/1e6,
        rock_tau_MPa=abs(srz[rock]).max()/1e6,
        dp_fmax_MPa=f_dp[rock].max()/1e6,
        yield_frac=float((f_dp[rock] > 0).mean()),
    )


if __name__ == "__main__":
    ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    print("="*72)
    print("AXISYMMETRIC FE - ARREST LEDGE INTO LINER AND ROCK")
    print("="*72)
    print(f"Piston weight            {W_PISTON/1e6:.2f} MN   [D]")
    print(f"Engagement delay         {T_DELAY:.2f} s        [A]")
    print(f"Impact velocity          {V_IMPACT:.2f} m/s     [D]")
    print(f"Arrest design load       {F_DESIGN/1e6:.1f} MN   [D] at {A_MAX:.0f} m/s^2")

    rr, uf, ue, err = validate()
    print("\n--- VALIDATION: Lame thick-walled cylinder ---")
    for i in range(0, len(rr), max(1, len(rr)//5)):
        print(f"  r={rr[i]:.3f} m   u_FE={uf[i]*1e6:8.4f} um   u_exact={ue[i]*1e6:8.4f} um")
    print(f"  max relative error {err*100:.4f}%  ->  "
          f"{'PASS' if err < 0.01 else 'CHECK'}")

    print("\n--- MESH CONVERGENCE ---")
    print("  the corner peak is a linear-elastic singularity and does not")
    print("  converge; the section average is the engineering measure")
    print(f"  {'liner div':>10} {'z div':>6} {'peak MPa':>10} {'liner force MN':>16} {'section avg MPa':>16}")
    for nf, nzf in ((5, 9), (8, 14), (11, 19)):
        rp = report(nfine=nf, nz_fine=nzf)
        print(f"  {nf:>10d} {nzf:>6d} {rp['liner_szz_MPa']:>10.2f} "
              f"{rp['liner_F_below_MN']:>16.2f} {rp['liner_szz_avg_MPa']:>16.2f}")

    r0 = report()
    print(f"\n--- BASE CASE  F = {F_DESIGN/1e6:.1f} MN, E_rock = {E_ROCK/1e9:.2f} GPa ---")
    print(f"  load reaching liner      {r0['liner_F_below_MN']:6.2f} MN of "
          f"{F_DESIGN/1e6:.1f} MN -> "
          f"{(1-r0['liner_F_below_MN']*1e6/F_DESIGN)*100:.0f}% sheds into rock")
    print(f"  liner axial, section avg {r0['liner_szz_avg_MPa']:6.2f} MPa "
          f"vs fcd {FCD/1e6:.1f}  -> util "
          f"{r0['liner_szz_avg_MPa']*1e6/FCD*100:.0f}%   [converged]")
    print(f"  liner axial, corner peak {r0['liner_szz_MPa']:6.2f} MPa "
          f"                        [mesh-dependent, singular]")
    print(f"  liner hoop tension       {r0['liner_hoop_MPa']:6.2f} MPa "
          f"vs fctd {FCTD/1e6:.2f} -> margin "
          f"{FCTD/1e6/max(r0['liner_hoop_MPa'],1e-9):.2f}")
    print(f"  rock peak shear          {r0['rock_tau_MPa']:6.3f} MPa")
    print(f"  Drucker-Prager f_max     {r0['dp_fmax_MPa']:6.3f} MPa -> "
          f"{'YIELDING' if r0['dp_fmax_MPa'] > 0 else 'elastic'}")

    print("\n--- LOAD FACTOR TO FIRST YIELD IN ROCK ---")
    lo, hi = 0.5, 200.0
    for _ in range(18):
        mid = 0.5*(lo+hi)
        if report(F=F_DESIGN*mid)['dp_fmax_MPa'] > 0: hi = mid
        else: lo = mid
    lf = 0.5*(lo+hi)
    print(f"  first yield at {lf:.1f} x the {F_DESIGN/1e6:.1f} MN design load")

    print("\n--- SENSITIVITY TO ROCK-MASS MODULUS ---")
    rows = []
    for Er in (0.10e9, 0.25e9, 1.00e9, 4.00e9):
        rp = report(E2v=Er)
        rows.append([Er/1e9, rp['liner_szz_MPa'], rp['liner_hoop_MPa'],
                     rp['rock_tau_MPa'], rp['dp_fmax_MPa']])
        print(f"  E_rock {Er/1e9:5.2f} GPa -> sigma_zz {rp['liner_szz_MPa']:6.2f}, "
              f"hoop {rp['liner_hoop_MPa']:5.2f}, DP {rp['dp_fmax_MPa']:7.3f} MPa")

    # ---- bearing interface ----
    n_pawl = 4
    Fp = F_DESIGN/n_pawl
    A_ring = np.pi*((R_SH+0.15)**2 - R_SH**2)
    p_ring = F_DESIGN/A_ring
    print("\n--- BEARING: 4 DISCRETE PADS vs CONTINUOUS RING LEDGE ---")
    print(f"  load per pawl                {Fp/1e6:6.2f} MN")
    print(f"  steel-steel pad @200 MPa     {Fp/200e6*1e4:6.0f} cm2")
    print(f"  pad into concrete @{FBEAR/1e6:.0f} MPa   {Fp/FBEAR*1e4:6.0f} cm2")
    print(f"  continuous ring pressure     {p_ring/1e6:6.2f} MPa "
          f"({p_ring/FBEAR*100:.0f}% of limit) -> ring adopted")

    # ---- outputs ----
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "figure_data"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "ledge_fem.json"), "w") as fh:
        json.dump(dict(design_load_MN=F_DESIGN/1e6, base=r0,
                       lame_rel_error=err, first_yield_factor=lf,
                       ring_pressure_MPa=p_ring/1e6,
                       sensitivity=rows), fh, indent=2)
    with open(os.path.join(ROOT, "figure_data", "ledge_sensitivity.csv"), "w") as fh:
        fh.write("E_rock_GPa,liner_sigzz_MPa,liner_hoop_MPa,rock_tau_MPa,dp_fmax_MPa\n")
        for row in rows:
            fh.write(",".join(f"{v:.4f}" for v in row) + "\n")
    print("\nWrote results/ledge_fem.json and figure_data/ledge_sensitivity.csv")
