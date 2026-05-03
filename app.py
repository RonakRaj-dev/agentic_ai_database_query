"""
app.py
------
Gradio 6.13.0 compatible chat interface with:
- DB selector (MongoDB / Supabase / Mock)
- Dynamic collection/table selector based on chosen DB
- Agent reloads when DB or collection changes
- HuggingFace Spaces compatible
"""

import sys
import os
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from agentscope.message import Msg
from src.agents.query_agent import build_query_agent
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Global state ──────────────────────────────────────────────────────────────
_agent      = None
_db_client  = None
_db_object  = None
_db_type    = "mock"

SYSTEM_DB   = {"admin", "config", "local"}


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_mongo_databases() -> list:
    try:
        from src.database import loadMongoClient
        client = loadMongoClient()
        return [d for d in client.list_database_names() if d not in SYSTEM_DB]
    except Exception as e:
        logger.error(f"MongoDB list DBs failed: {e}")
        return []


def get_mongo_collections(db_name: str) -> list:
    try:
        from src.database import loadMongoClient
        client = loadMongoClient()
        return client[db_name].list_collection_names()
    except Exception as e:
        logger.error(f"MongoDB list collections failed: {e}")
        return []


def get_supabase_tables() -> list:
    try:
        from src.database import loadSupabaseClient
        client = loadSupabaseClient()
        response = client.rpc("get_public_tables", {}).execute()
        if response.data:
            return [row["table_name"] for row in response.data]
        return ["Employee"]
    except Exception as e:
        logger.error(f"Supabase list tables failed: {e}")
        return ["Employee"]


# ── Agent builder ─────────────────────────────────────────────────────────────

def initialise_agent(db_type: str, db_name: str = "", collection: str = "") -> str:
    global _agent, _db_client, _db_object, _db_type
    _db_type = db_type

    try:
        if db_type == "mock":
            _agent = build_query_agent(use_mock=True)
            return "✅ Agent ready — Mock data (employees dataset)"

        elif db_type == "mongodb":
            from src.database import loadMongoClient
            import src.tools.mongo_tools as tools
            import src.utils.schema_loader as schema_loader

            _db_client = loadMongoClient()
            _db_object = _db_client[db_name]
            tools.init_tools(_db_object)

            schema = schema_loader.build_full_schema(_db_object)
            prompt = _build_mongo_prompt(_db_object, schema, collection)
            _agent = build_query_agent(use_mock=False, system_prompt_override=prompt)

            col_label = collection or "all collections"
            return f"✅ Agent ready — MongoDB · {db_name} · {col_label}"

        elif db_type == "supabase":
            from src.database import loadSupabaseClient
            import src.tools.supabase_tools as tools

            _db_client = loadSupabaseClient()
            tools.init_tools(_db_client, table_name=collection)

            prompt = _build_supabase_prompt(collection)
            _agent = build_query_agent(use_mock=False, system_prompt_override=prompt)

            return f"✅ Agent ready — Supabase · table: {collection or 'not selected'}"

        else:
            return "❌ Unknown DB type selected."

    except Exception as e:
        logger.error(f"Agent init failed: {e}")
        _agent = build_query_agent(use_mock=True)
        return f"⚠️ Connection failed: {e}. Fell back to mock data."


def _build_mongo_prompt(db, schema: dict, collection: str) -> str:
    import src.utils.schema_loader as schema_loader
    if collection and collection in schema:
        info   = schema[collection]
        fields = info.get("fields", [])
        count  = info.get("document_count", "?")
        return (
            f"You are a data assistant connected to MongoDB database '{db.name}'.\n\n"
            f"Active collection: {collection}\n"
            f"Fields: {', '.join(fields)}\n"
            f"Documents: {count}\n\n"
            f"Tools: get_schema, query_collection, count_records, aggregate_collection.\n"
            f"Always apply filters. Never fetch all records. Limit=10. Never fabricate data."
        )
    schema_text = schema_loader.schema_to_prompt(schema)
    return (
        f"You are a data assistant connected to MongoDB database '{db.name}'.\n\n"
        f"{schema_text}\n"
        f"Tools: get_schema, query_collection, count_records, aggregate_collection.\n"
        f"Always apply filters. Never fetch all records. Limit=10. Never fabricate data."
    )


