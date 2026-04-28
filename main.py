import os
from dotenv import load_dotenv
import src.database as db


load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

client = db.loadClient(mongo_uri=mongo_uri)

db.testConnection(client)
