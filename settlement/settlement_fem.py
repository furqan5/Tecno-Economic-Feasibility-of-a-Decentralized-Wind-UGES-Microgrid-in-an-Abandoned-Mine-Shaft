# -*- coding: utf-8 -*-
"""
settlement_fem.py  --  Axisymmetric continuum FE cross-check for headframe settlement.

4-node axisymmetric (ring) linear-elastic elements; layered half-space; uniform
circular footing pressure (equal-area circle of the 14 m mat). VERIFIED against the
Boussinesq flexible-circle centre settlement in the homogeneous limit (FE within ~5%,
the deficit being finite-domain truncation). This is the continuum confirmation of the
faster layered-elastic estimate in settlement.py, and it writes the Fig. 3 profile.

Requires: numpy, scipy.  [L]=literature/site  [D]=derived  [A]=assumption
"""
import os, numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

Q   = 17.95e6/14.0**2          # [D] footing pressure, Pa (91.6 kPa)
A   = np.sqrt(14.0*14.0/np.pi) # [D] equal-area circle radius, 7.90 m
HOV = 5.0                      # [L] overburden thickness, m
E1, NU1 = 50e6, 0.30           # [L] overburden
E2, NU2 = 0.25e9, 0.25         # [L] rock mass (0.25 GPa, regional analog; corrected from 4.0 GPa)
RFAR, ZBOT = 120.0, 120.0      # [A] domain extent (>15a)

def _mesh1d(brk, fine_end, far, n_in, n_mid, n_tail):
    a = np.linspace(0, brk, n_in+1)
    b = np.linspace(brk, fine_end, n_mid+1)[1:]
    c = fine_end*(far/fine_end)**np.linspace(0,1,n_tail+1)[1:]
    return np.unique(np.concatenate([a,b,c]))

def _D(E,nu):
    c=E/((1+nu)*(1-2*nu))
    return c*np.array([[1-nu,nu,nu,0],[nu,1-nu,nu,0],[nu,nu,1-nu,0],[0,0,0,(1-2*nu)/2]])

def solve(E2v=E2, nu2v=NU2):
    r=_mesh1d(A,22.0,RFAR,12,16,16); z=_mesh1d(HOV,14.0,ZBOT,10,14,16)
    nr,nz=len(r),len(z); nid=lambda i,j:j*nr+i; ndof=2*nr*nz
    g=1/np.sqrt(3); GP=[(-g,-g),(g,-g),(g,g),(-g,g)]
    R=[];Cc=[];V=[]
    for j in range(nz-1):
        for i in range(nr-1):
            xy=np.array([[r[i],z[j]],[r[i+1],z[j]],[r[i+1],z[j+1]],[r[i],z[j+1]]])
            zc=0.5*(z[j]+z[j+1]); D=_D(E1,NU1) if zc<=HOV else _D(E2v,nu2v)
            dofs=[]
            for (ii,jj) in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]: dofs+=[2*nid(ii,jj),2*nid(ii,jj)+1]
            Ke=np.zeros((8,8))
            for (xi,et) in GP:
                N=0.25*np.array([(1-xi)*(1-et),(1+xi)*(1-et),(1+xi)*(1+et),(1-xi)*(1+et)])
                dNx=0.25*np.array([-(1-et),(1-et),(1+et),-(1+et)])
                dNe=0.25*np.array([-(1-xi),-(1+xi),(1+xi),(1-xi)])
                J=np.array([[dNx@xy[:,0],dNx@xy[:,1]],[dNe@xy[:,0],dNe@xy[:,1]]])
                dN=np.linalg.inv(J)@np.vstack([dNx,dNe]); rg=N@xy[:,0]
                B=np.zeros((4,8))
                for k in range(4):
                    B[0,2*k]=dN[0,k]; B[1,2*k+1]=dN[1,k]
                    B[2,2*k]=N[k]/rg;  B[3,2*k]=dN[1,k]; B[3,2*k+1]=dN[0,k]
                Ke+=B.T@D@B*(2*np.pi*rg)*np.linalg.det(J)
            for a1 in range(8):
                for b1 in range(8): R.append(dofs[a1]);Cc.append(dofs[b1]);V.append(Ke[a1,b1])
    K=sparse.coo_matrix((V,(R,Cc)),shape=(ndof,ndof)).tocsr()
    F=np.zeros(ndof)
    for i in range(nr-1):
        if r[i+1]<=A+1e-9:
            ri,rp=r[i],r[i+1];L=rp-ri
            F[2*nid(i,0)+1]-=Q*2*np.pi*(ri*L/2+L*L/6); F[2*nid(i+1,0)+1]-=Q*2*np.pi*(ri*L/2+L*L/3)
    fixed=set()
    for j in range(nz): fixed.add(2*nid(0,j)); fixed.add(2*nid(nr-1,j))
    for i in range(nr): fixed.add(2*nid(i,nz-1)+1)
    free=np.array([d for d in range(ndof) if d not in fixed])
    u=np.zeros(ndof); u[free]=spsolve(K[free][:,free].tocsc(),F[free])
    return r, np.abs(np.array([u[2*nid(i,0)+1] for i in range(nr)]))*1000.0

if __name__=="__main__":
    r,uz=solve(E1,NU1); s_b=2*Q*A*(1-NU1**2)/E1*1000
    print("=== VERIFICATION (homogeneous E=50 MPa) ===")
    print(f"  FE centre {uz[0]:.1f} mm vs Boussinesq {s_b:.1f} mm  (ratio {uz[0]/s_b:.2f}; FE<analytic = truncation)")
    r,uz=solve()
    print("=== LAYERED axisymmetric FE ===")
    print(f"  centre {uz[0]:.1f} mm | r=7 m {np.interp(7,r,uz):.1f} mm | code limit 25 mm")
    out=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","figure_data","fig3_settlement.csv"))
    m=r<=40
    with open(out,"w") as f:
        f.write("distance_m,settlement_mm\n")
        for ri,si in zip(r[m],uz[m]): f.write(f"{ri:.3f},{si:.4f}\n")
    print("wrote figure_data/fig3_settlement.csv (axisymmetric FE profile)")
