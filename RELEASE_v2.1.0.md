# Release metadata for v2.1.0

## Tag

```
v2.1.0
```

Minor bump, not major. Every v2.0.0 result reproduces unchanged, no module or
entry point is removed, and no CSV or JSON contract changes. Four modules are
added. v2.0.0 was correctly a major bump because it changed headline numbers and
removed `gen_figs.py`; nothing here does either.

## Commit message

```
Add shaft arrest system and emergency discharge path

Gravitational storage holds energy in a suspended mass. The v2.0.0
survivability model counted buried inventory as surviving a surface strike,
but a strike that destroys the headframe also destroys the rope path holding
the piston: it falls 469 m and the whole charge dissipates in the shaft-bottom
dampers. That result was conditional on hardware that had not been specified.
This adds, sizes and verifies it, plus a discharge path that bypasses the
headframe.

arrest/arrest_anchorage.py       engagement dynamics against the 9-20 m/s2
    shaft safety-catch deceleration band, plus closed-form bearing, shear
    transfer and liner utilisation checks
arrest/ledge_fem.py              axisymmetric continuum FE of the ledge-liner
    -rock load path, reusing the 4-node ring formulation of
    settlement/settlement_fem.py; verified against the Lame thick-walled
    cylinder solution to 0.01%
arrest/jacking_recovery.py       in-shaft regenerative jacking discharge with
    Darcy-Weisbach line losses and Monte-Carlo conversion chain
resilience/survivability_arrest.py  survivability with the per-strike loss
    probability split into shaft collapse and arrest-system reliability

Results:
- arrest load 19-30 MN, fixed by the deceleration limit and independent of
  engagement delay; the delay sets the stroke only
- a continuous ring ledge holds bearing at 12.2 MPa, 15% of the EN 1992-1-1
  limit and 6.5x better than four discrete pads
- about 49% of the load sheds into the rock before reaching the liner, so the
  closed-form annulus check is conservative by roughly a factor of two
- liner hoop tension 0.66 MPa against 1.67 MPa is the closest check, margin 2.5
- rock stays elastic to 58x the design load
- recovery conversion 78% (P10-P90 76-80%), 0.99 MWh delivered, 9.9 h at a
  0.1 MW protected load, consistent with the 10.8 h calm buffer
- holding the 90% survivability headline needs arrest reliability >= 0.999,
  though a single shaft beats an above-ground battery for any R > 0.21

No new dependency: the continuum FE reuses numpy + scipy.sparse. Existing
modules, CSVs, JSONs and figures are unchanged. run_simulation.py registers the
four modules (16 -> 20); CITATION.cff and CHANGELOG.md updated.
```

## GitHub release description

```markdown
Closes a physical gap in the v2.0.0 resilience argument.

Gravitational storage holds energy in a **suspended** mass. A strike that
destroys the headframe also destroys the rope path holding the piston up, so
the piston falls 469 m and the entire charge is dissipated as heat in the
shaft-bottom dampers. The v2.0.0 survivability result was therefore conditional
on hardware that had not been specified. This release specifies, sizes and
verifies that hardware, and adds a discharge path that does not run through the
headframe.

### New modules

| Module | Purpose |
| ------ | ------- |
| `arrest/arrest_anchorage.py` | Engagement dynamics against the 9–20 m s⁻² shaft safety-catch band; bearing, shear and liner checks |
| `arrest/ledge_fem.py` | Axisymmetric continuum FE of the ledge–liner–rock path, verified against the Lamé solution |
| `arrest/jacking_recovery.py` | In-shaft regenerative jacking discharge, Darcy–Weisbach losses, Monte-Carlo chain |
| `resilience/survivability_arrest.py` | Survivability with arrest reliability separated from shaft geology |

### Results

- Arrest design load **19–30 MN**, set by the deceleration limit alone —
  engagement delay controls only the stroke.
- A **continuous ring ledge** holds bearing at 12.2 MPa, 15% of the
  EN 1992-1-1 limit and 6.5× better than four discrete pads.
- About **49% of the load sheds into the rock** before reaching the liner, so
  the closed-form annulus check is conservative by roughly a factor of two.
- **Liner hoop tension is the closest check** at 0.66 MPa against 1.67 MPa,
  margin 2.5. Rock stays elastic to 58× the design load.
- Recovery conversion **78% (P10–P90 76–80%)** → 0.99 MWh delivered, 9.9 h at
  a 0.1 MW protected load, consistent with the 10.8 h calm buffer.
- Holding the 90% survivability headline needs **R ≥ 0.999**, but the ordering
  is robust: a single shaft beats an above-ground battery for any `R > 0.21`.

### Verification

`arrest/ledge_fem.py` reproduces the Lamé thick-walled-cylinder solution to
within 0.01% and reports mesh convergence on every run. The peak stress at the
ledge corner is a linear-elastic singularity and is reported as such; the
converged quantity is the axial force resultant in the liner annulus.
`resilience/survivability_arrest.py` reproduces the v2.0.0 published figures
exactly at `R = 1` before extending them.

### Limitations

Linear elastic with a post-processed Drucker–Prager check: no plastic
redistribution beyond first yield, pawls smeared into an axisymmetric ring. No
arrestor of this capacity has been built and no in-shaft regenerative discharge
path has been demonstrated at 9.78 MN. Both remain open bottlenecks.

### Compatibility

Additive. **No new dependency** — the continuum FE reuses numpy + scipy.sparse.
Every v2.0.0 result reproduces unchanged.
```

## Git commands

```bash
git checkout -b feature/shaft-arrest
git add arrest/ resilience/survivability_arrest.py \
        run_simulation.py README.md CHANGELOG.md CITATION.cff requirements.txt \
        results/ figure_data/ figures/
git commit          # paste the commit message above
git push -u origin feature/shaft-arrest
# merge the PR, then:
git checkout main && git pull
git tag -a v2.1.0 -m "Shaft arrest system and emergency discharge"
git push origin v2.1.0
```

Publishing the GitHub release against `v2.1.0` triggers Zenodo to mint the new
version DOI if the webhook is enabled.
