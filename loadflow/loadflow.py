"""
Steady-state load-flow of the 50 MW Jhimpir Wind-UGES plant interconnection.
Steady-state load-flow model (pandapower, Newton-Raphson).

Topology (grounded in NTDC public data):
  - 50 MW wind farm (20 x 2.5 MW) collected on a 33 kV bus.
  - 5 MW UGES (PMSM + 4-quadrant AFE drive) on the same 33 kV collector bus,
    behind the meter, via a 6.6/33 kV 12 MVA unit transformer.
  - 33/132 kV, 63 MVA step-up at the plant grid station (Dy11).
  - ~6 km 132 kV double-circuit ACSR line (Lynx) to the 220/132 kV
    Jhimpir-II grid station, modelled as the slack (external grid).

Sources for topology / ratings:
  - NTDC Jhimpir-II is 220/132 kV with 3 x 250 MVA transformers; the 132 kV
    D/C line evacuates the 50 MW Indus, Liberty-1 and Liberty-2 plants
    (Business Recorder, 21 Jun 2023; Daily Times, 22 Feb 2022).
  - 132 kV NTDC lines use ACSR Lynx/Panther, ampacity ~420 A
    (Pakistan transmission conductor study, ResearchGate fig. 299624537).
Transformer reactances and line R/X are STANDARD ENGINEERING ESTIMATES for the
voltage/MVA class per IEC 60076 / typical NTDC practice (exact nameplate
impedances for these specific units are not public) - flagged in the paper.
"""
import pandapower as pp

def build(scenario):
    net = pp.create_empty_network(sn_mva=100)

    # ---- buses ----
    b_grid = pp.create_bus(net, vn_kv=132.0, name="Jhimpir-II 132 kV (grid)")
    b_hv   = pp.create_bus(net, vn_kv=132.0, name="Plant 132 kV bus")
    b_mv   = pp.create_bus(net, vn_kv=33.0,  name="33 kV collector bus")
    b_uges = pp.create_bus(net, vn_kv=6.6,   name="6.6 kV UGES bus")

    # ---- external grid = Jhimpir-II (slack) ----
    pp.create_ext_grid(net, b_grid, vm_pu=1.01, name="Jhimpir-II 220/132 kV")

    # ---- 132 kV D/C line, ~6 km, ACSR Lynx (per-circuit ~0.156 ohm/km R,
    #      ~0.41 ohm/km X, ~9.1 nF/km C); two parallel circuits ----
    pp.create_line_from_parameters(
        net, b_grid, b_hv, length_km=6.0,
        r_ohm_per_km=0.156/2, x_ohm_per_km=0.41/2, c_nf_per_km=9.1*2,
        max_i_ka=0.420*2, name="132 kV D/C ACSR Lynx")

    # ---- 33/132 kV, 63 MVA step-up (Dy11), ~12.5% impedance ----
    pp.create_transformer_from_parameters(
        net, b_hv, b_mv, sn_mva=63.0, vn_hv_kv=132.0, vn_lv_kv=33.0,
        vkr_percent=0.45, vk_percent=12.5, pfe_kw=35.0, i0_percent=0.08,
        shift_degree=330, name="63 MVA 132/33 kV Dy11")

    # ---- 6.6/33 kV, 12 MVA UGES unit transformer, ~8% impedance ----
    pp.create_transformer_from_parameters(
        net, b_mv, b_uges, sn_mva=12.0, vn_hv_kv=33.0, vn_lv_kv=6.6,
        vkr_percent=0.6, vk_percent=8.0, pfe_kw=8.0, i0_percent=0.1,
        shift_degree=0, name="12 MVA 33/6.6 kV UGES")

    # ---- wind farm: 50 MW at unity pf on the 33 kV bus (as generation) ----
    pp.create_sgen(net, b_mv, p_mw=50.0, q_mvar=0.0, name="50 MW wind farm")

    # ---- UGES on 6.6 kV bus ----
    if scenario == "charge":
        # motoring: draws 5.155 MW (load). AFE at unity pf.
        pp.create_load(net, b_uges, p_mw=5.155, q_mvar=0.0, name="UGES motor (charge)")
    elif scenario == "discharge":
        # generating: injects 5.0 MW. AFE at unity pf.
        pp.create_sgen(net, b_uges, p_mw=5.0, q_mvar=0.0, name="UGES generator (discharge)")

    pp.runpp(net, algorithm="nr", calculate_voltage_angles=True, init="dc")
    return net

def report(net, scenario):
    g = net.res_ext_grid.iloc[0]
    pcc = net.res_bus.loc[net.bus.index[net.bus.name=="Plant 132 kV bus"][0]]
    mv  = net.res_bus.loc[net.bus.index[net.bus.name=="33 kV collector bus"][0]]
    tx  = net.res_trafo.iloc[0]   # 63 MVA main
    line= net.res_line.iloc[0]
    p_grid = -g.p_mw   # ext_grid p_mw>0 = import; flip so + = export to grid
    print(f"\n===== SCENARIO: {scenario.upper()} =====")
    print(f"  Power to grid (132 kV)      : {p_grid:7.2f} MW")
    print(f"  PCC voltage (Plant 132 kV)  : {pcc.vm_pu*100:6.2f} %  ({pcc.vm_pu*132:6.2f} kV)")
    print(f"  33 kV collector bus voltage : {mv.vm_pu*100:6.2f} %  ({mv.vm_pu*33:6.2f} kV)")
    print(f"  Main 63 MVA xfmr loading    : {tx.loading_percent:6.2f} %")
    print(f"  132 kV line loading         : {line.loading_percent:6.2f} %")
    print(f"  Total losses (P)            : {net.res_line.pl_mw.sum()+net.res_trafo.pl_mw.sum():6.3f} MW")
    return p_grid, pcc.vm_pu*100, tx.loading_percent

print("="*60)
print("Jhimpir Wind-UGES interconnection - pandapower load flow")

print("="*60)
for sc in ("charge", "discharge"):
    net = build(sc)
    report(net, sc)


