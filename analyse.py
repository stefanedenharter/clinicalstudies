import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# ------------- PAGE SETUP -------------
st.set_page_config(layout="wide")
st.title("🚑 Clinical Trials Explorer")

# ------------- SEARCH INPUT -------------
query = st.text_input(
    "Enter a condition or keyword (e.g., BPH, prostate cancer):", "BPH"
)

# --- Session state to preserve search results for smooth filtering ---
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

            # --- Create DataFrame ---
            df = pd.DataFrame(records, columns=[
                "NCT ID", "Title", "Sponsor", "Status", "Study Type",
                "Company Study ID", "Start", "End", "Last Verified", "Link"
            ])

            # --- Convert to datetime, drop records without valid dates ---
            def normalize_date(date_str):
                if isinstance(date_str, str) and len(date_str) == 7:
                    date_str += "-01"
                return pd.to_datetime(date_str, errors='coerce')
            df["Start"] = df["Start"].apply(normalize_date)
            df["End"] = df["End"].apply(normalize_date)
            df = df.dropna(subset=["Start", "End"])

            # --- Sort by start/end date for timeline sensibility ---
            df = df.sort_values(by=["Start", "End"]).reset_index(drop=True)

            # --- Drop duplicate NCT IDs so only one row/bar per study ---
            df = df.drop_duplicates(subset=["NCT ID"], keep="first").reset_index(drop=True)

            # --- Assign running number after sorting/deduplication ---
            df["#"] = range(1, len(df) + 1)
            df["Bar Label"] = df.apply(lambda row: f"{row['NCT ID']} ({row['#']})", axis=1)

            # --- Make NCT ID a clickable link in the table ---
            df["Link"] = df["NCT ID"].apply(
                lambda x: f'<a href="https://clinicaltrials.gov/study/{x}" target="_blank">{x}</a>'
            )

            st.session_state.df = df  # Store for filtering
        else:
            st.error("Failed to fetch data. Try again later.")

# ------------- FILTERS & DATA DISPLAY -------------
if st.session_state.df is not None:
    df = st.session_state.df.copy()

    # --- Filters side by side ---
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

    # --- Sort and deduplicate after filtering, assign row numbers ---
    df = df.sort_values(by=["Start", "End"]).drop_duplicates(subset=["NCT ID"], keep="first").reset_index(drop=True)
    df["#"] = range(1, len(df) + 1)
    df["Bar Label"] = df.apply(lambda row: f"{row['NCT ID']} ({row['#']})", axis=1)

    # --- Download buttons for CSV and Excel (TOP RIGHT) ---
    csv = df.to_csv(index=False).encode('utf-8')
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Studies')
    excel_data = excel_buffer.getvalue()

    # Three columns: [empty, CSV, Excel] - buttons right-aligned
    col_dl1, col_dl2, col_dl3 = st.columns([6, 1, 1])
    with col_dl2:
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name='clinical_trials.csv',
            mime='text/csv',
            key="csv_dl"
        )
    with col_dl3:
        st.download_button(
            label="⬇️ Download Excel",
            data=excel_data,
            file_name='clinical_trials.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key="excel_dl"
        )

    # --- Table for display ---
    df_display = df[[
        "#", "Link", "Title", "Sponsor", "Status", "Study Type",
        "Company Study ID", "Start", "End", "Last Verified"
    ]]
    st.markdown("### 🧾 Search Results")
    st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ------------- TIMELINE CHART -------------
    st.markdown("### 📊 Study Timeline")
    custom_colors = {
        "RECRUITING": "blue",
        "COMPLETED": "green",
        "TERMINATED": "#ff9999",
        "NOT YET RECRUITING": "purple",
        "ACTIVE, NOT RECRUITING": "orange",
        "UNKNOWN STATUS": "gray",
        "WITHDRAWN": "brown"
    }

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="End",
        y="Bar Label",
        color="Status",
        color_discrete_map=custom_colors,
        hover_data=["Bar Label", "NCT ID", "Title", "Sponsor", "Status", "Study Type", "Company Study ID"],
        custom_data=["Link"],
        text="Bar Label"
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        marker_line_width=0,
        textfont=dict(size=16, color="white", family="Arial")
    )

    fig.update_yaxes(
        autorange="reversed",
        showticklabels=False,      # Hide y-axis tick labels
        showline=True,
        linecolor="black",
        linewidth=2,
        mirror=True
    )

    today = datetime.today().date().isoformat()
    fig.add_vline(
        x=today,
        line_width=2,
        line_dash="dash",
        line_color="red"
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

    st.plotly_chart(fig, use_container_width=True)
