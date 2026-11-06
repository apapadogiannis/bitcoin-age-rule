"""What each method would set as Bitcoin's discount rate today (last month in the data), next to its backtest record.
Usage: python3 -I today_rates.py DATA_DIR OUT_DIR   (reuses functions from section5.py in the same folder)"""
import sys, os, io, runpy, contextlib
import numpy as np
import pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, b_trail, b_pl, b_ed, age_of, GEN, ext_tv = (ns[k] for k in ['fwd', 'b_exp', 'b_trail', 'b_pl', 'b_expdecay', 'age_of', 'GEN', 'ext_tv'])
btc, gold, spx = ns['btc'], ns['gold'], ns['spx']
p, idx = btc.values, btc.index
age = age_of(idx, GEN['BTC'])
T = len(p) - 1
asof = idx[T]
mask = np.array([t >= pd.Period('2012-01', 'M') for t in idx])


def pl_today(h):
    x, y = np.log(age[:T + 1]), np.log(p[:T + 1])
    b, _ = np.polyfit(x, y, 1)
    return (((age[T] + 365.25 * h) / age[T]) ** (b / h)) - 1


def record(rate_fn):
    """beaten share, median miss and average miss ((mean K-hat)^(1/h) - 1) across h = 3, 4, 5 (periods from Jan 2012)"""
    beat, med, avg = [], [], []
    for h in (3, 4, 5):
        m = 12 * h
        g = fwd(p, m)
        c = rate_fn(h)
        ok = mask & ~np.isnan(g) & ~np.isnan(c)
        rel = (1 + g[ok]) / (1 + c[ok]) - 1
        beat.append((rel > 0).mean()); med.append(np.median(rel)); avg.append(np.mean((1 + rel) ** h) ** (1 / h) - 1)
    return min(beat), max(beat), min(med), max(med), min(avg), max(avg)


rows = []
def add(label, today, rate_fn):
    b0, b1, m0, m1, a0, a1 = record(rate_fn)
    rows.append(dict(method=label, today=today, beat_lo=b0, beat_hi=b1, med_lo=m0, med_hi=m1, avg_lo=a0, avg_hi=a1))


i2010, i2012 = idx.get_loc(pd.Period('2010-08', 'M')), idx.get_loc(pd.Period('2012-01', 'M'))
for r in (0.07, 0.10, 0.12):
    add(f'Fixed comparison rate {int(r * 100)}\\%', f'{100 * r:.0f}', lambda h, r=r: np.full(len(p), r))
g10 = ext_tv(idx, gold); s10 = ext_tv(idx, spx)
gold_today = (gold.iloc[-1] / gold.iloc[-121]) ** 0.1 - 1
spx_today = (spx.iloc[-1] / spx.iloc[-121]) ** 0.1 - 1
add('Trailing ten-year CAGR of gold', f'{100 * gold_today:.0f}', lambda h: g10)
add('Trailing ten-year CAGR of the S\\&P 500 TR', f'{100 * spx_today:.0f}', lambda h: s10)
add('CAGR since Aug 2010', f'{100 * ((p[T] / p[i2010]) ** (12 / (T - i2010)) - 1):.0f}', lambda h: b_exp(p, i2010))
add('CAGR since Jan 2012', f'{100 * ((p[T] / p[i2012]) ** (12 / (T - i2012)) - 1):.0f}', lambda h: b_exp(p, i2012))
add('Trailing 3-year CAGR', f'{100 * ((p[T] / p[T - 36]) ** (1 / 3) - 1):.0f}', lambda h: b_trail(p, 36))
add('Trailing 4-year CAGR', f'{100 * ((p[T] / p[T - 48]) ** (1 / 4) - 1):.0f}', lambda h: b_trail(p, 48))
pl3, pl5 = pl_today(3), pl_today(5)
add('Power-law trend, fitted to date', f'{100 * pl5:.0f}--{100 * pl3:.0f}', lambda h: b_pl(p, age, 12 * h))
ed = {L: (b_ed(p, 36, L=L)[T], b_ed(p, 60, L=L)[T]) for L in (36, 48, 60)}
add('Exponential slowdown, 4-year window', f'{100 * ed[48][1]:.0f}--{100 * ed[48][0]:.0f}', lambda h: b_ed(p, 12 * h, L=48))
R = pd.DataFrame(rows)
pd.set_option('display.width', 200)
print('as of', asof, 'BTC price', round(p[T]))
print(R.round(3).to_string(index=False))
print('exp-decay today by window (h=3, h=5):', {L // 12: (round(100 * a, 1), round(100 * b, 1)) for L, (a, b) in ed.items()})
print('gold 10y today %.1f%%, S&P TR 10y today %.1f%%' % (100 * gold_today, 100 * spx_today))
R.to_csv(f'{OUT}/today_rates.csv', index=False)


def rng(a, b, signed=False):
    fa, fb = round(100 * a), round(100 * b)
    f = (lambda v: ('$-$' if v < 0 else ('$+$' if v > 0 else '')) + str(abs(v))) if signed else str
    return f(fa) if fa == fb else f'{f(fa)} to {f(fb)}' if signed else f'{fa}--{fb}'


lines = [f"{r.method} & {r.today} & {rng(r.avg_lo, r.avg_hi, True)} & {rng(r.med_lo, r.med_hi, True)} & {rng(r.beat_lo, r.beat_hi)} \\\\" for r in R.itertuples()]
open(f'{OUT}/tab_today.tex', 'w').write('\n'.join(lines))
open(f'{OUT}/today_meta.txt', 'w').write(f"{asof}|{round(p[T])}|" + '|'.join(f"{L//12}:{100*a:.0f}:{100*b:.0f}" for L, (a, b) in ed.items()))
print(open(f'{OUT}/tab_today.tex').read())
