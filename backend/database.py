import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    return connection


if __name__ == "__main__":
    try:
        conn = get_connection()

        if conn.is_connected():
            print("✅ FastAPI backend connected to MySQL successfully!")

        conn.close()

    except Exception as e:
        print("❌ Database connection failed:")
        print(e)