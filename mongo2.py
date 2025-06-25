from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# Connect to local MongoDB
client = MongoClient("mongodb://localhost:27017/")

# Access database and collection
db = client["bank"]
collection = db["transactions"]

# Generate 50 mock transaction documents
categories = ["Groceries", "Utilities", "Entertainment", "Transport", "Dining", "Health"]
descriptions = {
    "Groceries": ["Walmartt", "Trader Joe's", "Costco"],
    "Utilities": ["Electric Bill", "Water Bill", "Internet"],
    "Entertainment": ["Netflix", "Spotify", "Movie Theater"],
    "Transport": ["Uber", "Gas Station", "Bus Pass"],
    "Dining": ["McDonald's", "Starbucks", "Chipotle"],
    "Health": ["Pharmacy", "Doctor Visit", "Gym Membership"]
}

documents = []
for _ in range(50):
    category = random.choice(categories)
    description = random.choice(descriptions[category])
    amount = round(random.uniform(5.0, 150.0), 2)
    date = datetime.now() - timedelta(days=random.randint(0, 180))

    doc = {
        "date": date.isoformat(),
        "description": description,
        "category": category,
        "amount": amount
    }
    documents.append(doc)

# Insert the documents
insert_result = collection.insert_many(documents)
print(f"Inserted {len(insert_result.inserted_ids)} documents into 'bankdb.transactions'.")

# Retrieve and print one document
retrieved_doc = collection.find_one()
print("Sample document:", retrieved_doc)
