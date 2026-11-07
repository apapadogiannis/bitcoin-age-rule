"""Robustness checks for the benchmark-strategy result (self-referential vs external c)."""
import sys
import numpy as np
import pandas as pd

D = sys.argv[1]
OUT = sys.argv[2]
rng = np.random.default_rng(20261031)
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)

# ---------------- data ----------------
bs = pd.read_csv(f"{D}/btc_monthly.csv")
bs = pd.Series(bs.close.values, index=pd.PeriodIndex(bs.dt, freq="M"))[:"2026-09"]
cmb = pd.read_csv(f"{D}/cm_btc.csv", usecols=["time", "PriceUSD"]).dropna()
cmb["time"] = pd.to_datetime(cmb.time)
cmb = cmb.groupby(cmb.time.dt.to_period("M")).PriceUSD.last()
btc = pd.concat([cmb[:"2011-12"], bs["2012-01":]])
btc = btc["2010-08":]  # first full month in Coin Metrics
btc.name = "BTC"

cme = pd.read_csv(f"{D}/cm_eth.csv", usecols=["time", "PriceUSD"]).dropna()
cme["time"] = pd.to_datetime(cme.time)
eth = cme.groupby(cme.time.dt.to_period("M")).PriceUSD.last()["2015-08":"2026-04"]
eth.name = "ETH"

g = pd.read_csv(f"{D}/gold_monthly.csv")
gold = pd.Series(g.Price.values, index=pd.PeriodIndex(g.Date, freq="M"))["1971-01":]
gold.name = "Gold"

s = pd.read_csv(f"{D}/sp500.csv", parse_dates=["Date"])
s.index = s.Date.dt.to_period("M")
dy = (s.Dividend / s.SP500).where(s.Dividend > 0).ffill()
dy[dy.index > pd.Period("2023-06", "M")] = 0.013
spx = ((s.SP500 / s.SP500.shift(1)) * (1 + dy.shift(1) / 12)).fillna(1).cumprod()

GENESIS = {"BTC": pd.Timestamp("2009-01-03"), "ETH": pd.Timestamp("2015-07-30")}


# ---------------- helpers (numpy, index-based) ----------------
def fwd_cagr(p, m):
    """forward CAGR over m months for each start index; NaN where unavailable"""
    out = np.full(len(p), np.nan)
    out[: len(p) - m] = (p[m:] / p[:-m]) ** (12 / m) - 1
    return out


def base_expanding(p, i0, min_m=36):
    out = np.full(len(p), np.nan)
    t = np.arange(i0 + min_m, len(p))
    out[t] = (p[t] / p[i0]) ** (12 / (t - i0)) - 1
    return out


def base_trailing(p, L):
    out = np.full(len(p), np.nan)
    out[L:] = (p[L:] / p[:-L]) ** (12 / L) - 1
    return out


def base_powerlaw(p, age_days, m, i0=0, min_m=36):
    """real-time OLS of log p on log age using data i0..t; c = trend-to-trend CAGR over m months"""
    x = np.log(age_days)
    y = np.log(p)
    out = np.full(len(p), np.nan)
    Sx = np.cumsum(x[i0:]); Sy = np.cumsum(y[i0:]); Sxx = np.cumsum(x[i0:] ** 2); Sxy = np.cumsum(x[i0:] * y[i0:])
    for t in range(i0 + min_m, len(p) - m):
        k = t - i0
        n = k + 1
        b = (n * Sxy[k] - Sx[k] * Sy[k]) / (n * Sxx[k] - Sx[k] ** 2)
        out[t] = (age_days[t + m] / age_days[t]) ** (b * 12 / m) - 1
    return out


def ext_tv(index, which):
    c = ((which / which.shift(120)) ** (1 / 10) - 1)
    return c.reindex(index).values


def disagree(gw, base, ext, mask):
    ok = mask & ~np.isnan(gw) & ~np.isnan(base) & ~np.isnan(ext)
    if ok.sum() == 0:
        return np.nan, np.nan, 0
    v_b = gw[ok] > base[ok]
    v_e = gw[ok] > ext[ok]
    return (v_b != v_e).mean(), 1 - v_b.mean(), int(ok.sum())


def age_of(idx, genesis):
    return np.array([(p.end_time.normalize() - genesis).days for p in idx], dtype=float)


# ---------------- 1. deterministic grid ----------------
def grid(series, name, starts, trailing, horizons, sub_split, window_from):
    p = series.values
    idx = series.index
    age = age_of(idx, GENESIS[name]) if name in GENESIS else None
    rows = []
    wmask_base = np.array([t >= pd.Period(window_from, "M") for t in idx])
    for h in horizons:
        m = 12 * h
        gw = fwd_cagr(p, m)
        exts = {"7%": np.full(len(p), .07), "10%": np.full(len(p), .10), "12%": np.full(len(p), .12),
                "gold 10y": ext_tv(idx, gold), "S&P 10y": ext_tv(idx, spx)}
        bases = {}
        for st in starts:
            i0 = idx.get_loc(pd.Period(st, "M"))
            bases[f"expanding from {st}"] = base_expanding(p, i0)
        for L in trailing:
            bases[f"trailing {L}y"] = base_trailing(p, 12 * L)
        if age is not None:
            bases["power law (real-time)"] = base_powerlaw(p, age, m)
        for bn, b in bases.items():
            for sub in ("all", "early", "late"):
                if sub == "all":
                    mask = wmask_base
                elif sub == "early":
                    mask = wmask_base & np.array([t < pd.Period(sub_split, "M") for t in idx])
                else:
                    mask = np.array([t >= pd.Period(sub_split, "M") for t in idx])
                r = dict(asset=name, h=h, baseline=bn, subsample=sub)
                for en, e in exts.items():
                    d, opt, n = disagree(gw, b, e, mask)
                    r[f"dis_{en}"] = d
                    r["n"] = max(r.get("n", 0), n)
                    if en == "10%":
                        r["self_says_optimistic"] = opt
                        r["n_10"] = n
                rows.append(r)
    return pd.DataFrame(rows)


