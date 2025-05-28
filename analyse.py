import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ------------- PAGE SETUP -------------
st.set_page_config(layout="wide")
st.title("🚑 Clinical Trials Explorer")

# ------------- SEARCH INPUT -------------
query = st.text_input(
    "Enter a condition or keyword (e.g., BPH, prostate cancer):", ""
)

# --- Keep search results in memory so filters don’t break UX ---
if "df" not in st.session_state:
    st.session_state.df = None

# ------------- DATA FETCHING FROM API -------------
if st.button("Search"):
    with st.spinner("Fetching data from ClinicalTrials.gov..."):
        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={query}&pageSize=30"
        response = requests.get(url)

        if response.status_code == 200:
            studies = response.json().get("studies", [])
            records = []

            # --- Extract selected fields from each study for our DataFrame ---
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
                    company_id = id_mod.get("orgStudyIdInfo", {}).get("id", "")
                    link = f"https://clinicaltrials.gov/study/{nct_id}"

                    records.append((
                        nct_id, title, sponsor, status, study_type,
                        company_id, start_date, end_date, last_verified, link
                    ))
                except Exception:
                    continue

            # --- Create DataFrame for all studies ---
            df = pd.DataFrame(records, columns=[
                "NCT ID", "Title", "Sponsor", "Status", "Study Type",
                "Company Study ID", "Start", "End", "Last Verified", "Link"
            ])

            # --- Convert start/end dates to datetime for sorting and plotting ---
            def normalize_date(date_str):
                if isinstance(date_str, str) and len(date_str) == 7:
                    date_str += "-01"
                return pd.to_datetime(date_str, errors='coerce')

            df["Start"] = df["Start"].apply(normalize_date)
            df["End"] = df["End"].apply(normalize_date)
            df = df.dropna(subset=["Start", "End"])  # Only keep studies with valid dates

            # --- Sort first by Start Date for better timeline sense ---
            df = df.sort_values(by=["Start", "End"]).reset_index(drop=True)

            # --- Assign row numbers after sorting by start date ---
            df["#"] = range(1, len(df) + 1)

            # --- Bar label combines NCT ID and running number for clear mapping ---
            df["Bar Label"] = df.apply(lambda row: f"{row['NCT ID']} ({row['#']})", axis=1)

            # --- Turn NCT IDs into clickable links for table ---
            df["Link"] = df["NCT ID"].apply(
                lambda x: f'<a href="https://clinicaltrials.gov/study/{x}" target="_blank">{x}</a>'
            )

            st.session_state.df = df  # Store results for use with filters
            st.dataframe(df)
        else:
            st.error("Failed to fetch data. Try again later.")

# ------------- FILTERS & DATA DISPLAY -------------
if st.session_state.df is not None:
    df = st.session_state.df.copy()  # Work with a copy to allow re-filtering

    # --- Show filters side-by-side for Sponsor and Study Type ---
    col1, col2 = st.columns(2)
    with col1:
        sponsors = sorted(df["Sponsor"].dropna().unique())
        sponsor_filter = st.selectbox("Filter by Sponsor", ["All"] + sponsors)
        if sponsor_filter != "All":
            df = df[df["Sponsor"] == sponsor_filter]
    with col2:
        study_types = sorted(df["Study Type"].dropna().unique())
        type_filter = st.selectbox("Filter by Study Type", ["All"] + study_types)
        if type_filter != "All":
            df = df[df["Study Type"] == type_filter]

    # --- After filtering, sort again by Start Date and assign new row numbers ---
    df = df.sort_values(by=["Start", "End"]).reset_index(drop=True)
    df["#"] = range(1, len(df) + 1)
    df["Bar Label"] = df.apply(lambda row: f"{row['NCT ID']} ({row['#']})", axis=1)

    # --- Build table for display ---
    df_display = df[[
        "#", "Link", "Title", "Sponsor", "Status", "Study Type",
        "Company Study ID", "Start", "End", "Last Verified"
    ]]
    st.markdown("### 🧾 Search Results")
    st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.dataframe(df_display)
    # ------------- TIMELINE CHART -------------
    st.markdown("### 📊 Study Timeline")

    # --- Custom color palette for study status ---
    custom_colors = {
        "RECRUITING": "blue",
        "COMPLETED": "green",
        "TERMINATED": "#ff9999",
        "NOT YET RECRUITING": "orange",
        "ACTIVE, NOT RECRUITING": "orange",
        "UNKNOWN STATUS": "gray",
        "WITHDRAWN": "brown"
    }

    # --- Keep plot order in sync with table by using Bar Label as y ---
    bar_labels = df["Bar Label"].tolist()

    # --- Create Plotly Gantt/timeline chart ---
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="End",
        y="Bar Label",
        color="Status",
        color_discrete_map=custom_colors,
        category_orders={"Bar Label": bar_labels},  # Force order!
        hover_data=["NCT ID", "Title", "Sponsor", "Status", "Study Type", "Company Study ID"],
        custom_data=["Link"]
    )

    # --- Text inside bars: show "NCT ID (#)" ---
    fig.update_traces(
        text=df["Bar Label"],
        textposition="inside",
        insidetextanchor="middle",
        marker_line_width=0,
        textfont=dict(size=16, color="white", family="Arial")
    )

    # --- Add a vertical "today" line (as ISO string for safest date handling) ---
    today = datetime.today().date().isoformat()
    fig.add_vline(
        x=today,
        line_width=2,
        line_dash="dash",
        line_color="red"
    )

    # --- Layout, fonts, colors, etc ---
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
    # --- Strong black frame on plot ---
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    fig.update_yaxes(autorange="reversed")  # Ensures chart order matches table

    st.plotly_chart(fig, use_container_width=True)
