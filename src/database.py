from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")


def loadClient():
    client = MongoClient(mongo_uri)
    return client


def listAllDb(client):
    print(client.list_database_names())


def testConnection(client):
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
