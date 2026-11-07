#!/usr/bin/env bash
# Reproduces every number, table body and figure in the paper. Runs in about a minute.
set -e
cd "$(dirname "$0")/scripts"
mkdir -p ../outputs ../figures
for f in anchor_flip robustness section5 calibration today_rates today_rates_h capm_required \
         expected_return_bands formula_ci btc_formula adoption ether_gold_today post_publication \
         fig_main fig_agerule fig_agerule_eth; do
  echo "== $f"; python3 -I "$f.py" ../data ../outputs
done
mv -f ../outputs/*.pdf ../outputs/*.png ../figures/
