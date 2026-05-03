"""
database.py
-----------
Unified database client — supports both MongoDB and Supabase (PostgreSQL).
MongoDB  → NoSQL document store (primary DB for this project)
Supabase → PostgreSQL-based relational DB (optional SQL data source)

Usage:
    from src.database import loadMongoClient, loadSupabaseClient
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

# ── Environment variables ─────────────────────────────────────────────────────
mongo_uri  = os.getenv("MONGO_URI")
supa_url   = os.getenv("SUPABASE_URL")
supa_key   = os.getenv("SUPABASE_SECRET_KEY")


# ══════════════════════════════════════════════════════════════════════════════
# MONGODB
# ══════════════════════════════════════════════════════════════════════════════

def loadMongoClient() -> MongoClient:
    """
    Create and verify a MongoDB client connection.
    Pings the cluster to confirm the connection is alive.
    Raises RuntimeError if connection fails or URI is missing.
    """
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        raise RuntimeError("MONGO_URI not set in environment variables.")

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        logger.info("MongoDB connected successfully.")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")


# Keep old name as alias so existing code doesn't break
loadClient = loadMongoClient


def testMongoConnection(client: MongoClient):
    """Ping MongoDB and print connection status."""
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(f"MongoDB ping failed: {e}")


def listAllDb(client: MongoClient):
    """Print all database names on the MongoDB cluster."""
    print(client.list_database_names())


def verify_collection(db, collection_name: str) -> dict:
    """
    Returns basic stats about a MongoDB collection.
    Use this to confirm data exists before running the agent.

    Returns:
        dict with collection name, document count, field names, and sample record
    """
    collection = db[collection_name]
    count  = collection.count_documents({})
    sample = collection.find_one({})
    fields = list(sample.keys()) if sample else []

    stats = {
        "collection":     collection_name,
        "document_count": count,
        "fields":         fields,
        "sample":         {k: sample[k] for k in list(sample.keys())[:5]} if sample else {},
    }
    logger.info(f"Collection '{collection_name}': {count} documents, fields: {fields}")
    return stats


# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE (PostgreSQL)
# ══════════════════════════════════════════════════════════════════════════════

def loadSupabaseClient():
    """
    Create and return a Supabase client.
    Requires SUPABASE_URL and SUPABASE_SECRET_KEY in .env

    Returns:
        supabase.Client instance

    Raises:
        RuntimeError if credentials are missing or connection fails
    """
    if not supa_url or not supa_key:
        raise RuntimeError(
            "Missing Supabase credentials. "
            "Set SUPABASE_URL and SUPABASE_SECRET_KEY in your .env file."
        )
    try:
        from supabase import create_client, Client
        client: Client = create_client(supabase_url=supa_url, supabase_key=supa_key)
        logger.info("Supabase client created successfully.")
        return client
    except Exception as e:
        raise RuntimeError(f"Supabase connection failed: {e}")


def testSupabaseConnection(supabase_client, table_name: str = "Employee"):
    """
    Test Supabase connection by fetching one row from a table.

    Args:
        supabase_client: Supabase Client instance
        table_name: Table to test against (default: 'Employee')
    """
    try:
        response = supabase_client.table(table_name).select("*").limit(1).execute()
        if response.data is not None:
            logger.info(f"Supabase connected. Table '{table_name}' accessible.")
            print(f"Connected to Supabase successfully. Sample row: {response.data}")
        else:
            print("Supabase connected but no data returned.")
    except Exception as e:
        print(f"Supabase connection test failed: {e}")