import asyncio
import argparse
from dotenv import load_dotenv
from agentscope.message import Msg

from src.agents.query_agent import build_query_agent
from src.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


async def chat_loop(use_mock: bool):
    try:
        agent = build_query_agent(use_mock=use_mock)
    except ImportError as e:
        logger.error(str(e))
        return

    print("=" * 55)
    print("  NL Data Query Agent — powered by AgentScope")
    print("  Ask anything about the employees dataset.")
    if use_mock:
        print("  [MODE: MOCK — using fake data, no DB needed]")
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

        try:
            response = await agent(user_msg)
            print(f"\nAgent: {response.content}")
        except Exception as e:
            logger.error(f"Agent error: {e}")
            print(f"\n[Error] {e}")


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Run without MongoDB")
    args = parser.parse_args()
    asyncio.run(chat_loop(use_mock=args.mock))


if __name__ == "__main__":
    run()