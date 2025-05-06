import streamlit as st
import pandas as pd
import datetime
import openai
import yfinance as yf
import os

# --- CONFIG ---
BUDGET = 1000
SAVINGS_GOAL = 300
# Initialize OpenAI client
client = openai.OpenAI(api_key=st.secrets.get("openai_api_key", ""))
# Use GPT-3.5-turbo instead of GPT-4 for wider accessibility
AI_MODEL = "gpt-3.5-turbo"

# --- FILES ---
EXPENSES_FILE = "data/expenses.csv"
INVESTMENTS_FILE = "data/investments.csv"

# --- SETUP ---
st.set_page_config(page_title="Finance Agent", layout="wide")
st.title("💸 Personal Finance & Investment Tracker")

# --- ENSURE DATA DIRECTORY EXISTS ---
os.makedirs("data", exist_ok=True)

# --- LOAD EXPENSES FROM CSV ---
def load_expenses():
    try:
        if os.path.exists(EXPENSES_FILE):
            df = pd.read_csv(EXPENSES_FILE)
            df['date'] = pd.to_datetime(df['date']).dt.date
            return df
        else:
            return pd.DataFrame(columns=['date', 'category', 'amount'])
    except Exception as e:
        st.warning(f"Error loading expenses: {str(e)}")
        return pd.DataFrame(columns=['date', 'category', 'amount'])

# --- LOAD INVESTMENTS FROM CSV ---
def load_investments():
    try:
        if os.path.exists(INVESTMENTS_FILE):
            df = pd.read_csv(INVESTMENTS_FILE)
            return df
        else:
            return pd.DataFrame(columns=['symbol', 'amount_invested', 'date_added'])
    except Exception as e:
        st.warning(f"Error loading investments: {str(e)}")
        return pd.DataFrame(columns=['symbol', 'amount_invested', 'date_added'])

# --- SAVE INVESTMENT TO CSV ---
def add_investment(symbol, amount):
    try:
        investments = load_investments()
        new_row = pd.DataFrame([[symbol, amount, datetime.date.today()]], 
                              columns=['symbol', 'amount_invested', 'date_added'])
        investments = pd.concat([investments, new_row], ignore_index=True)
        investments.to_csv(INVESTMENTS_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Error adding investment: {str(e)}")
        return False

# --- LOAD DATA ---
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
        try:
            new_row = pd.DataFrame([[date, category, amount]], columns=expenses.columns)
            expenses = pd.concat([expenses, new_row], ignore_index=True)
            expenses.to_csv(EXPENSES_FILE, index=False)
            st.success("Expense added!")
        except Exception as e:
            st.error(f"Error adding expense: {str(e)}")

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
        if add_investment(symbol.upper(), amount):
            st.success(f"Investment in {symbol.upper()} added!")
            # Refresh investments data
            investments = load_investments()

# --- INVESTMENT TRACKER ---
st.header("📈 Investment Tracker")
investment_data = []
total_value = 0.0
total_invested = 0.0

if not investments.empty:
    with st.spinner("Fetching current market data..."):
        for _, row in investments.iterrows():
            symbol = row['symbol']
            invested = float(row['amount_invested'])
            total_invested += invested
            try:
                ticker = yf.Ticker(symbol)
                price = ticker.history(period="1d")["Close"].iloc[-1]
                # Assuming the investment is in shares, calculate number of shares
                # This is a simple version - you might want to refine this calculation
                approx_shares = invested / price
                current_value = price * approx_shares
                
                investment_data.append({
                    "Symbol": symbol,
                    "Invested (€)": round(invested, 2),
                    "Approx. Shares": round(approx_shares, 4),
                    "Current Price (€)": round(price, 2),
                    "Current Value (€)": round(current_value, 2),
                    "Gain/Loss (€)": round(current_value - invested, 2),
                    "Gain/Loss (%)": round(((current_value - invested) / invested) * 100, 2)
                })
                total_value += current_value
            except Exception as e:
                st.warning(f"Could not fetch data for {symbol}: {str(e)}")
                # Add row with missing data
                investment_data.append({
                    "Symbol": symbol,
                    "Invested (€)": round(invested, 2),
                    "Approx. Shares": "N/A",
                    "Current Price (€)": "N/A",
                    "Current Value (€)": "N/A",
                    "Gain/Loss (€)": "N/A",
                    "Gain/Loss (%)": "N/A"
                })
                continue

if investment_data:
    st.dataframe(pd.DataFrame(investment_data))
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"€{total_invested:.2f}")
    col2.metric("Current Portfolio Value", f"€{total_value:.2f}")
    col3.metric("Total Gain/Loss", 
                f"€{total_value - total_invested:.2f}", 
                f"{((total_value - total_invested) / total_invested * 100):.2f}%" if total_invested > 0 else "0.00%")
