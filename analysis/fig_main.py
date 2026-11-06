"""Main exhibit: for each candidate rate, the average miss with its 95% bootstrap band, the rate the method implies
today and the share of periods in which the asset beat it. Bitcoin at h=5 (all candidates), Ether at h=3, gold at h=5.
Usage: python3 -I fig_main.py DATA_DIR OUT_DIR   (reuses section5.py in the same folder)"""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__)); sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, b_trail, b_pl, b_ed, age_of, GEN, ext_tv = (ns[k] for k in ['fwd', 'b_exp', 'b_trail', 'b_pl', 'b_expdecay', 'age_of', 'GEN', 'ext_tv'])
btc, eth, gold, spx = ns['btc'], ns['eth'], ns['gold'], ns['spx']
rng = np.random.default_rng(20261105)

# CPI and r_f
s = pd.read_csv(f'{D}/sp500.csv', parse_dates=['Date']); s.index = s.Date.dt.to_period('M')
cpi = s['Consumer Price Index'][s['Consumer Price Index'] > 0][:'2022-12']
f = pd.read_csv(f'{D}/cpi_fred_2023_2026.csv'); f.index = pd.PeriodIndex(f.Date, freq='M'); f = f.CPIAUCNS.astype(float)
f[pd.Period('2025-10', 'M')] = np.sqrt(f[pd.Period('2025-09', 'M')] * f[pd.Period('2025-11', 'M')])
cpi = pd.concat([cpi, f]).sort_index(); infl10 = (cpi.shift(1) / cpi.shift(121)) ** 0.1 - 1
rf = s['Long Interest Rate'][s['Long Interest Rate'] > 0][:'2022-12'] / 100
g = pd.read_csv(f'{D}/gs10_fred_2023_2026.csv'); g.index = pd.PeriodIndex(g.Date, freq='M'); rf = pd.concat([rf, g.GS10 / 100]).sort_index()


def boot(Kh, h, reps=5000):
    N = len(Kh); L = 12 * h; p = 1.0 / L
    idx = np.empty((reps, N), int); idx[:, 0] = rng.integers(0, N, reps)
    new = rng.random((reps, N)) < p; jump = rng.integers(0, N, (reps, N))
    for j in range(1, N):
        idx[:, j] = np.where(new[:, j], jump[:, j], (idx[:, j - 1] + 1) % N)
    return np.percentile(Kh[idx].mean(1) ** (1 / h) - 1, [2.5, 97.5])


def evaluate(ser, h, win_from, rates):
    p, idx = ser.values, ser.index; mask = np.array([t >= pd.Period(win_from, 'M') for t in idx]); g = fwd(p, 12 * h)
    out = []
    for label, today, c in rates:
        ok = mask & ~np.isnan(g) & ~np.isnan(c); rel = (1 + g[ok]) / (1 + c[ok]) - 1; Kh = (1 + rel) ** h
        lo, hi = boot(Kh, h)
        out.append(dict(rate=label, today=today, n=int(ok.sum()), avg=Kh.mean() ** (1 / h) - 1, lo=lo, hi=hi, med=np.median(rel), beat=(rel > 0).mean()))
    return pd.DataFrame(out)


# ---- Bitcoin, h = 5
p, idx = btc.values, btc.index; age = age_of(idx, GEN['BTC']); T = len(p) - 1
rb = btc.pct_change(); rm = spx.reindex(btc.index).pct_change(); bt = rb.rolling(48).cov(rm) / rm.rolling(48).var()
capm = (rf.reindex(btc.index) + bt * 0.04).values
def pl_today(h):
    b, _ = np.polyfit(np.log(age[:T + 1]), np.log(p[:T + 1]), 1); return ((age[T] + 365.25 * h) / age[T]) ** (b / h) - 1
