import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set page layout
st.set_page_config(layout="wide")
st.title("🧪 Clinical Trials Explorer")

# Text input for clinical condition search
query = st.text_input("Enter a condition or keyword (e.g., BPH, prostate cancer):", "BPH")

# Start search on button click
if st.button("Search"):
    with st.spinner("Fetching data from ClinicalTrials.gov..."):

        # Call ClinicalTrials.gov API
        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={query}&pageSize=30"
        response = requests.get(url)

        if response.status_code != 200:
            st.error("Failed to fetch data. Try again later.")
        else:
            data = response.json()
            studies = data.get("studies", [])

            # Extract relevant fields from each study
            records = []
            for study in studies:
                try:
                    sec = study.get("protocolSection", {})
                    id_mod = sec.get("identificationModule", {})
                    status_mod = sec.get("statusModule", {})
                    sponsor_mod = sec.get("sponsorCollaboratorsModule", {})
                    design_mod = sec.get("designModule", {})

                    nct_id = id_mod.get("nctId", "")
                    title = id_mod.get("briefTitle", "")
                    sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "N/A")
                    status = status_mod.get("overallStatus", "").upper()
                    start_date = status_mod.get("startDateStruct", {}).get("date", "")
                    end_date = status_mod.get("completionDateStruct", {}).get("date", "")
                    last_verified = status_mod.get("lastUpdatePostDateStruct", {}).get("date", "")
                    study_type = design_mod.get("studyType", "")

                    # Extract Company Study ID
                    company_id = id_mod.get("orgStudyIdInfo", {}).get("id", "")

                    # Extract enrollment from enrollmentInfo
                    enrollment = str(design_mod.get("enrollmentInfo", {}).get("count", "N/A"))

                    link = f"https://clinicaltrials.gov/study/{nct_id}"

                    records.append((
                        nct_id, title, sponsor, status, study_type,
                        company_id, start_date, end_date, last_verified, enrollment, link
                    ))
                except Exception:
                    continue

            if not records:
                st.warning("No results found.")
            else:
                # Build DataFrame
                df = pd.DataFrame(records, columns=[
                    "NCT ID", "Title", "Sponsor", "Status", "Study Type",
                    "Company Study ID", "Start", "End", "Last Verified", "Enrollment", "Link"
                ])

                # Normalize dates
                def normalize_date(date_str):
                    if isinstance(date_str, str) and len(date_str) == 7:
                        date_str += "-01"
                    return pd.to_datetime(date_str, errors='coerce')

                df["Start"] = df["Start"].apply(normalize_date)
                df["End"] = df["End"].apply(normalize_date)
                df = df.dropna(subset=["Start", "End"])
                df = df.sort_values(by="Status")

                # Add link HTML
                df["Link"] = df["NCT ID"].apply(
                    lambda x: f'<a href="https://clinicaltrials.gov/study/{x}" target="_blank">{x}</a>'
                )

                # Display table
                df_display = df[[
                    "Link", "Title", "Sponsor", "Status", "Study Type",
                    "Company Study ID", "Enrollment", "Start", "End", "Last Verified"
                ]]
                st.markdown("### 🧾 Search Results")
                st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

                # Color map
                custom_colors = {
                    "RECRUITING": "blue",
                    "COMPLETED": "green",
                    "TERMINATED": "#ff9999",
                    "NOT YET RECRUITING": "orange",
                    "ACTIVE, NOT RECRUITING": "orange",
                    "UNKNOWN STATUS": "gray",
                    "WITHDRAWN": "brown"
                }

                # Chart
                st.markdown("### 📊 Study Timeline")
                fig = px.timeline(
                    df,
                    x_start="Start",
                    x_end="End",
                    y="NCT ID",
                    color="Status",
                    color_discrete_map=custom_colors,
                    hover_data=["Title", "Sponsor", "Status", "Study Type", "Company Study ID", "Enrollment"],
                    custom_data=["Link"]
                )

                fig.update_traces(
                    text=df["NCT ID"],
                    textposition="inside",
                    insidetextanchor="middle",
                    marker_line_width=0,
                    textfont=dict(size=16, color="white", family="Arial")
                )

                fig.update_layout(
                    showlegend=True,
                    xaxis=dict(
                        title=None,
                        showticklabels=True,
                        showline=True,
                        linecolor="black",
                        tickfont=dict(size=18, family="Arial", color="black")
                    ),
                    yaxis=dict(
                        title=None,
                        showticklabels=False,
                        showline=True,
                        linecolor="black"
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    hoverlabel=dict(font_size=14, font_family="Arial"),
                    font=dict(size=16, family="Arial", color="black"),
                    margin=dict(l=20, r=20, t=40, b=40),
                    height=40 * len(df) + 200
                )

                fig.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
                fig.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True)

                st.plotly_chart(fig, use_container_width=True)