else:
    st.info("No investments yet. Add your first investment above!")

# --- EXPENSE VISUALIZATION ---
st.header("💰 Expense Breakdown")
if not expenses.empty:
    # Category breakdown
    category_totals = expenses.groupby('category')['amount'].sum().reset_index()
    st.bar_chart(category_totals.set_index('category'))
    
    # Show recent expenses
    st.subheader("Recent Expenses")
    st.dataframe(expenses.sort_values(by='date', ascending=False).head(10))
else:
    st.info("No expenses recorded yet.")

# --- AI FEEDBACK --- (Updated to use GPT-3.5-turbo)
st.header("🤖 Smart Weekly Feedback")

def generate_feedback(expenses, total_spent, savings, investments_data):
    if not st.secrets.get("openai_api_key", ""):
        return "OpenAI API key not configured. Please add it to your secrets."
        
    try:
        # Create a rich context combining expenses and investments
        investment_summary = "No investments yet."
        if investments_data:
            total_invested = sum(item.get("Invested (€)", 0) for item in investments_data if isinstance(item.get("Invested (€)"), (int, float)))
            symbols = [item["Symbol"] for item in investments_data]
            investment_summary = f"You have invested €{total_invested:.2f} in {len(symbols)} stocks: {', '.join(symbols)}."
        
        # Weekly expense summary
        expense_summary = f"This week, you spent €{total_spent:.2f}. Your savings are €{savings:.2f} towards your goal of €{SAVINGS_GOAL}."
        if not expenses.empty:
            category_breakdown = expenses['category'].value_counts().to_dict()
            expense_summary += f" Expenses by category: {category_breakdown}"
        
        # Combined prompt
        prompt = f"{expense_summary} {investment_summary} Please provide friendly financial advice based on this information."
        
        # Updated to use GPT-3.5-turbo
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You're a friendly personal finance coach. Provide concise, actionable advice."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Unable to generate feedback: {str(e)}"

if not weekly.empty or not investments.empty:
    with st.spinner("Analyzing your finances..."):
        feedback = generate_feedback(weekly, total_spent, savings, investment_data)
        st.success(feedback)
else:
    st.info("Add some expenses or investments to get personalized feedback.")

# --- CHAT FUNCTION --- (Updated to use GPT-3.5-turbo)
st.header("💬 Ask the Finance Bot")

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_input("Ask me anything about your finances or investments:")
if user_input:
    st.session_state.chat_history.append(("You", user_input))
    
    # Create context from financial data
    context = f"Current weekly spending: €{total_spent:.2f}. Budget: €{BUDGET}. Savings goal: €{SAVINGS_GOAL}."
    if not investments.empty:
        context += f" You have investments in: {', '.join(investments['symbol'].unique())}."
    
    try:
        # Updated to use GPT-3.5-turbo
        chat_response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": f"You are a smart, friendly financial assistant. Answer clearly and helpfully based on this financial context: {context}"},
                {"role": "user", "content": user_input}
            ]
        )
        response_text = chat_response.choices[0].message.content
        st.session_state.chat_history.append(("Bot", response_text))
    except Exception as e:
        response_text = f"Chat failed: {str(e)}"
        st.session_state.chat_history.append(("Bot", f"Error: {str(e)}"))

# Display chat history
for role, text in st.session_state.chat_history:
    if role == "You":
        st.write(f"**You:** {text}")
    else:
        st.write(f"**Finance Bot:** {text}")
