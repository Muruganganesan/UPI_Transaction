import os
import re
import tempfile
import pandas as pd
import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# Streamlit Secrets-ல் இருந்து API key ஏற்றல்
try:
    GEMINI_API_KEY = st.secrets["AIzaSyB18ifF7apBJR1mQKxg9HBdA89TEMn5C3I"]
except Exception:
    st.error("⚠️ GEMINI_API_KEY Streamlit Secrets-ல் இல்லை. தயவுசெய்து secrets.toml-ல் சேர்க்கவும்.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# Streamlit UI அமைப்பு
st.set_page_config(page_title="SmartSpend AI", page_icon="💰", layout="wide")

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
st.markdown('<p class="sub-title">உங்கள் வங்கி பரிவர்த்தனை PDF-ஐ பதிவேற்றவும், நுண்ணறிவு நிதி பகுப்பாய்வை பெறுங்கள்</p>', unsafe_allow_html=True)

st.sidebar.title("ℹ️ இந்த கருவி எப்படி பயன்படுத்துவது?")
st.sidebar.write("- உங்கள் வங்கி அறிக்கை PDF-ஐ பதிவேற்றவும்.")
st.sidebar.write("- PDF கடவுச்சொல் இருந்தால், அதை உள்ளிடவும்.")
st.sidebar.write("- சரியான கடவுச்சொல்லை உள்ளிடும் வரை 'INCORRECT PASSWORD' என காட்டப்படும்.")
st.sidebar.write("- AI-யால் உருவாக்கப்பட்ட நிதி பகுப்பாய்வை பெறுங்கள்.")

uploaded_file = st.file_uploader("📂 PDF கோப்பை பதிவேற்றவும்", type=["pdf"])
pdf_password = st.text_input("🔐 PDF கடவுச்சொல் (தவிர்க்கலாம்)", type="password") if uploaded_file else ""

def extract_text_from_pdf(file_path, pdf_password=""):
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not pdf_password:
                doc.close()
                return None, "❌ கடவுச்சொல் தேவைப்படுகிறது."
            if not doc.authenticate(pdf_password):
                doc.close()
                return None, "❌ தவறான கடவுச்சொல். மீண்டும் முயற்சி செய்யவும்."
        all_text = ""
        for page in doc:
            all_text += page.get_text() + "\n"
        doc.close()

        pattern = re.compile(r"""
            (\d{2}-\d{2}-\d{4})\s+                # தேதி (dd-mm-yyyy)
            ([A-Z\*\/\-]+)?\s*                    # முறை (optional)
            ((?:UPI|NEFT|RTGS|IMPS|CHEQUE|ATM|B/F|SBIN|[A-Za-z0-9@\/\-\.\s]+?))\s+  # விவரங்கள்
            ([\d,]+\.\d{2})?\s*                   # வைப்பு (optional)
            ([\d,]+\.\d{2})?\s*                   # பணம் எடுத்தல் (optional)
            ([\d,]+\.\d{2})                       # இருப்பு (balance)
        """, re.VERBOSE)

        matches = pattern.findall(all_text)
        if not matches:
            return None, "⚠️ PDF-இல் பொருத்தமான பரிவர்த்தனை தரவு கிடைக்கவில்லை."

        data = []
        previous_balance = None

        for m in matches:
            date = m[0]
            mode = m[1].strip() if m[1] else ""
            particulars = m[2].replace('\n', ' ').strip()
            deposits = float(m[3].replace(',', '')) if m[3] else 0.0
            withdrawals = float(m[4].replace(',', '')) if m[4] else 0.0
            balance = float(m[5].replace(',', ''))

            if previous_balance is not None:
                diff = round(balance - previous_balance, 2)
                if deposits == 0.0 and withdrawals == 0.0:
                    deposits = diff if diff > 0 else 0.0
                    withdrawals = abs(diff) if diff < 0 else 0.0

            data.append({
                "Date": date,
                "Mode": mode,
                "Particulars": particulars,
                "Deposits": deposits,
                "Withdrawals": withdrawals,
                "Balance": balance
            })
            previous_balance = balance

        df = pd.DataFrame(data)
        return df, None

    except Exception as e:
        return None, f"⚠️ பிழை: {str(e)}"

def analyze_financial_data(df: pd.DataFrame):
    model = genai.GenerativeModel("learnlm-1.5-pro-experimental")
    data_text = df.to_string(index=False)
    prompt = f"""
    கீழே உள்ள வங்கி பரிவர்த்தனை வரலாறு தரவுகளைப் பயன்படுத்தி நிதி பகுப்பாய்வை செய்க:

    {data_text}

    கீழ்காணும் தலைப்புகளில் விரிவான விளக்கங்களை வழங்கவும்:

    **நிதி பகுப்பாய்வுகள்**

    - மாதாந்திர வருமானம் மற்றும் செலவுகள்
    - சேமிப்பு வீதம்
    - முக்கிய செலவுக் பிரிவுகள்
    - செலவுக் கையாள்வில் பரிந்துரைகள் மற்றும் போக்குகள்
    """
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return "⚠️ நிதி தரவை செயலாக்குவதில் பிழை ஏற்பட்டது."
    except Exception as e:
        return f"⚠️ AI பகுப்பாய்வு பிழை: {str(e)}"

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_pdf_path = tmp_file.name

    with st.spinner("📄 PDF-இல் இருந்து உரை எடுக்கப்படுகிறது..."):
        df, error_msg = extract_text_from_pdf(temp_pdf_path, pdf_password)

    if error_msg:
        st.error(error_msg)
    elif df is None or df.empty:
        st.warning("⚠️ PDF-இல் பொருத்தமான தகவல் எடுக்க முடியவில்லை. வேறு கோப்பை முயற்சி செய்யவும்.")
    else:
        st.success("✅ PDF வெற்றிகரமாக செயலாக்கப்பட்டது!")
        st.dataframe(df)

        with st.spinner("🧠 AI உங்கள் நிதி தரவை பகுப்பாய்வு செய்கிறது..."):
            insights = analyze_financial_data(df)

        st.subheader("📊 நிதி பகுப்பாய்வு அறிக்கை")
        st.markdown(f'<div class="result-card"><b>📄 {uploaded_file.name} - நிதி அறிக்கை</b></div>', unsafe_allow_html=True)
        st.write(insights)
        st.markdown('<div class="success-banner">🎉 பகுப்பாய்வு முடிந்தது! உங்கள் நிதி திட்டமிடலை சிறப்பாக்குங்கள். 🚀</div>', unsafe_allow_html=True)
        st.snow()

    try:
        os.remove(temp_pdf_path)
    except Exception:
        st.warning("⚠️ தற்காலிக கோப்பு நீக்க முடியவில்லை. PDF-ஐ திறந்துள்ள விண்டோக்களை மூடவும்.")
else:
    st.info("📌 மேலே PDF கோப்பை பதிவேற்றவும் மற்றும் கடவுச்சொல்லை (தேவைப்பட்டால்) உள்ளிடவும்.")
