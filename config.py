# config.py - Database configuration
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig:
    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "medical")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "tapas1245ss")
    
    # Connection URL for SQLAlchemy
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # For direct psycopg2 connection
    @classmethod
    def get_connection_params(cls):
        return {
            "host": cls.POSTGRES_HOST,
            "port": cls.POSTGRES_PORT,
            "database": cls.POSTGRES_DB,
            "user": cls.POSTGRES_USER,
            "password": cls.POSTGRES_PASSWORD
        }