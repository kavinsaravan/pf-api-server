from http.client import HTTPException
from typing import Optional
#from fastapi import HTTPException
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from firebase_auth import FirebaseAuthAdmin
import os


load_dotenv('../app.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)


# Pydantic models for request validation
class SignUpRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

class SignInRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Dependency to verify Firebase ID token
async def get_current_user(authorization: str):
    try:
        token = authorization.replace("Bearer ", "")

        result = FirebaseAuthAdmin.verify_id_token(token)

        if result["success"]:
            return result["decoded_token"]
        else:
            raise HTTPException(status_code=401, detail=result["error"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))




app = Flask(__name__)
 # Enable CORS for React frontend
CORS(app, origins=["http://localhost:3000", "https://pf-reactjs.onrender.com"], supports_credentials=True)
#CORS(app)

# MongoDB connection
# Update these with your MongoDB credentials
#MONGO_URI = os.getenv('MONGO_URI', 'mongodb://service.sandymist.com:19340/')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = os.getenv('MONGO_PORT', '27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', '')
MONGO_DB_USERNAME = os.getenv('MONGO_DB_USERNAME', '')
MONGO_DB_PASSWORD = os.getenv('MONGO_DB_PASSWORD', '')
COLLECTION_NAME = 'transactions'

# Initialize MongoDB client
#client = MongoClient(MONGO_URI)
client = MongoClient(
    host=MONGO_HOST,
    port=int(MONGO_PORT),
    username=MONGO_DB_USERNAME,
    password=MONGO_DB_PASSWORD,
    authSource=MONGO_DB_NAME,  # Usually 'admin' or your database name
    authMechanism="SCRAM-SHA-1"  # Default auth mechanism
)
db = client[MONGO_DB_NAME]
collection = db[COLLECTION_NAME]



@app.route('/', methods=['GET'])
def home():
    return {'message': 'hello'}

@app.route("/api/signup", methods=['POST'])
def api_signup():
    """
    Sign up endpoint using pure Firebase Admin SDK
    Returns custom token for client-side sign-in
    """
    print(f"received sign up request")
    try:
        json_data = request.get_json()

        if not json_data or 'email' not in json_data or 'password' not in json_data:
            return jsonify({'error': 'Email and password are required'}), 400

        email = json_data['email']
        password = json_data['password']
        display_name = json_data.get('display_name')
        print(f"received sign up request for email {email}")
        result = FirebaseAuthAdmin.sign_up(
            email=email,
            password=password,
            display_name=display_name
        )

        if result["success"]:
            # Don't return verification_link in production - send it via email instead
            return jsonify({
                "uid": result["uid"],
                "email": result["email"],
                "custom_token": result["custom_token"],
                "display_name": result["display_name"],
                "message": "User created. Use custom_token with signInWithCustomToken() on client."
            })
        else:
            raise Exception(result["error"])
    except Exception as e:
        print("error while signing up", e)
        return jsonify({'error': str(e)}), 500


@app.route("/api/signin", methods=['POST'])
def api_signin():
    """
    Sign in endpoint - still uses REST API for password verification
    """
    print(f"received sign in request")
    try:
        json_data = request.get_json()

        if not json_data or 'email' not in json_data or 'password' not in json_data:
            return jsonify({'error': 'Email and password are required'}), 400

        email = json_data['email']
        password = json_data['password']
        print(f"received sign in request for email {email}")

        result = FirebaseAuthAdmin.sign_in(email, password)
        print(f"this is the result {result}")

        if result["success"]:
            return jsonify({
                "status": "ok",
                "uid": result["uid"],
                "id_token": result["id_token"],
                "email": result["email"],
                "display_name": result["display_name"]
            })
        else:
            raise Exception(result["error"])
    except Exception as e:
        print("error while signing in", e)
        return jsonify({'error': str(e)}), 500


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
        required_fields = ['date', 'merchant', 'category', 'amount']
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
        required_fields = ['merchant', 'category', 'amount']
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
        merchant = data.get('merchant', '')

        if not merchant:
            return jsonify({'error': 'Merchant is required'}), 400

        # Call OpenAI API to categorize the transaction
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a financial transaction categorizer. Given the merchant from which the transaction was made, 
                    categorize it into one of these categories: Office, Technology, Travel, Meals, Marketing, 
                    Utilities, Education, Entertainment, Transportation, Insurance, Professional, Rent, 
                    Security, Maintenance, Taxes, Payroll, or Other. 
                    Respond with ONLY the category name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Categorize this transaction: {merchant}"
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
            'merchant': merchant,
            'suggested_category': category
        }), 200

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return jsonify({'error': 'Failed to categorize transaction'}), 500


port = int(os.environ.get("PF_SERVER_PORT", 5000))

if __name__ == '__main__':
    print("starting the server")
    app.run(host='0.0.0.0', debug=True, port=port)

