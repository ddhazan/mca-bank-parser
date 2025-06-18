import os
import tempfile
import openai
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)

@app.route("/api/parse-bank-statement", methods=["POST"])
def parse_bank_statement():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No PDF file uploaded"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file.save(tmp.name)
        text = ""
        with pdfplumber.open(tmp.name) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    messages = [
        {
            "role": "system",
            "content": "You are a financial underwriting assistant. Read raw bank statement text and return a JSON summary + categorized transactions."
        },
        {
            "role": "user",
            "content": f"""Analyze the following bank statement and return:

1. Monthly revenue (estimate)
2. Average daily balance (if possible)
3. Total number of NSF or returned items
4. Total days under $2,000 balance
5. Total cash deposits
6. Total inter-account transfers
7. Categorized transactions in this format:
[
  {{ "date": "...", "description": "...", "amount": ..., "category": "Income/Transfer/NSF/Other" }},
  ...
]

Bank Statement:
{text[:12000]}
"""
        }
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )
        parsed = response.choices[0].message["content"]
        return jsonify({"result": parsed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
