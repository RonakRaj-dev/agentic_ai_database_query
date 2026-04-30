from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def loadClient() -> MongoClient:
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        raise RuntimeError("MONGO_URI not set in environment variables.")

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Ping to verify connection is alive
        client.admin.command("ping")
        logger.info("MongoDB connected successfully.")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        raise RuntimeError(f"MongoDB connection failed: {e}")


def verify_collection(db, collection_name: str) -> dict:
    """
    Returns basic stats about a collection.
    Use this to confirm data exists before running agent.
    """
    collection = db[collection_name]
    count = collection.count_documents({})
    sample = collection.find_one({})
    fields = list(sample.keys()) if sample else []

    stats = {
        "collection": collection_name,
        "document_count": count,
        "fields": fields,
        "sample": {k: sample[k] for k in list(sample.keys())[:5]} if sample else {}
    }
    logger.info(f"Collection '{collection_name}': {count} documents, fields: {fields}")
    return stats


def listAllDb(client):
    print(client.list_database_names())


def testConnection(client):
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
