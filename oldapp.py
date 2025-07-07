'''from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import certifi
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend
username = "kavins" ### Add your username here
password = "Mn3166VE6rbdzFeZ" ### Add your password here

#uri = f"mongodb+srv://{username}:{password}@cluster0.wm4ac.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
uri = f"mongodb+srv://{username}:{password}@cluster0.tiut2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


# MongoDB connection
# Update these with your MongoDB credentials
#MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_URI = uri
#MONGO_URI = 'mongodb+srv://kavinsaravan:HYrHX6u9mjPrnZGWqBbT@cluster0.tiut2.mongodb.net/'
print("MONGO_URI: ", MONGO_URI)
DB_NAME = 'bank'
COLLECTION_NAME = 'transactions'

# Initialize MongoDB client
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())

db = client[DB_NAME]
collection = db[COLLECTION_NAME]

@app.route('/', methods=['GET'])
def get_home():
    return jsonify({'helloo': 'kavin'}), 200


@app.route('/api/entries', methods=['GET'])
def get_entries():
    try:
        # Fetch all entries from MongoDB
        print("fetching")
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


if __name__ == '__main__':
   #app.run(debug=True, port=5000)
   port = int(os.environ.get("PORT", 5009))
   app.run(host='0.0.0.0', port=port)'''


