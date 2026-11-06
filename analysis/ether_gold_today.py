"""Ether backtest record across h=3-5 (all rules) and implied rates at the end of its sample (April 2026); gold implied rates at September 2026.
Usage: python3 -I ether_gold_today.py DATA_DIR OUT_DIR   (reuses functions from section5.py in the same folder)"""
import sys, os, io, runpy, contextlib
import numpy as np, pandas as pd
D, OUT = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['section5.py', D, OUT]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(here, 'section5.py'))
fwd, b_exp, b_trail, b_pl, b_ed, age_of, GEN, ext_tv = (ns[k] for k in ['fwd','b_exp','b_trail','b_pl','b_expdecay','age_of','GEN','ext_tv'])
eth, gold, spx = ns['eth'], ns['gold'], ns['spx']
p, idx = eth.values, eth.index; age = age_of(idx, GEN['ETH']); T = len(p)-1
print('ETH as of', idx[T], 'price', round(p[T],1), 'n months', len(p))
mask = np.array([t >= pd.Period('2015-08','M') for t in idx])
def pl_today(h):
    b,_ = np.polyfit(np.log(age[:T+1]), np.log(p[:T+1]), 1); return ((age[T]+365.25*h)/age[T])**(b/h)-1, b
rates = {'7%': lambda h: np.full(len(p), .07), '10%': lambda h: np.full(len(p), .10), '12%': lambda h: np.full(len(p), .12),
         'gold 10y': lambda h: ext_tv(idx, gold), 'S&P 10y': lambda h: ext_tv(idx, spx),
         'CAGR since Aug 2015': lambda h: b_exp(p, 0), 'Trailing 3y': lambda h: b_trail(p, 36), 'Trailing 4y': lambda h: b_trail(p, 48),
         'Power law': lambda h: b_pl(p, age, 12*h), 'ED 3y': lambda h: b_ed(p, 12*h, L=36), 'ED 4y': lambda h: b_ed(p, 12*h, L=48), 'ED 5y': lambda h: b_ed(p, 12*h, L=60)}
rows=[]
for k,f in rates.items():
    for h in (3,4,5):
        g = fwd(p, 12*h); c = f(h); ok = mask & ~np.isnan(g) & ~np.isnan(c)
        if ok.sum()==0: continue
        rel=(1+g[ok])/(1+c[ok])-1; Kh=(1+rel)**h
        rows.append(dict(rate=k,h=h,n=ok.sum(),avg=Kh.mean()**(1/h)-1,med=np.median(rel),beat=(rel>0).mean(),mad=np.abs(rel).mean()))
R=pd.DataFrame(rows); pd.set_option('display.width',200); print(R.round(3).to_string(index=False)); R.to_csv(f'{OUT}/ether_record.csv', index=False)
print('today: CAGR since 2015 %.3f, trailing3 %.3f trailing4 %.3f' % ((p[T]/p[0])**(12/T)-1, (p[T]/p[T-36])**(1/3)-1, (p[T]/p[T-48])**(1/4)-1))
for h in (3,5): print('PL h=%d %.3f beta %.2f' % (h, *pl_today(h)))
for L in (36,48,60): print('ED L=%d h=3 %.3f h=5 %.3f' % (L, b_ed(p,36,L=L)[T], b_ed(p,60,L=L)[T]))
r = np.diff(np.log(p)); print('vol since 2015 %.2f, last 4y %.2f' % (r.std(ddof=1)*np.sqrt(12), r[-48:].std(ddof=1)*np.sqrt(12)))
print('ETH price path (Jan each year):', {str(t): round(v) for t,v in eth.items() if t.month==1})
gp = gold.values
print('GOLD as of', gold.index[-1], 'trailing 10y %.3f, CAGR since Jan 1971 %.3f, S&P TR trailing 10y %.3f' % ((gp[-1]/gp[-121])**.1-1, (gp[-1]/gold.loc[pd.Period('1971-01','M')])**(12/(len(gold.loc['1971-01':])-1))-1, (spx.iloc[-1]/spx.iloc[-121])**.1-1))
