import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# === Configuration ===
tickers = ["A", "MSCI", "JPM", "KDP", "OTIS", "PANW", "CTAS", "NTAP", "RMD"]
benchmark = "SPY"
investment = 100
#purchase_date = "2025-04-29"
purchase_date = "2023-05-01"
today = datetime.today().strftime("%Y-%m-%d")

# === Fetch price data ===
df_all = yf.download(tickers + [benchmark], start=purchase_date)["Close"]
# Check which tickers returned actual data
st.subheader("🔍 Ticker Coverage")
available_tickers = [ticker for ticker in df_all.columns if df_all[ticker].dropna().any()]
missing_tickers = [ticker for ticker in tickers + [benchmark] if ticker not in available_tickers]
st.write("✅ Available:", available_tickers)
st.write("❌ Missing or empty:", missing_tickers)



# === Calculate returns ===
returns = {}
for ticker in tickers:
    try:
        s = df_all[ticker].dropna()
        buy = s.iloc[0]
        now = s.iloc[-1]
        value = (investment / buy) * now
        ret = ((value - investment) / investment) * 100
        returns[ticker] = ret
    except:
        returns[ticker] = None

# Portfolio
valid_returns = [returns[t] for t in tickers if returns[t] is not None]
portfolio_return = sum(valid_returns) / len(valid_returns) if valid_returns else None

# SPY
spy = df_all[benchmark].dropna()
spy_return = ((spy.iloc[-1] - spy.iloc[0]) / spy.iloc[0]) * 100 if not spy.empty else None

# === Streamlit UI ===
st.title("📊 Test 1 Portfolio Tracker")
st.markdown(f"Tracking from **{purchase_date}** to **{today}**")

data = {**returns, "Portfolio": portfolio_return, "SPY": spy_return}
df = pd.DataFrame.from_dict(data, orient="index", columns=["Return (%)"]).dropna()

# === Bar Chart ===
colors = ["blue" if idx == "Portfolio" else "orange" if idx == "SPY" else ("green" if val > 0 else "red") for idx, val in df["Return (%)"].items()]
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(df.index, df["Return (%)"], color=colors)

# Add % labels
for bar, val in zip(bars, df["Return (%)"]):
    ax.text(bar.get_x() + bar.get_width()/2, val, f"{val:.1f}%", ha='center', va='bottom' if val >= 0 else 'top')

ax.axhline(0, color='gray', linestyle='--', linewidth=1)
ax.set_ylabel("Return (%)")
ax.set_title("Test 1 Stock Returns vs Portfolio vs SPY")
st.pyplot(fig)

# Optional: show table
st.dataframe(df.style.format({"Return (%)": "{:.2f}"}))
