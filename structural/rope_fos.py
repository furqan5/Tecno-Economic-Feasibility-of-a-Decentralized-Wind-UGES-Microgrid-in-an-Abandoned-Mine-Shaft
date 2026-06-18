"""
Wire-rope factor-of-safety calculation for the UGES multi-rope hoist.
First-principles, ISO 2408 / EN 12385-4 minimum breaking force.

Minimum breaking force of a stranded rope:
    MBF = K * d^2 * Rr           [N]   (d in mm, Rr in N/mm^2)
with K the fill+spinning factor (~0.330 for 6x36 IWRC) and Rr the rope grade.

Operating load = piston weight + rope self-weight (8 ... n ropes over 494 m),
shared across n ropes. FoS = total MBF / total operating load.

Finding: a single-piston 996.6 t mass over a 494 m shaft cannot reach the mine
code FoS of 6-7 with the originally stated 8 x 48 mm ropes (FoS ~ 1.2). A
multi-rope friction winder is required. The configuration below meets code.
"""
import numpy as np
g = 9.81
L = 494.0
m_piston = 996.6e3
W_piston = m_piston*g

K, Rr = 0.330, 1960          # ISO 2408 6x36 IWRC, grade 1960 MPa
mbf   = lambda d: K*d**2*Rr           # N, d in mm
rmass = lambda d: 0.00433*d**2        # kg/m, d in mm

def fos(n, d):
    W = W_piston + n*rmass(d)*L*g
    return n*mbf(d)/W, W

print("Operating load (piston only): %.2f MN" % (W_piston/1e6))
print("\nOriginal spec check:")
f, W = fos(8, 48)
print("  8 x 48 mm  -> total MBF %.1f MN, load %.2f MN, FoS %.2f  (below code 6-7)"
      % (8*mbf(48)/1e6, W/1e6, f))

print("\nCode-compliant multi-rope configuration:")
n, d = 36, 60
f, W = fos(n, d)
print("  %d x %d mm (grade %d, 6x36 IWRC) -> total MBF %.1f MN, load %.2f MN, FoS %.1f"
      % (n, d, Rr, n*mbf(d)/1e6, W/1e6, f))
print("  per-rope load %.0f kN; MBF/rope %.0f kN" % (W/n/1e3, mbf(d)/1e3))
Dsheave = 6.0
print("  D/d ratio with %.1f m sheave = %.0f (>=100 preferred for bending fatigue)"
      % (Dsheave, Dsheave*1000/d))
