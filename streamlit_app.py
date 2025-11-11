import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Flexibility Revenue & Cost Simulator", layout="wide")

# ----- Helper / placeholder model -----
def run_valuation(inputs):
    """Simple valuation model with cost comparison.
    Replace logic with your own model if available.
    """
    years = list(range(inputs['year_from'], inputs['year_to'] + 1))
    markets = inputs['markets']
    rows = []
    for y in years:
        row = {'year': y}
        total_rev = 0.0
        for m in markets:
            base = (
                inputs['pv_kw'] * 10
                + inputs['battery_kwh'] * 8
                + inputs['heatpump_kw'] * 6
                + inputs['ev_kwh'] * 5
            )
            market_factor = {
                'DA': 1.0,
                'ID': 0.7,
                'FCR': 0.5,
                'aFRR': 0.6,
                'mFRR': 0.4,
            }.get(m, 0.5)
            scenario_multiplier = {
                'Base': 1.0,
                'High': 1.25,
                'Low': 0.85,
            }[inputs['price_scenario']]
            year_growth = 1.0 + 0.03 * (y - years[0])
            value = (
                base
                * market_factor
                * scenario_multiplier
                * year_growth
                * (1 + np.random.normal(scale=0.02))
            )
            row[m] = round(value, 2)
            total_rev += value

        # ---- Cost logic ----
        baseline_cost = inputs['household_kwh'] * inputs['retail_price']
        optimized_cost = baseline_cost - total_rev
        savings = baseline_cost - optimized_cost
        savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        # ---- Store results ----
        row['total_revenue'] = round(total_rev, 2)
        row['baseline_cost'] = round(baseline_cost, 2)
        row['optimized_cost'] = round(optimized_cost, 2)
        row['savings'] = round(savings, 2)
        row['savings_pct'] = round(savings_pct, 2)
        rows.append(row)
    return pd.DataFrame(rows)


# ----- Sidebar UI -----
st.sidebar.header("Asset selection")
pv_kw = st.sidebar.number_input("PV size (kWp)", min_value=0.0, value=5.0, step=0.5)
battery_kwh = st.sidebar.number_input("Battery capacity (kWh)", min_value=0.0, value=10.0, step=1.0)
battery_kw = st.sidebar.number_input("Battery power (kW)", min_value=0.0, value=5.0, step=0.5)
ev_kwh = st.sidebar.number_input("EV battery (kWh available for flex)", min_value=0.0, value=0.0, step=1.0)
heatpump_kw = st.sidebar.number_input("Heat pump power (kW)", min_value=0.0, value=0.0, step=0.5)

st.sidebar.header("Household & Costs")
household_kwh = st.sidebar.number_input("Annual household consumption (kWh/year)", min_value=0.0, value=4000.0, step=100.0)
retail_price = st.sidebar.number_input("Retail electricity price (€/kWh)", min_value=0.0, value=0.30, step=0.01)

st.sidebar.header("Markets & Settings")
markets = st.sidebar.multiselect(
    "Select markets to monetize",
    ['DA', 'ID', 'FCR', 'aFRR', 'mFRR'],
    default=['DA', 'ID']
)
year_from = st.sidebar.selectbox("From year", options=list(range(2026, 2036)), index=0)
year_to = st.sidebar.selectbox("To year", options=list(range(2026, 2036)), index=4)
price_scenario = st.sidebar.selectbox("Price scenario", ['Base', 'High', 'Low'])
optimization = st.sidebar.selectbox("Optimization goal", ['Revenue maximizing', 'Cost minimizing'])

run_button = st.sidebar.button("Run simulation")

inputs = {
    'pv_kw': pv_kw,
    'battery_kwh': battery_kwh,
    'battery_kw': battery_kw,
    'ev_kwh': ev_kwh,
    'heatpump_kw': heatpump_kw,
    'household_kwh': household_kwh,
    'retail_price': retail_price,
    'markets': markets,
    'year_from': year_from,
    'year_to': year_to,
    'price_scenario': price_scenario,
    'optimization': optimization,
}

# ----- Main content -----
st.title("🔋 Flexibility Revenue & Cost Simulator")

if run_button:
    if not markets:
        st.warning("Please select at least one market.")
    else:
        with st.spinner("Running valuation..."):
            df = run_valuation(inputs)
            time.sleep(0.5)

        st.subheader("Annual Revenues by Market (€)")
        st.dataframe(df.set_index('year'))

        st.subheader("Revenue Composition (Stacked)")
        df_plot = df.set_index('year')
        st.bar_chart(df_plot[markets])

        st.subheader("Total Revenue Over Time (€)")
        st.line_chart(df_plot['total_revenue'])

        # ---- Cost comparison ----
        st.subheader("Cost Comparison (€)")
        cost_cols = ['baseline_cost', 'optimized_cost', 'savings', 'savings_pct']
        st.dataframe(df[['year'] + cost_cols].set_index('year'))

        st.subheader("Cost vs Revenue Over Time (€)")
        chart_df = df.set_index('year')[['total_revenue', 'baseline_cost', 'optimized_cost']]
        st.line_chart(chart_df)

        # ---- Pie chart of market share ----
        st.subheader("Market Share of Total Revenue")
        totals = df[markets].sum().rename('revenue').reset_index()
        totals.columns = ['market', 'revenue']
        fig = go.Figure(data=[go.Pie(labels=totals['market'], values=totals['revenue'])])
        st.plotly_chart(fig, use_container_width=True)

        # ---- Pie chart of cost savings ----
        st.subheader("Total Cost Savings Share")
        fig2 = go.Figure(
            data=[go.Pie(
                labels=['Baseline cost', 'Savings'],
                values=[df['baseline_cost'].sum(), df['savings'].sum()],
                hole=0.4
            )]
        )
        st.plotly_chart(fig2, use_container_width=True)

        # ---- Download ----
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results as CSV", csv, file_name='flex_revenue_costs.csv', mime='text/csv')
