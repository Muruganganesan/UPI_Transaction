import fitz  # PyMuPDF
import re
import pandas as pd
import getpass

# PDF file path
pdf_path = r'C:\Users\admin\Music\Guvi\Final_project\Statement_JUL2025_902773597.pdf'

# Get password from user
pdf_password = getpass.getpass("Enter the PDF password: ")

# Open the PDF
doc = fitz.open(pdf_path)
if doc.needs_pass:
    if not doc.authenticate(pdf_password):
        raise ValueError("Incorrect password!")

# Extract all text from PDF pages
all_text = ""
for page in doc:
    all_text += page.get_text()

# Define regex pattern for transaction extraction
pattern = re.compile(
    r"(\d{2}-\d{2}-\d{4})\s+"                  
    r"([A-Z\*\/\-]+)?\s*"                       
    r"((?:UPI|NEFT|RTGS|IMPS|CHEQUE|ATM|B/F|SBIN|[A-Za-z0-9@\/\-\.\s]+?))\s+"  
    r"([\d,]+\.\d{2})?\s*"                      
    r"([\d,]+\.\d{2})?\s*"                      
    r"([\d,]+\.\d{2})"                          
)

matches = pattern.findall(all_text)

# Extracted data to list
data = []
previous_balance = None

for m in matches:
    date = m[0]
    mode = m[1].strip() if m[1] else ""
    particulars = m[2].replace('\n', ' ').strip()
    current_balance = float(m[5].replace(',', ''))

    # Calculate deposits & withdrawals based on balance change
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

# Create DataFrame
df = pd.DataFrame(data)

# Save all transactions to CSV
df.to_csv("icici_transactions.csv", index=False)

# Filter UPI transactions (FIX: Use 'Particulars' column, not 'Mode')
upi_df = df[df['Particulars'].str.upper().str.contains("UPI")]

# Save UPI transactions to CSV
upi_df.to_csv("upi_transactions.csv", index=False)

# Output
print("Extraction complete!")
print("All transactions saved to icici_transactions.csv")
print("Only UPI transactions saved to upi_transactions.csv")
print(upi_df.head(10))
