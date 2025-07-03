import export
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# MongoDB connection
# Update these with your MongoDB credentials
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = 'bankdb'
COLLECTION_NAME = 'transactions'

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]


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


if __name__ == '__main__':
    app.run(debug=True, port=5000)

