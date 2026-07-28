"""
lca_resource.py

Abiotic resource-depletion extension of the carbon LCA: Wind+UGES storage medium
vs an LFP battery of equal 30-year service. Two metrics, different robustness:

  (1) ADP(elements), kg Sb-eq  -- FIRST-ORDER SYNTHESIS. Factors are from mixed
      LCIA methods (LFP EF2.0 per kWh-delivered; steel/concrete CML per mass), so
      the cross-system ratio is order-of-magnitude only. No published gravity-vs-
      battery element-depletion ratio exists; this is our construction, and it
      invites a harmonised single-method LCIA.
  (2) Critical-mineral mass, tonnes -- METHOD-INDEPENDENT, robust. Lithium and
      graphite are the clean differentiators: the UGES medium contains none.

Provenance:  [M] manuscript  [D] derived  [A] assumption  [L] literature (named)
Output: ../results/lca_resource.json
"""
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__)); _os.chdir(_HERE)
_sys.path.insert(0, _os.path.dirname(_HERE))
import common as C
import json
_os.makedirs("../results", exist_ok=True)

# ---- UGES bill of materials ([M]-derived, mirrors lca.py inventory) ----
steel_t = (120.0*1613.2064/1000 + 150.0*415.265/1000 + 76.0 + 350.0 + 15.59*36*1038/1000)
conc_m3 = 1613.2064 + 415.265 + 718.0/2.400

# ---- energy-service basis (same as carbon comparison) ----
DELIV_MWH_YR = 17337.5; YEARS = 30
deliv_kWh = DELIV_MWH_YR*1e3*YEARS
BESS_MWH  = C.DAILY_THROUGHPUT_MWH/0.90     # [M/A] 55.6 MWh nameplate for 50 MWh/day @90% DoD
BESS_BUILDS = 3                             # [L] 12-yr LFP life -> 3 builds/30 yr
cap_kWh_builds = BESS_MWH*1e3*BESS_BUILDS

# ---- (1) ADP(elements) kg Sb-eq  [method-mixed, flagged] ----
ADP_STEEL_PER_T = 0.0022    # [L] Burchart-Korol 2016 (CML); ~0, often <0 recycled
ADP_CONC_PER_M3 = 4.8e-3    # [L] SCM-concrete LCA midpoint 4.62-4.94e-3 kg Sb-eq/m3
ADP_LFP_PER_kWh = 4.8e-5    # [L] LFP EF2.0, per kWh delivered
adp_uges = steel_t*ADP_STEEL_PER_T + conc_m3*ADP_CONC_PER_M3
adp_bess = ADP_LFP_PER_kWh*deliv_kWh

# ---- (2) critical-mineral mass  [method-independent, robust] ----
GRAPHITE_kg_kWh=1.1; LI_kg_kWh=0.10; CU_kg_kWh=1.8    # [L] GREET-family order values
graphite_t=GRAPHITE_kg_kWh*cap_kWh_builds/1e3
li_t=LI_kg_kWh*cap_kWh_builds/1e3
cu_t=CU_kg_kWh*cap_kWh_builds/1e3

print(f"UGES BoM        : {steel_t:,.0f} t steel + {conc_m3*2.4:,.0f} t concrete")
print(f"ADP(elements)   : UGES ~{adp_uges:.0f} vs BESS ~{adp_bess:,.0f} kg Sb-eq "
      f"(~{adp_bess/adp_uges:,.0f}x, order-of-magnitude only)")
print(f"critical mineral: BESS graphite ~{graphite_t:.0f} t, Li ~{li_t:.0f} t, "
      f"cell-Cu ~{cu_t:.0f} t | UGES 0 of each")

json.dump(dict(
  steel_t=round(steel_t,0), concrete_m3=round(conc_m3,0), concrete_t=round(conc_m3*2.4,0),
  adp_uges_kgSbeq=round(adp_uges,1), adp_bess_kgSbeq=round(adp_bess,0),
  adp_ratio_order_of_magnitude=round(adp_bess/adp_uges,0),
  graphite_t=round(graphite_t,0), lithium_t=round(li_t,1), cell_copper_t=round(cu_t,0),
  bess_nameplate_MWh=round(BESS_MWH,1), bess_builds=BESS_BUILDS,
  functional_unit="30-yr firm storage service; UGES one build vs LFP 3 builds",
  robust_claim="critical-mineral mass (Li, graphite): UGES uses zero; method-independent",
  caveat="ADP ratio method-mixed (EF2.0 vs CML); order-of-magnitude own-synthesis; "
         "no published gravity-vs-battery depletion value"),
  open("../results/lca_resource.json","w"), indent=2)
print("wrote ../results/lca_resource.json")
