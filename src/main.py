"""
main.py
-------
Entry point with DB and collection selector at startup.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import argparse
import os
from dotenv import load_dotenv
from agentscope.message import Msg

load_dotenv()

from src.agents.query_agent import build_query_agent
from src.utils.logger import get_logger

logger = get_logger(__name__)


def select_database(client) -> tuple:
    """
    Interactive DB and collection selector.
    Returns (db_object, selected_collection_name)
    """
    # List all non-system databases
    system_dbs = {"admin", "config", "local"}
    available_dbs = [d for d in client.list_database_names() if d not in system_dbs]

    print("\n📦 Available Databases:")
    for i, db_name in enumerate(available_dbs, 1):
        print(f"  [{i}] {db_name}")

    while True:
        try:
            choice = int(input("\nSelect database number: ")) - 1
            if 0 <= choice < len(available_dbs):
                selected_db_name = available_dbs[choice]
                break
            print("Invalid choice. Try again.")
        except ValueError:
            print("Enter a number.")

    db = client[selected_db_name]

    # List collections in selected DB
    collections = db.list_collection_names()
    print(f"\n📂 Collections in '{selected_db_name}':")
    for i, col in enumerate(collections, 1):
        count = db[col].count_documents({})
        print(f"  [{i}] {col}  ({count} documents)")

    print(f"  [0] All collections")

    while True:
        try:
            choice = int(input("\nSelect collection number (0 for all): "))
            if choice == 0:
                selected_collection = None   # agent can query any collection
                break
            elif 1 <= choice <= len(collections):
                selected_collection = collections[choice - 1]
                break
            print("Invalid choice. Try again.")
        except ValueError:
            print("Enter a number.")

    return db, selected_collection


def build_dynamic_system_prompt(db, collection_name: str | None) -> str:
    """
    Builds system prompt dynamically based on selected DB and collection.
    """
    import src.utils.schema_loader as schema_loader

    schema = schema_loader.build_full_schema(db)

    if collection_name:
        # Narrow prompt to selected collection only
        info = schema.get(collection_name, {})
        fields = info.get("fields", [])
        count = info.get("document_count", 0)
        prompt = f"""You are a smart data assistant connected to MongoDB.

Active collection: {collection_name}
Fields available: {', '.join(fields)}
Total documents: {count}

Use query_collection(collection_name="{collection_name}", ...) for filtering.
Use aggregate_collection(group_by=..., collection_name="{collection_name}") for aggregations.
Use get_schema(collection_name="{collection_name}") if unsure about fields.
Return results in a clean, readable format. Never make up data."""
    else:
        # Broad prompt covering all collections
        schema_text = schema_loader.schema_to_prompt(schema)
        prompt = f"""You are a smart data assistant connected to MongoDB database '{db.name}'.

{schema_text}

Use query_collection(collection_name=...) to filter any collection.
Use aggregate_collection(group_by=..., collection_name=...) for aggregations.
Use get_schema(collection_name=...) to inspect any collection's fields.
Return results in a clean, readable format. Never make up data."""

    return prompt

MAX_RETRIES = 3

async def chat_loop(use_mock: bool):
    # ── Step 1: Connect MongoDB ───────────────────────────────────────────────
    db = None
    selected_collection = None

    if not use_mock:
        try:
            import src.database as database
            import src.tools.mongo_tools as tools

            client = database.loadClient()

            # Interactive selector
            db, selected_collection = select_database(client)
            logger.info(f"Selected DB: {db.name}, Collection: {selected_collection or 'All'}")

            # Inject DB into tools
            tools.init_tools(db)

        except RuntimeError as e:
            logger.error(f"DB connection failed: {e}")
            logger.info("Falling back to mock tools.")
            use_mock = True

    # ── Step 2: Build agent with dynamic prompt ───────────────────────────────
    try:
        if not use_mock and db is not None:
            system_prompt = build_dynamic_system_prompt(db, selected_collection)
            agent = build_query_agent(use_mock=False, system_prompt_override=system_prompt)
        else:
            agent = build_query_agent(use_mock=True)
    except Exception as e:
        logger.error(f"Agent build failed: {e}")
        return

    # ── Step 3: Chat loop ─────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  NL Data Query Agent — powered by AgentScope")
    if use_mock:
        print("  [MODE: MOCK — using fake data]")
    else:
        col_label = selected_collection or "All collections"
        print(f"  [MODE: LIVE — DB: {db.name} | Collection: {col_label}]")
    print("=" * 55)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        user_msg = Msg(name="User", content=user_input, role="user")

        # Retry on function-calling failures
        for attempt in range(MAX_RETRIES):
            try:
                response = await agent(user_msg)
                content = response.content
                if isinstance(content, list):
                    content = "\n".join(
                        c.get("text", "") for c in content if c.get("type") == "text"
                    )
                print(f"\nAgent: {content}")
                break
            except Exception as e:
                err = str(e)
                if "failed_generation" in err and attempt < MAX_RETRIES - 1:
                    print(f"\n[Retrying... attempt {attempt + 2}/{MAX_RETRIES}]")
                    continue
                logger.error(f"Agent error: {e}")
                print(f"\n[Error] {e}")
                break


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Run without MongoDB")
    args = parser.parse_args()
    asyncio.run(chat_loop(use_mock=args.mock))


if __name__ == "__main__":
    run()