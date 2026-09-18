import os
import json
import gradio as gr
import google.generativeai as genai

# =====================================================================
# 1. MOCK ENTERPRISE DATABASES & APIs
# =====================================================================

# Simulated SQL Database for User Profiles
USER_DB = {
    "U102": {
        "monthly_budget": 8000.0,
        "expenses": {"food": 12000.0, "fuel": 0.0, "utilities": 2500.0},
        "savings_goals": {"trip_to_goa": 20000.0},
        "liquid_cash": 18000.0
    }
}

# =====================================================================
# 2. DEFINE AGENT TOOLS (Function Calling)
# =====================================================================

def get_financial_profile(user_id: str = "U102") -> str:
    """Retrieves the user's current budget, liquid cash, and expenses from the database."""
    return json.dumps(USER_DB.get(user_id, {"error": "User not found"}))

def log_expense(category: str, amount: float, user_id: str = "U102") -> str:
    """Logs a new expense, deducts from liquid cash, and checks for budget overruns."""
    if user_id not in USER_DB: 
        return "User not found"
    
    cat = category.lower()
    USER_DB[user_id]["expenses"][cat] = USER_DB[user_id]["expenses"].get(cat, 0.0) + amount
    USER_DB[user_id]["liquid_cash"] -= amount
    
    total_spent = sum(USER_DB[user_id]["expenses"].values())
    budget = USER_DB[user_id]["monthly_budget"]
    
    if total_spent > budget:
        alert = f"CRITICAL: Budget overrun! Total spent (₹{total_spent}) exceeds budget (₹{budget})."
    else:
        alert = f"Status normal. Total spent (₹{total_spent}) is within budget (₹{budget})."
        
    return json.dumps({"status": "Expense logged", "new_balance": USER_DB[user_id]["liquid_cash"], "alert": alert})

def fetch_market_data(asset_name: str) -> str:
    """Simulates a live web search API to fetch current market prices and risk levels."""
    asset = asset_name.lower()
    if "apple" in asset:
        return json.dumps({"asset": "Apple (AAPL)", "price_usd": 175.0, "volatility": "Medium", "analyst_rating": "Buy"})
    elif "techcorp" in asset or "ipo" in asset:
        return json.dumps({"asset": "TechCorp IPO", "status": "Launching Today", "oversubscribed": "7x", "risk_level": "High"})
    elif "flight" in asset or "goa" in asset:
        return json.dumps({"asset": "Flight to Goa", "average_price_inr": 4500, "availability": "Limited"})
    else:
        return json.dumps({"error": "Market data unavailable for this asset."})

def calculate_confidence_score(liquid_cash: float, allocated_amount: float, asset_risk: str) -> str:
    """Calculates a financial recommendation confidence score (0-100) based on liquidity and risk."""
    score = 100
    liquidity_ratio = liquid_cash / allocated_amount if allocated_amount > 0 else 10
    
    if liquidity_ratio < 2.0:
        score -= 40  # Heavy penalty if asset consumes more than 50% of liquid cash
    if asset_risk.lower() == "high":
        score -= 25
    elif asset_risk.lower() == "medium":
        score -= 10
        
    verdict = "RECOMMENDED" if score >= 65 else "NOT RECOMMENDED"
    return json.dumps({"confidence_score": f"{score}%", "verdict": verdict})

# List of tools to provide to the LLM
financial_tools = [get_financial_profile, log_expense, fetch_market_data, calculate_confidence_score]


# =====================================================================
# 3. LLM ORCHESTRATOR
# =====================================================================

# REPLACE WITH YOUR ACTUAL API KEY OR SET IT IN YOUR TERMINAL ENVIRONMENT VARIABLES
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=API_KEY)

# Initialize the model with the defined tools and a strict system prompt
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=financial_tools,
    system_instruction=(
        "You are an Intelligent Financial Decision Agent. "
        "When a user asks a financial question, you must autonomously use the provided tools to gather data before answering. "
        "1. If logging an expense, use log_expense. "
        "2. If asked about adjusting spending, use get_financial_profile. "
        "3. If asked 'Should I buy/invest/book?', use get_financial_profile to check their cash, then use fetch_market_data, "
        "and finally use calculate_confidence_score. "
        "Always present the final answer clearly with the Confidence Score and Verdict if applicable."
    )
)

# Start a chat session that maintains tool history
chat = model.start_chat(enable_automatic_function_calling=True)


# =====================================================================
# 4. UI WITH GRADIO
# =====================================================================

def respond(message, history):
    if not API_KEY or API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "⚠️ Error: Please insert your Gemini API Key in the code first."
    
    try:
        # The LLM will autonomously decide if it needs to call tools based on the message
        response = chat.send_message(message)
        
        # Format the backend state to show judges what the DB looks like now
        db_state = json.dumps(USER_DB["U102"], indent=2)
        final_output = f"{response.text}\n\n---\n**Backend Database State:**\n```json\n{db_state}\n```"
        return final_output
    
    except Exception as e:
        return f"System Error: {str(e)}"

# Build the frontend
demo = gr.ChatInterface(
    fn=respond,
    title="Intelligent Financial Decision Agent (Agentic Workflow)",
    description="This agent uses actual Tool Calling/Function Calling. It will autonomously query mock databases and APIs before replying.",
    
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=10000)
