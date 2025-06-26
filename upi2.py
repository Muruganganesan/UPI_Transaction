import os
import fitz
import re
import pandas as pd
import streamlit as st
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Streamlit App Setup
st.set_page_config(page_title="Finance Insight Pro", page_icon="📊", layout="wide")

st.title("📊 Finance Insight Pro")
st.caption("AI-powered Bank Statement Analyzer using Google Gemini")

# Sidebar Instructions
with st.sidebar:
    st.header("🔍 How to Use")
    st.markdown("1. Upload your Bank PDF Statement")
    st.markdown("2. Enter PDF password if applicable")
    st.markdown("3. View AI-based financial analysis")

# File uploader
uploaded_file = st.file_uploader("📄 Upload your PDF bank statement", type=["pdf"])
pdf_password = st.text_input("🔐 PDF Password (if protected):", type="password") if uploaded_file else ""

# Function: Extract text and structure data from PDF
def extract_pdf_text(file_path, password=""):
    try:
        doc = fitz.open(file_path)
        if doc.needs_pass and not doc.authenticate(password):
            return None, "❌ Incorrect password."

        raw_text = "".join(page.get_text() for page in doc)
        doc.close()

        # Sample regex extraction logic (customize per bank)
        pattern = re.compile(
            r"(\d{2}-\d{2}-\d{4})\s+.*?([A-Za-z0-9\s@/-]+)\s+([\d,]+\.\d{2})?\s*([\d,]+\.\d{2})?\s*([\d,]+\.\d{2})"
        )
        matches = pattern.findall(raw_text)

        rows, prev_balance = [], None
        for date, description, credit, debit, balance in matches:
            balance = float(balance.replace(",", ""))
            credit = float(credit.replace(",", "")) if credit else 0
            debit = float(debit.replace(",", "")) if debit else 0
            rows.append({
                "Date": date,
                "Description": description.strip(),
                "Credit": credit,
                "Debit": debit,
                "Balance": balance
            })
            prev_balance = balance

        df = pd.DataFrame(rows)
        return df.to_string(index=False), None

    except Exception as e:
        return None, f"⚠️ Error: {e}"

# Function: Analyze using Gemini

def analyze_with_gemini(text):
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""
    Given the following bank transaction history:
    {text}

    Analyze and summarize:
    - Monthly income and spending
    - Categories with most expenses
    - Percentage of savings
    - Red flags and recommendations
    """
    response = model.generate_content(prompt)
    return response.text.strip() if response else "⚠️ Error generating response."

# App Logic
if uploaded_file:
    file_path = f"temp_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    with st.spinner("📄 Reading PDF..."):
        extracted, error = extract_pdf_text(file_path, pdf_password)

    if error:
        st.error(error)
    elif not extracted:
        st.warning("No valid text found. Check PDF format.")
    else:
        st.success("✅ Data extracted successfully!")
        with st.spinner("🧠 Analyzing with Gemini..."):
            result = analyze_with_gemini(extracted)
        st.subheader("🔍 AI Financial Insights")
        st.markdown(result)

    try:
        os.remove(file_path)
    except:
        pass
