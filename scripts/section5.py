"""Section 5 numbers, LaTeX table bodies and figure. Usage: python3 -I section5.py DATA_DIR OUT_DIR"""
import sys
import numpy as np
import pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(20261031)

# ---------------- data ----------------
bs = pd.read_csv(f"{D}/btc_monthly.csv")
bs = pd.Series(bs.close.values, index=pd.PeriodIndex(bs.dt, freq="M"))[:"2026-09"]
cmb = pd.read_csv(f"{D}/cm_btc.csv", usecols=["time", "PriceUSD"]).dropna()
cmb["time"] = pd.to_datetime(cmb.time)
cmb = cmb.groupby(cmb.time.dt.to_period("M")).PriceUSD.last()
btc = pd.concat([cmb[:"2011-12"], bs["2012-01":]])["2010-08":]
cme = pd.read_csv(f"{D}/cm_eth.csv", usecols=["time", "PriceUSD"]).dropna()
cme["time"] = pd.to_datetime(cme.time)
eth = cme.groupby(cme.time.dt.to_period("M")).PriceUSD.last()["2015-08":"2026-04"]
g = pd.read_csv(f"{D}/gold_monthly.csv")
gold = pd.Series(g.Price.values, index=pd.PeriodIndex(g.Date, freq="M"))["1971-01":]
s = pd.read_csv(f"{D}/sp500.csv", parse_dates=["Date"])
s.index = s.Date.dt.to_period("M")
dy = (s.Dividend / s.SP500).where(s.Dividend > 0).ffill()
dy[dy.index > pd.Period("2023-06", "M")] = 0.013
spx = ((s.SP500 / s.SP500.shift(1)) * (1 + dy.shift(1) / 12)).fillna(1).cumprod()
GEN = {"BTC": pd.Timestamp("2009-01-03"), "ETH": pd.Timestamp("2015-07-30")}


def age_of(idx, gen):
    return np.array([(p.end_time.normalize() - gen).days for p in idx], float)


def fwd(p, m):
    o = np.full(len(p), np.nan); o[:len(p) - m] = (p[m:] / p[:-m]) ** (12 / m) - 1; return o


def b_exp(p, i0, min_m=36):
    o = np.full(len(p), np.nan); t = np.arange(i0 + min_m, len(p)); o[t] = (p[t] / p[i0]) ** (12 / (t - i0)) - 1; return o


def b_trail(p, L):
    o = np.full(len(p), np.nan); o[L:] = (p[L:] / p[:-L]) ** (12 / L) - 1; return o


def b_pl(p, age, m, min_m=36):
    x, y = np.log(age), np.log(p)
    Sx, Sy, Sxx, Sxy = np.cumsum(x), np.cumsum(y), np.cumsum(x * x), np.cumsum(x * y)
    o = np.full(len(p), np.nan)
    for t in range(min_m, len(p) - m):
        n = t + 1
        b = (n * Sxy[t] - Sx[t] * Sy[t]) / (n * Sxx[t] - Sx[t] ** 2)
        o[t] = (age[t + m] / age[t]) ** (b * 12 / m) - 1
    return o


def b_expdecay(p, m, L=48, min_obs=24):
    """real-time exponential decay of trailing L-month annualized log growth:
    ln(gL_s) = a + b*s fitted on s <= t (positive-growth months only);
    c = exp(predicted growth at horizon midpoint) - 1"""
    lp = np.log(p)
    gL = np.full(len(p), np.nan); gL[L:] = (lp[L:] - lp[:-L]) * 12 / L
    o = np.full(len(p), np.nan)
    for t in range(L, len(p)):
        s_ = np.arange(L, t + 1)
        v = gL[L:t + 1]
        ok = v > 0
        if ok.sum() < min_obs:
            continue
        b, a = np.polyfit(s_[ok], np.log(v[ok]), 1)
        o[t] = np.exp(np.exp(a + b * (t + m / 2))) - 1
    return o


def ext_tv(idx, ser):
    return ((ser / ser.shift(120)) ** 0.1 - 1).reindex(idx).values


def dis(gw, base, ext, mask):
    ok = mask & ~np.isnan(gw) & ~np.isnan(base) & ~np.isnan(ext)
    vb, ve = gw[ok] > base[ok], gw[ok] > ext[ok]
    return (vb != ve).mean(), 1 - vb.mean(), int(ok.sum())


