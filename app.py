import openai
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)


app = Flask(__name__)
 # Enable CORS for React frontend
#CORS(app, origins=["http://localhost:3000"], supports_credentials=True)
CORS(app)

# MongoDB connection
# Update these with your MongoDB credentials
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = 'bankdb'
COLLECTION_NAME = 'transactions'

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]


@app.route('/', methods=['GET'])
def home():
    return {'message': 'hello'}
@app.route('/api/entries', methods=['GET'])
def get_entries():
    try:
        # Fetch all entries from MongoDBB
        entries = list(collection.find())

        # Convert ObjectId to string for JSON serialization
        for entry in entries:
            entry['_id'] = str(entry['_id'])
            # Ensure date is properly formatted
            if isinstance(entry.get('date'), datetime):
                entry['date'] = entry['date'].isoformat()

        return jsonify(entries), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries', methods=['POST'])
def create_entry():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['date', 'description', 'category', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Convert date string to datetime object
        data['date'] = datetime.fromisoformat(data['date'])

        # Insert into MongoDB
        result = collection.insert_one(data)

        # Return the created entry
        data['_id'] = str(result.inserted_id)
        data['date'] = data['date'].isoformat()

        return jsonify(data), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check_transaction', methods=['POST'])
def check_transaction():
    print("hey checking the transaction")
    try:
        request_data = request.get_json()
        print(request_data)

        # Validate required fields
        required_fields = ['description', 'category', 'amount']
        for field in required_fields:
            if field not in request_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        response_data = {'status': "ok", 'category': request_data['category'].upper()}

        return jsonify(response_data), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/categorize', methods=['POST'])
def categorize_transaction():
    try:
        data = request.get_json()
        description = data.get('description', '')

        if not description:
            return jsonify({'error': 'Description is required'}), 400

        # Call OpenAI API to categorize the transaction
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a financial transaction categorizer. Given a transaction description, 
                    categorize it into one of these categories based on the description name or which company the transaction was made at: Office, Technology, Travel, Meals, Marketing, 
                    Utilities, Education, Entertainment, Transportation, Insurance, Professional, Rent, 
                    Security, Maintenance, Taxes, Payroll, or Other. 
                    Respond with ONLY the category name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Categorize this transaction: {description}"
                }
            ],
            temperature=0.3,
            max_tokens=50
        )

        category = response.choices[0].message.content.strip()

        # Validate the category
        valid_categories = [
            'Office', 'Technology', 'Travel', 'Meals', 'Marketing',
            'Utilities', 'Education', 'Entertainment', 'Transportation',
            'Insurance', 'Professional', 'Rent', 'Security', 'Maintenance',
            'Taxes', 'Payroll', 'Other'
        ]

        if category not in valid_categories:
            category = 'Other'

        return jsonify({
            'description': description,
            'suggested_category': category
        }), 200

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return jsonify({'error': 'Failed to categorize transaction'}), 500


port = int(os.environ.get("PF_SERVER_PORT", 5000))

if __name__ == '__main__':
    app.run(debug=True, port=port)

