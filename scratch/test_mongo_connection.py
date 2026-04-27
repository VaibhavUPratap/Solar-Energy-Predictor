
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env file
load_dotenv()

uri = os.getenv('MONGODB_URI')
db_name = os.getenv('MONGODB_DB', 'solar_energy_db')

print(f"Testing connection to: {uri}")

try:
    client = MongoClient(uri)
    # The ping command is cheap and does not require auth.
    client.admin.command('ping')
    print("[OK] Pinged your deployment. You successfully connected to MongoDB!")
    
    db = client[db_name]
    collection = db['predictions']
    count = collection.count_documents({})
    print(f"[OK] Successfully accessed database '{db_name}'. Current document count in 'predictions': {count}")
    
except Exception as e:
    print(f"[ERROR] Could not connect to MongoDB: {e}")