def strategy_table(ser, name, win_from, starts, trails, horizons):
    p, idx = ser.values, ser.index
    age = age_of(idx, GEN[name])
    mask = np.array([t >= pd.Period(win_from, "M") for t in idx])
    rows = []
    for h in horizons:
        m = 12 * h
        gw = fwd(p, m)
        ext = {"7": np.full(len(p), .07), "10": np.full(len(p), .10), "12": np.full(len(p), .12),
               "gold": ext_tv(idx, gold), "spx": ext_tv(idx, spx)}
        bases = {}
        for st in starts:
            bases[f"CAGR since {pd.Period(st, 'M').strftime('%b %Y')}"] = b_exp(p, idx.get_loc(pd.Period(st, "M")))
        for L in trails:
            bases[f"Trailing {L}-year CAGR"] = b_trail(p, 12 * L)
        bases["Power-law trend, fitted to date"] = b_pl(p, age, m)
        bases["Exponential slowdown, fitted to date"] = b_expdecay(p, m)
        for bn, b in bases.items():
            d10, opt, n = dis(gw, b, ext["10"], mask)
            ds = [dis(gw, b, e, mask)[0] for e in ext.values()]
            rows.append(dict(asset=name, h=h, baseline=bn, n=n, dis10=d10, dis_min=min(ds), dis_max=max(ds), optimistic=opt))
    return pd.DataFrame(rows)


T5 = pd.concat([
    strategy_table(btc, "BTC", "2012-01", ["2010-08", "2012-01", "2013-01", "2014-01"], [3, 4, 7], [3, 4, 5]),
    strategy_table(eth, "ETH", "2015-08", ["2015-08", "2017-01"], [3, 4], [3, 5]),
])
T5.to_csv(f"{OUT}/strategy_table.csv", index=False)
pd.set_option("display.width", 220)
print(T5.round(3).to_string())

# ---------------- anchor-choice table (re-use first-round results) ----------------
A = pd.read_csv(f"{OUT}/anchor_flip_results.csv")
print(A[["asset", "h", "windows", "med_cagr", "flip_fixed", "flip_tv", "anchor_to_sd"]].round(3).to_string())


# ---------------- LaTeX fragments ----------------
def pct(x):
    return f"{100 * x:.0f}"


def rng_s(r):
    lo, hi = pct(r.dis_min), pct(r.dis_max)
    return f"{pct(r.dis10)} [{lo}--{hi}]" if lo != hi else f"{pct(r.dis10)}"


def t5_rows(asset, hs):
    out = []
    sub = T5[T5.asset == asset]
    if asset == "ETH":
        sub = sub[~sub.baseline.str.startswith("Exponential")]
    for bn in sub.baseline.unique():
        cells = [bn]
        for h in hs:
            r = sub[(sub.baseline == bn) & (sub.h == h)].iloc[0]
            cells += [str(r.n), rng_s(r), pct(r.optimistic)]
        out.append(" & ".join(cells) + r" \\")
    return "\n".join(out)


with open(f"{OUT}/tab_strategy_btc.tex", "w") as f:
    f.write(t5_rows("BTC", [3, 5]))
with open(f"{OUT}/tab_strategy_btc_h4.tex", "w") as f:
    f.write(t5_rows("BTC", [4]))
with open(f"{OUT}/tab_strategy_eth.tex", "w") as f:
    f.write(t5_rows("ETH", [3, 5]))

lab = {"BTC": ("Bitcoin", "2012--2026"), "ETH": ("Ether", "2015--2026"),
       "Gold (BTC sample)": ("Gold", "2012--2026"), "Gold (1971-)": ("Gold", "1971--2026"),
       "S&P500 TR (BTC sample)": ("S\\&P 500 TR", "2012--2026"), "S&P500 TR (1971-)": ("S\\&P 500 TR", "1971--2026")}
rows = []
for a in ["BTC", "ETH", "Gold (BTC sample)", "Gold (1971-)", "S&P500 TR (BTC sample)", "S&P500 TR (1971-)"]:
    r3 = A[(A.asset == a) & (A.h == 3)].iloc[0]
    r5 = A[(A.asset == a) & (A.h == 5)].iloc[0]
    rows.append(f"{lab[a][0]} & {lab[a][1]} & {int(r5.windows)} & {pct(r5.med_cagr)} & {pct(r3.flip_fixed)} & {pct(r5.flip_fixed)} & {pct(r5.flip_tv)} & {r5.anchor_to_sd:.2f}" + r" \\")
with open(f"{OUT}/tab_anchor.tex", "w") as f:
    f.write("\n".join(rows))

