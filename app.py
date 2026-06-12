"""Streamlit UI: upload an FNOL document, see extracted fields + routing decision."""

import json
import os
import tempfile
from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from claims_agent.agent import process_document

ROUTE_STYLES = {
    "Fast-track": ("✅", "#16a34a"),
    "Manual Review": ("📝", "#d97706"),
    "Investigation Flag": ("🚨", "#dc2626"),
    "Specialist Queue": ("🩺", "#7c3aed"),
    "Standard Processing": ("📂", "#2563eb"),
}

st.set_page_config(page_title="FNOL Claims Agent", page_icon="🚗", layout="wide")
st.title("🚗 Autonomous Insurance Claims Processing Agent")
st.caption("Upload an FNOL (First Notice of Loss) document — the agent extracts fields, "
           "checks completeness, and routes the claim with an explanation.")

if os.environ.get("LLM_API_KEY"):
    mode = f"LLM ({os.environ.get('LLM_MODEL', 'llama-3.3-70b-versatile')}) + rules"
else:
    mode = "Regex fallback + rules (no API key set)"
st.sidebar.header("Agent")
st.sidebar.write(f"**Extraction mode:** {mode}")
st.sidebar.markdown(
    "**Routing precedence**\n"
    "1. Fraud keywords → Investigation Flag\n"
    "2. Injury claim → Specialist Queue\n"
    "3. Missing mandatory field → Manual Review\n"
    "4. Damage < 25,000 → Fast-track\n"
    "5. Otherwise → Standard Processing"
)

uploaded = st.file_uploader("FNOL document", type=["pdf", "txt"])

if uploaded:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    try:
        with st.spinner("Processing claim..."):
            result = process_document(tmp_path)
    finally:
        os.unlink(tmp_path)
    result["meta"]["sourceFile"] = uploaded.name

    route = result["recommendedRoute"]
    icon, color = ROUTE_STYLES.get(route, ("📄", "#6b7280"))
    st.markdown(
        f"<div style='padding:14px;border-radius:10px;background:{color}20;"
        f"border-left:6px solid {color};font-size:1.25rem;'>"
        f"{icon} <b>Recommended route: {route}</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**Reasoning:** {result['reasoning']}")

    col_fields, col_status = st.columns([3, 2])

    with col_fields:
        st.subheader("Extracted fields")
        rows = []
        for section, keys in result["extractedFields"].items():
            for key, value in keys.items():
                rows.append(
                    {
                        "Section": section,
                        "Field": key,
                        "Value": value if value is not None else "—",
                    }
                )
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with col_status:
        st.subheader("Completeness")
        if result["missingFields"]:
            for field in result["missingFields"]:
                st.warning(f"Missing: `{field}`")
        else:
            st.success("All mandatory fields present.")

        if result["meta"]["inconsistencies"]:
            st.subheader("Consistency warnings")
            for issue in result["meta"]["inconsistencies"]:
                st.error(issue)

        st.caption(f"Extraction method: {result['meta']['extractionMethod']}")

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    st.subheader("Result JSON")
    st.code(payload, language="json")
    st.download_button(
        "Download JSON",
        payload,
        file_name=f"{Path(uploaded.name).stem}_result.json",
        mime="application/json",
    )
else:
    st.info("Upload a sample from the `samples/` folder to try the agent.")