def _build_supabase_prompt(table: str) -> str:
    return (
        f"You are a data assistant connected to Supabase (PostgreSQL).\n\n"
        f"Active table: {table or 'not set — call get_schema first'}\n\n"
        f"Tools: get_schema, query_collection, count_records, aggregate_collection.\n"
        f"Always apply filters. Never fetch all records. Limit=10. Never fabricate data."
    )


# ── Chat function ─────────────────────────────────────────────────────────────

async def chat(user_message: str, history: list) -> tuple:
    if not user_message.strip():
        return "", history

    if _agent is None:
        history.append({"role": "user",      "content": user_message})
        history.append({"role": "assistant", "content": "⚠️ No agent loaded. Please select a database and click Connect."})
        return "", history

    user_msg = Msg(name="User", content=user_message, role="user")
    content  = ""

    for attempt in range(3):
        try:
            response = await _agent(user_msg)
            content  = response.content
            if isinstance(content, list):
                content = "\n".join(
                    c.get("text", "") for c in content if c.get("type") == "text"
                )
            if content:
                break
        except Exception as e:
            err = str(e)
            if "failed_generation" in err and attempt < 2:
                continue
            content = f"Error: {err}"
            break

    history.append({"role": "user",      "content": user_message})
    history.append({"role": "assistant", "content": content or "Could not generate a response. Please rephrase."})
    return "", history


def clear_chat() -> list:
    return []


# ── UI event handlers ─────────────────────────────────────────────────────────

def on_db_type_change(db_type: str):
    if db_type == "mock":
        return (
            gr.update(visible=False, choices=[]),
            gr.update(visible=False, choices=[]),
            gr.update(visible=False, choices=[]),
        )
    elif db_type == "mongodb":
        dbs = get_mongo_databases()
        return (
            gr.update(visible=True,  choices=dbs, value=dbs[0] if dbs else None),
            gr.update(visible=False, choices=[]),
            gr.update(visible=False, choices=[]),
        )
    elif db_type == "supabase":
        tables = get_supabase_tables()
        return (
            gr.update(visible=False, choices=[]),
            gr.update(visible=True,  choices=tables, value=tables[0] if tables else None),
            gr.update(visible=True,  choices=tables, value=tables[0] if tables else None),
        )
    return gr.update(), gr.update(), gr.update()


def on_mongo_db_change(db_name: str):
    if not db_name:
        return gr.update(visible=False, choices=[])
    cols = ["All collections"] + get_mongo_collections(db_name)
    return gr.update(visible=True, choices=cols, value=cols[0] if cols else None)


def on_connect(db_type: str, mongo_db: str, mongo_col: str, supa_table: str):
    if db_type == "mock":
        status = initialise_agent("mock")
    elif db_type == "mongodb":
        col    = "" if mongo_col in ("All collections", None) else mongo_col
        status = initialise_agent("mongodb", db_name=mongo_db or "", collection=col)
    elif db_type == "supabase":
        status = initialise_agent("supabase", collection=supa_table or "")
    else:
        status = "❌ No DB type selected."
    return status, []


# ── Startup: load mock agent immediately ─────────────────────────────────────
initialise_agent("mock")


# ══════════════════════════════════════════════════════════════════════════════
# GRADIO UI
# ══════════════════════════════════════════════════════════════════════════════

