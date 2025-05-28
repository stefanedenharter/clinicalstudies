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
                    # enrollment = design_mod.get("enrollmentModule", {}).get("enrollmentCount", "")  # Optional: enable later
                    link = f"https://clinicaltrials.gov/study/{nct_id}"

                  # from identificationModule
                    # org_study_id = id_mod.get("orgStudyId", "")
                    # acronym = id_mod.get("acronym", "")
                    # brief_summary = id_mod.get("briefSummary", "")
                    
                    # from statusModule
                    # study_first_submitted = status_mod.get("studyFirstSubmitDateStruct", {}).get("date", "")
                    # study_first_posted = status_mod.get("studyFirstPostDateStruct", {}).get("date", "")
                    # last_update_submitted = status_mod.get("lastUpdateSubmitDateStruct", {}).get("date", "")
                    # last_update_posted = status_mod.get("lastUpdatePostDateStruct", {}).get("date", "")
                    # completion_date_type = status_mod.get("completionDateStruct", {}).get("type", "")
                    # start_date_type = status_mod.get("startDateStruct", {}).get("type", "")
                    
                    # from sponsorCollaboratorsModule
                    # collaborator_names = [c.get("name", "") for c in sponsor_mod.get("collaborators", [])]
                    
                    # from designModule
                    # study_type = design_mod.get("studyType", "")
                    # allocation = design_mod.get("allocation", "")
                    # intervention_model = design_mod.get("interventionModel", "")
                    # primary_purpose = design_mod.get("primaryPurpose", "")
                    # masking = design_mod.get("masking", "")
                    
                    # from descriptionModule
                    # detailed_description = sec.get("descriptionModule", {}).get("detailedDescription", "")
                    
                    # from eligibilityModule
                    # eligibility_mod = sec.get("eligibilityModule", {})
                    # gender = eligibility_mod.get("sex", "")
                    # minimum_age = eligibility_mod.get("minimumAge", "")
                    # maximum_age = eligibility_mod.get("maximumAge", "")
                    # eligibility_criteria = eligibility_mod.get("eligibilityCriteria", "")
                    
                    # from contactsLocationsModule
                    # locations = sec.get("contactsLocationsModule", {}).get("locations", [])
                    
                    # from conditionsModule
                    # conditions = sec.get("conditionsModule", {}).get("conditions", [])
                    
                    # from interventionsModule
                    # interventions = sec.get("interventionsModule", {}).get("interventions", [])
                    
                    # from armsInterventionsModule
                    # arms = sec.get("armsInterventionsModule", {}).get("arms", [])
                    
                    records.append((nct_id, title, sponsor, status, start_date, end_date, last_verified, study_type, link))
                except Exception:
                    continue

            if not records:
                st.warning("No results found.")
            else:
                # Build DataFrame
                df = pd.DataFrame(records, columns=[
                    "NCT ID", "Title", "Sponsor", "Status", "Start", "End", "Last Verified", "Study Type", "Link"
                ])

                # Normalize partial dates (YYYY-MM → YYYY-MM-01)
                def normalize_date(date_str):
                    if isinstance(date_str, str) and len(date_str) == 7:
                        date_str += "-01"
                    return pd.to_datetime(date_str, errors='coerce')

                df["Start"] = df["Start"].apply(normalize_date)
                df["End"] = df["End"].apply(normalize_date)
                df = df.dropna(subset=["Start", "End"])
                df = df.sort_values(by="Status")

                # Convert NCT IDs to clickable links
                df["Link"] = df["NCT ID"].apply(
                    lambda x: f'<a href="https://clinicaltrials.gov/study/{x}" target="_blank">{x}</a>'
                )

                # Display table with added Study Type
                df_display = df[["Link", "Title", "Sponsor", "Status", "Study Type", "Start", "End", "Last Verified"]]
                st.markdown("### 🧾 Search Results")
                st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

                # Define custom colors by status
                custom_colors = {
                    "RECRUITING": "blue",
                    "COMPLETED": "green",
                    "TERMINATED": "#ff9999",  # light red
                    "NOT YET RECRUITING": "orange",
                    "ACTIVE, NOT RECRUITING": "orange",
                    "UNKNOWN STATUS": "gray",
                    "WITHDRAWN": "brown"
                }

                st.markdown("### 📊 Study Timeline")

                # Create Plotly timeline chart
                fig = px.timeline(
                    df,
                    x_start="Start",
                    x_end="End",
                    y="NCT ID",
                    color="Status",
                    color_discrete_map=custom_colors,
                    hover_data=["Title", "Sponsor", "Status", "Study Type"],
                    custom_data=["Link"]
                    # ,hover_data=["Enrollment"]  # Optional: enable later
                )

                # Format NCT ID labels inside bars
                fig.update_traces(
                    text=df["NCT ID"],
                    textposition="inside",
                    insidetextanchor="middle",
                    marker_line_width=0,
                    textfont=dict(size=16, color="white", family="Arial")
                )

                # Style chart layout
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

                # Add chart frame
                fig.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
                fig.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True)

                # Render chart
                st.plotly_chart(fig, use_container_width=True)
