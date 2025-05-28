import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Minimal dummy data for demo
df = pd.DataFrame({
    "NCT ID": ["NCT001", "NCT002", "NCT003"],
    "Title": ["Study 1", "Study 2", "Study 3"],
    "Sponsor": ["A", "B", "C"],
    "Status": ["COMPLETED", "RECRUITING", "TERMINATED"],
    "Start": pd.to_datetime(["2018-01-01", "2019-05-01", "2020-08-01"]),
    "End": pd.to_datetime(["2020-12-31", "2023-11-01", "2022-01-15"])
})

df = df.sort_values(by=["Start", "End"]).reset_index(drop=True)
df["#"] = range(1, len(df) + 1)
df["Bar Label"] = df.apply(lambda row: f"{row['NCT ID']} ({row['#']})", axis=1)

# Table display
st.write(df[["#", "NCT ID", "Title", "Status", "Start", "End"]])

# Plotly Timeline
custom_colors = {
    "RECRUITING": "blue",
    "COMPLETED": "green",
    "TERMINATED": "#ff9999"
}

fig = px.timeline(
    df,
    x_start="Start",
    x_end="End",
    y="Bar Label",            # Categorical Y-axis
    color="Status",
    color_discrete_map=custom_colors,
    hover_data=["Bar Label", "NCT ID", "Title", "Status"],
    text="Bar Label"          # <-- THE CRUCIAL FIX!
)

fig.update_traces(
    textposition="inside",
    insidetextanchor="middle"
)
fig.update_yaxes(autorange="reversed")
today = datetime.today().date().isoformat()
fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red")

st.plotly_chart(fig, use_container_width=True)
