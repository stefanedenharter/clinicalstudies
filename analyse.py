import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO

st.set_page_config(layout="wide")
st.title("🧪 Clinical Trials Explorer")

# Input for clinical condition
query = st.text_input("Enter a condition or keyword (e.g., BPH, prostate cancer):", "BPH")

if st.button("Search"):
    with st.spinner("Fetching data from ClinicalTrials.gov..."):
        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={query}&pageSize=30"
        response = requests.get(url)

        if response.status_code != 200:
            st.error("Failed to fetch data.")
        else:
            data = response.json()
            studies = data.get("studies", [])

            records = []
            for i, study in enumerate(studies, start=1):
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
                    company_id = id_mod.get("orgStudyIdInfo", {}).get("id", "")
                    link = f"https://clinicaltrials.gov/study/{nct_id}"

                    records.append((
                        i, nct_id, title, sponsor, status, study_type,
                        company_id, start_date, end_date, last_verified, link
                    ))
                except Exception:
                    continue

            if not records:
                st.warning("No results found.")
            else:
                df = pd.DataFrame(records, columns=[
                    "#", "NCT ID", "Title", "Sponsor", "Status", "Study Type",
                    "Company Study ID", "Start", "End", "Last Verified", "Link"
                ])

                # Convert partial date strings to datetime
                def normalize_date(date_str):
                    if isinstance(date_str, str) and len(date_str) == 7:
                        date_str += "-01"
                    return pd.to_datetime(date_str, errors='coerce')

                df["Start"] = df["Start"].apply(normalize_date)
                df["End"] = df["End"].apply(normalize_date)
                df = df.dropna(subset=["Start", "End"])
                df = df.sort_values(by="Status")

                # Filter: Sponsor
                sponsors = sorted(df["Sponsor"].dropna().unique())
                sponsor_filter = st.selectbox("Filter by Sponsor", options=["All"] + sponsors)
                if sponsor_filter != "All":
                    df = df[df["Sponsor"] == sponsor_filter]

                # Filter: Start Date Range
                min_date_raw = df["Start"].min()
                max_date_raw = df["Start"].max()

                if pd.notnull(min_date_raw) and pd.notnull(max_date_raw):
                    min_date = min_date_raw.to_pydatetime()
                    max_date = max_date_raw.to_pydatetime()

                    start_range = st.slider(
                        "Start Date Range",
                        min_value=min_date,
                        max_value=max_date,
                        value=(min_date, max_date)
                    )

                    df = df[df["Start"].between(start_range[0], start_range[1])]
                else:
                    st.warning("No valid start dates available for filtering.")

                # Excel download using BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.drop(columns=["Link"]).to_excel(writer, index=False)
                output.seek(0)

                st.download_button(
                    label="📥 Download Results as Excel",
                    data=output,
                    file_name="clinical_trials.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # Make row number and NCT ID clickable
                df["#"] = df.apply(lambda row: f'<a href="https://clinicaltrials.gov/study/{row["NCT ID"]}" target="_blank">{row["#"]}</a>', axis=1)
                df["Link"] = df["NCT ID"].apply(
                    lambda x: f'<a href="https://clinicaltrials.gov/study/{x}" target="_blank">{x}</a>'
                )

                df_display = df[[
                    "#", "Link", "Title", "Sponsor", "Status", "Study Type",
                    "Company Study ID", "Start", "End", "Last Verified"
                ]]

                st.markdown("### 🧾 Search Results")
                st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

                # Label for timeline bars (NCT ID + row number)
                df["Bar Label"] = df.apply(
                    lambda row: f"{row['NCT ID']} ({row['#'].split('>')[1].split('<')[0]})",
                    axis=1
                )

                # Custom color scheme
                custom_colors = {
                    "RECRUITING": "blue",
                    "COMPLETED": "green",
                    "TERMINATED": "#ff9999",
                    "NOT YET RECRUITING": "orange",
                    "ACTIVE, NOT RECRUITING": "orange",
                    "UNKNOWN STATUS": "gray",
                    "WITHDRAWN": "brown"
                }

                st.markdown("### 📊 Study Timeline")

                fig = px.timeline(
                    df,
                    x_start="Start",
                    x_end="End",
                    y="NCT ID",
                    color="Status",
                    color_discrete_map=custom_colors,
                    hover_data=["Title", "Sponsor", "Status", "Study Type", "Company Study ID"],
                    custom_data=["Link"]
                )

                fig.update_traces(
                    text=df["Bar Label"],
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
