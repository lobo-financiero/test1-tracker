import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.graph_objects as go
from pandas.tseries.offsets import BDay

# === CONFIGURATION ===
purchase_date = "2025-05-15"
today = (datetime.today() - BDay(1)).strftime("%Y-%m-%d")
benchmark = "SPY"
investment = 100

# === Ticker groups ===
tickers_50 = [
    "MTCH","IVZ","HAS","APA","AES","MOS","PARA","MKTX","CZR","NCLH",
    "HSIC","ALB","MHK","ENPH","LW","WBA","HII","CRL","WYNN","AMCR",
    "MSCI","GNRC","HAL","FRT","MAR","TDG","FICO","HPQ","AZO","MGM",
    "HST","HRL","LKQ","KDP","DELL","VRSN","BKNG","CPB","WDAY","MAS",
    "SMCI","FCX","EQT","VTRS","AIZ","BF-B","AME","CDNS","CSX","HPE"

]
tickers_10 = tickers_50[:10]
tickers_30 = tickers_50[:30]

# === Streamlit Setup ===
st.set_page_config(page_title="XGB Classifier Portfolio Monitor", layout="wide")
st.title("✨ Orion Portfolio Monitor")
st.markdown(f"Tracking real returns from **{purchase_date}** to **{today}**")

# === FMP price fetcher ===
@st.cache_data(ttl=86400)
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

for symbol in tickers_50 + [benchmark]:
    s = fetch_fmp_price_history(symbol, purchase_date, today)
    if not s.empty:
        price_data[symbol] = s
    else:
        errors.append(symbol)

if errors:
    st.error(f"❌ Failed tickers: {', '.join(errors)}")
else:
    st.success("✅ All price data loaded")

# === Calculate returns ===
returns = {}
for symbol in tickers_50:
    s = price_data.get(symbol)
    if s is None or s.empty:
        continue
    buy = s.iloc[0]
    now = s.iloc[-1]
    value = (investment / buy) * now
    returns[symbol] = ((value - investment) / investment) * 100

# === Portfolio Aggregates ===
def portfolio_return(symbols):
    vals = [returns[s] for s in symbols if s in returns]
    return sum(vals) / len(vals) if vals else None

top10_return = portfolio_return(tickers_10)
top30_return = portfolio_return(tickers_30)
top50_return = portfolio_return(tickers_50)

# === Benchmark Return ===
spy = price_data.get(benchmark, pd.Series())
spy_return = ((spy.iloc[-1] - spy.iloc[0]) / spy.iloc[0]) * 100 if not spy.empty else None

# === Prepare Chart ===
bar_labels = tickers_10 + ["🔝 Top 10", "🧰 Top 30", "📦 Top 50", "📈 SPY"]
bar_returns = [returns.get(t, 0) for t in tickers_10] + [
    top10_return, top30_return, top50_return, spy_return
]
bar_colors = (
    ["#97E956" if r > 0 else "#F44A46" for r in bar_returns[:10]] +
    ["#057DC9", "#288CFF", "#4FB7FF", "orange"]
)

fig = go.Figure(
    data=[go.Bar(
        x=bar_labels,
        y=bar_returns,
        marker_color=bar_colors,
        text=[f"{r:.1f}%" if r is not None else "N/A" for r in bar_returns],
        textposition="outside"
    )]
)

fig.update_layout(
    template="plotly_dark",
    title=f"Returns Since {purchase_date}",
    yaxis_title="Return (%)",
    xaxis_title="",
    showlegend=False,
    height=550
)

# === Display chart ===
st.plotly_chart(fig, use_container_width=True)

# === Table of All 50 ===
df_50 = pd.DataFrame.from_dict(returns, orient="index", columns=["Return (%)"])
df_50.index.name = "Symbol"
df_50 = df_50.reset_index()

# Add Portfolio Label
def get_portfolio_label(ticker):
    if ticker in tickers_10:
        return "Top 10"
    elif ticker in tickers_30:
        return "Top 30"
    else:
        return "Top 50"

df_50["Portfolio"] = df_50["Symbol"].apply(get_portfolio_label)

# Add Predicted Rank
df_50["Prediction Rank"] = df_50["Symbol"].apply(lambda s: tickers_50.index(s) + 1 if s in tickers_50 else None)

# Reorder columns: Prediction Rank first
cols = ["Prediction Rank"] + [col for col in df_50.columns if col != "Prediction Rank"]
df_50 = df_50[cols]

# Sort by return (or keep original order)
df_50 = df_50.sort_values("Return (%)", ascending=False)

# Display styled table
st.markdown("### 📋 All 50 Stocks with Return")

st.dataframe(
    df_50.style
        .format({"Return (%)": "{:.2f}%"})
        .background_gradient(subset=["Return (%)"], cmap="Greens"),
    hide_index=True
)
