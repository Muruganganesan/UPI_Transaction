import fitz  # PyMuPDF
import re
import pandas as pd
import getpass

pdf_path = r'C:\Users\admin\Music\Guvi\Final_project\Statement_APR2025_902773597.pdf'
# User-இன் input மூலம் password வாங்குதல்
pdf_password = getpass.getpass("Enter the PDF password: ")


# PDF open செய்யும்
doc = fitz.open(pdf_path)
if doc.needs_pass:
    if not doc.authenticate(pdf_password):
        raise ValueError("Incorrect password")

# PDF-இல் உள்ள அனைத்து பக்கங்களின் text-ஐ சேகரித்தல்
all_text = ""
for page in doc:
    all_text += page.get_text()

# Transaction table-இல் உள்ள ஒவ்வொரு வரியையும் regex-ஆல் பிடித்தல்
# Pattern: Date, Mode, Particulars, Deposits, Withdrawals, Balance
pattern = re.compile(
    r"(\d{2}-\d{2}-\d{4})\s+"                  # Date (dd-mm-yyyy)
    r"([A-Z\*\/\-]+)?\s*"                       # Mode (optional)
    r"((?:UPI|NEFT|RTGS|IMPS|CHEQUE|ATM|B/F|SBIN|[A-Za-z0-9@\/\-\.\s]+?))\s+"  # Particulars (can be multiline)
    r"([\d,]+\.\d{2})?\s*"                      # Deposits (optional)
    r"([\d,]+\.\d{2})?\s*"                      # Withdrawals (optional)
    r"([\d,]+\.\d{2})"                          # Balance
)

matches = pattern.findall(all_text)

# Extracted data-வை DataFrame-ஆக மாற்றுதல்
# Extracted data-வை DataFrame-ஆக மாற்றுதல்
data = []
previous_balance = None

for m in matches:
    date = m[0]
    mode = m[1].strip() if m[1] else ""
    particulars = m[2].replace('\n', ' ').strip()
    current_balance = float(m[5].replace(',', ''))

    # Deposits & Withdrawals calculation based on balance change
    if previous_balance is None:
        deposits = 0.0
        withdrawals = 0.0
    else:
        diff = round(current_balance - previous_balance, 2)
        if diff > 0:
            deposits = diff
            withdrawals = 0.0
        elif diff < 0:
            deposits = 0.0
            withdrawals = abs(diff)
        else:
            deposits = 0.0
            withdrawals = 0.0

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

# DataFrame-ஐ CSV ஆக சேமித்தல்
df.to_csv("icici_transactions.csv", index=False)

print("Extraction complete! Data saved to icici_transactions.csv")
print(df.head(10))

