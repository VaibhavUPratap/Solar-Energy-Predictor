"""
Database initialization script for SolarEnergyPredictor
Creates the predictions table if it doesn't exist
"""
import sqlite3
import os
from datetime import datetime

def init_database(db_path='database/database.db'):
    """
    Initialize the SQLite database and create predictions table
    
    Args:
        db_path (str): Path to the database file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print(f"[OK] Created database directory: {db_dir}")
        
        # Connect to database (creates file if doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                city TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                poa_direct REAL NOT NULL,
                poa_sky_diffuse REAL NOT NULL,
                poa_ground_diffuse REAL NOT NULL,
                solar_elevation REAL NOT NULL,
                wind_speed REAL NOT NULL,
                temp_air REAL NOT NULL,
                predicted_P REAL NOT NULL
            )
        ''')
        
        conn.commit()
        print(f"[OK] Database initialized successfully at: {db_path}")
        print("[OK] Table 'predictions' created/verified")
        
        # Display existing record count
        cursor.execute('SELECT COUNT(*) FROM predictions')
        count = cursor.fetchone()[0]
        print(f"[OK] Current predictions in database: {count}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def insert_prediction(db_path, data):
    """
    Insert a new prediction record into the database
    
    Args:
        db_path (str): Path to the database file
        data (dict): Prediction data containing all required fields
    
    Returns:
        int: ID of inserted record, or None if failed
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions (
                timestamp, city, latitude, longitude,
                poa_direct, poa_sky_diffuse, poa_ground_diffuse,
                solar_elevation, wind_speed, temp_air, predicted_P
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['timestamp'],
            data['city'],
            data['latitude'],
            data['longitude'],
            data['poa_direct'],
            data['poa_sky_diffuse'],
            data['poa_ground_diffuse'],
            data['solar_elevation'],
            data['wind_speed'],
            data['temp_air'],
            data['predicted_P']
        ))
        
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return record_id
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error inserting prediction: {e}")
        return None


def get_recent_predictions(db_path, limit=10):
    """
    Retrieve recent predictions from the database
    
    Args:
        db_path (str): Path to the database file
        limit (int): Maximum number of records to retrieve
    
    Returns:
        list: List of prediction records as dictionaries
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM predictions
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        predictions = [dict(row) for row in rows]
        return predictions
        
    except sqlite3.Error as e:
        print(f"[ERROR] Error retrieving predictions: {e}")
        return []


if __name__ == '__main__':
    # Run database initialization when script is executed directly
    init_database()