G = pd.concat([
    grid(btc, "BTC", ["2010-08", "2011-01", "2012-01", "2013-01", "2014-01"], [3, 4, 5, 7], [3, 4, 5], "2017-01", "2012-01"),
    grid(eth, "ETH", ["2015-08", "2016-01", "2017-01"], [3, 4, 5], [3, 5], "2019-01", "2015-08"),
    grid(gold, "Gold", ["1971-01", "1980-01", "2000-01"], [3, 5, 10], [3, 5], "2000-01", "1971-01"),
])
G.to_csv(f"{OUT}/robust_grid.csv", index=False)
cols = ["asset", "h", "baseline", "subsample", "n_10", "self_says_optimistic", "dis_7%", "dis_10%", "dis_12%", "dis_gold 10y", "dis_S&P 10y"]
print("=== Deterministic grid (disagreement between self-referential and external verdicts) ===")
print(G[G.subsample == "all"][cols].round(2).to_string(index=False))
print("\n=== Sub-periods, h=3 (BTC split 2017-01; ETH 2019-01; gold 2000-01) ===")
print(G[(G.subsample != "all") & (G.h == 3)][cols].round(2).to_string(index=False))


# ---------------- 2. block bootstraps ----------------
def stationary_idx(n, L):
    out = np.empty(n, dtype=int)
    out[0] = rng.integers(n)
    for i in range(1, n):
        out[i] = rng.integers(n) if rng.random() < 1 / L else (out[i - 1] + 1) % n
    return out


def boot(series, name, start, h, Ls=(12, 24), reps=2000, pre=None):
    """returns distribution of: disagreement (expanding-from-start vs 10%), disagreement (power law vs 10%),
    anchor flip share (7-12%), under (a) no-decay null and (b) power-law decay model"""
    m = 12 * h
    sub = series[start:]
    p = sub.values
    lr = np.diff(np.log(p))
    idx = sub.index
    pre_p = series[:start].values[:-1] if pre is None else pre
    full_idx = series.index
    age_full = age_of(full_idx, GENESIS[name])
    # power-law trend on full available history (for the decay model)
    xf, yf = np.log(age_full), np.log(series.values)
    bf, af = np.polyfit(xf, yf, 1)
    trend = af + bf * np.log(age_of(idx, GENESIS[name]))
    d = np.diff(trend)
    resid = lr - d
    resid = resid - resid.mean()  # residuals centred: drift comes only from the trend
    n_pre = len(pre_p)
    res = []
    for model in ("no-decay null", "power-law decay"):
        for L in Ls:
            for _ in range(reps):
                j = stationary_idx(len(lr), L)
                r = lr[j] if model == "no-decay null" else d + resid[j]
                path = p[0] * np.exp(np.concatenate([[0], np.cumsum(r)]))
                gw = fwd_cagr(path, m)
                b_exp = base_expanding(path, 0)
                fullpath = np.concatenate([pre_p, path])
                b_pl = base_powerlaw(fullpath, age_full, m)[n_pre:]
                ten = np.full(len(path), .10)
                d1, _, _ = disagree(gw, b_exp, ten, np.ones(len(path), bool))
                d2, _, _ = disagree(gw, b_pl, ten, np.ones(len(path), bool))
                ok = ~np.isnan(gw)
                flip = ((gw[ok] > .07) & (gw[ok] <= .12)).mean()
                res.append(dict(asset=name, h=h, model=model, block=L, dis_expanding=d1, dis_powerlaw=d2, anchor_flip=flip))
    return pd.DataFrame(res), bf


def actual(series, name, start, h):
    m = 12 * h
    sub = series[start:]
    p = sub.values
    gw = fwd_cagr(p, m)
    ten = np.full(len(p), .10)
    age_full = age_of(series.index, GENESIS[name])
    n_pre = len(series[:start]) - 1
    b_pl = base_powerlaw(series.values, age_full, m)[n_pre:]
    ok = ~np.isnan(gw)
    return dict(dis_expanding=disagree(gw, base_expanding(p, 0), ten, np.ones(len(p), bool))[0],
                dis_powerlaw=disagree(gw, b_pl, ten, np.ones(len(p), bool))[0],
                anchor_flip=((gw[ok] > .07) & (gw[ok] <= .12)).mean())


print("\n=== Block bootstrap (2,000 reps per cell; 5th / 50th / 95th percentiles) ===")
allb = []
for name, ser, st in (("BTC", btc, "2012-01"), ("ETH", eth, "2015-08")):
    for h in (3, 5):
        if name == "ETH" and h == 5:
            pass
        B, bf = boot(ser, name, st, h, reps=2000 if name == "BTC" else 1000)
        allb.append(B)
        a = actual(ser, name, st, h)
        print(f"\n{name} h={h}  power-law slope (full sample) = {bf:.2f}   actual: " + ", ".join(f"{k}={v:.2f}" for k, v in a.items()))
        q = B.groupby(["model", "block"])[["dis_expanding", "dis_powerlaw", "anchor_flip"]].quantile([.05, .5, .95]).unstack()
        print(q.round(2).to_string())
pd.concat(allb).to_csv(f"{OUT}/robust_bootstrap_draws.csv", index=False)
