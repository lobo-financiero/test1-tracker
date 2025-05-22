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
            portfolio_value += final_value
    return returns, portfolio_value

# Streamlit app
st.title("Stock Portfolio Returns Analysis")

# Define stocks and parameters
stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'WMT']
symbols = stocks + ['SPY']
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = "2025-05-19"
api_key = st.secrets["secrets"]["FMP_API_KEY"]

# Fetch data
with st.spinner("Fetching stock data..."):
    stock_data = fetch_stock_data(symbols, api_key, start_date, end_date)

# Calculate returns
returns, portfolio_value = calculate_returns(stock_data)
initial_investment = 50 * len(stocks)
portfolio_return = ((portfolio_value - initial_investment) / initial_investment) * 100

# Prepare data for bar chart
bar_data = [{'Symbol': symbol, 'Return (%)': info['return_pct']} for symbol, info in returns.items()]
bar_data.append({'Symbol': 'Portfolio', 'Return (%)': portfolio_return})
bar_df = pd.DataFrame(bar_data)

# Bar chart with return labels
fig_bar = px.bar(bar_df, x='Symbol', y='Return (%)', title="Returns of $50 Investment per Stock and Portfolio",
                 color='Symbol', color_discrete_sequence=px.colors.qualitative.Plotly)
fig_bar.update_traces(
    text=bar_df['Return (%)'].round(2).astype(str) + '%',
    textposition='auto',
    hovertemplate='%{x}<br>Return: %{y:.2f}%'
)
fig_bar.update_layout(showlegend=False, yaxis_title="Return (%)", xaxis_title="Symbol")
st.plotly_chart(fig_bar, use_container_width=True)

# Additional Visualization 1: Portfolio Value Over Time
st.subheader("Portfolio Value Over Time")
portfolio_df = pd.DataFrame()
for symbol in stocks:
    if symbol in stock_data and not stock_data[symbol].empty:
        shares = 50 / stock_data[symbol]['close'].iloc[-1]  # Shares bought at start
        stock_value = stock_data[symbol]['close'] * shares
        portfolio_df[symbol] = stock_value
portfolio_df = portfolio_df.fillna(method='ffill').sum(axis=1)
portfolio_df = portfolio_df.reset_index().rename(columns={0: 'Portfolio Value', 'date': 'Date'})

fig_line = px.line(portfolio_df, x='Date', y='Portfolio Value', title="Portfolio Value Over Time ($)")
fig_line.update_traces(line_color='#1f77b4', hovertemplate='Date: %{x}<br>Value: $%{y:.2f}')
fig_line.update_layout(yaxis_title="Portfolio Value ($)", xaxis_title="Date")
st.plotly_chart(fig_line, use_container_width=True)

# Additional Visualization 2: Portfolio Allocation Pie Chart
st.subheader("Portfolio Allocation (Final Values)")
pie_data = [{'Symbol': symbol, 'Value': info['final_value']} for symbol, info in returns.items() if symbol in stocks]
pie_df = pd.DataFrame(pie_data)
fig_pie = px.pie(pie_df, names='Symbol', values='Value', title="Portfolio Allocation by Stock",
                 color_discrete_sequence=px.colors.qualitative.Plotly)
fig_pie.update_traces(hovertemplate='%{label}<br>Value: $%{value:.2f}<br>%{percent}')
st.plotly_chart(fig_pie, use_container_width=True)

# Display summary metrics
st.subheader("Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Initial Investment", f"${initial_investment:.2f}")
col2.metric("Final Portfolio Value", f"${portfolio_value:.2f}")
col3.metric("Portfolio Return", f"{portfolio_return:.2f}%")
