# app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- Configuration ---
# FMP_API_KEY = st.secrets.get("FMP_API_KEY") # For FMP (if you switch from yfinance)
CACHE_TTL_SECONDS = 24 * 60 * 60 # 24 hours

# --- Hardcoded Prediction Data ---
# Replace this with a sample of your actual prediction data
# (ticker, latest_report_date_str, predicted_1y_return)
# For a real app with many stocks, you'd likely still load from a file or database,
# but for a static "experiment view," hardcoding a subset is okay.
# Ensure dates are 'YYYY-MM-DD'
HARCODED_PREDICTIONS_SAMPLE = [
    {'ticker': 'AAPL', 'latest_report_date': '2023-10-27', 'predicted_1y_return': 0.25},
    {'ticker': 'MSFT', 'latest_report_date': '2023-10-24', 'predicted_1y_return': 0.22},
    {'ticker': 'GOOGL', 'latest_report_date': '2023-10-24', 'predicted_1y_return': 0.18},
    {'ticker': 'AMZN', 'latest_report_date': '2023-10-26', 'predicted_1y_return': 0.30},
    {'ticker': 'NVDA', 'latest_report_date': '2023-11-21', 'predicted_1y_return': 0.45},
    {'ticker': 'TSLA', 'latest_report_date': '2023-10-18', 'predicted_1y_return': 0.15},
    {'ticker': 'META', 'latest_report_date': '2023-10-25', 'predicted_1y_return': 0.28},
    {'ticker': 'JPM', 'latest_report_date': '2023-10-13', 'predicted_1y_return': 0.12},
    {'ticker': 'V', 'latest_report_date': '2023-10-24', 'predicted_1y_return': 0.16},
    {'ticker': 'JNJ', 'latest_report_date': '2023-10-17', 'predicted_1y_return': 0.08},
    # Add more of your actual top predictions (at least 10, ideally up to 100 if you want that portfolio view)
    # For example:
    {'ticker': 'BRK-B', 'latest_report_date': '2023-11-04', 'predicted_1y_return': 0.14},
    {'ticker': 'UNH', 'latest_report_date': '2023-10-13', 'predicted_1y_return': 0.17},
    {'ticker': 'XOM', 'latest_report_date': '2023-10-27', 'predicted_1y_return': 0.10},
    {'ticker': 'LLY', 'latest_report_date': '2023-11-02', 'predicted_1y_return': 0.35},
    {'ticker': 'PG', 'latest_report_date': '2023-10-18', 'predicted_1y_return': 0.09},
    # ... and so on for up to num_to_display (max 100 in this example)
]
# If you have too much data, it's better to load from CSV as originally planned.
# This hardcoding is for a small, fixed set for quick viewing of THIS experiment.

