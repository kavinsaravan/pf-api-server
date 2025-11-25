import json
import logging
import logging.handlers
#from calendar import error
from typing import Optional

from bson import json_util
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from pydantic import BaseModel
from pymongo import MongoClient
import datetime
from dotenv import load_dotenv
from firebase_auth import FirebaseAuthAdmin
import os


load_dotenv('../app.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
#ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
#anthropic_client = OpenAI(api_key=ANTHROPIC_API_KEY, base_url="https://api.anthropic.com/v1/")
#print(ANTHROPIC_API_KEY)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()  # Also log to console
    ]
)

# Create specific loggers
app_logger = logging.getLogger('pf_app')
openai_logger = logging.getLogger('openai_api')
error_logger = logging.getLogger('api_errors')

# Set up rotating file handler for OpenAI API logs
openai_handler = logging.handlers.RotatingFileHandler(
    'openai_api.log', maxBytes=10*1024*1024, backupCount=5
)
openai_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
openai_logger.addHandler(openai_handler)
openai_logger.setLevel(logging.DEBUG)

# Set up error tracking
error_handler = logging.handlers.RotatingFileHandler(
    'api_errors.log', maxBytes=5*1024*1024, backupCount=3
)
error_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
))
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.WARNING)


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
def get_current_user(authorization: str):
    try:
        token = authorization.replace("Bearer ", "")

        result = FirebaseAuthAdmin.verify_id_token(token)

        if result["success"]:
            return result["decoded_token"]
        else:
            return None
    except Exception as e:
        return None




app = Flask(__name__)
# Enable CORS for React frontend
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://pf-reactjs.onrender.com"], supports_credentials=True)

# MongoDB connection
# Update these with your MongoDB credentials
#MONGO_URI = os.getenv('MONGO_URI', 'mongodb://service.sandymist.com:19340/')
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = os.getenv('MONGO_PORT', '27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', '')
MONGO_DB_USERNAME = os.getenv('MONGO_DB_USERNAME', '')
MONGO_DB_PASSWORD = os.getenv('MONGO_DB_PASSWORD', '')
COLLECTION_NAME = 'newertransdb'

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
                "token": result["custom_token"],
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
                "token": result["id_token"],
                "email": result["email"],
                "display_name": result["display_name"]
            })
        else:
            raise Exception(result["error"])
    except Exception as e:
        print("error while signing in", e)
        return jsonify({'error': str(e)}), 500


