import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
from scipy.optimize import curve_fit
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, age_of, GEN = ns['fwd'], ns['age_of'], ns['GEN']
btc = ns['btc']; p, idx = btc.values, btc.index
A = age_of(idx, GEN['BTC']) / 365.25; T = len(p) - 1
x, y = np.log(A), np.log(p)
X = np.column_stack([np.ones_like(x), x]); bhat = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ bhat
n = len(y); XtXi = np.linalg.inv(X.T @ X)
def nw(L):
    S = (X * e[:, None]).T @ (X * e[:, None])
    for l in range(1, L + 1):
        w = 1 - l / (L + 1); G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None]); S += w * (G + G.T)
    return np.sqrt((XtXi @ S @ XtXi)[1, 1])
print('beta %.3f, OLS se %.3f' % (bhat[1], np.sqrt(e @ e / (n - 2) * XtXi[1, 1])))
for L in (12, 24, 48, 60):
    se = nw(L); lo, hi = bhat[1] - 1.96 * se, bhat[1] + 1.96 * se
    r5 = lambda b: (1 + 5 / A[T]) ** (b / 5) - 1; r1 = lambda b: (1 + 1 / A[T]) ** b - 1
    print(f'NW lag {L}: se {se:.3f}, 95% CI beta {lo:.2f}-{hi:.2f}, 5y c {100*r5(lo):.1f}-{100*r5(hi):.1f}%, 1y c {100*r1(lo):.1f}-{100*r1(hi):.1f}%')
# residual persistence
print('resid AR1 %.3f' % np.corrcoef(e[1:], e[:-1])[0, 1])
# ex post functional forms for forward log growth (periods from 2012)
mask = np.array([t >= pd.Period('2012-01', 'M') for t in idx]); tt = np.arange(len(p)) / 12.0
for h in (3, 4, 5):
    g = fwd(p, 12 * h); ok = mask & ~np.isnan(g)
    yy = np.log(1 + g[ok]); xh = np.log(1 + h / A[ok]) / h
    k = (xh @ yy) / (xh @ xh); sse_h = ((yy - k * xh) ** 2).sum()
    f = lambda s, a, b: np.exp(a + b * s)
    (a, b), _ = curve_fit(f, tt[ok] + h / 2, yy, p0=(0, -0.15), maxfev=20000); sse_e = ((yy - f(tt[ok] + h / 2, a, b)) ** 2).sum()
    # hyperbolic with free exponent on age: c*A^-d (2 params) for comparison
    f2 = lambda Av, c0, d: c0 * Av ** (-d)
    (c0, d), _ = curve_fit(f2, A[ok] + h / 2, yy, p0=(5, 1), maxfev=20000); sse_2 = ((yy - f2(A[ok] + h / 2, c0, d)) ** 2).sum()
    sst = ((yy - yy.mean()) ** 2).sum()
    print(f'h={h}: hyperbolic k/A (1 param) k={k:.2f} R2={1-sse_h/sst:.2f} | exponential in time (2 params) half-life={np.log(2)/-b:.1f}y R2={1-sse_e/sst:.2f} | c0*A^-d (2 params) d={d:.2f} R2={1-sse_2/sst:.2f}')
