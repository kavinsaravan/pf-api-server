import xml.etree.ElementTree as ET
from pymongo import MongoClient

# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")  # Replace with your URI if needed
db = client["xml"]
collection = db["xmlfiles"]

# Path to your XML file (adjust as needed for your PyCharm project)
xml_file_path = "workspace.xml"

# Parse the XML file
tree = ET.parse(xml_file_path)
print("hello", tree)
root = tree.getroot()
print("hello", root)

# Loop through each <record> and convert to dictionary
documents = []
for option in root.findall("component"):
    doc = {child.tag: child.text for child in option}
    documents.append(doc)

# Insert documents into MongoDB
if documents:
    collection.insert_many(documents)
    print(f"Inserted {len(documents)} documents into the MongoDB.")
else:
    print("No records found in XML.")
