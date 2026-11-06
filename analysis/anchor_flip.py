import sys
import numpy as np
import pandas as pd

"""Outcome flips across comparison rates. Usage: python3 -I anchor_flip.py DATA_DIR OUT_DIR"""
D, OUT = sys.argv[1], sys.argv[2]

# ---------- load monthly series (month-end or monthly avg; PeriodIndex M) ----------
btc = pd.read_csv(f"{D}/btc_monthly.csv")
btc = pd.Series(btc.close.values, index=pd.PeriodIndex(btc.dt, freq="M"), name="BTC")
btc = btc[: "2026-09"]  # drop partial October

cm = pd.read_csv(f"{D}/cm_eth.csv", usecols=["time", "PriceUSD"]).dropna()
cm["time"] = pd.to_datetime(cm.time)
eth = cm.groupby(cm.time.dt.to_period("M")).PriceUSD.last()
eth = eth[: "2026-04"]  # drop partial May
eth.name = "ETH"

g = pd.read_csv(f"{D}/gold_monthly.csv")
gold = pd.Series(g.Price.values, index=pd.PeriodIndex(g.Date, freq="M"), name="Gold")

s = pd.read_csv(f"{D}/sp500.csv", parse_dates=["Date"])
s.index = s.Date.dt.to_period("M")
px = s.SP500
dy = (s.Dividend / s.SP500).where(s.Dividend > 0)  # annual dividend yield
dy = dy.ffill().fillna(0.013)
dy[dy.index > pd.Period("2023-06", "M")] = 0.013  # Shiller dividends end 2023-06
tr = (px / px.shift(1)) * (1 + dy.shift(1) / 12)
spx = tr.fillna(1).cumprod()
spx = spx["1871-02":]
spx.name = "S&P500 TR"

# synthetic staked ETH: ETH price x accrued staking yield (approximate net APR schedule)
apr = {2020: 0.055, 2021: 0.050, 2022: 0.045, 2023: 0.038, 2024: 0.032, 2025: 0.029, 2026: 0.028}
e = eth["2020-12":]
accr = pd.Series([(1 + apr[p.year]) ** (1 / 12) for p in e.index], index=e.index)
accr.iloc[0] = 1.0
steth = e * accr.cumprod()
steth.name = "Staked ETH (synthetic)"


def cagr_windows(p, h, start=None, end=None):
    """Realized CAGR for every monthly start date with a full h-year window."""
    m = 12 * h
    if start:
        p = p[start:]
    if end:
        p = p[:end]
    r = (p.shift(-m) / p) ** (1 / h) - 1
    return r.dropna()


def trailing_cagr(p, years):
    m = 12 * years
    return ((p / p.shift(m)) ** (1 / years) - 1)


FIX = [0.07, 0.10, 0.12]


