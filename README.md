# Bitcoin's Expected Return: An Age Rule That Beats Current Practice

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24004326.svg)](https://doi.org/10.5281/zenodo.24004326)

Replication package for the working paper by Agisilaos Papadogiannis (November 2026).
Paper: `paper/manuscript.pdf`. Archived on Zenodo: [doi:10.5281/zenodo.24004326](https://doi.org/10.5281/zenodo.24004326) (concept DOI, always resolves to the latest version; v1.0 is 10.5281/zenodo.24004327).

Companion paper: [Bitcoin's Required Return](https://github.com/apapadogiannis/bitcoin-required-return) ([doi:10.5281/zenodo.24003938](https://doi.org/10.5281/zenodo.24003938)).

## What this is

A backtest of the ways practitioners set Bitcoin's long-run expected return, against the
returns that followed over rolling three- to five-year periods since 2012, with gold as a
control and Ether as a younger comparison:

1. **The rates used in practice fail.** Constant rates of 7–21% a year (the level of
   institutional capital market assumptions) were beaten in about nine periods in ten;
   Bitcoin's own long-run average growth was almost never beaten.
2. **The age rule comes closest.** In log terms, Bitcoin's expected return is its
   power-law exponent (about 5.6) divided by its age in years: about 32% a year for
   September 2026 to 2031, far above a CAPM required return of 6–18%.

## Layout

```
scripts/    one script per exhibit or calculation (see below)
outputs/    all result tables used in the paper (CSV, LaTeX table bodies)
figures/    all paper exhibits
paper/      the manuscript PDF and LaTeX source
data/       all input data (see Data and licensing)
```

## Reproducing

Requirements: Python 3.11+, `pip install -r requirements.txt` (pandas, numpy,
matplotlib, statsmodels, openpyxl).

```bash
./run_all.sh    # runs every script below in order, about a minute
```

The scripts are deterministic (fixed random seeds for the bootstraps); re-running them
reproduces `outputs/` and `figures/` exactly. Each takes `python3 -I <script>.py DATA_DIR OUT_DIR`.

| Script | What it produces | Where it appears |
|---|---|---|
| `anchor_flip.py` | How often the outcome changes across comparison rates | input to `section5.py` |
| `robustness.py` | Bootstrap draws for the trend models | input to `section5.py` |
| `section5.py` | Monthly series, candidate rates and the backtest machinery | used by the other scripts |
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
| `make_btc_monthly.py` | Builds `data/btc_monthly.csv` from the raw Bitstamp candles | Appendix A.1 |

## Data and licensing

- Bitcoin price: `btc_monthly.csv`, Bitstamp BTC/USD month-end close, built with
  `scripts/make_btc_monthly.py` from the one-minute candles in
  [ff137/bitstamp-btcusd-minute-data](https://github.com/ff137/bitstamp-btcusd-minute-data)
  (about 150 MB, not included).
- Crypto reference prices and address counts: `cm_btc.csv`, `cm_eth.csv`, from
  [Coin Metrics community data](https://github.com/coinmetrics/data) (CC BY-NC 4.0;
  redistributed here with attribution, non-commercial use only).
- Gold: `gold_monthly.csv`, from [datasets/gold-prices](https://github.com/datasets/gold-prices)
  (World Bank Commodity Markets).
- S&P 500, CPI and long rate to 2022: `sp500.csv`, Shiller data via
  [datasets/s-and-p-500](https://github.com/datasets/s-and-p-500).
- CPI and ten-year Treasury yield from 2023: `cpi_fred_2023_2026.csv`,
  `gs10_fred_2023_2026.csv`, FRED series CPIAUCNS and GS10.
- Samples end in September 2026 (April 2026 for Ether and the address counts); data
  accessed 31 October to 3 November 2026.
- Code: MIT License. Output tables and figures (`outputs/`, `figures/`): CC BY 4.0, cite the paper.

## Citation

> Papadogiannis, A. (2026). "Bitcoin's Expected Return: An Age Rule That Beats Current Practice." Working paper.
> https://doi.org/10.5281/zenodo.24004326

## Disclaimer

Independent research; no funding, no institutional position. Not investment advice.
