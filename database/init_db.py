"""
Database initialization script for SolarEnergyPredictor
Refactored to use MongoDB
"""
from database.mongodb_db import mongo_db

def init_database(db_path=None):
    """
    Initialize the database (connects to MongoDB)
    """
    return mongo_db.connect()


def insert_prediction(db_path, data):
    """
    Insert a new prediction record into MongoDB
    """
    return mongo_db.insert_prediction(data)


def get_recent_predictions(db_path, limit=10):
    """
    Retrieve recent predictions from MongoDB
    """
    return mongo_db.get_recent_predictions(limit)


if __name__ == '__main__':
    # Run database initialization when script is executed directly
    init_database()