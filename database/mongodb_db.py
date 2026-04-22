"""
MongoDB Database Module for SolarEnergyPredictor
Handles connection and operations for MongoDB storage
"""
from pymongo import MongoClient
from datetime import datetime
import os
from config import Config

class MongoDB:
    def __init__(self, uri=None, db_name=None):
        self.uri = uri or Config.MONGODB_URI
        self.db_name = db_name or Config.MONGODB_DB
        self.client = None
        self.db = None
        self.collection = None

    def connect(self):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            self.collection = self.db['predictions']
            # Test connection
            self.client.admin.command('ping')
            print(f"[OK] Connected to MongoDB at: {self.uri}")
            print(f"[OK] Using database: {self.db_name}")
            return True
        except Exception as e:
            print(f"[ERROR] MongoDB connection failed: {e}")
            return False

    def insert_prediction(self, data):
        """Insert a new prediction record"""
        try:
            if self.collection is None:
                self.connect()
            
            result = self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"[ERROR] MongoDB insert failed: {e}")
            return None

    def get_recent_predictions(self, limit=10):
        """Retrieve recent predictions"""
        try:
            if self.collection is None:
                self.connect()
            
            cursor = self.collection.find().sort('_id', -1).limit(limit)
            predictions = []
            for doc in cursor:
                # Convert ObjectId to string for JSON compatibility
                doc['id'] = str(doc.pop('_id'))
                predictions.append(doc)
            return predictions
        except Exception as e:
            print(f"[ERROR] MongoDB retrieval failed: {e}")
            return []

# Global instance
mongo_db = MongoDB()
