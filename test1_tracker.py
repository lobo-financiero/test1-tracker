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
st.write("📡 Fetching price data...")
price_data = {}
errors = []

for symbol in tickers + [benchmark]:
    s = fetch_fmp_price_history(symbol, purchase_date, today)
    if not s.empty:
        price_data[symbol] = s
    else:
        errors.append(symbol)

if errors:
    st.error(f"❌ Some tickers failed to load: {', '.join(errors)}")
else:
    st.success("✅ All data loaded successfully.")


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

import plotly.graph_objects as go

# === Build DataFrame for display/charting ===
data = {**returns, "Portfolio": portfolio_return, "SPY": spy_return}
df = pd.DataFrame.from_dict(data, orient="index", columns=["Return (%)"]).dropna()
df = df.loc[[t for t in tickers if t in df.index] + ["Portfolio", "SPY"]]

# === Prepare chart inputs ===
bar_labels = [i for i in df.index]
bar_returns = df["Return (%)"].tolist()
bar_colors = ["#97E956" if val > 0 else "#F44A46" for val in bar_returns]

# Portfolio and SPY coloring
if "Portfolio" in bar_labels:
    idx = bar_labels.index("Portfolio")
    bar_colors[idx] = "#057DC9"
if "SPY" in bar_labels:
    idx = bar_labels.index("SPY")
    bar_colors[idx] = "orange"

# === Build Plotly chart ===
fig = go.Figure(
    data=[go.Bar(
        x=bar_labels,
        y=bar_returns,
        marker_color=bar_colors,
        text=[f"{r:.1f}%" for r in bar_returns],
        textposition="outside"
    )]
)

fig.update_layout(
    template="plotly_dark",
    title=f"Test 1 Returns Since {purchase_date}",
    yaxis_title="Return (%)",
    xaxis_title="",
    showlegend=False,
    height=500,
    width=700
)

# Optional separator line
sep_index = len(tickers) - 0.5
fig.add_shape(
    type="line",
    x0=sep_index, x1=sep_index,
    y0=min(bar_returns) * 1.1,
    y1=max(bar_returns) * 1.1,
    line=dict(color="white", width=1, dash="dot")
)

fig.update_yaxes(showgrid=True, zeroline=True, zerolinewidth=1, zerolinecolor='gray')

# === Layout side-by-side ===
col1, col2 = st.columns([2, 1])
with col1:
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.dataframe(df.style.format({"Return (%)": "{:.2f}"}))
