import streamlit as st
import pandas as pd
import datetime
import openai
import yfinance as yf

# --- CONFIG ---
BUDGET = 1000
SAVINGS_GOAL = 300
openai.api_key = st.secrets["openai_api_key"]

# --- FILES ---
EXPENSES_FILE = "data/expenses.csv"
INVESTMENTS_FILE = "data/investments.csv"

# --- SETUP ---
st.set_page_config(page_title="Finance Agent", layout="wide")
st.title("💸 Personal Finance & Investment Tracker")

# --- LOAD DATA ---
def load_expenses():
    try:
        df = pd.read_csv(EXPENSES_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    except Exception as e:
        return pd.DataFrame(columns=['date', 'category', 'amount'])

def load_investments():
    try:
        return pd.read_csv(INVESTMENTS_FILE)
    except:
        return pd.DataFrame(columns=['symbol', 'amount_invested'])

expenses = load_expenses()
investments = load_investments()

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
st.header("➕ Add Investment")
with st.form("add_investment"):
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Stock Symbol (e.g. AAPL, TSLA, MSFT)")
    with col2:
        amount_invested = st.number_input("Amount Invested (€)", min_value=0.0, step=1.0)
    inv_submitted = st.form_submit_button("Add Investment")
    if inv_submitted and symbol:
        new_inv = pd.DataFrame([[symbol.upper(), amount_invested]], columns=investments.columns)
        investments = pd.concat([investments, new_inv], ignore_index=True)
        investments.to_csv(INVESTMENTS_FILE, index=False)
        st.success(f"Investment in {symbol.upper()} added!")

# --- INVESTMENTS ---
st.header("📈 Investment Tracker")
investment_data = []
total_value = 0.0
for _, row in investments.iterrows():
    symbol = row['symbol']
    invested = float(row['amount_invested'])
    ticker = yf.Ticker(symbol)
    try:
        price = ticker.history(period="1d")["Close"].iloc[-1]
        current_value = price  # Placeholder: kun je vermenigvuldigen met gekocht aantal als je dat opslaat
        investment_data.append({
            "Symbol": symbol,
            "Invested (€)": invested,
            "Current Price (€)": round(price, 2),
            "Current Value (€)": round(current_value, 2)
        })
        total_value += current_value
    except:
        continue
if investment_data:
    st.dataframe(pd.DataFrame(investment_data))
    st.write(f"💼 Total portfolio value: €{total_value:.2f}")

# --- AI FEEDBACK ---
st.header("🤖 Smart Weekly Feedback")

def generate_feedback(expenses, total_spent, savings, investments_df, total_portfolio_value):
    try:
        exp_by_category = expenses.groupby("category")["amount"].sum().to_dict()
        inv_summary = ", ".join(
            f"{row['symbol']} (€{row['amount_invested']})"
            for _, row in investments_df.iterrows()
        )

        prompt = (
            f"This week, you spent €{total_spent:.2f} and saved €{savings:.2f}. "
            f"Your expenses per category: {exp_by_category}. "
            f"You also invested in: {inv_summary}. "
            f"Total portfolio value: €{total_portfolio_value:.2f}. "
            f"Give helpful weekly feedback including tips or suggestions."
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're a friendly and smart personal finance coach."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Unable to generate feedback. Please check your OpenAI setup."

if not weekly.empty:
    with st.spinner("Analyzing your week..."):
        feedback = generate_feedback(weekly, total_spent, savings, investments, total_value)
        st.success(feedback)
else:
    st.info("Add some expenses to get feedback.")

