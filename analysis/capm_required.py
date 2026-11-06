"""Expected versus required return: a CAPM required return for Bitcoin, Ether and gold.
Required return = r_f + beta * ERP, with r_f the ten-year Treasury yield (Shiller long rate to Dec 2022, FRED GS10 from
Jan 2023) and beta from monthly simple returns on the S&P 500 total-return index (Newey-West standard errors, 6 lags).
ERP of 4% (in line with the fundamentals-based estimates of Fama and French 2002) and 6% as a high case.
Also backtests a real-time CAPM rate (trailing four-year beta, r_f at t, ERP 4%) as an expected return for Bitcoin.
Usage: python3 -I capm_required.py DATA_DIR OUT_DIR   (reuses section5.py and expected_return_bands.py helpers)"""
import sys, os, io, runpy, contextlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
btc, eth, gold, spx, fwd = ns['btc'], ns['eth'], ns['gold'], ns['spx'], ns['fwd']
rng = np.random.default_rng(20261103)

s = pd.read_csv(f'{D}/sp500.csv', parse_dates=['Date']); s.index = s.Date.dt.to_period('M')
rf = s['Long Interest Rate'][s['Long Interest Rate'] > 0][:'2022-12'] / 100
f = pd.read_csv(f'{D}/gs10_fred_2023_2026.csv'); f.index = pd.PeriodIndex(f.Date, freq='M')
rf = pd.concat([rf, f.GS10 / 100]).sort_index()
print('r_f Sep 2026:', rf[pd.Period('2026-09', 'M')])


def beta(a, m, start, end='2026-09'):
    r = pd.concat([a.pct_change(), m.pct_change()], axis=1, keys=['a', 'm']).dropna()
    r = r[(r.index >= pd.Period(start, 'M')) & (r.index <= pd.Period(end, 'M'))]
    X = sm.add_constant(r.m.values)
    fit = sm.OLS(r.a.values, X).fit(cov_type='HAC', cov_kwds={'maxlags': 6})
    b, se = fit.params[1], fit.bse[1]
    return dict(beta=b, lo=b - 1.96 * se, hi=b + 1.96 * se, corr=r.corr().iloc[0, 1], n=len(r))


rows = []
for name, ser, starts in [('Bitcoin', btc, ['2012-01', '2016-01', '2021-10', '2022-10']),
                          ('Ether', eth, ['2016-08', '2021-10']),   # Ether to Apr 2026
                          ('Gold', gold, ['1981-01', '2012-01', '2021-10'])]:
    for st in starts:
        end = '2026-04' if name == 'Ether' else '2026-09'
        b = beta(ser, spx, st, end)
        r0 = rf[pd.Period(end, 'M')]
        rows.append(dict(asset=name, start=st, end=end, **b, rf=r0))
R = pd.DataFrame(rows)
R['req_erp4'] = R.rf + R.beta * 0.04
R['req_erp6'] = R.rf + R.beta * 0.06
R['req_erp4_lo'] = R.rf + R.lo * 0.04
R['req_erp6_hi'] = R.rf + R.hi * 0.06
pd.set_option('display.width', 220)
print(R.round(3).to_string(index=False))
R.to_csv(f'{OUT}/capm_required.csv', index=False)

# Real-time CAPM rate for Bitcoin, used as an expected return: trailing 48-month beta, r_f at t, ERP 4%
rb = btc.pct_change(); rm = spx.reindex(btc.index).pct_change()
bt = (rb.rolling(48).cov(rm) / rm.rolling(48).var())
capm_t = (rf.reindex(btc.index) + bt * 0.04).values
p = btc.values
print('real-time beta, Jan 2016 / Jan 2020 / Jan 2024 / Sep 2026:',
      [round(bt[pd.Period(x, 'M')], 2) for x in ('2016-01', '2020-01', '2024-01', '2026-09')])
print('real-time CAPM rate Sep 2026:', round(capm_t[-1], 4))
mask = np.array([t >= pd.Period('2012-01', 'M') for t in btc.index])
for h in (3, 4, 5):
    g = fwd(p, 12 * h)
    ok = mask & ~np.isnan(g) & ~np.isnan(capm_t)
    rel = (1 + g[ok]) / (1 + capm_t[ok]) - 1
    Kh = (1 + rel) ** h
    print(f'h={h}: n={ok.sum()} CAPM rate mean {np.mean(capm_t[ok]):.3f}, average miss {Kh.mean() ** (1 / h) - 1:+.3f}, '
          f'median {np.median(rel):+.3f}, beaten {(rel > 0).mean():.2f}')
