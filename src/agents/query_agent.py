"""
query_agent.py
--------------
NL Data Query Agent using AgentScope v1.x API.
Member 1 owns this file.
"""

import json
import os

from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.tool import Toolkit, ToolResponse
from agentscope.agent import ReActAgent
from pathlib import Path

# ── Hardcode your config paths (Windows style) ────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
AGENT_CFG = BASE_DIR / "configs" / "agents_config.json"
MODEL_CFG = BASE_DIR / "configs" / "model_config.json"

from dotenv import load_dotenv
load_dotenv()

def _load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def _build_toolkit(use_mock: bool = False) -> Toolkit:
    if use_mock:
        from src.tools.mock_tools import (
            query_collection,
            aggregate_collection,
            get_schema,
        )
        # count_records is not in mock_tools — define a simple stub
        from agentscope.tool import ToolResponse
        def count_records(collection_name: str, field_name: str = "", field_value: str = "") -> ToolResponse:
            """Count records matching filters (mock mode — returns placeholder)."""
            return ToolResponse(content=[{"type": "text", "text": '{"count": "N/A (mock mode)"}'}])

        print("[DEV] Running with MOCK tools — no DB connection required.\n")
    else:
        try:
            from src.tools.mongo_tools import (
                query_collection,
                aggregate_collection,
                get_schema,
                count_records,
            )
        except ImportError as e:
            raise ImportError(
                "mongo_tools.py not found. Make sure src/tools/mongo_tools.py exists."
            ) from e

    toolkit = Toolkit()
    toolkit.register_tool_function(query_collection)
    toolkit.register_tool_function(aggregate_collection)
    toolkit.register_tool_function(get_schema)
    toolkit.register_tool_function(count_records)
    return toolkit


def build_query_agent(use_mock: bool = False, system_prompt_override: str = None) -> ReActAgent:
    agent_cfg = _load_json(AGENT_CFG)

    # Use override if provided, else fall back to config file prompt
    system_prompt = system_prompt_override or agent_cfg["system_prompt"]

    api_key = os.environ.get("GROQ_API_KEY", "")
    print(f"API KEY LOADED: {api_key[:8]}...")

    model = OpenAIChatModel(
        model_name="llama-3.3-70b-versatile",
        api_key=api_key,
        client_kwargs={"base_url": "https://api.groq.com/openai/v1"},
        generate_kwargs={"temperature": 0.2},
    )
    formatter = OpenAIChatFormatter()

    agent = ReActAgent(
        name=agent_cfg["agent_name"],
        sys_prompt=system_prompt,       # ← uses override or config
        model=model,
        formatter=formatter,
        toolkit=_build_toolkit(use_mock=use_mock),
        max_iters=agent_cfg.get("max_retries", 5),
    )
    return agent


# ── Quick test entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio
    from agentscope.message import Msg

    async def main():
        agent = build_query_agent(use_mock=True)
        print("Agent ready:", agent.name)

        test_questions = [
            "Show me all employees in Engineering",
            "Who earns more than 70000?",
            "What is the average salary by department?",
        ]

        for q in test_questions:
            print(f"\nYou: {q}")
            response = await agent(Msg(name="User", content=q, role="user"))
            print(f"Agent: {response.content}")

    asyncio.run(main())