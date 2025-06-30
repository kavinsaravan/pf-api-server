import csv
from pymongo import MongoClient

# MongoDB connection details
MONGO_URI = "mongodb://localhost:27017/"  # Update if using MongoDB Atlas
DATABASE_NAME = "csv"
COLLECTION_NAME = "csvinfo"

# CSV file path
CSV_FILE_PATH = "sample_sales_data.csv"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Read and insert CSV data
with open(CSV_FILE_PATH, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    data = list(reader)  # Convert to list of dictionaries
    for doc in data:
        # Convert numeric fields to appropriate types
        doc['TransactionID'] = int(doc['TransactionID'])
        doc['Quantity'] = int(doc['Quantity'])
        doc['Price'] = float(doc['Price'])
        doc['Total'] = float(doc['Total'])

    # Insert data into MongoDB
    collection.insert_many(data)

print(f"Inserted {len(data)} records into {DATABASE_NAME}.{COLLECTION_NAME}")
