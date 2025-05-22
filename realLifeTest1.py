import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit import cache_data

# --- Parameters ---
stocks    = ["PLTR","HWM","TPR","FTNT","ABBV","BLK","CHTR","FOX","GILD","NVR"]
symbols   = ["SPY"] + stocks
start_date = "2025-05-19"
end_date   = datetime.today().strftime("%Y-%m-%d")
api_key    = st.secrets["FMP_API_KEY"]

# Streamlit page configuration
st.set_page_config(page_title="Stock Portfolio Returns", layout="wide")

# Function to fetch stock data from FMP API
#@cache_data(ttl=43200)  # Cache for 12 hours
def fetch_stock_data(symbols, api_key, start_date, end_date):
    data = {}
    for symbol in symbols:
        url = (
            f"https://financialmodelingprep.com/api/v3/historical-price-full/"
            f"{symbol}?from={start_date}&to={end_date}&apikey={api_key}"
        )
        resp = requests.get(url)
        if resp.status_code == 200:
            js = resp.json()
            if js.get("historical"):
                df = pd.DataFrame(js["historical"])
                df["date"] = pd.to_datetime(df["date"])
                # sort oldest → newest
                df = df[["date", "close"]].sort_values("date").set_index("date")
                data[symbol] = df
            else:
                st.warning(f"No data for {symbol}")
        else:
            st.error(f"Error fetching {symbol}: {resp.status_code}")
    return data

# Calculate returns for a $50 investment
def calculate_returns(data, invest=50):
    rtns = {}
    portfolio_value = 0
    for sym, df in data.items():
        if df.empty:
            continue
        # oldest price = first row; latest = last row
        start_price = df["close"].iloc[0]
        end_price   = df["close"].iloc[-1]
        pct = (end_price - start_price) / start_price * 100
        final = invest * end_price / start_price
        rtns[sym] = {"return_pct": pct, "final_value": final}
        if sym != "SPY":
            portfolio_value += final
    return rtns, portfolio_value

st.title("Stock Portfolio Returns Analysis")

st.markdown(
    f"<p style='font-size:16px; color:#aaaaaa;'>"
    f"Tracking portfolio returns from {start_date} to {end_date}"
    "</p>", 
    unsafe_allow_html=True
)
st.header(f"Tracking portfolio returns from {start_date} to {end_date}")

st.write("🛠 caption debug")

# --- Fetch ---
with st.spinner("Fetching data…"):
    stock_data = fetch_stock_data(symbols, api_key, start_date, end_date)

# --- Returns ---
returns, port_val = calculate_returns(stock_data)
init_inv = 50 * len(stocks)
port_pct = (port_val - init_inv) / init_inv * 100

# --- Bar chart ---
bar_rows = []
for sym, info in returns.items():
    bar_rows.append({"Symbol": sym, "Return": info["return_pct"]})
bar_rows.append({"Symbol": "Portfolio", "Return": port_pct})
bar_df = pd.DataFrame(bar_rows)

# build a color list per row
colors = []
for _, row in bar_df.iterrows():
    if row.Symbol == "Portfolio":
        colors.append("#057DC9")
    elif row.Symbol == "SPY":
        colors.append("#FFA500")
    elif row.Return >= 0:
        colors.append("#97E956")
    else:
        colors.append("#F44A46")

fig_bar = px.bar(
    bar_df,
    x="Symbol",
    y="Return",
    title="Returns on $50 Investment per stock",
    text=bar_df["Return"].round(2).map(lambda x: f"{x:.2f}%"),
)
# get the SPY return value
spy_return = bar_df.loc[bar_df['Symbol']=='SPY', 'Return'].iloc[0]

# add a horizontal dashed line at SPY's return
fig_bar.add_hline(
    y=spy_return,
    line_dash="dot",
    line_width=1,
    line_color="white",
    annotation_text="",
    annotation_position="top right"
)
fig_bar.update_traces(marker_color=colors, textposition="auto")
fig_bar.update_layout(showlegend=False, yaxis_title="Return (%)")
st.plotly_chart(fig_bar, use_container_width=True)

# --- Line chart: Portfolio vs SPY over time ---
# Build a DataFrame of daily values
port_df = pd.DataFrame()
for sym in stocks:
    df = stock_data.get(sym)
    if df is None or df.empty:
        continue
    # buy at start_price
    start_price = df["close"].iloc[0]
    shares = 50 / start_price
    port_df[sym] = df["close"] * shares

# sum up
port_df["Portfolio"] = port_df.sum(axis=1)

# add SPY
spy_df = stock_data.get("SPY")
if spy_df is not None and not spy_df.empty:
    # new: same total capital as your portfolio
    initial_investment = 50 * len(stocks)  # = $500
    spy_shares = initial_investment / spy_df["close"].iloc[0]

    port_df["SPY"] = spy_df["close"] * spy_shares

# ensure Date column
port_df.index.name = "Date"
port_df = port_df.reset_index()

fig_line = go.Figure()
fig_line.add_trace(
    go.Scatter(
        x=port_df["Date"],
        y=port_df["Portfolio"],
        mode="lines",
        name="Portfolio",
        line=dict(color="#057DC9"),
        hovertemplate="Date: %{x}<br>Portfolio: $%{y:.2f}",
    )
)
if "SPY" in port_df:
    fig_line.add_trace(
        go.Scatter(
            x=port_df["Date"],
            y=port_df["SPY"],
            mode="lines",
            name="SPY",
            line=dict(color="#FFA500"),
            hovertemplate="Date: %{x}<br>SPY: $%{y:.2f}",
        )
    )

fig_line.update_layout(
    title="Portfolio vs SPY Value Over Time",
    xaxis_title="Date",
    yaxis_title="Value ($)",
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
)

#st.subheader("Portfolio and SPY Value Over Time")
st.plotly_chart(fig_line, use_container_width=True)

# --- Summary metrics ---
st.subheader("Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Initial Investment", f"${init_inv:.2f}")
c2.metric("Final Portfolio Value", f"${port_val:.2f}")
c3.metric("Portfolio Return", f"{port_pct:.2f}%")
