import os
import fitz
import re
import pandas as pd
import streamlit as st
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])


# Streamlit UI Setup
st.set_page_config(page_title="Smart Spend AI", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 34px; font-weight: bold; color: #4CAF50; }
    .sub-title { text-align: center; font-size: 18px; color: #ddd; margin-bottom: 20px; }
    .result-card { background: rgba(0, 150, 136, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .success-banner { background: linear-gradient(to right, #2E7D32, #1B5E20); color: white;
                      padding: 15px; font-size: 18px; border-radius: 8px; text-align: center; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">💰 SmartSpend AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Upload your Bank Transaction History PDF for Financial Insights</p>', unsafe_allow_html=True)

st.sidebar.title("ℹ️ How to Use This Tool?")
st.sidebar.write("- Upload your bank statement PDF.")
st.sidebar.write("- Enter PDF password if needed.")
st.sidebar.write("- It will show INCORRECT PASSWORD until you enter the password..")
st.sidebar.write("- Get AI-generated financial analysis.")

# Upload file
uploaded_file = st.file_uploader("📂 Upload PDF File", type=["pdf"])
pdf_password = st.text_input("🔐 Enter PDF Password (if any):", type="password") if uploaded_file else ""

def extract_text_from_pdf(file_path, pdf_password=""):
    try:
        doc = fitz.open(file_path)

        if doc.needs_pass:
            if not doc.authenticate(pdf_password):
                doc.close()
                return None, "❌ Incorrect password. Please try again."

        all_text = ""
        for page in doc:
            all_text += page.get_text()
        doc.close()

        pattern = re.compile(
            r"(\d{2}-\d{2}-\d{4})\s+"
            r"([A-Z\*\/\-]+)?\s*"
            r"((?:UPI|NEFT|RTGS|IMPS|CHEQUE|ATM|B/F|SBIN|[A-Za-z0-9@\/\-\.\s]+?))\s+"
            r"([\d,]+\.\d{2})?\s*"
            r"([\d,]+\.\d{2})?\s*"
            r"([\d,]+\.\d{2})"
        )

        matches = pattern.findall(all_text)
        data, previous_balance = [], None

        for m in matches:
            date = m[0]
            mode = m[1].strip() if m[1] else ""
            particulars = m[2].replace('\n', ' ').strip()
            current_balance = float(m[5].replace(',', ''))

            if previous_balance is None:
                deposits, withdrawals = 0.0, 0.0
            else:
                diff = round(current_balance - previous_balance, 2)
                deposits = diff if diff > 0 else 0.0
                withdrawals = abs(diff) if diff < 0 else 0.0

            data.append({
                "Date": date,
                "Mode": mode,
                "Particulars": particulars,
                "Deposits": deposits,
                "Withdrawals": withdrawals,
                "Balance": current_balance
            })

            previous_balance = current_balance

        df = pd.DataFrame(data)
        return df.to_string(index=False), None

    except Exception as e:
        return None, f"⚠️ Error: {str(e)}"

def analyze_financial_data(text):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"""
    Analyze the following Paytm transaction history and generate financial insights:
    {text}

    Provide a detailed breakdown in the following format:

    **Financial Insights**

    - **Monthly Income/Expense Summary**
    - **Savings Percentage**
    - **Top Spending Categories**
    - **Trends/Recommendations**
    """
    response = model.generate_content(prompt)
    return response.text.strip() if response else "⚠️ Error processing financial data."

# Processing flow
if uploaded_file:
    file_path = f"temp_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    with st.spinner("📄 Extracting text from PDF..."):
        extracted_text, error_msg = extract_text_from_pdf(file_path, pdf_password)

    if error_msg:
        st.error(error_msg)
    elif not extracted_text:
        st.warning("⚠️ No text could be extracted. Try another file.")
    else:
        st.success("✅ PDF processed successfully!")
        progress_bar = st.progress(0)
        with st.spinner("🧠 AI is analyzing your financial data..."):
            insights = analyze_financial_data(extracted_text)
        progress_bar.progress(100)

        st.subheader("📊 Financial Insights Report")
        st.markdown(f'<div class="result-card"><b>📄 Financial Report for {uploaded_file.name}</b></div>', unsafe_allow_html=True)
        st.write(insights)
        st.markdown('<div class="success-banner">🎉 Analysis Completed! Plan your finances wisely. 🚀</div>', unsafe_allow_html=True)
        st.snow()

    # Delete temp file safely
    try:
        os.remove(file_path)
    except PermissionError:
        st.warning("⚠️ Temporary file could not be deleted. Please close any open PDF viewers.")

