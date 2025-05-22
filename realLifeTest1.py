import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from streamlit import cache_data

# Streamlit page configuration
st.set_page_config(page_title="Stock Portfolio Returns", layout="wide")

# Function to fetch stock data from FMP API
@cache_data(ttl=43200)  # Cache for 12 hours (43200 seconds)
def fetch_stock_data(symbols, api_key, start_date, end_date):
    data = {}
    for symbol in symbols:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={start_date}&to={end_date}&apikey={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            json_data = response.json()
            if 'historical' in json_data and json_data['historical']:
                df = pd.DataFrame(json_data['historical'])
                df['date'] = pd.to_datetime(df['date'])
                df = df[['date', 'close']].set_index('date').sort_index()
                data[symbol] = df
            else:
                st.warning(f"No data found for {symbol}")
        else:
            st.error(f"Failed to fetch data for {symbol}")
    return data

# Calculate returns for a $50 investment
def calculate_returns(data, investment_per_stock=50):
    returns = {}
    portfolio_value = 0
    for symbol, df in data.items():
        if not df.empty:
            start_price = df['close'].iloc[-1]  # Oldest price
            end_price = df['close'].iloc[0]    # Latest price
            return_pct = (end_price - start_price) / start_price * 100
            final_value = investment_per_stock * (end_price / start_price)
            returns[symbol] = {'return_pct': return_pct, 'final_value': final_value}
            if symbol != 'SPY':  # Exclude SPY from portfolio value
                portfolio_value += final_value
    return returns, portfolio_value

# Streamlit app
st.title("Stock Portfolio Returns Analysis")

# Define stocks and parameters
stocks = ['GILD', 'FTNT', 'PLTR', 'CHTR', 'HWM', 'FOX', 'BLK', 'ABBV', 'TPR', 'NVR']
symbols = stocks + ['SPY']
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = "2025-05-19"
api_key = st.secrets["FMP_API_KEY"]

# Fetch data
with st.spinner("Fetching stock data..."):
    stock_data = fetch_stock_data(symbols, api_key, start_date, end_date)

# Calculate returns
returns, portfolio_value = calculate_returns(stock_data)
initial_investment = 50 * len(stocks)  # $50 per stock, excluding SPY
portfolio_return = ((portfolio_value - initial_investment) / initial_investment) * 100

# Prepare data for bar chart
bar_data = [{'Symbol': symbol, 'Return (%)': info['return_pct']} for symbol, info in returns.items()]
bar_data.append({'Symbol': 'Portfolio', 'Return (%)': portfolio_return})
bar_df = pd.DataFrame(bar_data)

# Bar chart with return labels
fig_bar = px.bar(bar_df, x='Symbol', y='Return (%)', title="Returns of $50 Investment per Stock and Portfolio",
                 color='Symbol', color_discrete_sequence=px.colors.qualitative.Plotly)
fig_bar.update_traces(
    text=bar_df['Return (%)'].round(2).apply(lambda x: f"{x:.2f}%"),
    textposition='auto',
    hovertemplate='%{x}<br>Return: %{y:.2f}%'
)
fig_bar.update_layout(showlegend=False, yaxis_title="Return (%)", xaxis_title="Symbol")
st.plotly_chart(fig_bar, use_container_width=True)

# Portfolio and SPY Value Over Time
st.subheader("Portfolio and SPY Value Over Time")
portfolio_df = pd.DataFrame()
for symbol in stocks:
    if symbol in stock_data and not stock_data[symbol].empty:
        shares = 50 / stock_data[symbol]['close'].iloc[-1]  # Shares bought at start
        stock_value = stock_data[symbol]['close'] * shares
        portfolio_df[symbol] = stock_value
portfolio_df['Portfolio'] = portfolio_df.fillna(method='ffill').sum(axis=1)

# Add SPY to the line chart
if 'SPY' in stock_data and not stock_data['SPY'].empty:
    spy_shares = 50 / stock_data['SPY']['close'].iloc[-1]  # Shares bought at start
    portfolio_df['SPY'] = stock_data['SPY']['close'] * spy_shares

portfolio_df = portfolio_df.reset_index().rename(columns={'date': 'Date'})

# Create line chart with Portfolio and SPY
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(x=portfolio_df['Date'], y=portfolio_df['Portfolio'],
                              mode='lines', name='Portfolio', line=dict(color='#1f77b4'),
                              hovertemplate='Date: %{x}<br>Portfolio: $%{y:.2f}'))
if 'SPY' in portfolio_df:
    fig_line.add_trace(go.Scatter(x=portfolio_df['Date'], y=portfolio_df['SPY'],
                                  mode='lines', name='SPY', line=dict(color='#ff7f0e'),
                                  hovertemplate='Date: %{x}<br>SPY: $%{y:.2f}'))
fig_line.update_layout(title="Portfolio and SPY Value Over Time ($)",
                       yaxis_title="Value ($)", xaxis_title="Date",
                       legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
st.plotly_chart(fig_line, use_container_width=True)

# Display summary metrics
st.subheader("Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Initial Investment", f"${initial_investment:.2f}")
col2.metric("Final Portfolio Value", f"${portfolio_value:.2f}")
col3.metric("Portfolio Return", f"{portfolio_return:.2f}%")
