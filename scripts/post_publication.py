"""Age rule and alternatives in periods beginning January 2020 or later (after the power law was published, Sep 2019).
Usage: python3 -I post_publication.py DATA_DIR OUT_DIR"""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__)); sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
btc, fwd, b_pl, b_exp, b_trail, age_of, GEN = (ns[k] for k in ['btc', 'fwd', 'b_pl', 'b_exp', 'b_trail', 'age_of', 'GEN'])
p, idx = btc.values, btc.index; age = age_of(idx, GEN['BTC'])
mask = np.array([t >= pd.Period('2020-01', 'M') for t in idx])
def pct(x, signed=True):
    v = 100 * x
    if round(v) == 0: return '0'
    t = f'{v:+.0f}' if signed else f'{v:.0f}'
    return t.replace('-', '$-$').replace('+', '$+$') if signed else t
rows = []; lines = []
for h in (3, 4, 5):
    m = 12 * h; g = fwd(p, m)
    rates = {'Comparison: 10\\%': np.full(len(p), 0.10), 'J.P.\\ Morgan: 21\\%': np.full(len(p), 0.21),
             'CAGR since Jan 2012': b_exp(p, idx.get_loc(pd.Period('2012-01', 'M'))), 'Trailing 4-year CAGR': b_trail(p, 48),
             'Age rule (power-law trend)': b_pl(p, age, m)}
    first = True
    for k, c in rates.items():
        ok = mask & ~np.isnan(g) & ~np.isnan(c); rel = (1 + g[ok]) / (1 + c[ok]) - 1; Kh = (1 + rel) ** h
        r = dict(h=h, rate=k, n=int(ok.sum()), avg=Kh.mean() ** (1 / h) - 1, median=np.median(rel), beat=(rel > 0).mean(), mad=np.mean(np.abs(rel)))
        rows.append(r)
        lines.append(f"{('$h=%d$' % h) if first else ''} & {k} & {r['n']} & {pct(r['avg'])} & {pct(r['median'])} & {pct(r['beat'], False)} & {pct(r['mad'], False)} \\\\")
        first = False
    lines.append('\\addlinespace')
R = pd.DataFrame(rows); print(R.round(3).to_string(index=False)); R.to_csv(f'{OUT}/post_publication.csv', index=False)
open(f'{OUT}/tab_postpub.tex', 'w').write('\n'.join(lines[:-1]))
