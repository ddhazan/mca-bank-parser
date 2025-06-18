import os
import tempfile
import pdfplumber
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file (including OPENAI_API_KEY)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow CORS from any origin

# Health check endpoint
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# PDF parsing endpoint
@app.route("/api/parse-bank-statement", methods=["POST"])
def parse_bank_statement():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            text = ""
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"

        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a financial underwriting assistant. Analyze the text of a bank statement "
                    "and return the following in JSON format:\n\n"
                    "- Estimated monthly revenue\n"
                    "- Number of NSF/returned payments\n"
                    "- Total cash deposits\n"
                    "- Number of days under $2,000\n"
                    "- Total amount of inter-account transfers\n"
                    "- Categorized transactions in array form (with date, amount, description, and category)\n\n"
                    "Return ONLY JSON as the output."
                )
            },
            {
                "role": "user",
                "content": text[:12000]  # Limit input to first 12,000 characters
            }
        ]

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=prompt,
            temperature=0.2
        )

        result = response.choices[0].message["content"]
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Required for Render deployment (bind to 0.0.0.0 and PORT)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