@app.route("/api/profile", methods=['GET'])
def api_get_profile():
    """
    Get user profile endpoint - requires valid Firebase ID token
    """
    try:
        # Get authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header is required'}), 401

        # Verify the token and get user info
        decoded_token = get_current_user(auth_header)
        if not decoded_token:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Get additional user info from Firebase
        uid = decoded_token.get('uid')
        result = FirebaseAuthAdmin.get_user(uid)

        if result["success"]:
            user_data = result["user"]
            return jsonify({
                "uid": user_data["uid"],
                "email": user_data["email"],
                "display_name": user_data["display_name"],
                "email_verified": user_data["email_verified"],
                "disabled": user_data["disabled"]
            })
        else:
            return jsonify({'error': result["error"]}), 404

    except Exception as e:
        print("Error getting user profile:", e)
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
            if isinstance(entry.get('date'), datetime.datetime):
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
    request_id = f"cat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    try:
        data = request.get_json()
        # Support both 'description' and 'merchant' for backward compatibility
        merchant = data.get('merchant', '')

        app_logger.info(f"[{request_id}] Categorization request for merchant: '{merchant}'")

        if not merchant:
            error_logger.warning(f"[{request_id}] Missing merchant in categorization request")
            return jsonify({'error': 'Merchant or merchant field is required'}), 400

        # Define valid categories
        valid_categories = [
            'Office', 'Technology', 'Travel', 'Meals', 'Marketing',
            'Utilities', 'Education', 'Entertainment', 'Transportation',
            'Insurance', 'Professional', 'Rent', 'Security', 'Maintenance',
            'Taxes', 'Payroll', 'Other'
        ]

        # Log OpenAI API call start
        openai_logger.info(f"[{request_id}] Starting OpenAI categorization call for merchant: '{merchant}'")
        
        start_time = datetime.datetime.now()
        
        # Call OpenAI API to categorize the transaction
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a financial transaction categorizer. Given the merchant from which the transaction was made, 
                    categorize it into one of these categories: {', '.join(valid_categories)}. 
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
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        raw_category = response.choices[0].message.content.strip()
        
        # Log detailed API response
        openai_logger.info(f"[{request_id}] OpenAI response - Duration: {duration:.2f}s, Raw category: '{raw_category}', Usage: {response.usage}")

        # Validate the category and detect mistakes
        category = raw_category
        is_mistake = False
        mistake_reason = None
        
        if category not in valid_categories:
            is_mistake = True
            mistake_reason = f"Invalid category returned: '{raw_category}'"
            category = 'Other'
            
            # Log the mistake
            error_logger.error(f"[{request_id}] OpenAI API MISTAKE: {mistake_reason} for merchant '{merchant}'. Expected one of: {valid_categories}")
            
        # Additional mistake detection patterns
        if len(raw_category) > 50:
            is_mistake = True
            mistake_reason = f"Response too long ({len(raw_category)} chars): '{raw_category[:100]}...'"
            error_logger.error(f"[{request_id}] OpenAI API MISTAKE: {mistake_reason}")
            
        if any(word in raw_category.lower() for word in ['sorry', 'cannot', 'unable', 'error', 'unclear']):
            is_mistake = True
            mistake_reason = f"API indicated uncertainty or error: '{raw_category}'"
            error_logger.error(f"[{request_id}] OpenAI API MISTAKE: {mistake_reason}")

        # Log successful categorization
        if not is_mistake:
            openai_logger.info(f"[{request_id}] Successful categorization: '{merchant}' -> '{category}'")
        else:
            openai_logger.warning(f"[{request_id}] Categorization with mistake corrected: '{merchant}' -> '{category}' (was: '{raw_category}')")

        response_data = {
            'merchant': merchant,
            'suggested_category': category
        }
        
        # Include mistake info in response for debugging (can be removed in production)
        if is_mistake:
            response_data['_debug'] = {
                'mistake_detected': True,
                'original_response': raw_category,
                'mistake_reason': mistake_reason
            }

        app_logger.info(f"[{request_id}] Categorization completed successfully")
        return jsonify(response_data), 200

    except Exception as e:
        error_logger.error(f"[{request_id}] Exception in categorize_transaction: {str(e)}", exc_info=True)
        app_logger.error(f"[{request_id}] Error calling OpenAI API: {e}")
        return jsonify({'error': 'Failed to categorize transaction'}), 500


@app.route('/api/insights', methods = ['GET'])
def get_insights():
    request_id = f"main_insights_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        query = request.args.get('query', '')
        app_logger.info(f"[{request_id}] Insights request received for query: '{query}'")
        
        if not query:
            error_logger.warning(f"[{request_id}] Missing query parameter in insights request")
            return jsonify({'error': 'Query parameter is required'}), 400

        # step 1 - Extract time window
        app_logger.info(f"[{request_id}] Step 1: Extracting time window")
        time_window = get_time_window(query)
        
        if 'error' in time_window:
            error_logger.error(f"[{request_id}] Step 1 failed: {time_window['error']}")
            return jsonify({'error': f"Time window extraction failed: {time_window['error']}"}), 500
            
        start_date = time_window["start_date"]
        end_date = time_window["end_date"]
        app_logger.info(f"[{request_id}] Time window extracted: {start_date} to {end_date}")
        
        # step 2 - Query transactions
        app_logger.info(f"[{request_id}] Step 2: Querying transactions")
        transactions = query_transactions(start_date, end_date)
        app_logger.info(f"[{request_id}] Found {len(transactions)} transactions")
        
        # step 3 - Generate insights
        app_logger.info(f"[{request_id}] Step 3: Generating insights")
        insights = resolve_query(query, transactions)
        
        app_logger.info(f"[{request_id}] Insights request completed successfully")
        return jsonify({
            "insights": insights
        })

    except Exception as e:
        error_logger.error(f"[{request_id}] Exception in get_insights: {str(e)}", exc_info=True)
        app_logger.error(f"[{request_id}] Error in insights endpoint: {e}")
        return jsonify({'error': str(e)}), 500

