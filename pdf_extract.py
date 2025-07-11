import fitz  # PyMuPDF
import re
import pandas as pd
import getpass

pdf_path = r'C:\Users\admin\Music\Guvi\Final_project\Statement_APR2025_902773597.pdf'
# Password acquisition through user input
pdf_password = getpass.getpass("Enter the PDF password: ")


# PDF open 
doc = fitz.open(pdf_path)
if doc.needs_pass:
    if not doc.authenticate(pdf_password):
        raise ValueError("Incorrect password")

# Collecting text from all pages in a PDF
all_text = ""
for page in doc:
    all_text += page.get_text()

# Capturing each row in the transaction table with regex
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

# Converting extracted data into a DataFrame
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

# Saving a DataFrame as CSV
df.to_csv("icici_transactions.csv", index=False)

print("Extraction complete! Data saved to icici_transactions.csv")
print(df.head(10))

