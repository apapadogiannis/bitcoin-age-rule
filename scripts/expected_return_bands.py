"""Can the backtest tell candidate expected returns apart?
For each asset, horizon and candidate rate: the average miss (mean test) with a 95% band from a stationary block
bootstrap (Politis and Romano 1994) of the monthly sequence of K-hat, mean block length 12h months (and 24h as a check).
Also adds the gold rate implied by the long-run evidence (Barro and Misra 2016): trailing ten-year CPI inflation + 1%,
using CPI of the previous month (real time). CPI: Shiller CPI-U to Dec 2022 (sp500.csv), FRED CPIAUCNS from Jan 2023
(cpi_fred_2023_2026.csv; Oct 2025 not published, interpolated geometrically).
Usage: python3 -I expected_return_bands.py DATA_DIR OUT_DIR   (reuses section5.py in the same folder)"""
import sys, os, io, runpy, contextlib
import numpy as np
import pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, b_trail, b_pl, b_ed, age_of, GEN, ext_tv = (ns[k] for k in
    ['fwd', 'b_exp', 'b_trail', 'b_pl', 'b_expdecay', 'age_of', 'GEN', 'ext_tv'])
btc, eth, gold, spx = ns['btc'], ns['eth'], ns['gold'], ns['spx']
rng = np.random.default_rng(20261103)

# ---------------- CPI ----------------
s = pd.read_csv(f'{D}/sp500.csv', parse_dates=['Date']); s.index = s.Date.dt.to_period('M')
cpi = s['Consumer Price Index'][s['Consumer Price Index'] > 0][:'2022-12']
f = pd.read_csv(f'{D}/cpi_fred_2023_2026.csv'); f.index = pd.PeriodIndex(f.Date, freq='M')
f = f.CPIAUCNS.astype(float)
f[pd.Period('2025-10', 'M')] = np.sqrt(f[pd.Period('2025-09', 'M')] * f[pd.Period('2025-11', 'M')])
cpi = pd.concat([cpi, f]).sort_index()
assert cpi.index.is_unique and (cpi.index[1:] - cpi.index[:-1] == 1 * cpi.index.freq).all()
infl10 = ((cpi.shift(1) / cpi.shift(121)) ** 0.1 - 1)          # known at the start of month t
print('CPI', cpi.index[0], '-', cpi.index[-1], '; trailing 10y inflation (to Aug 2026):', round(infl10.iloc[-1], 4))


def boot_avg(Kh, h, L, reps=5000):
    """stationary bootstrap of the K-hat sequence; returns 2.5 and 97.5 percentiles of the annualized average miss"""
    N = len(Kh); p = 1.0 / L
    idx = np.empty((reps, N), int)
    idx[:, 0] = rng.integers(0, N, reps)
    new = rng.random((reps, N)) < p
    jump = rng.integers(0, N, (reps, N))
    for j in range(1, N):
        idx[:, j] = np.where(new[:, j], jump[:, j], (idx[:, j - 1] + 1) % N)
    a = Kh[idx].mean(1) ** (1 / h) - 1
    return np.percentile(a, [2.5, 97.5])


def evaluate(asset, ser, h, win_from, rates):
    p, idx = ser.values, ser.index
    mask = np.array([t >= pd.Period(win_from, 'M') for t in idx])
    g = fwd(p, 12 * h)
    rows = []
    for k, c in rates.items():
        ok = mask & ~np.isnan(g) & ~np.isnan(c)
        rel = (1 + g[ok]) / (1 + c[ok]) - 1
        Kh = (1 + rel) ** h
        lo, hi = boot_avg(Kh, h, 12 * h)
        lo2, hi2 = boot_avg(Kh, h, 24 * h, reps=2000)
        rows.append(dict(asset=asset, sample_from=win_from, h=h, rate=k, n=int(ok.sum()), avg=Kh.mean() ** (1 / h) - 1,
                         lo=lo, hi=hi, lo_L2=lo2, hi_L2=hi2, median=np.median(rel), beat=(rel > 0).mean(),
                         mad=np.mean(np.abs(rel)), rate_now=c[~np.isnan(c)][-1]))
    return rows


def crypto_rates(name, ser, start, h):
    p, idx = ser.values, ser.index; m = 12 * h
    age = age_of(idx, GEN[name])
    return {'Comparison: 10\\%': np.full(len(p), 0.10),
            f"CAGR since {pd.Period(start, 'M').strftime('%b %Y')}": b_exp(p, idx.get_loc(pd.Period(start, 'M'))),
            'Trailing 3-year CAGR': b_trail(p, 36), 'Trailing 4-year CAGR': b_trail(p, 48),
            'Power-law trend': b_pl(p, age, m), 'Exp.\\ slowdown, 4-year window': b_ed(p, m, L=48)}