with gr.Blocks() as demo:

    gr.HTML("""
        <div style='text-align:center; padding:24px 0 8px'>
            <h1 style='font-size:2rem; margin:0'>🤖 NL Data Query Agent</h1>
            <p style='color:#888; margin:6px 0 0'>
                Ask questions about your database in plain English.
            </p>
        </div>
    """)

    # ── DB Selector ───────────────────────────────────────────────────────────
    with gr.Group():
        gr.Markdown("### 🔌 Connect to a Database")

        with gr.Row():
            db_type_radio = gr.Radio(
                choices=["mock", "mongodb", "supabase"],
                value="mock",
                label="Database Type",
                info="Mock = built-in demo data, no credentials needed",
            )

        with gr.Row():
            mongo_db_dropdown = gr.Dropdown(
                choices=[],
                label="MongoDB Database",
                visible=False,
                scale=1,
            )
            supa_table_dropdown = gr.Dropdown(
                choices=[],
                label="Supabase Table",
                visible=False,
                scale=1,
            )
            collection_dropdown = gr.Dropdown(
                choices=[],
                label="Collection",
                visible=False,
                scale=1,
            )

        with gr.Row():
            connect_btn = gr.Button("⚡ Connect & Load Agent", variant="primary", scale=1)
            status_box  = gr.Textbox(
                value="✅ Agent ready — Mock data (employees dataset)",
                label="Status",
                interactive=False,
                scale=3,
            )

    gr.HTML("<hr style='border:none; border-top:1px solid #333; margin:8px 0'>")

    # ── Chat + Sidebar ────────────────────────────────────────────────────────
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Agent Conversation",
                height=460,
                layout="bubble",
                show_label=True,
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="e.g. Show me accounts with limit > 9000",
                    label="Your Question",
                    scale=4,
                    lines=1,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

        with gr.Column(scale=1):
            gr.Markdown("### 💡 Example Queries")

            with gr.Accordion("MongoDB — Analytics", open=True):
                for ex in [
                    "Show me accounts with limit > 9000",
                    "Which accounts have InvestmentStock?",
                    "How many accounts per product type?",
                    "Show me active customers",
                    "List customers from New York",
                ]:
                    gr.Button(ex, size="sm").click(fn=lambda x=ex: x, outputs=msg_input)

            with gr.Accordion("MongoDB — Airbnb", open=False):
                for ex in [
                    "Show listings with more than 4 bedrooms",
                    "What property types are available?",
                    "Listings with WiFi in amenities",
                    "Average price by room type",
                ]:
                    gr.Button(ex, size="sm").click(fn=lambda x=ex: x, outputs=msg_input)

            with gr.Accordion("MongoDB — Supplies", open=False):
                for ex in [
                    "Show me all sales",
                    "How many sales per item?",
                    "What items were sold online?",
                ]:
                    gr.Button(ex, size="sm").click(fn=lambda x=ex: x, outputs=msg_input)

            with gr.Accordion("Mock — Employees", open=False):
                for ex in [
                    "Show all employees in Engineering",
                    "Who earns more than 70000?",
                    "Average salary by department",
                    "List employees from Bangalore",
                ]:
                    gr.Button(ex, size="sm").click(fn=lambda x=ex: x, outputs=msg_input)

            gr.Markdown("### ℹ️ About")
            gr.Markdown("""
            **ReAct Agent** loop:
            1. Understands your question
            2. Picks the right tool
            3. Queries the database
            4. Formats the answer

            **Stack:** AgentScope · Groq · MongoDB · Supabase · Gradio
            """)

    # ── Event wiring ──────────────────────────────────────────────────────────
    db_type_radio.change(
        fn=on_db_type_change,
        inputs=db_type_radio,
        outputs=[mongo_db_dropdown, supa_table_dropdown, collection_dropdown],
    )

    mongo_db_dropdown.change(
        fn=on_mongo_db_change,
        inputs=mongo_db_dropdown,
        outputs=collection_dropdown,
    )

    connect_btn.click(
        fn=on_connect,
        inputs=[db_type_radio, mongo_db_dropdown, collection_dropdown, supa_table_dropdown],
        outputs=[status_box, chatbot],
    )

    send_btn.click(fn=chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
    msg_input.submit(fn=chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
    clear_btn.click(fn=clear_chat, outputs=chatbot)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)