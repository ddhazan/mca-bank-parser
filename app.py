@app.route("/api/parse-bank-statement", methods=["POST"])
def parse_bank_statement():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)

            # Extract text from PDF
            text = ""
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"

        if not text.strip():
            return jsonify({"error": "Unable to extract text from PDF. It may be image-only or scanned without OCR."}), 422

        # Send to OpenAI
        prompt = [
            {
                "role": "system",
                "content": (
                    "You're a financial underwriting assistant. Read the bank statement and return JSON:\n"
                    "- Monthly revenue\n- NSF count\n- Transfers\n- Cash deposits\n- Days under $2K\n"
                    "- Transactions as objects with date, description, amount, category"
                )
            },
            {
                "role": "user",
                "content": text[:12000]
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
        # Log error and respond
        return jsonify({"error": f"Internal error: {str(e)}"}), 500