i2010, i2012 = idx.get_loc(pd.Period('2010-08', 'M')), idx.get_loc(pd.Period('2012-01', 'M'))
h = 5
btc_rates = [('Comparison rate 7%', '7', np.full(len(p), 0.07)), ('Comparison rate 10%', '10', np.full(len(p), 0.10)),
             ('Comparison rate 12%', '12', np.full(len(p), 0.12)),
             ('Trailing 10-year CAGR, gold', f'{100 * ((gold.iloc[-1] / gold.iloc[-121]) ** 0.1 - 1):.0f}', ext_tv(idx, gold)),
             ('Trailing 10-year CAGR, S&P 500', f'{100 * ((spx.iloc[-1] / spx.iloc[-121]) ** 0.1 - 1):.0f}', ext_tv(idx, spx)),
             ('J.P. Morgan 2027 (arithmetic)', '21', np.full(len(p), 0.21)),
             ('CAPM, trailing 4-year beta', '6–7', capm),
             ('CAGR since Aug 2010', f'{100 * ((p[T] / p[i2010]) ** (12 / (T - i2010)) - 1):.0f}', b_exp(p, i2010)),
             ('CAGR since Jan 2012', f'{100 * ((p[T] / p[i2012]) ** (12 / (T - i2012)) - 1):.0f}', b_exp(p, i2012)),
             ('Trailing 3-year CAGR', f'{100 * ((p[T] / p[T - 36]) ** (1 / 3) - 1):.0f}', b_trail(p, 36)),
             ('Trailing 4-year CAGR', f'{100 * ((p[T] / p[T - 48]) ** (1 / 4) - 1):.0f}', b_trail(p, 48)),
             ('Age rule (power-law trend)', f'{100 * pl_today(5):.0f}', b_pl(p, age, 12 * h)),
             ('Exp. slowdown (sensitivity)', f'{100 * b_ed(p, 60, L=48)[T]:.0f}', b_ed(p, 12 * h, L=48))]
B = evaluate(btc, 5, '2012-01', btc_rates)

# ---- Ether, h = 3 (implied rates as of April 2026)
pe, ie = eth.values, eth.index; agee = age_of(ie, GEN['ETH']); Te = len(pe) - 1; i2015 = ie.get_loc(pd.Period('2015-08', 'M'))
def pl_today_e(h):
    b, _ = np.polyfit(np.log(agee[:Te + 1]), np.log(pe[:Te + 1]), 1); return ((agee[Te] + 365.25 * h) / agee[Te]) ** (b / h) - 1
eth_rates = [('Comparison rate 10%', '10', np.full(len(pe), 0.10)),
             ('CAGR since Aug 2015', f'{100 * ((pe[Te] / pe[i2015]) ** (12 / (Te - i2015)) - 1):.0f}', b_exp(pe, i2015)),
             ('Trailing 3-year CAGR', f'{100 * ((pe[Te] / pe[Te - 36]) ** (1 / 3) - 1):.0f}', b_trail(pe, 36)),
             ('Trailing 4-year CAGR', f'{100 * ((pe[Te] / pe[Te - 48]) ** (1 / 4) - 1):.0f}', b_trail(pe, 48)),
             ('Age rule (power-law trend)', f'{100 * pl_today_e(3):.0f}', b_pl(pe, agee, 36)),
             ('Exp. slowdown (sensitivity)', f'{100 * b_ed(pe, 36, L=48)[Te]:.0f}', b_ed(pe, 36, L=48))]
E = evaluate(eth, 3, '2015-08', eth_rates)

# ---- Gold, h = 5, from 1981
pg, ig = gold.values, gold.index; Tg = len(pg) - 1; i1971 = ig.get_loc(pd.Period('1971-01', 'M'))
gold_rates = [('Inflation + 1%', f'{100 * (infl10[ig[Tg]] + 0.01):.1f}', (infl10.reindex(ig) + 0.01).values),
              ('Comparison rate 5.5%', '5.5', np.full(len(pg), 0.055)), ('Comparison rate 7%', '7', np.full(len(pg), 0.07)),
              ('CAGR since Jan 1971', f'{100 * ((pg[Tg] / pg[i1971]) ** (12 / (Tg - i1971)) - 1):.1f}', b_exp(pg, i1971)),
              ('Trailing 10-year CAGR, gold', f'{100 * ((pg[Tg] / pg[Tg - 120]) ** 0.1 - 1):.1f}', ext_tv(ig, gold))]
G = evaluate(gold, 5, '1981-01', gold_rates)
for nm, d in (('BTC', B), ('ETH', E), ('Gold', G)):
    print(nm); print(d.round(3).to_string(index=False))
