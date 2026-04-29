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


def build_full_schema(db):
    schema = {}

    for name in db.list_collection_names():
        sample = db[name].find_one()
        if sample:
            schema[name] = extract_nested_fields(sample)

    return schema
