"""Exhibit 1 with each horizon shown: what each method implies for Bitcoin's expected return today, and its record
as a forecast at h = 3, 4 and 5 years (periods from Jan 2012). Usage: python3 -I today_rates_h.py DATA_DIR OUT_DIR"""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__)); sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, b_trail, b_pl, b_ed, age_of, GEN, ext_tv = (ns[k] for k in ['fwd', 'b_exp', 'b_trail', 'b_pl', 'b_expdecay', 'age_of', 'GEN', 'ext_tv'])
btc, gold, spx = ns['btc'], ns['gold'], ns['spx']
p, idx = btc.values, btc.index; age = age_of(idx, GEN['BTC']); T = len(p) - 1
mask = np.array([t >= pd.Period('2012-01', 'M') for t in idx])
# CAPM real-time rate: r_f (Shiller long rate to 2022, FRED GS10 after) + trailing 48-month beta * 4%
s = pd.read_csv(f'{D}/sp500.csv', parse_dates=['Date']); s.index = s.Date.dt.to_period('M')
rf = s['Long Interest Rate'][s['Long Interest Rate'] > 0][:'2022-12'] / 100
f = pd.read_csv(f'{D}/gs10_fred_2023_2026.csv'); f.index = pd.PeriodIndex(f.Date, freq='M'); rf = pd.concat([rf, f.GS10 / 100]).sort_index()
rb = btc.pct_change(); rm = spx.reindex(btc.index).pct_change(); bt = rb.rolling(48).cov(rm) / rm.rolling(48).var()
capm = (rf.reindex(btc.index) + bt * 0.04).values
def pl_today(h):
    b, _ = np.polyfit(np.log(age[:T + 1]), np.log(p[:T + 1]), 1); return ((age[T] + 365.25 * h) / age[T]) ** (b / h) - 1
def rec(rate_fn):
    out = {}
    for h in (3, 4, 5):
        g = fwd(p, 12 * h); c = rate_fn(h); ok = mask & ~np.isnan(g) & ~np.isnan(c)
        rel = (1 + g[ok]) / (1 + c[ok]) - 1
        out[h] = (np.mean((1 + rel) ** h) ** (1 / h) - 1, np.median(rel), (rel > 0).mean())
    return out
i2010, i2012 = idx.get_loc(pd.Period('2010-08', 'M')), idx.get_loc(pd.Period('2012-01', 'M'))
g10, s10 = ext_tv(idx, gold), ext_tv(idx, spx)
items = [('Fixed comparison rate 7\\%', '7', lambda h: np.full(len(p), 0.07)),
         ('Fixed comparison rate 10\\%', '10', lambda h: np.full(len(p), 0.10)),
         ('Fixed comparison rate 12\\%', '12', lambda h: np.full(len(p), 0.12)),
         ('Trailing ten-year CAGR of gold', f'{100 * ((gold.iloc[-1] / gold.iloc[-121]) ** 0.1 - 1):.0f}', lambda h: g10),
         ('Trailing ten-year CAGR of the S\\&P 500 TR', f'{100 * ((spx.iloc[-1] / spx.iloc[-121]) ** 0.1 - 1):.0f}', lambda h: s10),
         ('J.P.\\ Morgan 2027 CMA (21\\% arithmetic)', '21', lambda h: np.full(len(p), 0.21)),
         ('CAPM, trailing four-year beta', '6--7', lambda h: capm),
         ('CAGR since Aug 2010', f'{100 * ((p[T] / p[i2010]) ** (12 / (T - i2010)) - 1):.0f}', lambda h: b_exp(p, i2010)),
         ('CAGR since Jan 2012', f'{100 * ((p[T] / p[i2012]) ** (12 / (T - i2012)) - 1):.0f}', lambda h: b_exp(p, i2012)),
         ('Trailing 3-year CAGR', f'{100 * ((p[T] / p[T - 36]) ** (1 / 3) - 1):.0f}', lambda h: b_trail(p, 36)),
         ('Trailing 4-year CAGR', f'{100 * ((p[T] / p[T - 48]) ** (1 / 4) - 1):.0f}', lambda h: b_trail(p, 48)),
         ('Age rule (power-law trend)', f'{100 * pl_today(5):.0f}--{100 * pl_today(3):.0f}', lambda h: b_pl(p, age, 12 * h)),
         ('Exponential slowdown (sensitivity)', f'{100 * b_ed(p, 60, L=48)[T]:.0f}--{100 * b_ed(p, 36, L=48)[T]:.0f}', lambda h: b_ed(p, 12 * h, L=48))]
def sg(x):
    v = round(100 * x); return '0' if v == 0 else ('$-$' if v < 0 else '$+$') + str(abs(v))
lines = []; rows = []
for label, today, fn in items:
    r = rec(fn)
    rows.append(dict(method=label, today=today, **{f'{k}{h}': r[h][i] for h in (3, 4, 5) for i, k in enumerate(('avg', 'med', 'beat'))}))
    lines.append(f"{label} & {today} & " + ' & '.join(sg(r[h][0]) for h in (3, 4, 5)) + ' & ' + ' & '.join(sg(r[h][1]) for h in (3, 4, 5)) + ' & ' + ' & '.join(str(round(100 * r[h][2])) for h in (3, 4, 5)) + ' \\\\')
pd.DataFrame(rows).to_csv(f'{OUT}/today_rates_by_horizon.csv', index=False)
open(f'{OUT}/tab_today_h.tex', 'w').write('\n'.join(lines)); print('\n'.join(lines))
