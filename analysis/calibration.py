"""Calibration of discount rates: how far each rate missed the return that followed.
Two tests are reported:
  * mean test (cost-of-capital): if c is the expected return over the horizon, E[K-hat] = 1, so the
    average of K-hat across periods should be close to one; reported annualized as (mean K-hat)^(1/h) - 1;
  * median test: share of periods in which the rate was beaten and median of K-hat^(1/h) - 1.
Also prints realized volatilities and, under lognormal returns, the share of periods in which a correctly
set expected return would be beaten: 1 - Phi(sigma*sqrt(h)/2).
Usage: python3 -I calibration.py DATA_DIR OUT_DIR   (reuses functions from section5.py in the same folder)"""
import sys, os, io, runpy, contextlib
import numpy as np
import pandas as pd
from scipy.stats import norm

D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, b_trail, b_pl, b_ed, age_of, GEN = (ns[k] for k in ['fwd', 'b_exp', 'b_trail', 'b_pl', 'b_expdecay', 'age_of', 'GEN'])
btc, eth, gold, spx = ns['btc'], ns['eth'], ns['gold'], ns['spx']


def stats(g, c, ok, h):
    rel = (1 + g[ok]) / (1 + c[ok]) - 1          # annual return relative to the rate = K-hat^(1/h) - 1
    Kh = (1 + rel) ** h
    top = max(1, int(round(0.05 * len(Kh))))
    return dict(n=int(ok.sum()), median=np.median(rel), avg=Kh.mean() ** (1 / h) - 1,
                avg_trim=np.sort(Kh)[:-top].mean() ** (1 / h) - 1, mad=np.mean(np.abs(rel)), beat=(rel > 0).mean())


def calib(name, ser, start, h, win_from, windows=(48,), include_fixed=True, trailing=(36, 48)):
    p, idx = ser.values, ser.index
    age = age_of(idx, GEN[name])
    mask = np.array([t >= pd.Period(win_from, 'M') for t in idx])
    m = 12 * h
    g = fwd(p, m)
    rates = {}
    if include_fixed:
        rates['Comparison rate: 10\\%'] = np.full(len(p), 0.10)
    rates[f"CAGR since {pd.Period(start, 'M').strftime('%b %Y')}"] = b_exp(p, idx.get_loc(pd.Period(start, 'M')))
    for L in trailing:
        rates[f'Trailing {L // 12}-year CAGR'] = b_trail(p, L)
    rates['Power-law trend, fitted to date'] = b_pl(p, age, m)
    for L in windows:
        rates[f'Exponential slowdown, {L // 12}-year window'] = b_ed(p, m, L=L)
    rows = []
    for k, c in rates.items():
        ok = mask & ~np.isnan(g) & ~np.isnan(c)
        rows.append(dict(asset=name, h=h, rate=k, **stats(g, c, ok, h)))
    return pd.DataFrame(rows)


main = pd.concat([calib('BTC', btc, '2012-01', h, '2012-01') for h in (3, 4, 5)] +
                 [calib('ETH', eth, '2015-08', 3, '2015-08')])
sens = pd.concat([calib('BTC', btc, '2012-01', h, '2012-01', windows=(36, 48, 60), include_fixed=False, trailing=()) for h in (3, 5)] +
                 [calib('ETH', eth, '2015-08', 3, '2015-08', windows=(36, 48, 60), include_fixed=False, trailing=())])
sens = sens[sens.rate.str.startswith('Exponential') | sens.rate.str.startswith('Power')]
pd.set_option('display.width', 200)
print(main.round(3).to_string(index=False)); print(); print(sens.round(3).to_string(index=False))
main.to_csv(f'{OUT}/calibration_main.csv', index=False); sens.to_csv(f'{OUT}/calibration_window_sensitivity.csv', index=False)


# Volatility and the lognormal benchmark for the beat share of a correctly set expected return
def vol(s, a, b=None):
    s = s[(s.index >= pd.Period(a, 'M')) & ((s.index <= pd.Period(b, 'M')) if b else True)]
    return np.diff(np.log(s.values)).std(ddof=1) * np.sqrt(12)


