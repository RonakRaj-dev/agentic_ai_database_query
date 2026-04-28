from pymongo import MongoClient


def loadClient(mongo_uri: str | None):
    client = MongoClient(mongo_uri)
    return client


def listAllDb(client):
    print(client.list_database_names())


def loadDb(DbName: str, client):
    db = client[DbName]
    return db


def testConnection(client):
    try:
        client.admin.command("ping")
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
