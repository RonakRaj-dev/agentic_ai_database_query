"""
supabase_tools.py
-----------------
AgentScope tool functions for querying Supabase (PostgreSQL).
Mirrors mongo_tools.py interface exactly — same 4 functions,
same parameter names, same ToolResponse format.

The agent never knows whether it's talking to MongoDB or Supabase.
Swap tool source in query_agent.py's _build_toolkit() to switch.

Member 2 owns this file.
"""

import json
from agentscope.tool import ToolResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Global Supabase client — injected from main.py at startup
_supabase = None
_active_table: str = ""


def init_tools(supabase_client, table_name: str = ""):
    """
    Call this once from main.py after Supabase connects.

    Args:
        supabase_client: Supabase Client instance from loadSupabaseClient()
        table_name: Default table to query (can be overridden per call)
    """
    global _supabase, _active_table
    _supabase = supabase_client
    _active_table = table_name
    logger.info(f"supabase_tools initialised. Default table: '{table_name or 'none set'}'")


def _make_response(data) -> ToolResponse:
    """Wrap any data into a ToolResponse for AgentScope."""
    text = json.dumps(data, indent=2, default=str) if not isinstance(data, str) else data
    return ToolResponse(content=[{"type": "text", "text": text}])


def _resolve_table(table_name: str) -> str:
    """Use provided table or fall back to the globally set default."""
    return table_name if table_name else _active_table


# ══════════════════════════════════════════════════════════════════════════════
# TOOL 1 — get_schema
# ══════════════════════════════════════════════════════════════════════════════

