from pymongo import MongoClient

# Connect to local MongoDB
client = MongoClient("mongodb://localhost:27017/")

# Access (or create) database and collection
db = client["mydatabase"]
collection = db["mycollection"]

# Insert a document
doc = {"name": "Alicee", "age": 30, "city": "New York"}
insert_result = collection.insert_one(doc)
print(f"Inserted document with _id: {insert_result.inserted_id}")

# Find one document
retrieved_doc = collection.find_one({"name": "Alice"})
print("Retrieved document:", retrieved_doc)

# date of transaction, item description, item category, transaction amount
# database name: bankdb, collection: transactions