#step 1
def get_time_window(query: str) -> dict[str, str]:
    request_id = f"time_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        today = datetime.date.today().isoformat()
        openai_logger.info(f"[{request_id}] Starting time window extraction for query: '{query}'")
        
        start_time = datetime.datetime.now()
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # lightweight & good for structured output
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for a financial transaction search API. "
                        "Given a user query, extract the specific date range they are asking about. "
                        f"Today is {today}. "
                        "If the query is vague (e.g., 'recent transactions'), return your best guess (e.g., last 30 days). "
                        "Always respond in strict JSON with keys 'start_date' and 'end_date' in YYYY-MM-DD format."
                    )
                },
                {"role": "user", "content": query}
            ],
            temperature=0,
            response_format={"type": "json_object"}  # ensures valid JSON
        )
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        raw_response = response.choices[0].message.content
        openai_logger.info(f"[{request_id}] Time window API response - Duration: {duration:.2f}s, Raw response: '{raw_response}', Usage: {response.usage}")
        
        try:
            time_window = json.loads(raw_response)
            
            # Validate the response structure
            if not isinstance(time_window, dict) or 'start_date' not in time_window or 'end_date' not in time_window:
                error_logger.error(f"[{request_id}] OpenAI API MISTAKE: Invalid JSON structure in time window response: {raw_response}")
                return {'error': 'Invalid time window format from API'}
                
            openai_logger.info(f"[{request_id}] Successful time window extraction: {time_window}")
            return time_window
            
        except json.JSONDecodeError as je:
            error_logger.error(f"[{request_id}] OpenAI API MISTAKE: Invalid JSON in time window response: {raw_response}")
            return {'error': 'Invalid JSON response from API'}
            
    except Exception as e:
        error_logger.error(f"[{request_id}] Exception in get_time_window: {str(e)}", exc_info=True)
        return {'error': str(e)}


#step 2
def query_transactions(start_date: str, end_date: str) -> list[{}]:

    # Convert to datetime objects
    start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

    # Query the collection
    query = {
        "date": {
            "$gte": start_datetime,
            "$lte": end_datetime
        }
    }

    results = collection.find(query).limit(10)

    vals = []
    for doc in results:
        vals.append(doc)

    return vals

#step 3
def resolve_query(query: str, transactions: list[{}]) -> str:
    request_id = f"insights_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        openai_logger.info(f"[{request_id}] Starting insights generation for query: '{query}' with {len(transactions)} transactions")
        
        transactions_json = json_util.dumps(transactions, ensure_ascii=False)
        start_time = datetime.datetime.now()
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # lightweight & good for structured output
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for a financial transaction search API. "
                        f"""Analyze the provided transaction data to generate insights related to the user query. 
                        Always respond with valid JSON that contains meaningful insights about the transactions."""
                    )
                },
                {"role": "user", "content": f"Query: {query}\n\nTransactions: {transactions_json}"}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        raw_response = response.choices[0].message.content
        openai_logger.info(f"[{request_id}] Insights API response - Duration: {duration:.2f}s, Usage: {response.usage}")
        
        # Validate JSON response
        try:
            json.loads(raw_response)  # Test if it's valid JSON
            openai_logger.info(f"[{request_id}] Successful insights generation")
            return raw_response
            
        except json.JSONDecodeError:
            error_logger.error(f"[{request_id}] OpenAI API MISTAKE: Invalid JSON in insights response: {raw_response[:500]}...")
            # Return a fallback JSON response
            fallback_response = json.dumps({
                "error": "API returned invalid JSON",
                "query": query,
                "transaction_count": len(transactions)
            })
            return fallback_response
            
    except Exception as e:
        error_logger.error(f"[{request_id}] Exception in resolve_query: {str(e)}", exc_info=True)
        # Return error as JSON
        return json.dumps({"error": str(e), "query": query})


