import streamlit as st
import pandas as pd
import datetime
import openai
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
BUDGET = 1000
SAVINGS_GOAL = 300
openai.api_key = st.secrets["openai_api_key"]

# --- FILES ---
EXPENSES_FILE = "data/expenses.csv"
GOOGLE_SHEET_NAME = "FinanceTracker-Investments"

# --- SETUP ---
st.set_page_config(page_title="Finance Agent", layout="wide")
st.title("💸 Personal Finance & Investment Tracker")

# --- LOAD EXPENSES FROM CSV ---
def load_expenses():
    try:
        df = pd.read_csv(EXPENSES_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['date', 'category', 'amount'])

# --- LOAD INVESTMENTS FROM GOOGLE SHEETS ---
@st.cache_resource
def load_google_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gcredentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# --- SAVE TO GOOGLE SHEETS ---
def add_investment_to_sheet(symbol, amount):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gcredentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    sheet.append_row([symbol, amount])

# --- LOAD DATA ---
expenses = load_expenses()
investments = load_google_sheet(GOOGLE_SHEET_NAME)

# --- ADD EXPENSE ---
st.header("➕ Add Weekly Expense")
with st.form("add_expense"):
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("Date", datetime.date.today())
    with col2:
        category = st.selectbox("Category", ["Food", "Rent", "Gym", "Fun", "Other"])
    with col3:
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
    submitted = st.form_submit_button("Add Expense")
    if submitted:
        new_row = pd.DataFrame([[date, category, amount]], columns=expenses.columns)
        expenses = pd.concat([expenses, new_row], ignore_index=True)
        expenses.to_csv(EXPENSES_FILE, index=False)
        st.success("Expense added!")

# --- WEEKLY SUMMARY ---
st.header("📊 Weekly Summary")
today = datetime.date.today()
seven_days_ago = today - datetime.timedelta(days=7)
weekly = expenses[expenses['date'] >= seven_days_ago].copy()
total_spent = weekly['amount'].sum()
savings = BUDGET - total_spent

col1, col2, col3 = st.columns(3)
col1.metric("Total Spent (This Week)", f"€{total_spent:.2f}")
col2.metric("Remaining Budget", f"€{BUDGET - total_spent:.2f}")
col3.metric("Progress to Savings Goal", f"€{savings:.2f} / €{SAVINGS_GOAL}")

# --- ADD INVESTMENT ---
st.header("💹 Add Investment")
with st.form("add_investment"):
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Stock Symbol (e.g. AAPL)")
    with col2:
        amount = st.number_input("Amount Invested (€)", min_value=0.0, step=0.01)
    invest_submit = st.form_submit_button("Add Investment")
    if invest_submit and symbol and amount > 0:
        add_investment_to_sheet(symbol.upper(), amount)
        st.success(f"Investment in {symbol.upper()} added!")

# --- INVESTMENT TRACKER ---
st.header("📈 Investment Tracker")
investment_data = []
total_value = 0.0
for _, row in investments.iterrows():
    symbol = row['symbol']
    invested = float(row['amount_invested'])
    ticker = yf.Ticker(symbol)
    try:
        price = ticker.history(period="1d")["Close"].iloc[-1]
        current_value = invested  # Placeholder logic
        investment_data.append({
            "Symbol": symbol,
            "Invested (€)": invested,
            "Current Price (€)": round(price, 2),
            "Current Value (€)": round(price, 2)  # Can multiply with quantity
        })
        total_value += price
    except:
        continue
if investment_data:
    st.dataframe(pd.DataFrame(investment_data))
    st.write(f"💼 Total portfolio value: €{total_value:.2f}")

# --- AI FEEDBACK ---
st.header("🤖 Smart Weekly Feedback")

def generate_feedback(expenses, total_spent, savings):
    try:
        text = f"This week, you spent €{total_spent:.2f}. Your savings are €{savings:.2f}. Expenses by category: {expenses['category'].value_counts().to_dict()}."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're a friendly personal finance coach."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except:
        return "Unable to generate feedback. Please check your OpenAI setup."

if not weekly.empty:
    with st.spinner("Analyzing your week..."):
        feedback = generate_feedback(weekly, total_spent, savings)
        st.success(feedback)
else:
    st.info("Add some expenses to get feedback.")

# --- CHAT FUNCTION ---
st.header("💬 Ask the Finance Bot")

user_input = st.text_input("Ask me anything about your finances or investments:")
if user_input:
    try:
        chat_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a smart, friendly financial assistant. Answer clearly and helpfully."},
                {"role": "user", "content": user_input}
            ]
        )
        st.success(chat_response.choices[0].message.content)
    except:
        st.error("Chat failed. Check OpenAI API key.")
