"""Ether counterpart of Exhibit 2: exponent fitted each month (data from Aug 2015), three-year forecast vs realized."""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__)); sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, age_of, GEN = ns['fwd'], ns['age_of'], ns['GEN']
eth = ns['eth']; p, idx = eth.values, eth.index; age = age_of(idx, GEN['ETH']) / 365.25; T = len(p) - 1
x, y = np.log(age), np.log(p)
beta = np.full(len(p), np.nan)
for t in range(36, len(p)):
    beta[t] = np.polyfit(x[:t + 1], y[:t + 1], 1)[0]
h = 3; c = ((age + h) / age) ** (beta / h) - 1; g = fwd(p, 12 * h)
m = ~np.isnan(g) & ~np.isnan(c)
print('ETH periods', m.sum(), 'avg forecast', round(np.nanmean(c[m]), 3), 'avg realized', round(np.nanmean(g[m]), 3), 'beta range', round(np.nanmin(beta), 2), round(np.nanmax(beta), 2), 'last', round(beta[T], 2))
for d in ('2018-08', '2019-08', '2020-08', '2021-08', '2022-08', '2023-08', '2024-08', '2026-04'):
    i = idx.get_loc(pd.Period(d, 'M')); print(d, round(beta[i], 2), round(100 * c[i]), None if np.isnan(g[i]) else round(100 * g[i]))
pd.DataFrame(dict(month=idx.astype(str), age=age, beta=beta, agerule_3y=c, realized_3y=g)).to_csv(f'{OUT}/fig_agerule_eth.csv', index=False)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import matplotlib.dates as mdates
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Nimbus Roman', 'DejaVu Serif'], 'font.size': 8.5, 'axes.linewidth': 0.6})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.4, 4.6), gridspec_kw={'height_ratios': [1, 2.2]}, sharex=True)
dates = idx.to_timestamp(); sel = dates >= pd.Timestamp('2018-08-01')
a1.plot(dates[sel], beta[sel], color='#1f5fbf', lw=1.4); a1.set_ylim(0, 4); a1.grid(axis='y', color='0.9', lw=0.5)
a1.tick_params(labelbottom=True, labelsize=7.5); a1.set_ylabel('Exponent $\\beta_t$', fontsize=8)
a1.set_title('(a) Power-law exponent for Ether, fitted each month on data from August 2015 to that month', fontsize=8.6, loc='left')
a2.plot(dates[sel], 100 * c[sel], color='#1f5fbf', lw=1.5, label='Age rule for Ether: three-year expected return forecast at that date')
a2.plot(dates[sel], 100 * g[sel], color='0.1', lw=1.1, label='Ether: realized return over the three years from that date')
a2.axhline(10, color='0.55', lw=1.0, ls=':', label='Comparison rate 10%')
a2.set_ylim(-60, 160); a2.axhline(0, color='0.75', lw=0.5); a2.set_ylabel('% a year', fontsize=8); a2.grid(axis='y', color='0.9', lw=0.5)
a2.set_title('(b) Three-year expected return forecast by the age rule, and what followed', fontsize=8.6, loc='left')
a2.legend(frameon=False, fontsize=7.4, loc='upper right'); a2.set_xlabel('Date of estimate (start of the three-year period)', fontsize=8)
a2.xaxis.set_major_locator(mdates.YearLocator(1)); a2.xaxis.set_major_formatter(mdates.DateFormatter('%Y')); a2.set_xlim(pd.Timestamp('2018-07-01'), pd.Timestamp('2026-07-01'))
for ax in (a1, a2):
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
fig.tight_layout(h_pad=1.2); fig.savefig(f'{OUT}/fig_agerule_eth.pdf'); fig.savefig(f'{OUT}/fig_agerule_eth.png', dpi=150); print('written')
