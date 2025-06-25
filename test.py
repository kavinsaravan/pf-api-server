from pymongo import MongoClient
import certifi


username = "kavins" ### Add your username here
password = "Mn3166VE6rbdzFeZ" ### Add your password here

#uri = f"mongodb+srv://{username}:{password}@cluster0.wm4ac.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
uri = f"mongodb+srv://{username}:{password}@cluster0.tiut2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB (local instance; change URI if using MongoDB Atlas or remote)
#client = MongoClient("mongodb://localhost:27017/")
client = MongoClient(uri, tlsCAFile=certifi.where())

# Access a database (it will be created if it doesn't exist)
db = client["yourdatabase"]

# Access a collection (table equivalent)
collection = db["users"]

# Insert a sample document (optional for demo)
collection.insert_one({"name": "Bob", "age": 40})

# Perform a simple query
result = collection.find_one({"name": "Bob"})

# Print the result
print(result)

