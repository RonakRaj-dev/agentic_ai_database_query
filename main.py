import src.database as db

client = db.loadClient()
db.testConnection(client)

db.listAllDb(client)

data_db = client["sample_analytics"]

data_db.list_collection_names()
data = data_db["customers"]

for doc in data.find().limit(5):
    print(doc)
