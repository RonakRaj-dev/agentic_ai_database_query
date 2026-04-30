"""
app.py
------
Gradio 6.13.0 compatible chat interface.
HuggingFace Spaces forces gradio==6.13.0 — do NOT pin gradio in requirements.txt

Key facts about Gradio 6.13.0 Chatbot:
- NO 'type' parameter
- NO 'bubble_full_width' parameter
- History must be list of {"role": ..., "content": ...} dicts
- layout="bubble" or layout="panel" replaces the old type param
"""

import sys
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
        if not content:
            content = "No response generated."
    except Exception as e:
        content = f"Error: {str(e)}"

    # Gradio 6.13.0 message format
    history.append({"role": "user",      "content": user_message})
    history.append({"role": "assistant", "content": content})
    return "", history


def clear_chat() -> list:
    return []


# ── UI — Gradio 6.13.0 compatible ────────────────────────────────────────────
with gr.Blocks() as demo:

    gr.HTML("""
        <div style='text-align:center; padding:20px'>
            <h1>🤖 NL Data Query Agent</h1>
            <p>Ask questions about the dataset in plain English.</p>
        </div>
    """)

    gr.HTML(f"""
        <div style='font-size:12px; color:gray; text-align:center; margin-bottom:10px'>
            Mode: {'🟡 MOCK DATA' if USE_MOCK else '🟢 Live MongoDB'} &nbsp;|&nbsp;
            Model: Groq llama3-groq-70b-tool-use &nbsp;|&nbsp;
            Framework: AgentScope
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):

            # ── Gradio 6.13.0: no 'type', use 'layout' instead ───────────────
            chatbot = gr.Chatbot(
                label="Agent Conversation",
                height=500,
                layout="bubble",        # "bubble" or "panel" — replaces type=
                show_label=True,
            )

            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="e.g. Show me all employees in Engineering",
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
                "Average salary by department?",
                "Show ML Engineers with 5+ years experience",
                "How many employees in each city?",
                "Show me the available fields",
            ]
            for example in examples:
                gr.Button(example, size="sm").click(
                    fn=lambda x=example: x,
                    outputs=msg_input
                )

            gr.Markdown("### ℹ️ About")
            gr.Markdown("""
            **ReAct Agent** loop:
            1. Understands your question
            2. Picks the right tool
            3. Queries the database
            4. Formats the answer

            Built with **AgentScope** + **Groq**
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
        outputs=chatbot
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )