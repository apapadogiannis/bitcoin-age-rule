"""Build data/btc_monthly.csv (month-end close of Bitstamp BTC/USD) from the one-minute candle files of the
Kaggle dataset "Bitcoin Historical Data" (ff137 2026): btcusd_1-min_data.csv (history) and the latest-data file.
Usage: python3 make_btc_monthly.py HIST_CSV[.gz] LATEST_CSV OUT_CSV"""
import sys, pandas as pd
hist, latest, out = sys.argv[1:4]
d = pd.concat([pd.read_csv(hist, usecols=['timestamp', 'close']), pd.read_csv(latest, usecols=['timestamp', 'close'])])
d = d.dropna().drop_duplicates('timestamp').sort_values('timestamp')
d['dt'] = pd.to_datetime(d.timestamp, unit='s', utc=True).dt.to_period('M')
m = d.groupby('dt').close.last().reset_index()
m.to_csv(out, index=False); print(m.tail(3))
