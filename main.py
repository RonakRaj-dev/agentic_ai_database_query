import src.database as db
import src.tools.mongo_tools as tools
import src.utils.schema_loader as schema_loader

client = db.loadClient()

data_db = client["sample_analytics"]

schema = schema_loader.build_full_schema(data_db)

print(schema)

query_1 = {"limit": {"$gt": 9000}}
query_2 = {"products": "InvestmentStock"}
query_3 = {"products": {"$all": ["InvestmentStock", "Commodity"]}}

results = tools.queryDb(data_db=data_db, collection_name="accounts", query=query_3)

for r in results:
    print(r)
