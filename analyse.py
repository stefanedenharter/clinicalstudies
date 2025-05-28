import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.title("Clinical Trials Explorer")

query = st.text_input("Search condition (e.g., BPH, prostate cancer)", "BPH")

if st.button("Search"):
    url = f"https://clinicaltrials.gov/api/v2/studies?query.term={query}&pageSize=20"
    response = requests.get(url)
    data = response.json()
    studies = data.get("studies", [])

    records = []
    for study in studies:
        id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
        title = study.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", "")
        status = study.get("protocolSection", {}).get("statusModule", {}).get("overallStatus", "")
        start_date = study.get("protocolSection", {}).get("statusModule", {}).get("startDateStruct", {}).get("date", "")
        end_date = study.get("protocolSection", {}).get("statusModule", {}).get("completionDateStruct", {}).get("date", "")
        records.append((id, title, status, start_date, end_date))

        df = pd.DataFrame(records, columns=["ID", "Title", "Status", "Start", "End"])

        # Add hyperlinks in Markdown format
        df["ID"] = df["ID"].apply(lambda x: f"[{x}](https://clinicaltrials.gov/study/{x})")
        
        # Display as markdown-enabled table
        st.markdown("### Search Results")
        st.write(df.to_markdown(index=False), unsafe_allow_html=True)


    # Plot chart
    df = df.dropna(subset=["Start", "End"])
    df["Start"] = pd.to_datetime(df["Start"], errors='coerce')
    df["End"] = pd.to_datetime(df["End"], errors='coerce')
    df = df.dropna()

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, row in df.iterrows():
        ax.barh(i, (row["End"] - row["Start"]).days, left=row["Start"], height=0.6)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["Title"], fontsize=7)
    ax.set_xlabel("Date")
    st.pyplot(fig)
