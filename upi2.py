import os
import fitz
import re
import pandas as pd
import streamlit as st
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Streamlit UI Setup
st.set_page_config(page_title="SmartSpend AI", page_icon=" ", layout="wide")

st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 34px; font-weight: bold; color: #4CAF50; }
    .sub-title { text-align: center; font-size: 18px; color: #ddd; margin-bottom: 20px; }
    .result-card { background: rgba(0, 150, 136, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .success-banner { background: linear-gradient(to right, #2E7D32, #1B5E20); color: white;
                      padding: 15px; font-size: 18px; border-radius: 8px; text-align: center; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title"> SmartSpend AI </h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title"> Intelligent Financial Insights from Your Bank Statement </p>', unsafe_allow_html=True)

st.sidebar.title("- How to Use This Tool -")
st.sidebar.write("- Upload your bank statement PDF.")
st.sidebar.write("- Enter PDF password if needed.")
st.sidebar.write("- You will get full transaction extract + only UPI transactions + AI insights.")

# Upload file
uploaded_file = st.file_uploader("📂 Upload PDF File", type=["pdf"])
pdf_password = st.text_input("🔐 Enter PDF Password (if any):", type="password") if uploaded_file else ""

def extract_and_filter_pdf(file_path, pdf_password=""):
    try:
        doc = fitz.open(file_path)

        if doc.needs_pass:
            if not doc.authenticate(pdf_password):
                doc.close()
                return None, None, "❌ Incorrect password. Please try again."

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

        # Filter UPI transactions using Particulars
        upi_df = df[df['Particulars'].str.upper().str.contains("UPI")]

        # Save to CSV
        df.to_csv("all_transactions.csv", index=False)
        upi_df.to_csv("upi_transactions.csv", index=False)

        return df, upi_df, None

    except Exception as e:
        return None, None, f"⚠️ Error: {str(e)}"

def analyze_financial_data(text):
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""
    Analyze the following Bank transaction history and generate financial insights:
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

    start_analysis_button = st.button("🔍 Start Financial Analysis")

    if start_analysis_button:
        with st.spinner("📄 Extracting transactions from PDF..."):
            df, upi_df, error_msg = extract_and_filter_pdf(file_path, pdf_password)

        if error_msg:
            st.error(error_msg)
        elif df is None or df.empty:
            st.warning("⚠️ No transactions found in PDF.")
        else:
            st.success("✅ PDF processed successfully!")

            st.subheader("📄 All Transactions Preview")
            st.dataframe(df)

            st.subheader("💸 Only UPI Transactions Preview")
            if upi_df.empty:
                st.info("No UPI transactions found.")
            else:
                st.dataframe(upi_df)

            # Download buttons
            st.download_button("⬇️ Download All Transactions CSV", data=df.to_csv(index=False), file_name="all_transactions.csv", mime="text/csv")
            st.download_button("⬇️ Download UPI Transactions CSV", data=upi_df.to_csv(index=False), file_name="upi_transactions.csv", mime="text/csv")

            # AI Analysis
            st.subheader("🤖 AI Financial Insights")
            with st.spinner("🧠 Gemini AI is analyzing your data..."):
                insights = analyze_financial_data(df.to_string(index=False))
            st.markdown(f'<div class="result-card"><b>📊 Insights:</b><br>{insights}</div>', unsafe_allow_html=True)
            st.markdown('<div class="success-banner">🎉 Analysis Completed! Manage your spending smarter. 🚀</div>', unsafe_allow_html=True)
            st.snow()

        try:
            os.remove(file_path)
        except:
            pass