@app.route('/api/logs/errors', methods=['GET'])
def get_error_logs():
    """
    Endpoint to view recent OpenAI API errors and mistakes
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        filter_type = request.args.get('type', 'all')  # all, mistakes, errors
        
        app_logger.info(f"Log request: limit={limit}, type={filter_type}")
        
        logs = []
        
        try:
            # Read the error log file
            with open('api_errors.log', 'r') as f:
                lines = f.readlines()
                
            # Process the most recent logs
            recent_lines = lines[-limit*3:] if len(lines) > limit*3 else lines
            
            for line in recent_lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Parse log entries that contain OpenAI mistakes
                if 'OpenAI API MISTAKE' in line or (filter_type == 'errors' and 'ERROR' in line):
                    logs.append({
                        'timestamp': line.split(' - ')[0] if ' - ' in line else 'Unknown',
                        'message': line,
                        'type': 'mistake' if 'MISTAKE' in line else 'error'
                    })
                elif filter_type == 'all' and ('ERROR' in line or 'WARNING' in line):
                    logs.append({
                        'timestamp': line.split(' - ')[0] if ' - ' in line else 'Unknown', 
                        'message': line,
                        'type': 'general'
                    })
                    
        except FileNotFoundError:
            return jsonify({
                'message': 'No error log file found yet',
                'logs': [],
                'count': 0
            }), 200
            
        # Sort by timestamp (most recent first) and limit
        logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        return jsonify({
            'logs': logs,
            'count': len(logs),
            'filter_type': filter_type,
            'limit': limit
        }), 200
        
    except Exception as e:
        error_logger.error(f"Error reading logs: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to read logs: {str(e)}'}), 500


@app.route('/api/logs/openai', methods=['GET'])
def get_openai_logs():
    """
    Endpoint to view recent OpenAI API call logs
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        logs = []
        
        try:
            with open('openai_api.log', 'r') as f:
                lines = f.readlines()
                
            # Get recent lines
            recent_lines = lines[-limit*2:] if len(lines) > limit*2 else lines
            
            for line in recent_lines:
                line = line.strip()
                if line:
                    logs.append({
                        'timestamp': line.split(' - ')[0] if ' - ' in line else 'Unknown',
                        'message': line
                    })
                    
        except FileNotFoundError:
            return jsonify({
                'message': 'No OpenAI log file found yet',
                'logs': [],
                'count': 0
            }), 200
            
        # Sort by timestamp (most recent first) and limit
        logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        return jsonify({
            'logs': logs,
            'count': len(logs),
            'limit': limit
        }), 200
        
    except Exception as e:
        error_logger.error(f"Error reading OpenAI logs: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to read OpenAI logs: {str(e)}'}), 500


@app.route('/api/uploadcsv', methods=['POST'])
def upload_transactions():
    """
    Bulk upload transactions from CSV data
    Expects a JSON array of transaction objects in the request body
    """
    try:
        data = request.get_json()
        
        # Validate that we received a list
        if not isinstance(data, list):
            return jsonify({'error': 'Expected an array of transactions'}), 400
        
        if not data:
            return jsonify({'error': 'No transactions provided'}), 400
        
        # Validate each transaction
        required_fields = ['date', 'merchant', 'amount']
        processed_transactions = []
        validation_errors = []
        
        for i, transaction in enumerate(data):
            # Check required fields
            missing_fields = [field for field in required_fields if field not in transaction or transaction[field] is None]
            if missing_fields:
                validation_errors.append(f"Transaction {i+1}: Missing required fields: {', '.join(missing_fields)}")
                continue
            
            # Process the transaction
            processed_transaction = {
                'date': transaction['date'],
                'merchant': transaction['merchant'],
                'amount': float(transaction['amount']),
                'category': transaction.get('category', 'Uncategorized'),
                'created_at': datetime.datetime.utcnow(),
                'source': 'csv_upload'
            }
            
            # Convert date string to datetime object if it's a string
            if isinstance(processed_transaction['date'], str):
                try:
                    # Try different date formats
                    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
                    parsed_date = None
                    for date_format in date_formats:
                        try:
                            parsed_date = datetime.datetime.strptime(processed_transaction['date'], date_format)
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date is None:
                        validation_errors.append(f"Transaction {i+1}: Invalid date format: {processed_transaction['date']}")
                        continue
                    
                    processed_transaction['date'] = parsed_date
                except Exception as e:
                    validation_errors.append(f"Transaction {i+1}: Date parsing error: {str(e)}")
                    continue
            
            processed_transactions.append(processed_transaction)
        
        # Return validation errors if any
        if validation_errors:
            return jsonify({
                'error': 'Validation failed',
                'validation_errors': validation_errors,
                'processed_count': len(processed_transactions),
                'total_count': len(data)
            }), 400
        
        # Insert all valid transactions into MongoDB
        if processed_transactions:
            result = collection.insert_many(processed_transactions)
            inserted_count = len(result.inserted_ids)
            
            # Retrieve the inserted transactions to return them
            inserted_transactions = list(collection.find({'_id': {'$in': result.inserted_ids}}))
            
            # Convert ObjectId to string and format dates for JSON serialization
            for transaction in inserted_transactions:
                transaction['_id'] = str(transaction['_id'])
                if isinstance(transaction.get('date'), datetime.datetime):
                    transaction['date'] = transaction['date'].isoformat()
                if isinstance(transaction.get('created_at'), datetime.datetime):
                    transaction['created_at'] = transaction['created_at'].isoformat()
            
            return jsonify({
                'message': f'Successfully uploaded {inserted_count} transactions',
                'inserted_count': inserted_count,
                'inserted_ids': [str(id) for id in result.inserted_ids],
                'transactions': inserted_transactions
            }), 201
        else:
            return jsonify({'error': 'No valid transactions to insert'}), 400
    
    except Exception as e:
        print(f"Error in upload_transactions: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


port = int(os.environ.get("PF_SERVER_PORT", 5000))

if __name__ == '__main__':
    print("starting the server")
    app.run(host='0.0.0.0', debug=True, port=port)

