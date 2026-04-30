import sys
import asyncio
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from agentscope.message import Msg
from src.agents.query_agent import build_query_agent

# ── Build agent once at startup ───────────────────────────────────────────────
USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"

print("Initialising agent...")
agent = build_query_agent(use_mock=USE_MOCK)
print(f"Agent ready. Mode: {'MOCK' if USE_MOCK else 'LIVE MongoDB'}")


# ── Core chat function ────────────────────────────────────────────────────────
async def chat(user_message: str, history: list) -> tuple:
    """
    Called by Gradio on each user message.
    history format: list of [user_msg, assistant_msg] pairs
    """
    if not user_message.strip():
        return "", history

    user_msg = Msg(name="User", content=user_message, role="user")

    try:
        response = await agent(user_msg)
        content = response.content
        if isinstance(content, list):
            content = "\n".join(
                c.get("text", "") for c in content if c.get("type") == "text"
            )
    except Exception as e:
        content = f"Error: {str(e)}"

    history.append([user_message, content])
    return "", history


def clear_chat():
    return [], []


# ── Gradio UI ─────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="NL Data Query Agent",
    theme=gr.themes.Soft(),
    css="""
        .header { text-align: center; padding: 20px; }
        .status-bar { font-size: 12px; color: gray; text-align: center; }
        .example-btn { font-size: 13px; }
    """
) as demo:

    gr.HTML("""
        <div class='header'>
            <h1>🤖 NL Data Query Agent</h1>
            <p>Ask questions about the employee dataset in plain English.</p>
        </div>
    """)

    gr.HTML(f"""
        <div class='status-bar'>
            Mode: {'🟡 MOCK DATA' if USE_MOCK else '🟢 Live MongoDB'} &nbsp;|&nbsp;
            Model: Groq llama-3.3-70b-versatile &nbsp;|&nbsp;
            Framework: AgentScope
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Agent Conversation",
                height=500,
                bubble_full_width=False,
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="Ask something... e.g. Show me all ML Engineers",
                    label="Your Question",
                    scale=4,
                    lines=1,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            clear_btn = gr.Button("Clear Chat", variant="secondary")

        with gr.Column(scale=1):
            gr.Markdown("### 💡 Try These")
            examples = [
                "Show me all employees in Engineering",
                "Who earns more than 70000?",
                "List employees from Bangalore",
                "What is the average salary by department?",
                "Show me ML Engineers with 5+ years experience",
                "How many employees are in each city?",
                "Who are the top earners?",
                "Show me the available fields",
            ]
            for example in examples:
                gr.Button(example, size="sm", elem_classes="example-btn").click(
                    fn=lambda x=example: x,
                    outputs=msg_input
                )

            gr.Markdown("### ℹ️ About")
            gr.Markdown("""
            This agent uses a **ReAct loop** to:
            1. Understand your question
            2. Pick the right tool
            3. Query the database
            4. Format the answer

            Built with **AgentScope** + **Groq** (llama-3.3-70b)
            """)

    # ── Event handlers ────────────────────────────────────────────────────────
    send_btn.click(
        fn=chat,
        inputs=[msg_input, chatbot],
        outputs=[msg_input, chatbot]
    )
    msg_input.submit(
        fn=chat,
        inputs=[msg_input, chatbot],
        outputs=[msg_input, chatbot]
    )
    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, chatbot]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False          # set share=True for a public link locally
    )