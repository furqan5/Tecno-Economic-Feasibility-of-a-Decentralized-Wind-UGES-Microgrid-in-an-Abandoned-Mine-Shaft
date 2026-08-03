"""Consolidated figure generator. Single source of truth - supersedes gen_figs.py
for Figs 1, 2, 3 so corrected versions cannot be overwritten by a stale script."""
import numpy as np, csv, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
FIG='wind-uges/figures/'
MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# ================= Fig 1: measured wind, Jhimpir 80 m (Khan et al. 2021) ==========
V80=np.array([4.97,5.18,5.39,6.48,8.10,8.28,9.07,8.08,6.82,5.03,4.77,5.03])
vmin=np.array([4.28,4.36,5.12,6.09,7.19,6.91,8.46,6.94,6.10,4.46,4.07,4.07])
vmax=np.array([5.59,6.18,5.62,6.97,9.44,9.22,9.46,9.05,7.99,5.66,5.77,6.47])
fig,ax=plt.subplots(figsize=(7.4,4.0)); x=np.arange(12)
ax.fill_between(x,vmin,vmax,color='#c6dbef',alpha=.85,label='yearly range, 2015\u20132018')
ax.plot(x,V80,'o-',color='#08519c',lw=2,ms=5,label='monthly mean, 80 m')
ax.axhline(6.50,color='#e6550d',ls='--',lw=1.3)
ax.text(0.12,6.72,'annual mean 6.50 m s$^{-1}$   (Weibull $k$ = 2.17, $c$ = 7.48 m s$^{-1}$)',
        fontsize=8.5,color='#c0430a')
ax.axvspan(3.5,8.5,color='#fff3cc',alpha=.55,zorder=0)
ax.text(6,10.55,'SW monsoon',ha='center',fontsize=8.5,color='#8a6d0b')
ax.set_xticks(x); ax.set_xticklabels(MON)
ax.set_ylabel('mean wind speed (m s$^{-1}$)'); ax.set_ylim(0,11.4); ax.set_xlim(-.5,11.5)
ax.legend(fontsize=8.5,loc='lower center',ncol=2,framealpha=.95)
ax.grid(alpha=.25,ls=':')
plt.tight_layout(); plt.savefig(FIG+'fig1_wind.png',dpi=155,bbox_inches='tight'); plt.close()

# ================= Fig 2: layout + wind rose (E/SE prevailing, Khan Table 9) ======
fig=plt.figure(figsize=(10.4,4.2))
ax1=fig.add_subplot(1,2,1)
D=.100; sx=sy=7*D; xs=[];ys=[]
for r in range(4):
    for c in range(5):
        xs.append(c*sx+(.5*sx if r%2 else 0)); ys.append(r*sy)
xs=np.array(xs[:20]); ys=np.array(ys[:20])
ax1.scatter(xs,ys,s=130,marker='1',color='#08519c',linewidths=2,zorder=3)
for i in range(20): ax1.add_patch(plt.Circle((xs[i],ys[i]),D*.5,fill=False,ec='#9ecae1',lw=.8))
ax1.annotate('',xy=(.06,.22),xytext=(.34,.08),xycoords='axes fraction',
             arrowprops=dict(arrowstyle='-|>',color='#e6550d',lw=2.4))
ax1.text(.36,.05,'prevailing E\u2013SE wind (72% of hours)',transform=ax1.transAxes,
         fontsize=8.5,color='#c0430a',ha='left')
ax1.set_xlabel('west\u2013east (km)'); ax1.set_ylabel('south\u2013north (km)')
ax1.set_title('(a) 50 MW layout: 20 \u00d7 2.5 MW, 7D \u00d7 7D',fontsize=10)
ax1.set_aspect('equal'); ax1.grid(alpha=.25,ls=':'); ax1.margins(.16)
ax2=fig.add_subplot(1,2,2,projection='polar')
pct=[10.61,8.29,38.52,33.24,3.23,3.25,1.65,1.22]
ang=np.deg2rad([90,45,0,-45,-90,-135,180,135])
ax2.set_theta_zero_location('E'); ax2.set_theta_direction(1)
ax2.bar(ang,pct,width=.62,color='#3182bd',edgecolor='white',alpha=.92)
ax2.set_xticks(ang); ax2.set_xticklabels(['N','NE','E','SE','S','SW','W','NW'],fontsize=9)
ax2.set_ylim(0,42); ax2.set_yticks([10,20,30,40]); ax2.tick_params(labelsize=7)
ax2.set_title('(b) Directional frequency (% of hours)',fontsize=10,pad=16)
plt.tight_layout(); plt.savefig(FIG+'fig2_layout.png',dpi=155,bbox_inches='tight'); plt.close()
print('Figs 1 and 2 regenerated (Jhimpir 80 m; E-SE wind rose)')

