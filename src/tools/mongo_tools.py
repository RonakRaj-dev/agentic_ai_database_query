"""
mongo_tools.py
--------------
Generic MongoDB tools — works with ANY collection, ANY fields.
"""

import json
from pymongo.database import Database
from agentscope.tool import ToolResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

_db: Database = None


def init_tools(db: Database):
    global _db
    _db = db
    logger.info(f"mongo_tools initialised with DB: {db.name}")


def _make_response(data) -> ToolResponse:
    text = json.dumps(data, indent=2, default=str) if not isinstance(data, str) else data
    return ToolResponse(content=[{"type": "text", "text": text}])


def query_collection(
    collection_name: str,
    field_name: str = "",
    field_value: str = "",
    numeric_field: str = "",
    min_value: float = None,
    max_value: float = None,
    array_field: str = "",
    array_contains: str = "",
    limit: int = 10,
) -> ToolResponse:
    """
    Query any MongoDB collection with flexible filters.

    Args:
        collection_name: Name of the collection to query
        field_name: Field to filter by exact or regex match e.g. active, username
        field_value: Value to match e.g. true, false, New York
        numeric_field: Numeric field for range filter e.g. limit, transaction_count
        min_value: Minimum value for numeric_field (inclusive)
        max_value: Maximum value for numeric_field (inclusive)
        array_field: Array field to search within e.g. products
        array_contains: Value that array_field must contain e.g. InvestmentStock
        limit: Max records to return (default 10, max 20)
    """
    if _db is None:
        return _make_response("Database not initialised.")

    try:
        query = {}

        # Boolean or string field match
        if field_name and field_value:
            if field_value.lower() == "true":
                query[field_name] = True
            elif field_value.lower() == "false":
                query[field_name] = False
            else:
                # Use regex for string fields to allow partial matches
                query[field_name] = {"$regex": field_value, "$options": "i"}

        # Numeric range
        if numeric_field:
            range_query = {}
            if min_value is not None:
                range_query["$gte"] = min_value
            if max_value is not None:
                range_query["$lte"] = max_value
            if range_query:
                query[numeric_field] = range_query

        # Array contains
        if array_field and array_contains:
            query[array_field] = array_contains

        # Hard cap limit
        safe_limit = min(int(limit), 20)

        collection = _db[collection_name]
        total = collection.count_documents(query)
        results = list(collection.find(query, {"_id": 0}).limit(safe_limit))

        if not results:
            return _make_response(f"No records found. Filter applied: {query}")

        # Return actual documents + summary
        return _make_response({
            "total_matching": total,
            "showing": len(results),
            "results": results
        })

    except Exception as e:
        logger.error(f"query_collection error: {e}")
        return _make_response(f"Query error: {str(e)}")


def aggregate_collection(
    collection_name: str,
    group_by: str,
    agg_field: str = "",
    agg_operator: str = "count",
    unwind_array: bool = False,
) -> ToolResponse:
    if _db is None:
        return _make_response("Database not initialised.")

    try:
        group_stage: dict = {"_id": f"${group_by}", "count": {"$sum": 1}}

        if agg_field and agg_operator in {"avg", "sum", "min", "max"}:
            group_stage[f"{agg_operator}_{agg_field}"] = {
                f"${agg_operator}": f"${agg_field}"
            }

        pipeline = []

        # Unwind array fields BEFORE grouping
        if unwind_array:
            pipeline.append({"$unwind": f"${group_by}"})

        pipeline += [
            {"$group": group_stage},
            {"$sort": {"count": -1}},
            {"$limit": 10}  # ← hard cap to control token usage
        ]

        collection = _db[collection_name]
        results = list(collection.aggregate(pipeline))
        for r in results:
            r[group_by] = r.pop("_id")

        return _make_response(results)

    except Exception as e:
        logger.error(f"aggregate_collection error: {e}")
        return _make_response(f"Aggregation error: {str(e)}")


def get_schema(collection_name: str) -> ToolResponse:
    """
    Get fields, document count, and a sample record from any collection.
    Always call this first when unsure about available fields or values.

    Args:
        collection_name: Collection to inspect e.g. accounts, customers, transactions
    """
    if _db is None:
        return _make_response("Database not initialised.")

    try:
        collection = _db[collection_name]
        sample = collection.find_one({}, {"_id": 0})
        count = collection.count_documents({})

        return _make_response({
            "collection": collection_name,
            "document_count": count,
            "fields": list(sample.keys()) if sample else [],
            "sample_record": sample,
            "tip": "Use field names exactly as shown above in your queries."
        })
    except Exception as e:
        return _make_response(f"Schema error: {str(e)}")

def count_records(
    collection_name: str,
    field_name: str = "",
    field_value: str = "",
    numeric_field: str = "",
    min_value: float = None,
    max_value: float = None,
    array_field: str = "",
    array_contains: str = "",
) -> ToolResponse:
    """
    Count documents matching filters WITHOUT returning all records.
    Use this instead of query_collection when you only need a number.

    Args:
        collection_name: Collection to count from
        field_name: Field for exact match filter
        field_value: Value to match
        numeric_field: Numeric field for range filter
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
        array_field: Array field to search within
        array_contains: Value the array must contain
    """
    if _db is None:
        return _make_response("Database not initialised.")

    try:
        query = {}
        if field_name and field_value:
            if field_value.lower() == "true":
                query[field_name] = True
            elif field_value.lower() == "false":
                query[field_name] = False
            else:
                query[field_name] = field_value

        if numeric_field:
            range_query = {}
            if min_value is not None:
                range_query["$gte"] = min_value
            if max_value is not None:
                range_query["$lte"] = max_value
            if range_query:
                query[numeric_field] = range_query

        if array_field and array_contains:
            query[array_field] = array_contains

        count = _db[collection_name].count_documents(query)  # pymongo method, fine here
        return _make_response({"count": count, "filter_applied": query})

    except Exception as e:
        return _make_response(f"Count error: {str(e)}")