# --- Helper Functions ---

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_prediction_data():
    # df = pd.read_csv(PREDICTIONS_FILE_PATH) # Original way
    df = pd.DataFrame(HARCODED_PREDICTIONS_SAMPLE) # Using hardcoded data
    df['latest_report_date'] = pd.to_datetime(df['latest_report_date'])
    df = df.sort_values(by='predicted_1y_return', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    return df

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_price_data_yf(ticker_symbol, start_date_str, end_date_str=None):
    try:
        stock = yf.Ticker(ticker_symbol)
        start_dt = pd.to_datetime(start_date_str)
        hist_start = stock.history(start=start_dt - timedelta(days=7), end=start_dt + timedelta(days=1))
        price_at_start = hist_start['Close'].iloc[-1] if not hist_start.empty else np.nan

        if end_date_str:
            end_dt = pd.to_datetime(end_date_str)
            hist_end = stock.history(start=end_dt - timedelta(days=7), end=end_dt + timedelta(days=1))
            price_at_end = hist_end['Close'].iloc[-1] if not hist_end.empty else np.nan
        else:
            hist_current = stock.history(start=datetime.now() - timedelta(days=5), end=datetime.now() + timedelta(days=1))
            price_at_end = hist_current['Close'].iloc[-1] if not hist_current.empty else np.nan
        return price_at_start, price_at_end
    except Exception:
        return np.nan, np.nan

# --- Main App Logic ---
st.set_page_config(layout="wide")
st.title("Transformer Stock Predictor Experiment Dashboard")
st.markdown(f"Displaying static prediction results. Dashboard loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

predictions_df_loaded = get_prediction_data()

if predictions_df_loaded.empty:
    st.warning("No prediction data to display.")
else:
    st.sidebar.header("Display Options")
    # Adjust max_value if your hardcoded list is smaller than 100
    max_slider_val = min(100, len(predictions_df_loaded))
    default_slider_val = min(30, max_slider_val)
    if max_slider_val < 5: # Ensure min_value is not greater than max_value
        num_to_display = max_slider_val
        st.sidebar.info(f"Displaying all {max_slider_val} available stocks.")
    else:
        num_to_display = st.sidebar.slider(
            "Number of top stocks to analyze:",
            min_value=min(5, max_slider_val), # Ensure min_value is reasonable
            max_value=max_slider_val,
            value=default_slider_val,
            step=5 if max_slider_val > 10 else 1
        )


    top_n_df = predictions_df_loaded.head(num_to_display).copy()
    
    st.subheader(f"Performance Analysis of Top {num_to_display} Predicted Stocks")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    real_gains_data = []

    for i, row in top_n_df.iterrows():
        ticker = row['ticker']
        pred_date = row['latest_report_date'] # Already datetime object
        pred_date_str = pred_date.strftime('%Y-%m-%d')
        status_text.text(f"Fetching price data for {ticker} ({i+1}/{len(top_n_df)})...")
        
        price_at_pred_date, current_price = get_price_data_yf(ticker, pred_date_str)
        
        current_gain = np.nan
        if pd.notna(price_at_pred_date) and pd.notna(current_price) and price_at_pred_date > 0:
            current_gain = (current_price - price_at_pred_date) / price_at_pred_date
        
        days_since_pred = (datetime.now() - pred_date).days

        real_gains_data.append({
            'rank': row['rank'],
            'ticker': ticker,
            'predicted_1y_return': row['predicted_1y_return'],
            'latest_report_date': pred_date_str,
            'days_since_prediction': days_since_pred,
            'price_at_prediction': price_at_pred_date,
            'current_price': current_price,
            'current_real_gain': current_gain
        })
        progress_bar.progress((i + 1) / len(top_n_df))

    status_text.text("Fetching SPY benchmark data...")
    # Use the average or median prediction date of the displayed stocks as common start for SPY for fairness
    if not top_n_df.empty:
        # Using median date of the displayed stocks
        common_start_date_dt = top_n_df['latest_report_date'].median()
        spy_pred_date_str_overall = common_start_date_dt.strftime('%Y-%m-%d')
    else: # Fallback if top_n_df is somehow empty
        spy_pred_date_str_overall = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')


    price_spy_at_start, current_price_spy = get_price_data_yf('SPY', spy_pred_date_str_overall)
    spy_gain = np.nan
    if pd.notna(price_spy_at_start) and pd.notna(current_price_spy) and price_spy_at_start > 0:
        spy_gain = (current_price_spy - price_spy_at_start) / price_spy_at_start # Corrected calculation

    progress_bar.empty()
    status_text.empty()

    if not real_gains_data:
        st.warning("Could not fetch any real gain data.")
    else:
        real_gains_df = pd.DataFrame(real_gains_data)
        # We want to keep all rows for the table, but chart needs non-NaN gains
        chartable_real_gains_df = real_gains_df.dropna(subset=['current_real_gain']).copy()

        chart_data = []
        top_10_for_chart = chartable_real_gains_df[chartable_real_gains_df['rank'] <= 10] # Select by rank
        for _, row_chart in top_10_for_chart.iterrows():
            chart_data.append({'Category': f"{row_chart['rank']}. {row_chart['ticker']}", 'Gain/Loss': row_chart['current_real_gain']})

        if not chartable_real_gains_df.empty:
            # Portfolio gains (ensure enough stocks are available after dropna)
            if len(chartable_real_gains_df[chartable_real_gains_df['rank'] <= 10]) > 0:
                gain_top10_portfolio = chartable_real_gains_df[chartable_real_gains_df['rank'] <= 10]['current_real_gain'].mean()
                chart_data.append({'Category': 'Portfolio: Top 10 Avg.', 'Gain/Loss': gain_top10_portfolio})

            if num_to_display >= 30 and len(chartable_real_gains_df[chartable_real_gains_df['rank'] <= 30]) > 0:
                gain_top30_portfolio = chartable_real_gains_df[chartable_real_gains_df['rank'] <= 30]['current_real_gain'].mean()
                chart_data.append({'Category': 'Portfolio: Top 30 Avg.', 'Gain/Loss': gain_top30_portfolio})
            
            if num_to_display >= 100 and len(chartable_real_gains_df[chartable_real_gains_df['rank'] <= 100]) > 0 :
                gain_top100_portfolio = chartable_real_gains_df[chartable_real_gains_df['rank'] <= 100]['current_real_gain'].mean()
                chart_data.append({'Category': 'Portfolio: Top 100 Avg.', 'Gain/Loss': gain_top100_portfolio})
        
        chart_data.append({'Category': 'Benchmark: SPY', 'Gain/Loss': spy_gain})
        
        chart_df = pd.DataFrame(chart_data)
        chart_df.dropna(subset=['Gain/Loss'], inplace=True)

        if not chart_df.empty:
            chart_df = chart_df.sort_values(by='Gain/Loss', ascending=False)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=chart_df['Category'],
                y=chart_df['Gain/Loss'],
                text=[f"{y*100:.2f}%" for y in chart_df['Gain/Loss']],
                textposition='outside', # 'auto' can overlap, 'outside' is usually clearer
                marker_color=['#2ca02c' if x >= 0 else '#d62728' for x in chart_df['Gain/Loss']] # Specific green/red
            ))
            
            # --- YOUR CUSTOM STYLING CODE WOULD GO HERE ---
            # Example:
            fig.update_layout(
                title_text=f"Current Realized Gain/Loss Since Prediction Date<br><span style='font-size:0.8em'>(Prediction dates are per stock, SPY benchmarked from {spy_pred_date_str_overall})</span>",
                xaxis_title=None, # "Stock/Portfolio Category" - often clear from labels
                yaxis_title="Gain/Loss", # Removed (%) as tickformat handles it
                yaxis_tickformat=".1%",
                height=500 + max(0, (len(chart_df)-5)*20), # Dynamically adjust height
                margin=dict(b=100), # Add bottom margin for potentially long x-axis labels
                xaxis_tickangle=-45 # Angle labels if they are long
            )
            # --- END OF EXAMPLE STYLING ---
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data to display the performance chart.")

        st.subheader("Detailed Stock Performance and Predictions")
        table_display_df = real_gains_df[[
            'rank', 'ticker', 'predicted_1y_return', 'latest_report_date', 
            'days_since_prediction', 'price_at_prediction', 'current_price', 'current_real_gain'
        ]].head(num_to_display).copy() # Show only num_to_display in table
        
        table_display_df['predicted_1y_return'] = table_display_df['predicted_1y_return'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
        table_display_df['current_real_gain'] = table_display_df['current_real_gain'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
        table_display_df['price_at_prediction'] = table_display_df['price_at_prediction'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        table_display_df['current_price'] = table_display_df['current_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        
        st.dataframe(table_display_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("Disclaimer: This dashboard is for informational and educational purposes only. Predictions are experimental and not financial advice. Past performance is not indicative of future results.")