print('\nAnnualized volatility of monthly log returns, and lognormal beat share 1-Phi(sigma*sqrt(h)/2) for h=3,5')
vrows = []
for nm, s, a in [('Bitcoin', btc, '2012-01'), ('Bitcoin, last 4 years', btc, str(btc.index[-49])), ('Ether', eth, '2015-08'),
                 ('Gold', gold, '2012-01'), ('S&P 500 TR', spx, '2012-01')]:
    v = vol(s, a)
    vrows.append(dict(series=nm, sigma=v, beat_h3=1 - norm.cdf(v * np.sqrt(3) / 2), beat_h5=1 - norm.cdf(v * np.sqrt(5) / 2),
                      mean_over_median_pa=np.exp(v ** 2 / 2) - 1))
V = pd.DataFrame(vrows); print(V.round(3).to_string(index=False)); V.to_csv(f'{OUT}/volatility_benchmark.csv', index=False)


def pct(x, signed=True):
    v = 100 * x
    if round(v) == 0:
        return '0'
    s = f'{v:+.0f}' if signed else f'{v:.0f}'
    return s.replace('-', '$-$').replace('+', '$+$') if signed else s


def cells(a):
    return f"{int(a.n)} & {pct(a.avg)} & {pct(a['median'])} & {pct(a.beat, False)} & {pct(a.mad, False)}"


# Main exhibit: Bitcoin h=3 and h=5 side by side; Ether h=3 as Panel B
b3 = main[(main.asset == 'BTC') & (main.h == 3)].set_index('rate')
b5 = main[(main.asset == 'BTC') & (main.h == 5)].set_index('rate')
lines = [f"{r} & {cells(b3.loc[r])} & {cells(b5.loc[r])} \\\\" for r in b3.index]
open(f'{OUT}/tab_calib_btc.tex', 'w').write('\n'.join(lines))
e3 = main[(main.asset == 'ETH') & (main.h == 3)].set_index('rate')
lines = [f"{r} & {cells(a)} \\\\" for r, a in e3.iterrows()]
open(f'{OUT}/tab_calib_eth.tex', 'w').write('\n'.join(lines))
# Window sensitivity exhibit
lines = []
for (asset, h), grp in sens.groupby(['asset', 'h'], sort=False):
    first = True
    for _, a in grp.iterrows():
        lab = (f"{'Bitcoin' if asset == 'BTC' else 'Ether'}, $h={h}$" if first else '')
        lines.append(f"{lab} & {a.rate} & {cells(a)} \\\\")
        first = False
    lines.append('\\addlinespace')
open(f'{OUT}/tab_calib_windows.tex', 'w').write('\n'.join(lines[:-1]))
print('written')

# Gold: comparison rates and own-history CAGR; periods from January 1981 (first month with a trailing ten-year gold rate)
ext_tv = ns['ext_tv']


def calib_gold(h, win_from):
    p, idx = gold.values, gold.index
    mask = np.array([t >= pd.Period(win_from, 'M') for t in idx])
    g = fwd(p, 12 * h)
    rates = {'Comparison: 7\\%': np.full(len(p), 0.07), 'Comparison: 10\\%': np.full(len(p), 0.10),
             'Comparison: 12\\%': np.full(len(p), 0.12), 'Trailing ten-year CAGR of gold': ext_tv(idx, gold),
             'Trailing ten-year CAGR of S\\&P 500 TR': ext_tv(idx, spx),
             'CAGR since Jan 1971': b_exp(p, idx.get_loc(pd.Period('1971-01', 'M')))}
    rows = []
    for k, c in rates.items():
        ok = mask & ~np.isnan(g) & ~np.isnan(c)
        rows.append(dict(asset='Gold', sample_from=win_from, h=h, rate=k, **stats(g, c, ok, h)))
    return pd.DataFrame(rows)


G = pd.concat([calib_gold(h, f) for f in ('1981-01', '2012-01') for h in (3, 4, 5)])
print(); print(G.round(3).to_string(index=False)); G.to_csv(f'{OUT}/calibration_gold.csv', index=False)
g3 = G[(G.sample_from == '1981-01') & (G.h == 3)].set_index('rate'); g5 = G[(G.sample_from == '1981-01') & (G.h == 5)].set_index('rate')
open(f'{OUT}/tab_calib_gold.tex', 'w').write('\n'.join(f"{r} & {cells(g3.loc[r])} & {cells(g5.loc[r])} \\\\" for r in g3.index))
print('gold written')

