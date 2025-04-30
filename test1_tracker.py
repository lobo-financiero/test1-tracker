import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import datetime

# === CONFIGURATION ===
tickers = ["NVDA", "MSCI", "JPM", "KDP", "OTIS", "PANW", "CTAS", "NTAP", "RMD"]
benchmark = "SPY"
investment = 100
purchase_date = "2025-04-29"
today = datetime.today().strftime("%Y-%m-%d")

st.set_page_config(page_title="Test 1 Portfolio Tracker", layout="wide")
st.title("📊 Test 1 Portfolio Tracker (via FMP)")
st.markdown(f"Tracking from **{purchase_date}** to **{today}**")

# === FMP price fetcher ===
@st.cache_data(ttl=86400)  # Cache for 1 day
def fetch_fmp_price_history(symbol, from_date, to_date):
    api_key = st.secrets["FMP_API_KEY"]
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={from_date}&to={to_date}&apikey={api_key}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        hist = res.json().get("historical", [])
        if not hist:
            return pd.Series(dtype=float)
        df = pd.DataFrame(hist)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df.set_index("date", inplace=True)
        return df["close"]
    except Exception as e:
        st.write(f"❌ {symbol}: Failed → {e}")
        return pd.Series(dtype=float)

# === Fetch all data ===
price_data = {}
for symbol in tickers + [benchmark]:
    st.write(f"🔄 Fetching {symbol}...")
    s = fetch_fmp_price_history(symbol, purchase_date, today)
    if not s.empty:
        price_data[symbol] = s

# === Calculate returns ===
returns = {}
for symbol in tickers:
    s = price_data.get(symbol)
    if s is None or s.empty:
        continue
    buy = s.iloc[0]
    now = s.iloc[-1]
    value = (investment / buy) * now
    returns[symbol] = ((value - investment) / investment) * 100

# === Portfolio return ===
valid_returns = list(returns.values())
portfolio_return = sum(valid_returns) / len(valid_returns) if valid_returns else None

# === Benchmark return ===
spy = price_data.get(benchmark, pd.Series())
spy_return = ((spy.iloc[-1] - spy.iloc[0]) / spy.iloc[0]) * 100 if not spy.empty else None

# === Display results ===
data = {**returns, "Portfolio": portfolio_return, "SPY": spy_return}
df = pd.DataFrame.from_dict(data, orient="index", columns=["Return (%)"]).dropna()
df = df.loc[[t for t in tickers if t in df.index] + ["Portfolio", "SPY"]]

# === Chart ===
colors = ["#057DC9" if idx == "Portfolio" else
          "#F4A300" if idx == "SPY" else
          "#97E956" if val > 0 else "#F44A46"
          for idx, val in df["Return (%)"].items()]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(df.index, df["Return (%)"], color=colors)

for bar, val in zip(bars, df["Return (%)"]):
    ax.text(bar.get_x() + bar.get_width()/2, val, f"{val:.1f}%",
            ha='center', va='bottom' if val >= 0 else 'top', fontsize=10)

ax.axhline(0, color='gray', linestyle='--', linewidth=1)
ax.set_ylabel("Return (%)")
ax.set_title("Returns Since Purchase Date")
plt.xticks(rotation=45)
st.pyplot(fig)

st.dataframe(df.style.format({"Return (%)": "{:.2f}"}))