# ---------------- figure ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "serif", "font.serif": ["TeX Gyre Termes", "Liberation Serif"], "mathtext.fontset": "stix", "pdf.fonttype": 42, "axes.unicode_minus": False, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.9), gridspec_kw={"width_ratios": [1, 1.25]})
names = ["BTC", "ETH", "Gold (BTC sample)", "Gold (1971-)", "S&P500 TR (1971-)"]
xl = ["Bitcoin", "Ether", "Gold\n2012 on", "Gold\n1971 on", "S&P 500\n1971 on"]
v5 = [100 * A[(A.asset == n) & (A.h == 5)].flip_fixed.iloc[0] for n in names]
ax[0].bar(range(5), v5, color="0.35", width=0.6)
for i, v in enumerate(v5):
    ax[0].text(i, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
ax[0].set_xticks(range(5)); ax[0].set_xticklabels(xl, fontsize=7)
ax[0].set_ylim(0, 100); ax[0].set_ylabel("% of 5-year periods")
ax[0].set_title("(a) Which comparison asset: 7% vs 10% vs 12%", fontsize=9)
bl = ["CAGR since Jan 2012", "CAGR since Jan 2014", "Trailing 4-year CAGR",
      "Power-law trend, fitted to date", "Exponential slowdown, fitted to date"]
bx = ["CAGR\nsince 2012", "CAGR\nsince 2014", "Trailing\n4-year CAGR", "Power-law\ntrend", "Exponential\nslowdown"]
w = 0.38
for k, (h, col) in enumerate(((3, "0.65"), (5, "0.25"))):
    vals = [100 * T5[(T5.asset == "BTC") & (T5.h == h) & (T5.baseline == b)].dis10.iloc[0] for b in bl]
    ax[1].bar(np.arange(5) + (k - 0.5) * w, vals, width=w, color=col, label=f"$h={h}$")
ax[1].axhline(50, color="0.5", lw=0.6, ls="--")
ax[1].set_xticks(range(5)); ax[1].set_xticklabels(bx, fontsize=7)
ax[1].set_ylim(0, 100); ax[1].set_ylabel("% of Bitcoin periods")
ax[1].set_title("(b) Own history vs comparison asset at 10%", fontsize=9)
ax[1].legend(frameon=False, fontsize=8, loc="upper right")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_section5.pdf")
# chart data for the journal (Excel)
with pd.ExcelWriter(f"{OUT}/exhibit_chart_data.xlsx") as xw:
    pd.DataFrame({"Asset and sample": [x.replace("\n", " ") for x in xl], "Share of 5-year periods in which the reading flips across 7%, 10% and 12% (%)": [round(v, 1) for v in v5]}).to_excel(xw, sheet_name="Panel a", index=False)
    rows = []
    for b, lbl in zip(bl, bx):
        r = {"Own-history benchmark": lbl.replace("\n", " ")}
        for h in (3, 5):
            r[f"Disagreement with 10% benchmark, h={h} (%)"] = round(100 * T5[(T5.asset == "BTC") & (T5.h == h) & (T5.baseline == b)].dis10.iloc[0], 1)
        rows.append(r)
    pd.DataFrame(rows).to_excel(xw, sheet_name="Panel b", index=False)
print("figure written")


# ---------------- bootstrap table (from robustness.py draws) ----------------
B = pd.read_csv(f"{OUT}/robust_bootstrap_draws.csv")
ACT = {("BTC", 3): (0.905, 0.475, 0.028), ("BTC", 5): (0.938, 0.531, 0.043),
       ("ETH", 3): (0.737, 0.105, 0.065), ("ETH", 5): (0.909, 0.091, 0.029)}
lines = []
for (a, h), (de, dp, af) in ACT.items():
    first = True
    for model in ("no-decay null", "power-law decay"):
        for L in (12, 24):
            gB = B[(B.asset == a) & (B.h == h) & (B.model == model) & (B.block == L)]
            q = lambda c: f"{100*gB[c].quantile(.5):.0f} [{100*gB[c].quantile(.05):.0f}--{100*gB[c].quantile(.95):.0f}]"
            pv = (gB.dis_expanding >= de - 1e-9).mean()
            head = f"{'Bitcoin' if a=='BTC' else 'Ether'}, $h={h}$ & {100*de:.0f} / {100*dp:.0f} / {100*af:.0f}" if first else " & "
            lines.append(f"{head} & {'No slowdown' if model.startswith('no') else 'Slowdown (power law)'} & {L} & {q('dis_expanding')} & {pv:.3f} & {q('dis_powerlaw')} & {q('anchor_flip')} \\\\")
            first = False
    lines.append("\\addlinespace")
open(f"{OUT}/tab_bootstrap.tex", "w").write("\n".join(lines[:-1]))
print(open(f"{OUT}/tab_bootstrap.tex").read())
