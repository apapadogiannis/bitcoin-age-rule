"""Exhibit 2: the age rule in real time. (a) the exponent fitted each month on data to that month; (b) the five-year
expected return the rule forecast each month, the five-year return that followed, two alternatives, and the projection
to 2040 with the exponent held at its last value. Usage: python3 -I fig_agerule.py DATA_DIR OUT_DIR"""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__)); sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, age_of, GEN = (ns[k] for k in ['fwd', 'b_exp', 'age_of', 'GEN'])
btc = ns['btc']; p, idx = btc.values, btc.index; age = age_of(idx, GEN['BTC']) / 365.25; T = len(p) - 1
x, y = np.log(age), np.log(p)
beta = np.full(len(p), np.nan)
for t in range(36, len(p)):
    beta[t] = np.polyfit(x[:t + 1], y[:t + 1], 1)[0]
c5 = ((age + 5) / age) ** (beta / 5) - 1
g5 = fwd(p, 60)
cagr12 = b_exp(p, idx.get_loc(pd.Period('2012-01', 'M')))
dates = idx.to_timestamp()
# projection
A_last, b_last = age[T], beta[T]
proj_t = pd.period_range(idx[T], '2040-12', freq='M'); proj_age = A_last + np.arange(len(proj_t)) / 12
proj_c5 = ((proj_age + 5) / proj_age) ** (b_last / 5) - 1
df = pd.DataFrame(dict(month=idx.astype(str), age=age, beta=beta, agerule_5y=c5, realized_5y=g5, cagr_since_2012=cagr12))
df.to_csv(f'{OUT}/fig_agerule.csv', index=False)
m = ~np.isnan(g5) & ~np.isnan(c5) & (idx >= pd.Period('2012-01', 'M'))
print('forecast vs realized, periods from 2012:', m.sum(), 'avg forecast', np.nanmean(c5[m]), 'avg realized', np.nanmean(g5[m]))
for d in ('2014-01', '2016-01', '2018-01', '2020-01', '2022-01', '2024-01', '2026-09'):
    i = idx.get_loc(pd.Period(d, 'M')); print(d, round(beta[i], 2), round(100 * c5[i]), None if np.isnan(g5[i]) else round(100 * g5[i]))
print('projection 2030/2035/2040:', [round(100 * proj_c5[list(proj_t.astype(str)).index(s)]) for s in ('2030-01', '2035-01', '2040-01')])

import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import matplotlib.dates as mdates
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Nimbus Roman', 'DejaVu Serif'], 'font.size': 8.5, 'axes.linewidth': 0.6})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.4, 5.6), gridspec_kw={'height_ratios': [1, 2.4]}, sharex=True)
start = pd.Timestamp('2013-01-01'); end = pd.Timestamp('2041-01-01')
sel = dates >= start
a1.plot(dates[sel], beta[sel], color='#1f5fbf', lw=1.4)
a1.axhline(b_last, color='0.6', lw=0.6, ls=':')
a1.tick_params(labelbottom=True, labelsize=7.5); a1.set_ylabel('Exponent $\\beta_t$', fontsize=8); a1.set_ylim(4.5, 8); a1.grid(axis='y', color='0.9', lw=0.5)
a1.set_title('(a) Power-law exponent fitted each month on data to that month', fontsize=8.6, loc='left')
pt = proj_t.to_timestamp()
a2.plot(dates[sel], 100 * c5[sel], color='#1f5fbf', lw=1.5, label='Age rule: five-year expected return forecast at that date')
a2.plot(pt, 100 * proj_c5, color='#1f5fbf', lw=1.3, ls='--', label='Age rule, exponent held at 5.62 (projection, not a forecast)')
a2.plot(dates[sel], 100 * g5[sel], color='0.1', lw=1.1, label='Bitcoin: realized return over the five years from that date')
a2.axhline(10, color='0.55', lw=1.0, ls=':', label='Comparison rate 10%')
a2.set_ylim(0, 200); a2.set_ylabel('% a year', fontsize=8); a2.grid(axis='y', color='0.9', lw=0.5)
a2.set_title('(b) Five-year expected return forecast by the age rule, and what followed', fontsize=8.6, loc='left'); a2.set_xlabel('Date of estimate (start of the five-year period)', fontsize=8)
a2.legend(frameon=False, fontsize=7.4, loc='upper right', bbox_to_anchor=(1.0, 0.97))
a2.xaxis.set_major_locator(mdates.YearLocator(3)); a2.xaxis.set_major_formatter(mdates.DateFormatter('%Y')); a2.set_xlim(start, end)
for ax in (a1, a2):
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
fig.tight_layout(h_pad=1.2)
fig.savefig(f'{OUT}/fig_agerule.pdf'); fig.savefig(f'{OUT}/fig_agerule.png', dpi=200); print('written')
