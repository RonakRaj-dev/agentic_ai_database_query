
from pymongo.database import Database
from src.utils.logger import get_logger

def get_schema(db):
    schema = {}

    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        sample = collection.find_one()

        if sample:
            schema[collection_name] = list(sample.keys())

    return schema


def extract_nested_fields(document, parent=""):
    fields = []

    for key, value in document.items():
        full_key = f"{parent}.{key}" if parent else key

        if isinstance(value, dict):
            fields.extend(extract_nested_fields(value, full_key))

        elif isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict):
                fields.extend(extract_nested_fields(value[0], full_key))
            else:
                fields.append(full_key)
        else:
            fields.append(full_key)

    return fields


logger = get_logger(__name__)

def build_full_schema(db: Database, sample_size: int = 5) -> dict:
    """
    Scans all collections in a DB and returns schema info.
    Used to dynamically build the agent's system prompt.
    """
    schema = {}
    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        samples = list(collection.find({}, {"_id": 0}).limit(sample_size))
        if not samples:
            continue

        # Collect all unique keys across samples
        all_keys = set()
        for doc in samples:
            all_keys.update(doc.keys())

        schema[collection_name] = {
            "fields": list(all_keys),
            "document_count": collection.count_documents({}),
            "sample": samples[0]
        }
        logger.info(f"Schema loaded for '{collection_name}': {list(all_keys)}")

    return schema


def schema_to_prompt(schema: dict) -> str:
    """
    Converts schema dict into a readable string for the system prompt.
    """
    lines = ["Available MongoDB collections and their fields:\n"]
    for collection, info in schema.items():
        lines.append(f"Collection: {collection}")
        lines.append(f"  Fields: {', '.join(info['fields'])}")
        lines.append(f"  Documents: {info['document_count']}")
        lines.append("")
    return "\n".join(lines)
