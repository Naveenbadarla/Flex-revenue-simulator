# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="Flex Revenue Simulator", layout="wide")

# ----- Helper / placeholder model -----
def run_valuation(inputs):
    """Placeholder valuation logic. Replace with call to your model.
    Returns a DataFrame with years x markets and totals.
    """
    years = list(range(inputs['year_from'], inputs['year_to'] + 1))
    markets = inputs['markets']
    rows = []
    for y in years:
        row = {'year': y}
        total = 0.0
        for m in markets:
            # toy formula: revenue depends on PV, battery, heatpump, random noise
            base = (inputs['pv_kw'] * 10 + inputs['battery_kwh'] * 8 + inputs['heatpump_kw'] * 6 + inputs['ev_kwh'] * 5)
            market_factor = {
                'DA': 1.0, 'ID': 0.7, 'FCR': 0.5, 'aFRR': 0.6, 'mFRR': 0.4
            }.get(m, 0.5)
            scenario_multiplier = {'Base': 1.0, 'High': 1.25, 'Low': 0.85}[inputs['price_scenario']]
            year_growth = 1.0 + 0.03 * (y - years[0])
            value = base * market_factor * scenario_multiplier * year_growth * (1 + np.random.normal(scale=0.02))
            row[m] = round(value, 2)
            total += value
        row['total'] = round(total, 2)
        rows.append(row)
    df = pd.DataFrame(rows)
    return df

# ----- UI: inputs -----
st.title("Flexibility Revenue Simulator")
with st.sidebar:
    st.header("Asset selection")
    pv_kw = st.number_input("PV size (kWp)", min_value=0.0, value=5.0, step=0.5)
    battery_kwh = st.number_input("Battery capacity (kWh)", min_value=0.0, value=10.0, step=1.0)
    battery_kw = st.number_input("Battery power (kW)", min_value=0.0, value=5.0, step=0.5)
    ev_kwh = st.number_input("EV battery (kWh) available for flex)", min_value=0.0, value=0.0, step=1.0)
    heatpump_kw = st.number_input("Heat pump power (kW)", min_value=0.0, value=0.0, step=0.5)

    st.header("Markets")
    markets = st.multiselect("Select markets to monetize", ['DA','ID','FCR','aFRR','mFRR'], default=['DA','ID'])

    st.header("Settings")
    year_from = st.selectbox("From year", options=list(range(2026, 2036)), index=0)
    year_to = st.selectbox("To year", options=list(range(2026, 2036)), index=4)
    price_scenario = st.selectbox("Price scenario", ['Base','High','Low'])
    optimization = st.selectbox("Optimization goal", ['Revenue maximizing','Cost minimizing'])

    run_button = st.button("Run simulation")

inputs = {
    'pv_kw': pv_kw,
    'battery_kwh': battery_kwh,
    'battery_kw': battery_kw,
    'ev_kwh': ev_kwh,
    'heatpump_kw': heatpump_kw,
    'markets': markets,
    'year_from': year_from,
    'year_to': year_to,
    'price_scenario': price_scenario,
    'optimization': optimization
}

# ----- Run and display -----
if run_button:
    if not markets:
        st.warning("Please select at least one market.")
    else:
        with st.spinner('Running valuation...'):
            df = run_valuation(inputs)
            time.sleep(0.5)
        st.subheader("Annual revenues by market")
        st.dataframe(df.set_index('year'))

        # charts
        st.subheader("Revenue composition (stacked)")
        df_plot = df.copy()
        df_plot = df_plot.set_index('year')
        st.bar_chart(df_plot[markets])

        st.subheader("Total revenue over time")
        st.line_chart(df_plot['total'])

        # market share
        totals = df[markets].sum().rename('revenue').reset_index()
        totals.columns = ['market','revenue']
        st.subheader("Total share by market")
        st.write(totals)
        st.plotly_chart(
            {
                'data': [{'labels': totals['market'].tolist(), 'values': totals['revenue'].tolist(), 'type': 'pie'}],
                'layout': {'title': 'Market share of total revenue'}
            }
        )

        # download as CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, file_name='flex_revenue.csv', mime='text/csv')