def summarize(name, p, h, start=None, end=None, external=True):
    gw = cagr_windows(p, h, start, end)
    n = len(gw)
    lnK_std = (h * np.log1p(gw)).std()
    anchor_range = h * (np.log(1.12) - np.log(1.07))
    flip_fixed = ((gw > 0.07) & (gw <= 0.12)).mean()
    out = dict(asset=name, h=h, windows=n,
               first=str(gw.index[0]), last=str(gw.index[-1]),
               indep_approx=round(n / (12 * h) + 1, 1),
               med_cagr=gw.median(), p10=gw.quantile(.1), p90=gw.quantile(.9),
               pess_7=(gw > 0.07).mean(), pess_10=(gw > 0.10).mean(), pess_12=(gw > 0.12).mean(),
               flip_fixed=flip_fixed,
               anchor_range_lnK=anchor_range, lnK_sd=lnK_std,
               anchor_to_sd=anchor_range / lnK_std)
    if external:
        cg = trailing_cagr(gold, 10).reindex(gw.index)
        cs = trailing_cagr(spx, 10).reindex(gw.index)
        lo = np.minimum(cg, cs)
        hi = np.maximum(cg, cs)
        ok = lo.notna() & hi.notna()
        out["flip_tv"] = ((gw > lo) & (gw <= hi))[ok].mean()
        out["tv_band_width"] = (hi - lo)[ok].mean()
    # self-referential: expanding-window trailing CAGR of the asset itself (min 3y history)
    first = pd.Period(SELF_START.get(name.split(" (")[0], str(p.dropna().index[0])), "M")
    yrs = pd.Series([(t - first).n / 12 for t in gw.index], index=gw.index)
    selfc = pd.Series([(p[t] / p[first]) ** (1 / y) - 1 if y >= 3 else np.nan
                       for t, y in zip(gw.index, yrs)], index=gw.index)
    ok = selfc.notna()
    if ok.sum() > 0:
        v_self = gw[ok] > selfc[ok]
        v_ext = gw[ok] > 0.10
        out["self_windows"] = int(ok.sum())
        out["self_c_median"] = selfc[ok].median()
        out["self_vs_ext10_disagree"] = (v_self != v_ext).mean()
        out["self_pess_share"] = v_self.mean()
    # robustness: rolling trailing-4y own CAGR as the self-referential baseline
    s4 = trailing_cagr(p, 4).reindex(gw.index)
    ok4 = s4.notna()
    if ok4.sum() > 0:
        out["self4_vs_ext10_disagree"] = ((gw[ok4] > s4[ok4]) != (gw[ok4] > 0.10)).mean()
    return out


SELF_START = {"BTC": "2012-01", "Gold": "1971-01", "S&P500 TR": "1926-01", "ETH": "2015-08"}


rows = []
for h in (3, 5):
    rows.append(summarize("BTC", btc, h, "2012-01"))
    rows.append(summarize("Gold (BTC sample)", gold, h, "2012-01"))
    rows.append(summarize("Gold (1971-)", gold, h, "1971-01"))
    rows.append(summarize("S&P500 TR (BTC sample)", spx, h, "2012-01"))
    rows.append(summarize("S&P500 TR (1971-)", spx, h, "1971-01"))
    rows.append(summarize("ETH", eth, h, "2015-08"))
rows.append(summarize("ETH (staking sample)", eth, 3, "2020-12"))
rows.append(summarize("Staked ETH (synthetic)", steth, 3, "2020-12"))

res = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_columns", 40)
print(res.round(3).to_string())
res.to_csv(f"{OUT}/anchor_flip_results.csv", index=False)

# ---------- peer-anchored vs heuristic-anchored K for staked ETH ----------
h = 3
gs = cagr_windows(steth, h, "2020-12")
ge = cagr_windows(eth, h, "2020-12").reindex(gs.index)
lnK_peer = h * np.log1p(gs) - h * np.log1p(ge)  # peer = realized unstaked ETH
lnK_heur10 = h * np.log1p(gs) - h * np.log(1.10)
print("\nStaked ETH, h=3, windows:", len(gs))
print("peer-anchored lnK: mean %.3f sd %.4f  share K>1 %.2f" % (lnK_peer.mean(), lnK_peer.std(), (lnK_peer > 0).mean()))
print("heuristic(10%%) lnK: mean %.3f sd %.4f  share K>1 %.2f" % (lnK_heur10.mean(), lnK_heur10.std(), (lnK_heur10 > 0).mean()))

# ---------- sanity checks against closed form ----------
gw = cagr_windows(btc, 5, "2012-01")
k07 = gw.index[0]
p0, p1 = btc[k07], btc[k07 + 60]
K_direct = p1 / (p0 * 1.07 ** 5)
K_form = np.exp(5 * np.log1p(gw[k07]) - 5 * np.log(1.07))
ceff = 1.07 * K_direct ** (-1 / 5) - 1
ceff_form = 1.07 ** 2 / (1 + gw[k07]) - 1
print("\ncheck K:", K_direct, K_form, " c_eff:", ceff, ceff_form)
