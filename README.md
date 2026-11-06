# Bitcoin's Expected Return: An Age Rule That Beats Current Practice

Agisilaos Papadogiannis, Independent Researcher (PhD, MBA). Correspondence: apapadogiannis@gmail.com. ORCID: [0009-0002-7753-7052](https://orcid.org/0009-0002-7753-7052)

Working paper, November 2026. This repository holds the paper, every data file it uses, the scripts that produce every exhibit, and the results they generate. Running `./run_all.sh` regenerates all of it in about a minute.

## What the paper does

It backtests the ways practitioners set Bitcoin's long-run expected return (constant rates of 7–21% a year, the level of institutional capital market assumptions; Bitcoin's own past growth; trend models; a CAPM rate) against the returns that followed over rolling three- to five-year periods since 2012, with gold as a control and Ether as a younger comparison. The institutional rates were beaten in about nine periods in ten; Bitcoin's long-run average growth was almost never beaten. An **age rule** implicit in Bitcoin's power-law price trend comes closest: in log terms, Bitcoin's expected return is its power-law exponent (about 5.6) divided by its age in years, a forecast of about 32% a year for September 2026 to 2031.

## Layout

```
paper/      the paper (PDF) and its LaTeX source with figures
data/       input data (see Sources below)
analysis/   one script per exhibit or calculation; python3 -I <script>.py DATA_DIR OUT_DIR
results/    everything the scripts write: CSV tables, LaTeX table bodies, figures
run_all.sh  runs the scripts in the right order
```

## Reproducing the results

```
pip install -r requirements.txt
./run_all.sh
```

Python 3.11+ with numpy, pandas, matplotlib, statsmodels and openpyxl. The scripts are deterministic (fixed random seeds for the bootstraps); re-running them reproduces the files in `results/` exactly.

| Script | What it produces | Where it appears |
|---|---|---|
| `anchor_flip.py` | How often the outcome changes across comparison rates | input to `section5.py` |
| `robustness.py` | Bootstrap draws for the trend models | input to `section5.py` |
| `section5.py` | Monthly series, candidate rates and the backtest machinery shared by the other scripts | used by the other scripts |
| `calibration.py` | Miss, median miss, share beaten, by rate and horizon | Exhibits A2–A3 |
| `today_rates.py`, `today_rates_h.py` | What each method implies today, by horizon | Exhibit A2 |
| `expected_return_bands.py` | Average miss with 95% stationary-bootstrap bands; gold candidates | Exhibit 1, Exhibit A3 |
| `fig_main.py` | Exhibit 1 | Section 4 |
| `fig_agerule.py` | The age rule in real time: exponent, forecast and realized return | Exhibit 2 |
| `fig_agerule_eth.py` | The same for Ether | Exhibit 3 |
| `btc_formula.py`, `formula_ci.py` | Age-rule arithmetic and the exponent's confidence interval | Sections 4–5, Appendix A.3 |
| `capm_required.py` | CAPM required returns and betas | Section 6, Appendix A.3 |
| `adoption.py` | Price, age and adoption: stationarity and cointegration tests | Exhibit A4 |
| `post_publication.py` | Periods beginning after the power law was published | Exhibit A5 |
| `ether_gold_today.py` | Ether and gold rates today | Section 7 |
| `make_btc_monthly.py` | Builds `data/btc_monthly.csv` from the raw Bitstamp candles (not included, see below) | Appendix A.1 |

## Data

All files in `data/` are redistributed from public sources and are used in the paper as described in its Appendix A.1.

| File | Content | Source |
|---|---|---|
| `btc_monthly.csv` | Bitstamp BTC/USD month-end close, Jan 2012–Oct 2026 | Derived with `analysis/make_btc_monthly.py` from the one-minute candles in [ff137/bitstamp-btcusd-minute-data](https://github.com/ff137/bitstamp-btcusd-minute-data) (about 150 MB, not included) |
| `cm_btc.csv`, `cm_eth.csv` | Daily reference price and address counts for Bitcoin and Ether | [Coin Metrics Community Network Data](https://github.com/coinmetrics/data), accessed 31 October 2026; redistributed under Coin Metrics' community-data terms (attribution, non-commercial) |
| `gold_monthly.csv` | Monthly gold price, USD per ounce, from 1833 | [datasets/gold-prices](https://github.com/datasets/gold-prices) (World Bank Commodity Markets / Bundesbank), accessed 31 October 2026 |
| `sp500.csv` | Shiller monthly S&P 500 price, dividends, CPI and long rate from 1871 | [datasets/s-and-p-500](https://github.com/datasets/s-and-p-500), accessed 31 October 2026 |
| `cpi_fred_2023_2026.csv` | CPI-U, not seasonally adjusted, Jan 2023 on | FRED series CPIAUCNS, accessed 3 November 2026 |
| `gs10_fred_2023_2026.csv` | Ten-year Treasury yield, Jan 2023 on | FRED series GS10, accessed 3 November 2026 |

Samples end in September 2026 (April 2026 for Ether and the address counts).

## Citation

Papadogiannis, A. 2026. "Bitcoin's Expected Return: An Age Rule That Beats Current Practice." Working paper. https://github.com/apapadogiannis/bitcoin-age-rule

## Licence

Code: MIT. Paper: all rights reserved, provided for reading and citation. Data: the terms of the sources above.
