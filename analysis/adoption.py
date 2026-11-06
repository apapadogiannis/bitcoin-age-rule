"""Is Bitcoin's age formula a spurious fit, and does adoption explain it?
(A) price on age:      ln P = alpha + beta ln A   -> stationarity of deviations (ADF, KPSS), half-life
(B/C) adoption:        ln N = a + b ln A          -> N = holder addresses (non-zero balance) or active addresses (Coin Metrics)
      Metcalfe-type:   ln P = c + d ln N          -> Engle-Granger cointegration; implied exponent b*d versus beta
HAC (Newey-West, 12 lags) confidence intervals. Address data end in April 2026.
Usage: python3 -I adoption.py DATA_DIR OUT_DIR   (reuses section5.py in the same folder for the price series)"""
import sys, os, io, runpy, contextlib, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint, kpss
warnings.filterwarnings('ignore')
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
btc = ns['btc']
d = pd.read_csv(f'{D}/cm_btc.csv', usecols=['time', 'AdrActCnt', 'AdrBalCnt']).dropna()
d['time'] = pd.to_datetime(d.time)
g = d.groupby(d.time.dt.to_period('M'))
MEAS = {'holders': g.AdrBalCnt.mean(), 'active': g.AdrActCnt.mean()}
END = pd.Period('2026-04', 'M')
def hac(y, x):
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type='HAC', cov_kwds={'maxlags': 12})
    return m.params[1], m.params[1] - 1.96 * m.bse[1], m.params[1] + 1.96 * m.bse[1], m
rows = []
for start in ('2010-08', '2012-01', '2016-01'):
    idx = btc.index[(btc.index >= pd.Period(start, 'M')) & (btc.index <= END)]
    lP = np.log(btc.loc[idx].values)
    lA = np.log(np.array([(p.end_time.normalize() - pd.Timestamp('2009-01-03')).days / 365.25 for p in idx]))
    beta, _, _, m3 = hac(lP, lA); e = m3.resid; ar1 = np.corrcoef(e[1:], e[:-1])[0, 1]
    r = dict(start=start, n=len(idx), beta=beta, r2=m3.rsquared, adf_p=adfuller(e, autolag='AIC')[1],
             adf_stat=adfuller(e, autolag='AIC')[0], kpss_p=kpss(e, regression='c', nlags='auto')[1], halflife=np.log(.5) / np.log(ar1))
    for k, N in MEAS.items():
        lN = np.log(N.reindex(idx).values)
        b, blo, bhi, m1 = hac(lN, lA); dd, dlo, dhi, m2 = hac(lP, lN)
        r.update({f'{k}_b': b, f'{k}_b_lo': blo, f'{k}_b_hi': bhi, f'{k}_adf_p': adfuller(m1.resid, autolag='AIC')[1],
                  f'{k}_d': dd, f'{k}_d_lo': dlo, f'{k}_d_hi': dhi, f'{k}_eg_p': coint(lP, lN, trend='c')[1], f'{k}_bd': b * dd})
    rows.append(r)
R = pd.DataFrame(rows); pd.set_option('display.width', 250)
print(R.round(3).T.to_string()); R.to_csv(f'{OUT}/adoption_results.csv', index=False)
# real-time adoption exponents (January of each year, data from August 2010)
for y in (2016, 2026):
    idx = btc.index[(btc.index >= pd.Period('2010-08', 'M')) & (btc.index <= pd.Period(f'{y}-01', 'M'))]
    lA = np.log(np.array([(p.end_time.normalize() - pd.Timestamp('2009-01-03')).days / 365.25 for p in idx]))
    print(y, {k: round(np.polyfit(lA, np.log(N.reindex(idx).values), 1)[0], 2) for k, N in MEAS.items()})
# Exhibit D5 rows
f2 = lambda x: f'{x:.2f}'
pv = lambda x: '$<$0.01' if x < 0.01 else f'{x:.2f}'
ci = lambda r, k: f"{r[k]:.2f} ({r[k+'_lo']:.2f}--{r[k+'_hi']:.2f})"
row = lambda lab, fn: f"\\quad {lab} & " + ' & '.join(fn(r) for r in rows) + ' \\\\'
L = [r'\multicolumn{4}{l}{\textit{Price on age:} $\ln P=\alpha+\beta\ln A$}\\',
     row('Exponent $\\beta$', lambda r: f2(r['beta'])), row('$R^2$', lambda r: f2(r['r2'])),
     row('ADF test on deviations, $p$-value', lambda r: pv(r['adf_p'])),
     row('KPSS test on deviations, $p$-value', lambda r: '$\\geq$0.10' if r['kpss_p'] >= 0.1 else f2(r['kpss_p'])),
     row('Half-life of deviations (months)', lambda r: f"{r['halflife']:.0f}"), r'\addlinespace']
for k, lab in [('holders', 'Holder addresses (non-zero balance)'), ('active', 'Active addresses')]:
    L += [f'\\multicolumn{{4}}{{l}}{{\\textit{{{lab}:}} $\\ln N=a+b\\ln A$; $\\ln P=c+d\\ln N$}}\\\\',
          row('Adoption exponent $b$ (95\\% CI)', lambda r: ci(r, f'{k}_b')),
          row('ADF test on deviations of $\\ln N$, $p$-value', lambda r: pv(r[f'{k}_adf_p'])),
          row('Network exponent $d$ (95\\% CI)', lambda r: ci(r, f'{k}_d')),
          row('Engle--Granger test of no cointegration, $p$-value', lambda r: pv(r[f'{k}_eg_p'])),
          r'\addlinespace']
open(f'{OUT}/tab_adoption.tex', 'w').write('\n'.join(L[:-1])); print('\n'.join(L[:-1]))
