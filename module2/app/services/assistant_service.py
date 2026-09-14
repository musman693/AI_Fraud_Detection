import openai
import json
from app.config import settings

openai.api_key = settings.OPENAI_API_KEY

async def query_investigation_assistant(tx_id: str, cust_id: str, question: str) -> str:
    prompt = f"""
    You are an AI Fraud Investigation Assistant.
    Transaction ID: {tx_id}
    Customer ID: {cust_id}

    Analyst Question: {question}

    Provide a concise, analytical response explaining risk factors, potential fraud network linkages, or investigation steps.
    """

    if not settings.OPENAI_API_KEY:
        return f"[Mock Assistant Response]: Customer {cust_id} showed elevated risk on transaction {tx_id} due to velocity spike and amount anomaly."

    res = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content