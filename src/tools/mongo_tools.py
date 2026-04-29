from typing import Dict, Optional
from typing import Any


def queryDb(
    data_db,
    collection_name: str,
    query: Dict[str, Any],
    projection: Optional[Dict[str, int]] = None,
    limit: int = 10,
):
    try:
        collection = data_db[collection_name]
        return list(collection.find(query, projection).limit(limit))
    except Exception as e:
        print("Query error: ", e)
        return []
