"""
02_feasibility_maps.py

Converts the single-site study into a TRANSFERABLE screening method via
dimensionless groups, and renders feasibility maps over shaft depth, piston
mass, and wind capacity factor. Directly answers the "one site = case study"
objection: Jhimpir becomes the worked example of a general method.

Dimensionless / derived groups
  E_cyc(h,m)   = m g h_stroke eta_RT / 3.6e9         [MWh/cycle]
  N_max(h)     = floor(T_day / t_cycle),  t_cycle = 2 h_stroke / v_hoist
  Q_day(h,m)   = N_max * E_cyc  (throughput capacity, power/kinematics limited) [MWh/day]
  Gamma        = Q_day / E_curtailed_day             (storage-adequacy ratio, -)
  N_c          = E_target_day / E_cyc                (required cycles for a target)
"""
import numpy as np, json, os
os.makedirs("../results", exist_ok=True); os.makedirs("../figures", exist_ok=True)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C

G, ETA, V = C.G, C.ETA_RT, C.V_HOIST_MS
PISTON_H = C.H_PISTON_M
T_DAY = 24*3600.0

def e_cycle_mwh(h_depth, m_kg):
    stroke = np.maximum(h_depth - PISTON_H, 1.0)
    return m_kg * G * stroke * ETA / 3.6e9

def n_max_cycles(h_depth):
    stroke = np.maximum(h_depth - PISTON_H, 1.0)
    t_cycle = 2*stroke / V
    return np.floor(T_DAY / t_cycle)

def q_day_mwh(h_depth, m_kg):
    return n_max_cycles(h_depth) * e_cycle_mwh(h_depth, m_kg)

# --- design-point group values ----------------------------------------------
h0, m0 = C.H_SHAFT_M, C.M_PISTON_KG
print("=== DIMENSIONLESS GROUPS AT DESIGN POINT (Jhimpir) ===")
print(f"E_cyc(494 m, 996.6 t)     : {e_cycle_mwh(h0,m0):.3f} MWh (manuscript 1.083)")
print(f"N_max(494 m)              : {n_max_cycles(h0):.0f} cycles/day (manuscript ~46)")
print(f"Q_day(494 m, 996.6 t)     : {q_day_mwh(h0,m0):.1f} MWh/day (manuscript 50)")

# --- grids ------------------------------------------------------------------
H = np.linspace(100, 1000, 220)      # shaft depth, m
M = np.linspace(200, 3000, 220)*1e3  # piston mass, kg
HH, MM = np.meshgrid(H, M)
ECY = e_cycle_mwh(HH, MM)
QDY = q_day_mwh(HH, MM)

# Table-I cutoffs [M]: depth>300 m; (diameter>=4 m handled separately)
DEPTH_CUT = 300.0
TARGET_DAY = C.DAILY_THROUGHPUT_MWH   # 50 MWh/day feasibility contour

fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))

# Panel A: energy per cycle
cs = axs[0].contourf(H, M/1e3, ECY, levels=18, cmap="viridis")
axs[0].contour(H, M/1e3, ECY, levels=[1.083], colors="w", linewidths=2)
axs[0].axvline(DEPTH_CUT, color="r", ls="--", lw=1.2)
axs[0].plot(h0, m0/1e3, "r*", ms=15, mec="k")
axs[0].set_xlabel("Shaft depth (m)"); axs[0].set_ylabel("Piston mass (t)")
axs[0].set_title("(a) Energy per cycle (MWh)\nwhite = 1.083 MWh design contour")
fig.colorbar(cs, ax=axs[0], shrink=0.85)

# Panel B: daily throughput capacity + 50 MWh/day feasibility
cs2 = axs[1].contourf(H, M/1e3, QDY, levels=18, cmap="magma")
axs[1].contour(H, M/1e3, QDY, levels=[TARGET_DAY], colors="cyan", linewidths=2)
axs[1].axvline(DEPTH_CUT, color="r", ls="--", lw=1.2)
axs[1].plot(h0, m0/1e3, "c*", ms=15, mec="k")
axs[1].set_xlabel("Shaft depth (m)"); axs[1].set_ylabel("Piston mass (t)")
axs[1].set_title(f"(b) Throughput capacity (MWh/day)\ncyan = {TARGET_DAY:.0f} MWh/day feasibility")
fig.colorbar(cs2, ax=axs[1], shrink=0.85)

# Panel C: storage-adequacy Gamma over depth x daily curtailed energy
CURT = np.linspace(5, 120, 220)            # daily curtailed wind available, MWh/day
HH2, CC = np.meshgrid(H, CURT)
QD_ref = q_day_mwh(HH2, m0)                 # at reference piston mass
GAMMA = QD_ref / CC
lv = [0.25,0.5,1.0,2.0,4.0]
cs3 = axs[2].contourf(H, CURT, np.clip(GAMMA,0,4), levels=20, cmap="cividis")
cc3 = axs[2].contour(H, CURT, GAMMA, levels=[1.0], colors="w", linewidths=2)
axs[2].axvline(DEPTH_CUT, color="r", ls="--", lw=1.2)
axs[2].set_xlabel("Shaft depth (m)"); axs[2].set_ylabel("Daily curtailed wind (MWh/day)")
axs[2].set_title("(c) Storage-adequacy $\\Gamma$ (m=996.6 t)\nwhite = $\\Gamma$=1 (store matches curtailment)")
fig.colorbar(cs3, ax=axs[2], shrink=0.85)

plt.tight_layout(); plt.savefig("../figures/fig_feasibility_maps.png", dpi=150); plt.close()

json.dump({"E_cyc_design_MWh":round(float(e_cycle_mwh(h0,m0)),3),
           "N_max_design":int(n_max_cycles(h0)),
           "Q_day_design_MWh":round(float(q_day_mwh(h0,m0)),1),
           "depth_cutoff_m":DEPTH_CUT,"target_day_MWh":TARGET_DAY,
           "groups":["E_cyc=m g h_stroke eta/3.6e9","N_max=floor(T/t_cycle)",
                     "Q_day=N_max*E_cyc","Gamma=Q_day/E_curtailed","N_c=E_target/E_cyc"]},
          open("../results/feasibility_groups.json","w"), indent=2)
print("Wrote figures/fig_feasibility_maps.png")
