import os
import tempfile
import pdfplumber
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORG_ID")
)


# Initialize Flask app
app = Flask(__name__)
CORS(app)

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/api/parse-bank-statement", methods=["POST"])
def parse_bank_statement():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # Save PDF to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)

            text = ""
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"

        if not text.strip():
            return jsonify({"error": "Unable to extract text from PDF. It may be image-only or scanned without OCR."}), 422

        # Send to GPT
        messages = [
            {
                "role": "system",
                "content": (
                    "You're a financial analyst AI. Analyze a bank statement PDF and return this as JSON:\n"
                    "- Estimated monthly revenue\n"
                    "- Total number of NSF (non-sufficient funds) occurrences\n"
                    "- Total cash deposits\n"
                    "- Days with balance under $2,000\n"
                    "- Total inter-account transfers\n"
                    "- A list of transactions with date, description, amount, and category"
                )
            },
            {
                "role": "user",
                "content": text[:12000]  # Truncate to safe GPT input size
            }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.2
        )

        result = response.choices[0].message.content
        return jsonify({"result": result}), 200

    except Exception as e:
        traceback.print_exc()  # Print error to Render logs
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
