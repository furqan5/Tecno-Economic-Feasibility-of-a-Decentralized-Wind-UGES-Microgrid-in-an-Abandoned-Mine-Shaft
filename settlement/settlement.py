"""
Surface-settlement analysis for the UGES headframe foundation (OpenSeesPy).
Plane-strain FE model with the site material set:
  Overburden : Mohr-Coulomb, E'=50 MPa, nu=0.30, gamma=20 kN/m3, c'=5 kPa, phi'=28 deg, ~5 m.
  Rock mass  : sandstone-shale (Hoek-Brown-derived MC continuum), E_rm=4.0 GPa, nu=0.25.
  Liner      : elastic concrete ring, E=30 GPa, nu=0.20, t=0.20 m, around the 2.5 m shaft.
Footing applies the 17.95 MN headframe load (14 m square mat, q=91.6 kPa).
Maximum surface settlement read at the footing centre.
"""
import openseespy.opensees as ops
import numpy as np

def run(q_kpa,B,Wd=40.0,Hd=40.0,nx=40,ny=40,
        E_over=50e3,nu_over=0.30,g_over=20.0,c_over=5.0,phi_over=28.0,h_over=5.0,
        E_rock=4.0e6,nu_rock=0.25,g_rock=25.0,c_rock=200.0,phi_rock=35.0,
        E_liner=30e6,nu_liner=0.20,g_liner=25.0,t_liner=0.20,r_shaft=2.5,profile=False):
    ops.wipe(); ops.model('basic','-ndm',2,'-ndf',2)
    dx,dy=Wd/nx,Hd/ny
    nid=lambda i,j:j*(nx+1)+i+1
    for j in range(ny+1):
        for i in range(nx+1): ops.node(nid(i,j),i*dx,-j*dy)
    for i in range(nx+1): ops.fix(nid(i,ny),1,1)
    for j in range(ny):
        ops.fix(nid(0,j),1,0); ops.fix(nid(nx,j),1,0)
    def mc(tag,E,nu,g,c,phi):
        rho=g/9.81;G=E/(2*(1+nu));K=E/(3*(1-2*nu))
        ops.nDMaterial('PressureIndependMultiYield',tag,2,rho,G,K,c,0.1,0.0,phi,0.0,20)
    mc(1,E_over,nu_over,g_over,c_over,phi_over)
    mc(2,E_rock,nu_rock,g_rock,c_rock,phi_rock)
    ops.nDMaterial('ElasticIsotropic',3,E_liner,nu_liner,g_liner/9.81)
    j_int=int(round(h_over/dy))
    i_lo=int(np.floor(r_shaft/dx)); i_hi=int(np.ceil((r_shaft+t_liner)/dx))
    for j in range(ny):
        for i in range(nx):
            tag=3 if i_lo<=i<i_hi else (1 if j<j_int else 2)
            ops.element('quad',j*nx+i+1,nid(i,j),nid(i+1,j),nid(i+1,j+1),nid(i,j+1),1.0,'PlaneStrain',tag)
    for t in (1,2): ops.updateMaterialStage('-material',t,'-stage',0)
    ops.timeSeries('Linear',1); ops.pattern('Plain',1,1)
    for j in range(ny):
        for i in range(nx):
            g=g_over if j<j_int else g_rock
            ops.eleLoad('-ele',j*nx+i+1,'-type','-selfWeight',0.0,-g,0.0)
    ops.system('BandGeneral');ops.numberer('RCM');ops.constraints('Transformation')
    ops.test('NormDispIncr',1e-4,50);ops.algorithm('Newton')
    ops.integrator('LoadControl',0.1);ops.analysis('Static');ops.analyze(10)
    ops.loadConst('-time',0.0)
    for t in (1,2): ops.updateMaterialStage('-material',t,'-stage',1)
    nfoot=max(1,int(round(B/dx)))
    ops.timeSeries('Linear',2);ops.pattern('Plain',2,2)
    for i in range(nfoot+1):
        trib=dx if(0<i<nfoot)else dx/2
        ops.load(nid(i,0),0.0,-q_kpa*trib)
    ops.test('NormDispIncr',1e-3,100);ops.algorithm('Newton')
    ops.integrator('LoadControl',0.05);ops.analyze(20)
    s=abs(ops.nodeDisp(nid(0,0),2))*1000.0
    if profile:
        xs=[i*dx for i in range(nx+1)];ss=[abs(ops.nodeDisp(nid(i,0),2))*1000.0 for i in range(nx+1)]
        return s,xs,ss
    return s

if __name__=='__main__':
    P=17.95e3;foot_side=14.0;q=P/foot_side**2
    s,xs,ss=run(q_kpa=q,B=foot_side/2,profile=True)
    print(f"Footing bearing pressure q = {q:.1f} kPa")
    print(f"OpenSeesPy max surface settlement = {s:.2f} mm")
    print(f"Within 25 mm code limit: {'yes' if s<25 else 'no'}")
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.family']='serif'
    fig,ax=plt.subplots(figsize=(3.6,2.4),dpi=300)
    ax.plot(xs,ss,'-',color='#2166ac',lw=1.6); ax.fill_between(xs,ss,alpha=0.12,color='#2166ac')
    ax.axhline(25.0,ls=':',color='k',lw=0.9,label='Code limit: 25 mm')
    ax.scatter([0],[s],color='#1a9850',zorder=5,s=18,label=f'Max settlement: {s:.1f} mm')
    ax.invert_yaxis(); ax.set_xlabel('Distance from footing centre (m)',fontsize=8)
    ax.set_ylabel('Surface settlement (mm)',fontsize=8)
    ax.legend(fontsize=6.2,frameon=False,loc='lower right'); ax.tick_params(labelsize=7); ax.grid(alpha=0.3,lw=0.4)
    plt.tight_layout()
    plt.savefig('fig_settlement.tiff',dpi=300,format='tiff',pil_kwargs={'compression':'tiff_lzw'},bbox_inches='tight')
    print("Fig 3 updated, max =",round(s,1),"mm")
