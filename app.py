import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import statsmodels.api as sm
import requests
from fredapi import Fred

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Macro-Inflation Tracker", layout="wide")
st.title("📊 Singapore Macro-Inflation Tracker")

# 2. CACHED DATA LOADING
@st.cache_data
def get_data():
    # Ingest FRED Data
    fred = Fred(api_key='add97eb05104bd5bbd287892b4dfd681')
    oil = fred.get_series('POILBREUSDM')
    food = fred.get_series('PFOODINDEXM')
    
    # Ingest SingStat Data
    singstat_url = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/M213751"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Accept': 'application/json'}
    response = requests.get(singstat_url, headers=headers).json()
    
    records = response['Data']['row']
    cpi_data = []
    for row in records:
        if row.get('rowText') == 'All Items':
            for col in row.get('columns', []):
                if col.get('Key') and col.get('Value'):
                    cpi_data.append({'Date': col['Key'], 'SG_CPI': float(col['Value'])})
    
    df_cpi = pd.DataFrame(cpi_data)
    df_cpi['Date'] = pd.to_datetime(df_cpi['Date'], format='%Y %b')
    df_cpi.set_index('Date', inplace=True)
    
    # Merge and Difference
    data = pd.DataFrame({'Oil': oil, 'Food': food, 'CPI': df_cpi['SG_CPI']}).dropna()
    diff = data.pct_change().dropna() * 100
    
    # Run OLS Regression
    Y = diff['CPI']
    X = sm.add_constant(diff[['Oil', 'Food']])
    model = sm.OLS(Y, X).fit()
    
    return model.params['Oil'], model.params['Food']

# 3. DASHBOARD UI
beta_oil, beta_food = get_data()

st.sidebar.header("Global Shock Parameters")
oil_shock = st.sidebar.slider("Global Oil Shock (%)", -50.0, 100.0, 0.0)
food_shock = st.sidebar.slider("Global Food Shock (%)", -50.0, 100.0, 0.0)

# Forecast calculation
baseline_inflation = 2.5
forecast = baseline_inflation + (oil_shock * beta_oil) + (food_shock * beta_food)

# Visualization
fig = go.Figure()
fig.add_trace(go.Scatter(x=np.arange(12), y=[baseline_inflation]*12, name='Baseline', line=dict(dash='dash', color='gray')))
fig.add_trace(go.Scatter(x=np.arange(12), y=np.linspace(baseline_inflation, forecast, 12), name='Forecast', line=dict(width=4, color='red')))
fig.update_layout(title="Inflation Forecast", yaxis_title="CPI % Change", xaxis_title="Month", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Policy Outlook")
st.write(f"Based on your inputs, the forecasted CPI change is **{forecast:.2f}%**.")
if forecast > 4.0:
    st.error("⚠️ Inflation Warning: Monitor potential cost-push pressures.")
else:
    st.success("✅ Outlook: Inflation remains within manageable parameters.")
