"""Bitcoin cost-of-capital formulas: real-time power-law exponent beta_t (ln(1+c) ~ beta/age), exponential-slowdown
parameters and half-life, ex post check of the hyperbolic form, and projections.
Usage: python3 -I btc_formula.py DATA_DIR OUT_DIR   (reuses functions from section5.py in the same folder)"""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, age_of, GEN = ns['fwd'], ns['age_of'], ns['GEN']
btc = ns['btc']; p, idx = btc.values, btc.index
A = age_of(idx, GEN['BTC']) / 365.25          # age in years
T = len(p) - 1
lp = np.log(p)

def beta_at(t):
    b, a = np.polyfit(np.log(A[:t + 1]), lp[:t + 1], 1); return b, a

rows = []
for t in range(36, T + 1):
    b, a = beta_at(t)
    rows.append(dict(month=str(idx[t]), age=A[t], beta=b, inst=np.exp(b / A[t]) - 1,
                     h5=(1 + 5 / A[t]) ** (b / 5) - 1, h3=(1 + 3 / A[t]) ** (b / 3) - 1))
B = pd.DataFrame(rows)
print('real-time beta, January of each year:')
print(B[B.month.str.endswith('-01') | (B.month == str(idx[T]))].round(3).to_string(index=False))
sub = B[B.month >= '2015-01']; print('beta range since 2015: %.2f-%.2f' % (sub.beta.min(), sub.beta.max()))
sub = B[B.month >= '2018-01']; print('beta range since 2018: %.2f-%.2f' % (sub.beta.min(), sub.beta.max()))
B.to_csv(f'{OUT}/btc_beta_realtime.csv', index=False)

# exponential slowdown parameters today (4-year window, months as time unit in code)
def ed_params(t, L=48, min_obs=24):
    gL = np.full(len(p), np.nan); gL[L:] = (lp[L:] - lp[:-L]) * 12 / L
    s_ = np.arange(len(p)); v = gL[:t + 1]; ok = ~np.isnan(v) & (v > 0)
    b, a = np.polyfit(s_[:t + 1][ok], np.log(v[ok]), 1); return a, b
for L in (36, 48, 60):
    a, b = ed_params(T, L)
    g_now = np.exp(a + b * T)
    print(f'ED L={L//12}y: current trend log growth {g_now:.3f} (simple {np.exp(g_now)-1:.3f}), half-life {np.log(2)/(-b)/12:.2f} years')
# half-life over time (4-year window)
hl = []
for t in range(48 + 24, T + 1):
    try:
        a, b = ed_params(t); hl.append((str(idx[t]), np.log(2) / (-b) / 12))
    except Exception: pass
H = pd.DataFrame(hl, columns=['month', 'half_life']); print(H[H.month.str.endswith('-01')].round(2).to_string(index=False))

# ex post check: regress realized forward log growth on ln(1+h/A)/h (no intercept) -> k (beta if the power law held exactly)
for h in (3, 4, 5):
    g = fwd(p, 12 * h); ok = ~np.isnan(g) & (np.array([t >= pd.Period('2012-01', 'M') for t in idx]))
    y = np.log(1 + g[ok]); x = np.log(1 + h / A[ok]) / h
    k = (x @ y) / (x @ x); res = y - k * x
    r2 = 1 - (res @ res) / ((y - y.mean()) @ (y - y.mean()))
    print(f'h={h}: ex post k = {k:.2f}, R2 (vs mean) = {r2:.2f}, n = {ok.sum()}')

# projections with today's beta and ED parameters
bT, _ = beta_at(T); aT, bT_ed = ed_params(T)
print('\nprojection (beta=%.2f; ED half-life %.2f y):' % (bT, np.log(2)/(-bT_ed)/12))
for yr in (2026.75, 2030, 2035, 2040, 2050):
    age = yr - 2009.0
    months_ahead = (yr - (2026 + 9/12 - 1/12)) * 12
    ed_g = np.exp(aT + bT_ed * (T + months_ahead))
    print(f'{yr}: age {age:.1f}, PL instantaneous {np.exp(bT/age)-1:.3f}, PL 5y {(1+5/age)**(bT/5)-1:.3f}, ED instantaneous {np.exp(ed_g)-1:.3f}')

# exhibit rows: history (real-time beta) and projections at today's beta
def r1(b, a): return (1 + 1 / a) ** b - 1
def r5(b, a): return (1 + 5 / a) ** (b / 5) - 1
lines = []
for mth in ['2014-01', '2016-01', '2018-01', '2020-01', '2022-01', '2024-01', str(idx[T])]:
    t = idx.get_loc(pd.Period(mth, 'M')); b, _ = beta_at(t); a = A[t]
    real = (p[t + 60] / p[t]) ** (1 / 5) - 1 if t + 60 <= T else np.nan
    lab = pd.Period(mth, 'M').strftime('%b %Y')
    lines.append(f"{lab} & {a:.1f} & {b:.2f} & {100*r1(b,a):.0f} & {100*r5(b,a):.0f} & " + (f"{100*real:.0f}" if not np.isnan(real) else '--') + " \\\\")
lines.append('\\addlinespace')
bT, _ = beta_at(T)
for yr in (2030, 2035, 2040):
    a = (pd.Timestamp(f'{yr}-01-31') - GEN['BTC']).days / 365.25
    lines.append(f"Jan {yr} & {a:.1f} & ({bT:.2f}) & {100*r1(bT,a):.0f} & {100*r5(bT,a):.0f} & -- \\\\")
open(f'{OUT}/tab_formula.tex', 'w').write('\n'.join(lines)); print('\n'.join(lines))
H2 = H[H.month >= '2017-01']; print('ED half-life range since 2017: %.1f-%.1f' % (H2.half_life.min(), H2.half_life.max()))
for k in (5.24, 5.71, 5.88): print('5y rate today with k=%.2f: %.3f' % (k, r5(k, A[T])))
print('age at 10%% (log): %.1f, year %.0f' % (bT / np.log(1.10), 2009 + bT / np.log(1.10)))
print('A today', A[T], '1y today', r1(bT, A[T]))