def get_schema(table_name: str = "") -> ToolResponse:
    """
    Get column names, row count, and a sample row from a Supabase table.
    Always call this first when unsure about available columns.

    Args:
        table_name: Name of the Supabase table to inspect e.g. Employee, accounts
    """
    if _supabase is None:
        return _make_response("Supabase client not initialised. Call init_tools() first.")

    table = _resolve_table(table_name)
    if not table:
        return _make_response("No table name provided and no default table set.")

    try:
        # Fetch one row to get column names
        response = _supabase.table(table).select("*").limit(1).execute()

        if not response.data:
            return _make_response(f"Table '{table}' exists but has no data.")

        sample = response.data[0]
        columns = list(sample.keys())

        # Count total rows
        count_response = _supabase.table(table).select("*", count="exact").execute()
        total = count_response.count if hasattr(count_response, "count") else "unknown"

        return _make_response({
            "table": table,
            "row_count": total,
            "columns": columns,
            "sample_row": sample,
            "tip": "Use column names exactly as shown above in your queries."
        })

    except Exception as e:
        logger.error(f"get_schema error: {e}")
        return _make_response(f"Schema error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# TOOL 2 — query_collection (same name as mongo_tools for agent compatibility)
# ══════════════════════════════════════════════════════════════════════════════

def query_collection(
    collection_name: str = "",
    field_name: str = "",
    field_value: str = "",
    numeric_field: str = "",
    min_value: float = None,
    max_value: float = None,
    array_field: str = "",
    array_contains: str = "",
    nested_field: str = "",
    nested_value: str = "",
    limit: int = 10,
) -> ToolResponse:
    """
    Query a Supabase table with optional filters.
    Parameter names match mongo_tools.query_collection exactly.

    Args:
        collection_name: Supabase table name e.g. Employee, accounts
        field_name: Column for exact or pattern match e.g. department, active
        field_value: Value to match e.g. Engineering, true, false
        numeric_field: Numeric column for range filter e.g. salary, age
        min_value: Minimum value for numeric_field (inclusive)
        max_value: Maximum value for numeric_field (inclusive)
        array_field: Not used in SQL — kept for interface compatibility
        array_contains: Not used in SQL — kept for interface compatibility
        nested_field: Column path for nested JSON field e.g. address->>city
        nested_value: Value to match for nested_field
        limit: Max rows to return (default 10, max 20)
    """
    if _supabase is None:
        return _make_response("Supabase client not initialised.")

    table = _resolve_table(collection_name)
    if not table:
        return _make_response("No table name provided.")

    try:
        safe_limit = min(int(limit), 20)
        query = _supabase.table(table).select("*")

        # String field filter — exact or pattern match
        if field_name and field_value:
            if field_value.lower() == "true":
                query = query.eq(field_name, True)
            elif field_value.lower() == "false":
                query = query.eq(field_name, False)
            else:
                # ilike = case-insensitive pattern match (SQL ILIKE)
                query = query.ilike(field_name, f"%{field_value}%")

        # Numeric range filters
        if numeric_field:
            if min_value is not None:
                query = query.gte(numeric_field, min_value)
            if max_value is not None:
                query = query.lte(numeric_field, max_value)

        # Nested JSON field (PostgreSQL JSON operator ->>)
        # e.g. nested_field="address->>city", nested_value="New York"
        if nested_field and nested_value:
            query = query.ilike(nested_field, f"%{nested_value}%")

        # Apply limit
        query = query.limit(safe_limit)
        response = query.execute()

        if not response.data:
            return _make_response("No records found matching the given filters.")

        return _make_response({
            "showing": len(response.data),
            "results": response.data
        })

    except Exception as e:
        logger.error(f"query_collection error: {e}")
        return _make_response(f"Query error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# TOOL 3 — count_records
# ══════════════════════════════════════════════════════════════════════════════

def count_records(
    collection_name: str = "",
    field_name: str = "",
    field_value: str = "",
    numeric_field: str = "",
    min_value: float = None,
    max_value: float = None,
    array_field: str = "",
    array_contains: str = "",
) -> ToolResponse:
    """
    Count rows matching filters WITHOUT fetching all records.
    Use for 'how many' questions — much cheaper than query_collection.

    Args:
        collection_name: Supabase table name
        field_name: Column for exact match filter
        field_value: Value to match
        numeric_field: Numeric column for range filter
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
        array_field: Kept for interface compatibility (unused in SQL)
        array_contains: Kept for interface compatibility (unused in SQL)
    """
    if _supabase is None:
        return _make_response("Supabase client not initialised.")

    table = _resolve_table(collection_name)
    if not table:
        return _make_response("No table name provided.")

    try:
        query = _supabase.table(table).select("*", count="exact")

        if field_name and field_value:
            if field_value.lower() == "true":
                query = query.eq(field_name, True)
            elif field_value.lower() == "false":
                query = query.eq(field_name, False)
            else:
                query = query.ilike(field_name, f"%{field_value}%")

        if numeric_field:
            if min_value is not None:
                query = query.gte(numeric_field, min_value)
            if max_value is not None:
                query = query.lte(numeric_field, max_value)

        # Limit to 1 — we only need the count, not actual rows
        response = query.limit(1).execute()
        total = response.count if hasattr(response, "count") else len(response.data)

        return _make_response({
            "count": total,
            "table": table,
            "filter_applied": {
                "field_name": field_name,
                "field_value": field_value,
                "numeric_field": numeric_field,
                "min_value": min_value,
                "max_value": max_value,
            }
        })

    except Exception as e:
        logger.error(f"count_records error: {e}")
        return _make_response(f"Count error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# TOOL 4 — aggregate_collection
# ══════════════════════════════════════════════════════════════════════════════

def aggregate_collection(
    collection_name: str = "",
    group_by: str = "",
    agg_field: str = "",
    agg_operator: str = "count",
    unwind_array: bool = False,
) -> ToolResponse:
    """
    Group and aggregate Supabase table data.
    Uses Supabase's RPC (PostgreSQL functions) for grouping.

    Args:
        collection_name: Supabase table name
        group_by: Column to group by e.g. department, city, role
        agg_field: Numeric column to aggregate e.g. salary, age
        agg_operator: One of: count, avg, sum, min, max
        unwind_array: Kept for interface compatibility (unused in SQL)
    """
    if _supabase is None:
        return _make_response("Supabase client not initialised.")

    table = _resolve_table(collection_name)
    if not table:
        return _make_response("No table name provided.")

    if not group_by:
        return _make_response("group_by parameter is required for aggregation.")

    valid_operators = {"count", "avg", "sum", "min", "max"}
    if agg_operator not in valid_operators:
        return _make_response(f"Invalid agg_operator '{agg_operator}'. Choose from: {valid_operators}")

    try:
        # Fetch data and aggregate in Python
        # (Supabase free tier doesn't support raw GROUP BY SQL via REST API)
        # For production, use supabase.rpc() with a PostgreSQL function instead
        response = _supabase.table(table).select("*").execute()

        if not response.data:
            return _make_response(f"No data found in table '{table}'.")

        # Group records by the group_by column
        groups: dict = {}
        for row in response.data:
            key = str(row.get(group_by, "Unknown"))
            groups.setdefault(key, []).append(row)

        # Compute aggregation per group
        result = []
        for group_key, rows in groups.items():
            entry = {group_by: group_key, "count": len(rows)}

            if agg_field and agg_operator != "count":
                values = [
                    float(r[agg_field])
                    for r in rows
                    if r.get(agg_field) is not None
                ]
                if values:
                    if agg_operator == "avg":
                        entry[f"avg_{agg_field}"] = round(sum(values) / len(values), 2)
                    elif agg_operator == "sum":
                        entry[f"sum_{agg_field}"] = sum(values)
                    elif agg_operator == "min":
                        entry[f"min_{agg_field}"] = min(values)
                    elif agg_operator == "max":
                        entry[f"max_{agg_field}"] = max(values)

            result.append(entry)

        # Sort by count descending, return top 10
        result.sort(key=lambda x: x["count"], reverse=True)
        result = result[:10]

        return _make_response(result)

    except Exception as e:
        logger.error(f"aggregate_collection error: {e}")
        return _make_response(f"Aggregation error: {str(e)}")