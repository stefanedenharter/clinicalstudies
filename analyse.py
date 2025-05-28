import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(layout="wide")
st.title("🧪 Clinical Trials Explorer")

# User input
query = st.text_input("Enter a condition or keyword (e.g., BPH, prostate cancer):", "BPH")

if st.button("Search"):
    with st.spinner("Fetching data from ClinicalTrials.gov..."):
        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={query}&pageSize=20"
        response = requests.get(url)

        if response.status_code != 200:
            st.error("Failed to fetch data. Try again later.")
        else:
            data = response.json()
            studies = data.get("studies", [])

            # Extract fields
            records = []
            for study in studies:
                try:
                    sec = study.get("protocolSection", {})
                    id_mod = sec.get("identificationModule", {})
                    status_mod = sec.get("statusModule", {})
                    sponsor_mod = sec.get("sponsorCollaboratorsModule", {})

                    nct_id = id_mod.get("nctId", "")
                    title = id_mod.get("briefTitle", "")
                    sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "N/A")
                    status = status_mod.get("overallStatus", "")
                    start_date = status_mod.get("startDateStruct", {}).get("date", "")
                    end_date = status_mod.get("completionDateStruct", {}).get("date", "")

                    records.append((nct_id, title, sponsor, status, start_date, end_date))
                except Exception:
                    continue

            if not records:
                st.warning("No results found.")
            else:
                # Create DataFrame
                df = pd.DataFrame(records, columns=["NCT ID", "Title", "Sponsor", "Status", "Start", "End"])

                # Sort by status
                df = df.sort_values(by="Status")

                # Add hyperlinks to NCT IDs
                df["Link"] = df["NCT ID"].apply(
                    lambda x: f'<a href="https://clinicaltrials.gov/study/{x}" target="_blank">{x}</a>'
                )
                df_display = df[["Link", "Title", "Sponsor", "Status", "Start", "End"]]

                st.markdown("### 🧾 Search Results")
                st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

                # Prepare chart data
                df_chart = df.dropna(subset=["Start", "End"]).copy()
                df_chart["Start"] = pd.to_datetime(df_chart["Start"], errors='coerce')
                df_chart["End"] = pd.to_datetime(df_chart["End"], errors='coerce')
                df_chart = df_chart.dropna()

                if not df_chart.empty:
                    st.markdown("### 📊 Study Duration Chart")

                    # Define colors for status
                    status_colors = {
                        "RECRUITING": "tab:blue",
                        "COMPLETED": "tab:green",
                        "TERMINATED": "tab:red",
                        "NOT YET RECRUITING": "tab:orange",
                        "ACTIVE, NOT RECRUITING": "tab:purple",
                        "UNKNOWN STATUS": "tab:gray",
                        "WITHDRAWN": "tab:brown"
                    }

                    fig, ax = plt.subplots(figsize=(10, len(df_chart) * 0.5))

                    for i, row in df_chart.iterrows():
                        duration = (row["End"] - row["Start"]).days
                        color = status_colors.get(row["Status"].upper(), "tab:gray")
                        ax.barh(i, duration, left=row["Start"], color=color)
                        ax.text(row["Start"] + pd.Timedelta(days=duration // 2),
                                i, row["NCT ID"], va='center', ha='center', fontsize=7, color="white")

                    ax.set_yticks([])  # Hide study titles
                    ax.set_xlabel("Date")


                    # Legend below chart with extra space
                    handles = [
                        plt.Line2D([0], [0], color=color, lw=6, label=status.title())
                        for status, color in status_colors.items()
                    ]
                    
                    # Expand the bottom margin to fit the legend cleanly
                    fig.subplots_adjust(bottom=0.3)  # Increased from 0.2 to 0.3
                    
                    # Move legend down slightly to avoid x-axis label overlap
                    ax.legend(
                        handles=handles,
                        title="Study Status",
                        loc='upper center',
                        bbox_to_anchor=(0.5, -0.25),  # lower vertical anchor
                        ncol=3,
                        fontsize=8,
                        title_fontsize=9
                    )

                    st.pyplot(fig)
                else:
                    st.info("No studies had valid dates for charting.")