def gold_rates():
    p, idx = gold.values, gold.index
    return {'Inflation $+$ 1\\%': (infl10.reindex(idx) + 0.01).values,
            'Comparison: 5.5\\%': np.full(len(p), 0.055), 'Comparison: 7\\%': np.full(len(p), 0.07),
            'CAGR since Jan 1971': b_exp(p, idx.get_loc(pd.Period('1971-01', 'M'))),
            '10-year CAGR, gold': ext_tv(idx, gold)}


rows = []
for h in (3, 4, 5):
    rows += evaluate('BTC', btc, h, '2012-01', crypto_rates('BTC', btc, '2012-01', h))
rows += evaluate('ETH', eth, 3, '2015-08', crypto_rates('ETH', eth, '2015-08', 3))
for fr in ('1981-01', '2012-01'):
    for h in (3, 4, 5):
        rows += evaluate('Gold', gold, h, fr, gold_rates())
R = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print(R.round(3).to_string(index=False))
R.to_csv(f'{OUT}/expected_return_bands.csv', index=False)

# gold: realized nominal and real growth since 1971 and 1981, to September 2026
for a in ('1971-01', '1981-01'):
    yrs = (gold.index[-1] - pd.Period(a, 'M')).n / 12
    gn = (gold.iloc[-1] / gold[a]) ** (1 / yrs) - 1
    ci = (cpi[gold.index[-1]] / cpi[a]) ** (1 / yrs) - 1
    print(f'Gold {a}-{gold.index[-1]}: nominal CAGR {gn:.4f}, CPI {ci:.4f}, real {(1 + gn) / (1 + ci) - 1:.4f}')
print('Inflation + 1% rate in Sep 2026:', round(infl10[pd.Period('2026-09', 'M')] + 0.01, 4))


# ---------------- LaTeX: gold panel of the calibration exhibit (adds the inflation row) ----------------
def pct(x, signed=True):
    v = 100 * x
    if round(v) == 0:
        return '0'
    t = f'{v:+.0f}' if signed else f'{v:.0f}'
    return t.replace('-', '$-$').replace('+', '$+$') if signed else t


def cells(a):
    return f"{int(a.n)} & {pct(a.avg)} & {pct(a['median'])} & {pct(a.beat, False)} & {pct(a.mad, False)}"


G = R[(R.asset == 'Gold') & (R.sample_from == '1981-01')]
g3, g5 = G[G.h == 3].set_index('rate'), G[G.h == 5].set_index('rate')
open(f'{OUT}/tab_calib_gold.tex', 'w').write('\n'.join(f"{r} & {cells(g3.loc[r])} & {cells(g5.loc[r])} \\\\" for r in g3.index))

# ---------------- Figure: average miss with 95% bands ----------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Nimbus Roman', 'DejaVu Serif'],
                     'font.size': 8.5, 'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6})
panels = [('(a) Bitcoin, $h=5$', R[(R.asset == 'BTC') & (R.h == 5)]),
          ('(b) Ether, $h=3$', R[(R.asset == 'ETH')]),
          ('(c) Gold, $h=5$, from 1981', G[G.h == 5])]
fig, axes = plt.subplots(3, 1, figsize=(6.3, 5.9), gridspec_kw={'height_ratios': [6, 6, 7]})
for ax, (title, d) in zip(axes, panels):
    d = d.reset_index(drop=True)
    y = np.arange(len(d))[::-1]
    ax.axvline(0, color='0.45', lw=0.7, ls='--', zorder=0)
    ax.grid(axis='x', color='0.88', lw=0.5, zorder=-1)
    ax.hlines(y, 100 * d.lo, 100 * d.hi, color='0.1', lw=1.4)
    ax.plot(100 * d.avg, y, 'o', ms=4.2, color='0.1', zorder=3)
    labels = [r.replace('\\%', '%').replace('\\&', '&').replace('\\ ', ' ').replace('$+$', '+') for r in d.rate]
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7.8)
    ax.set_ylim(-0.7, len(d) - 0.3)
    ax.set_title(title, fontsize=8.8, loc='left')
    ax.tick_params(axis='x', labelsize=7.8); ax.tick_params(axis='y', length=0)
    for sp in ('top', 'right', 'left'):
        ax.spines[sp].set_visible(False)
from matplotlib.ticker import MultipleLocator
axes[-1].xaxis.set_major_locator(MultipleLocator(2.5))
axes[-1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}'.replace('-', '\u2212')))
for ax in axes[:2]:
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}'.replace('-', '\u2212')))
axes[-1].set_xlabel('Average miss (% a year): positive means the asset beat the rate', fontsize=8)
fig.tight_layout(h_pad=0.9)
fig.savefig(f'{OUT}/fig_bands.pdf'); fig.savefig(f'{OUT}/fig_bands.png', dpi=200)
print('written')