# ================= Fig 3: settlement, legend clear of the code line ==============
import importlib.util,sys,os
sys.path.insert(0,'/home/claude/pkg'); _cwd=os.getcwd(); os.chdir('/home/claude/pkg/settlement')
spec=importlib.util.spec_from_file_location('sfem','settlement_fem.py'); sm=importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(sm)
except SystemExit: pass
r,w=sm.solve(); _,w_stiff=sm.solve(E2v=0.5e9); _,w_soft=sm.solve(E2v=0.1e9)
os.chdir(_cwd)
fig,ax=plt.subplots(figsize=(7.4,4.0))
ax.fill_between(r,w_stiff,w_soft,color='#c6dbef',alpha=.7,
                label='modulus band, $E$ = 0.5\u20130.1 GPa (9.2\u201316.5 mm)')
ax.plot(r,w,'-',color='#08519c',lw=2.2,label='axisymmetric FE, $E$ = 0.25 GPa')
ax.axhline(25,color='#cc0000',ls='--',lw=1.5)
ax.text(2,23.4,'code allowable, 25 mm',color='#cc0000',fontsize=9,va='top')
ax.annotate('peak %.1f mm'%w.max(),xy=(0,w.max()),xytext=(17,w.max()+2.6),fontsize=9.5,
            color='#08519c',arrowprops=dict(arrowstyle='->',color='#08519c',lw=1.1))
ax.set_xlim(0,110); ax.set_ylim(0,28)
ax.set_xlabel('radial distance from footing centre (m)')
ax.set_ylabel('surface settlement (mm)')
ax.legend(fontsize=8.5,loc='center right',framealpha=.95)   # clear of the 25 mm line
ax.grid(alpha=.25,ls=':')
plt.tight_layout(); plt.savefig('/home/',dpi=155,bbox_inches='tight'); plt.close()

# ================= Fig 6: structural FoS, legend off the long bar ================
rows=list(csv.reader(open('pkg/figure_data/fig6_structural.csv')))[1:]
comp=[x[0] for x in rows]; fos=[float(x[1]) for x in rows]; fmin=[float(x[2]) for x in rows]
fig,ax=plt.subplots(figsize=(7.6,3.9)); y=np.arange(len(comp))
ax.barh(y,fos,color='#2b8cbe',label='achieved factor of safety')
ax.barh(y,fmin,color='none',edgecolor='#e6550d',hatch='///',lw=1.2,label='code minimum')
for i,v in enumerate(fos): ax.text(v*1.06,i,('%g'%v),va='center',fontsize=8)
ax.set_xscale('log'); ax.set_xlim(1,4000)
ax.set_yticks(y); ax.set_yticklabels(comp,fontsize=8); ax.invert_yaxis()
ax.set_xlabel('factor of safety (log scale)')
ax.legend(fontsize=8,loc='upper right',framealpha=.95)      # top row bar is short
ax.grid(alpha=.25,ls=':',axis='x')
plt.tight_layout(); plt.savefig(FIG+'fig6_structural.png',dpi=155,bbox_inches='tight'); plt.close()

# ================= Fig 11: survivability, legend in the empty mid-band ===========
ra=list(csv.reader(open('pkg/figure_data/fig7a_survivability.csv')))[1:]
M=[int(x[0]) for x in ra]; AG1=[float(x[1]) for x in ra]; AG5=[float(x[2]) for x in ra]
UG1=[float(x[3]) for x in ra]; UG5=[float(x[4]) for x in ra]
rb=list(csv.reader(open('pkg/figure_data/fig7b_islanding.csv')))[1:]
lbl=[x[0] for x in rb]; P72=[float(x[1]) for x in rb]
fig,ax=plt.subplots(1,2,figsize=(10.2,3.9))
ax[0].plot(M,AG1,'o-',color='#d62728',lw=1.6,label='above-ground BESS, 1 site')
ax[0].plot(M,AG5,'s--',color='#fb9a99',lw=1.4,label='above-ground, 5 sites')
ax[0].plot(M,UG1,'^-',color='#2b8cbe',lw=1.6,label='UGES shaft, 1 site')
ax[0].plot(M,UG5,'D--',color='#31a354',lw=1.6,label='UGES, 5 dispersed shafts')
ax[0].set_xlabel('salvo size (successful strikes)'); ax[0].set_ylabel('surviving inventory (%)')
ax[0].set_title('(a) Expected surviving energy vs salvo size',fontsize=10)
ax[0].set_ylim(0,105); ax[0].grid(alpha=.25,ls=':')
ax[0].legend(fontsize=7.5,loc='center left',bbox_to_anchor=(0.02,0.40),framealpha=.95)
yb=np.arange(len(lbl))
ax[1].barh(yb,P72,color='#2b8cbe')
ax[1].set_yticks(yb); ax[1].set_yticklabels(lbl,fontsize=8); ax[1].invert_yaxis()
for i,v in enumerate(P72):
    inside = v>85
    ax[1].text(v-2 if inside else v+1.5, i, '%.1f%%'%v, va='center', fontsize=8,
               ha='right' if inside else 'left', color='white' if inside else 'black')
ax[1].set_xlabel('P(72 h islanding survival) (%)')
ax[1].set_title('(b) Islanding endurance by load class',fontsize=10)
ax[1].set_xlim(0,108); ax[1].grid(alpha=.25,ls=':',axis='x')
plt.tight_layout(); plt.savefig(FIG+'fig7_survivability.png',dpi=155,bbox_inches='tight'); plt.close()
print('Figs 3, 6, 11 regenerated with legends clear of data')
