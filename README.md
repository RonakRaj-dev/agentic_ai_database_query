---
title: NL Data Query Agent
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "6.13.0"
python_version: "3.13"
app_file: app.py
pinned: false
---

# 🤖 NL Data Query Agent

A conversational AI agent that lets users query MongoDB databases using plain English — no SQL, no code, no filters required.

---

## 📌 What It Does

You type a question like:

> *"Show me all accounts with a limit greater than 9000"*

The agent understands your intent, converts it into a MongoDB query, fetches the data, and returns a clean, readable answer — all in natural language.

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent Framework | AgentScope v1.x | Orchestrates the ReAct agent loop |
| LLM | Groq (llama-3.3-70b-versatile) | Understands NL, decides tool calls |
| Database | MongoDB Atlas | Stores and serves the dataset |
| Frontend | Gradio 6.13.0 | Chat UI deployed on HuggingFace Spaces |
| Language | Python 3.13 | Core implementation |

---

## 🗂️ Project Structure

```
nl-data-query-agent/
├── configs/
│   ├── model_config.json       # LLM backend configuration
│   └── agent_config.json       # System prompt and agent settings
├── src/
│   ├── agents/
│   │   └── query_agent.py      # ReActAgent definition and toolkit wiring
│   ├── tools/
│   │   ├── mongo_tools.py      # Real MongoDB tool functions
│   │   └── mock_tools.py       # Fake tools for testing without DB
│   ├── utils/
│   │   ├── schema_loader.py    # Extracts DB schema for system prompt
│   │   └── logger.py           # Centralised logging
│   ├── database.py             # MongoDB client and connection logic
│   └── main.py                 # CLI entry point with DB selector
├── app.py                      # Gradio dashboard (HuggingFace Spaces)
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
└── README.md
```

---

## ⚙️ Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/nl-data-query-agent.git
cd nl-data-query-agent
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```
GROQ_API_KEY=gsk_your_key_here
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DB_NAME=sample_analytics
MONGO_COLLECTION=accounts
USE_MOCK=false
```

Get your Groq API key free at [console.groq.com/keys](https://console.groq.com/keys)

### 3. Run locally

```bash
# With real MongoDB
python -m src.main

# With mock data (no DB needed)
python -m src.main --mock

# Launch Gradio dashboard locally
python app.py
```

---

## 🚀 HuggingFace Spaces Deployment

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces) → SDK: **Gradio**
2. Push your code to the Space repo
3. Go to **Settings → Variables and Secrets** and add:

| Secret Name | Value |
|-------------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `USE_MOCK` | `true` (mock) or `false` (live MongoDB) |
| `MONGO_URI` | Your Atlas connection string (if live) |

4. Space auto-builds and deploys

---

## 💬 Example Queries

| Question | What happens |
|----------|-------------|
| Show me all Engineering employees | `query_collection(field_name='department', field_value='Engineering')` |
| Who earns more than 70000? | `query_collection(numeric_field='salary', min_value=70000)` |
| Average salary by department | `aggregate_collection(group_by='department', agg_operator='avg')` |
| Accounts with InvestmentStock | `query_collection(array_field='products', array_contains='InvestmentStock')` |
| How many active customers? | `count_records(field_name='active', field_value='true')` |

---

## 🧪 Testing Without MongoDB

```bash
python -m src.main --mock
```

Uses hardcoded fake employee data. All agent logic, tool calling, and ReAct reasoning works identically — only the data source changes.

---

## 👥 Team

| Member | Role | Files Owned |
|--------|------|-------------|
| Member 1 | Agent & LLM Lead | `src/agents/`, `configs/`, `app.py` |
| Member 2 | Data & Backend Lead | `src/tools/`, `src/database.py`, `src/utils/schema_loader.py` |
| Member 3 | UI & Integration Lead | `app.py`, `src/main.py`, HuggingFace deployment |

---

## 📄 License

MIT License. See `LICENSE` for details.