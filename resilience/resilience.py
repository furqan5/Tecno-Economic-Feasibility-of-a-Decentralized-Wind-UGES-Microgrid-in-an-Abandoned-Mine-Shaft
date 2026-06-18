"""
Strike-survivability and islanding-endurance model for the Jhimpir Wind-UGES paper.
Section IX-B. Pure NumPy + matplotlib. Deterministic (seeded).

Part 1 - Survivability: a salvo of M independent precision strikes is allocated
as evenly as possible across n storage nodes holding equal shares of a fixed
energy inventory. Per strike: an above-ground node's inventory is destroyed
with probability p_AG; a UGES node's surface headframe is disabled with the
same p_AG, but the stored inventory is destroyed only via shaft collapse,
probability p_sh << p_AG. Expected surviving inventory fraction:
    f = (1/n) * sum_i (1 - p)^{m_i},  m_i = strikes on node i (even split).
Monte Carlo adds percentile bands. p values are ILLUSTRATIVE, swept; the
claimed result is the structural ordering, not a point prediction.

Part 2 - Islanding endurance: full piston = 1.083 MWh (validated single-cycle
capacity). Hourly wind sampled from the site Weibull (k=2.6, c=8.1 at 100 m)
with AR(1) persistence rho=0.85 (Gaussian copula); simplified power curve of
one 2.5 MW Class II-A turbine (cut-in 3, rated 12, cut-out 25 m/s). Computes
P(72 h uninterrupted supply) for three representative critical loads, assuming
hoist and turbine remain functional (the survivability model covers the
inventory question).
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)

# ---------------- Part 1: strike survivability ----------------
def even_alloc(M, n):
    base, extra = divmod(M, n)
    return np.array([base + 1] * extra + [base] * (n - extra))

def exp_surv(M, n, p):
    """Closed-form expected surviving inventory fraction."""
    m = even_alloc(M, n)
    return float(np.mean((1.0 - p) ** m))

def mc_surv(M, n, p, trials=100_000):
    """Monte Carlo distribution of surviving fraction."""
    m = even_alloc(M, n)
    probs = (1.0 - p) ** m                      # per-node survival probability
    alive = rng.random((trials, n)) < probs     # Bernoulli node survival
    return alive.mean(axis=1)

p_AG, p_sh = 0.8, 0.05
Ms = np.arange(0, 11)
arch = {
    'AG-BESS, single site':      dict(n=1, p=p_AG, ls='--', c='#b22222'),
    'AG-BESS, 5 nodes':          dict(n=5, p=p_AG, ls='--', c='#e08214'),
    'UGES, single shaft':        dict(n=1, p=p_sh, ls='-',  c='#2166ac'),
    'UGES, 5 dispersed shafts':  dict(n=5, p=p_sh, ls='-',  c='#1a9850'),
}
print("== Survivability (reference p_AG=0.8, p_sh=0.05) ==")
for M in (1, 2, 4):
    vals = {k: exp_surv(M, a['n'], a['p']) for k, a in arch.items()}
    print(f" M={M}: " + " | ".join(f"{k}: {v*100:.1f}%" for k, v in vals.items()))

mc = mc_surv(2, 5, p_sh)
print(f" MC (M=2, UGES 5 nodes): mean {mc.mean()*100:.1f}%, 5th pct {np.percentile(mc,5)*100:.1f}%")
mc1 = mc_surv(2, 1, p_AG)
print(f" MC (M=2, AG single):    mean {mc1.mean()*100:.1f}%")

# robustness of ordering across the full sweep
ok = True
for pa in np.linspace(0.5, 0.95, 10):
    for ps in np.linspace(0.0, 0.2, 9):
        for M in range(1, 11):
            a = exp_surv(M, 1, pa); u1 = exp_surv(M, 1, ps); u5 = exp_surv(M, 5, ps)
            if not (a <= u1 + 1e-12 and u1 <= u5 + 1e-12):
                ok = False
print(" ordering AG<=UGES(1)<=UGES(5) robust across p_AG in [0.5,0.95], p_sh in [0,0.2]:", ok)

# ---------------- Part 2: islanding endurance ----------------
E_cap = 1.083          # MWh, validated full-piston single-cycle capacity
k, c, rho = 2.6, 8.1, 0.85
H, T = 72, 20_000      # 72 h horizon, MC trials

def ndtr(z):           # standard normal CDF without scipy
    from math import sqrt
    return 0.5 * (1.0 + erf_vec(z / np.sqrt(2.0)))

def erf_vec(x):        # Abramowitz-Stegun 7.1.26, max abs err 1.5e-7
    sign = np.sign(x); x = np.abs(x)
    a1,a2,a3,a4,a5,pp = 0.254829592,-0.284496736,1.421413741,-1.453152027,1.061405429,0.3275911
    t = 1.0/(1.0+pp*x)
    y = 1.0-((((a5*t+a4)*t+a3)*t+a2)*t+a1)*t*np.exp(-x*x)
    return sign*y

z = np.empty((T, H))
z[:, 0] = rng.standard_normal(T)
eps = rng.standard_normal((T, H))
for t in range(1, H):
    z[:, t] = rho * z[:, t-1] + np.sqrt(1 - rho**2) * eps[:, t]
u = np.clip(ndtr(z), 1e-9, 1 - 1e-9)
v = c * (-np.log(1.0 - u)) ** (1.0 / k)        # Weibull marginal via inverse CDF

def pcurve(v):
    return np.where(v < 3, 0.0,
           np.where(v < 12, 2.5 * (v**3 - 27.0) / (12**3 - 27.0),
           np.where(v <= 25, 2.5, 0.0)))

Pw = pcurve(v)
print(f"\n== Endurance (E={E_cap} MWh, 1 x 2.5 MW turbine, Weibull k={k}, c={c}, AR1 rho={rho}) ==")
print(f" mean wind power: {Pw.mean():.2f} MW (single-turbine CF {Pw.mean()/2.5*100:.1f}%)")

loads = [("Hospital, full critical", 0.5), ("Hospital, shed core", 0.10), ("Forward operating base", 1.5), ("Telecom node", 0.01)]
results = []
for name, L in loads:
    soc = np.full(T, E_cap)
    ok72 = np.ones(T, bool)
    for t in range(H):
        soc_new = soc + (Pw[:, t] - L)         # 1 h step, MWh
        ok72 &= soc_new >= 0.0                 # outage if demand unmet
        soc = np.clip(soc_new, 0.0, E_cap)
    auton = E_cap / L
    p72 = ok72.mean()
    results.append((name, L, auton, p72))
    print(f" {name:<24} L={L:>5.2f} MW | zero-wind autonomy {auton:6.1f} h | P(72 h) = {p72*100:5.1f}%")

# ---------------- Figure ----------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 4.6), dpi=300)
plt.rcParams['font.family'] = 'serif'
for kname, a in arch.items():
    ax1.plot(Ms, [exp_surv(M, a['n'], a['p']) * 100 for M in Ms],
             a['ls'], color=a['c'], lw=1.4, label=kname, marker='o', ms=2.5)
ax1.set_xlabel('Salvo size M (strikes)', fontsize=8)
ax1.set_ylabel('Expected surviving\nenergy inventory (%)', fontsize=8)
ax1.set_title('(a) Strike survivability  ($p_{AG}$=0.8, $p_{sh}$=0.05)', fontsize=8)
ax1.legend(fontsize=6.2, frameon=False)
ax1.tick_params(labelsize=7); ax1.grid(alpha=0.3, lw=0.4)
ax1.set_xlim(0, 10); ax1.set_ylim(0, 102)

names = [r[0] for r in results]; p72s = [r[3] * 100 for r in results]
autons = [r[2] for r in results]
bars = ax2.barh(names, p72s, color=['#2166ac', '#b22222', '#1a9850'], height=0.55)
for b, a_h in zip(bars, autons):
    ax2.text(b.get_width() + 1.5, b.get_y() + b.get_height()/2,
             f'{b.get_width():.0f}%  ({a_h:.1f} h calm buffer)', va='center', fontsize=6.2)
ax2.set_xlabel('P(72 h uninterrupted islanded supply) (%)', fontsize=8)
ax2.set_title('(b) Islanding endurance at 1.083 MWh + 2.5 MW turbine', fontsize=8)
ax2.tick_params(labelsize=7); ax2.set_xlim(0, 118)
ax2.grid(alpha=0.3, lw=0.4, axis='x')
plt.tight_layout()
plt.savefig('resilience_fig.png', bbox_inches='tight')
print("\nfigure saved: resilience_fig.png")