pd.concat([B.assign(asset='Bitcoin', h=5), E.assign(asset='Ether', h=3), G.assign(asset='Gold', h=5)]).to_csv(f'{OUT}/fig_main.csv', index=False)

# ---- figure
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import matplotlib.ticker as mt
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Nimbus Roman', 'DejaVu Serif'], 'font.size': 8.5,
                     'axes.linewidth': 0.6, 'xtick.major.width': 0.6})
panels = [('(a) Bitcoin, five-year horizon, periods from 2012', B, (-70, 160)),
          ('(b) Ether, three-year horizon, periods from 2015', E, (-70, 210)),
          ('(c) Gold, five-year horizon, periods from 1981', G, (-11, 11))]
fig, axes = plt.subplots(3, 1, figsize=(6.6, 7.4), gridspec_kw={'height_ratios': [16, 8, 7]})
fmt = mt.FuncFormatter(lambda v, _: f'{v:g}'.replace('-', '−'))
for ax, (title, d, xl) in zip(axes, panels):
    y = np.arange(len(d))[::-1]
    ax.axvline(0, color='0.45', lw=0.7, ls='--', zorder=0); ax.grid(axis='x', color='0.88', lw=0.5, zorder=-1)
    cols = ['#1f5fbf' if r.startswith('Age rule') else '0.1' for r in d.rate]
    for yy, lo, hi, md, av, col in zip(y, d.lo, d.hi, d.med, d.avg, cols):
        ax.hlines(yy, 100 * lo, 100 * hi, color=col, lw=1.6 if col != '0.1' else 1.4)
        ax.plot(100 * md, yy, 'D', ms=4.0, mfc='white', mec=col, mew=0.9, zorder=3); ax.plot(100 * av, yy, 'o', ms=4.4, color=col, zorder=4)
    for lab in ax.get_yticklabels():
        if lab.get_text().startswith('Age rule'):
            lab.set_color('#1f5fbf')
    ax.set_yticks(y); ax.set_yticklabels(d.rate, fontsize=7.8); ax.set_xlim(*xl)
    ax.set_title(title, fontsize=8.4, loc='left'); ax.tick_params(axis='x', labelsize=7.6); ax.tick_params(axis='y', length=0)
    ax.xaxis.set_major_formatter(fmt)
    for sp in ('top', 'right', 'left'):
        ax.spines[sp].set_visible(False)
    # text columns to the right, in axes coordinates
    for yy, (td, bt_) in zip(y, zip(d.today, d.beat)):
        ax.text(1.06, yy, td, transform=ax.get_yaxis_transform(), fontsize=7.6, ha='center', va='center')
        ax.text(1.20, yy, f'{100 * bt_:.0f}', transform=ax.get_yaxis_transform(), fontsize=7.6, ha='center', va='center')
    ax.text(1.06, len(d) - 0.15, 'Rate\ntoday', transform=ax.get_yaxis_transform(), fontsize=7.2, ha='center', va='bottom')
    ax.text(1.20, len(d) - 0.15, 'Beaten\n(%)', transform=ax.get_yaxis_transform(), fontsize=7.2, ha='center', va='bottom')
    ax.set_ylim(-0.7, len(d) + 1.4)
axes[-1].set_xlabel('Miss, percentage points a year (positive: the asset beat the rate)', fontsize=8)
from matplotlib.lines import Line2D
handles = [Line2D([], [], marker='o', color='0.1', ls='-', lw=1.4, ms=4.2, label='Average miss, with 95% bootstrap band'), Line2D([], [], marker='D', mfc='white', mec='0.1', ls='', ms=4.0, label='Median miss'), Line2D([], [], marker='o', color='#1f5fbf', ls='-', lw=1.6, ms=4.4, label='Age rule')]
axes[0].legend(handles=handles, loc='upper left', bbox_to_anchor=(0.0, -0.1), ncol=3, frameon=False, fontsize=7.4, handlelength=2.2)
fig.subplots_adjust(left=0.30, right=0.80, top=0.97, bottom=0.06, hspace=0.5)
fig.savefig(f'{OUT}/fig_main.pdf'); fig.savefig(f'{OUT}/fig_main.png', dpi=200); print('written')
