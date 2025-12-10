# R^3: AI-Powered Personalized Daily Digest using RAG + Multi-Agent Workflow

This project implements a customized, personalized "Morning Brew" using **Retrieval-Augmented Generation (RAG)** and a coordinated **multi-agent system**. Users receive short-form, digestible summaries aligned with their professional interests (politics, finance, technology).

## 🎯 Project Overview

**Problem**: Professionals and students in fast-moving fields struggle to stay informed amid overwhelming information while attention spans shrink. Traditional news subscriptions deliver uniform content, not tailored to individual interests.

**Solution**: An AI-powered system that:
- Retrieves relevant articles from a JSONL news database using semantic search
- Summarizes them using RAG (grounding in retrieved context) for factual accuracy
- Personalizes and ranks content per user preferences
- Delivers via beautiful HTML email digest

## ✨ Key Features

- **RAG Pipeline**: Grounded summaries using retrieved context for factual accuracy
- **Multi-Agent Workflow**:
  - **Retriever Agent**: Semantic search with user preference awareness
  - **Summarizer Agent**: Azure OpenAI-powered concise, contextual summaries
  - **Ranker Agent**: Personalization and ranking per user interests
  - **Email Agent**: HTML digest assembly and delivery
- **Vector Store**: Chromadb with sentence-transformers embeddings
- **Acceptance Tests**: Validates KPIs (≥80% Retrieval Hit Rate, ≥95% Task Success Rate, <10s latency)
- **User Preferences**: "Select all that apply" for politics, finance, technology

## 🛠️ Tech Stack

- **Python 3.11+**
- **Chromadb** — vector store & retrieval
- **sentence-transformers** — embeddings (free & local)
- **Azure OpenAI** — LLM for summarization (cost-efficient)
- **scikit-learn** — ranking & TF-IDF similarity
- **pytest** — acceptance tests
- **FastAPI** (optional) — web API

## 📦 Setup

### 1. Clone & Install

```bash
cd /Users/ria/Downloads/R^3
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure `.env`

Copy `.env.example` to `.env` and fill in your Azure OpenAI credentials:

```bash
cp .env.example .env
# Edit .env with your Azure credentials:
# AZURE_OPENAI_API_KEY=<your-key>
# AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### 3. Ingest Articles

Place your `aithena_articles.jsonl` in the project root, then ingest:

```bash
python -c "
from scripts.run_pipeline import RAGPipeline
pipeline = RAGPipeline()
count = pipeline.ingest_articles('aithena_articles.jsonl')
print(f'✅ Ingested {count} articles')
"
```

## 🚀 Quick Start

### Generate a Personalized Digest

```bash
python scripts/run_pipeline.py
```

Or programmatically:

```python
from scripts.run_pipeline import RAGPipeline

pipeline = RAGPipeline()

# Run for a user with specific preferences
results = pipeline.run(
    user_preferences=["politics", "finance", "technology"],
    top_k=5,
    save_html=True,      # Save to HTML file
    send_email=False,     # Set to True if SMTP configured
    user_name="Alice",
)

print(results)
# {
#     'user_preferences': ['politics', 'finance', 'technology'],
#     'retrieved_articles': 15,
#     'summarized_articles': 15,
#     'ranked_articles': 15,
#     'html_saved': True,
#     'email_sent': False,
# }
```

## 📊 Agent Workflow

```
User Preferences (politics, finance, tech)
          ↓
   [Retriever Agent]
   Semantic search in vector store
          ↓
   [Summarizer Agent]
   Azure OpenAI RAG-grounded summaries
          ↓
   [Ranker Agent]
   TF-IDF + preference-based ranking
          ↓
   [Email Agent]
   HTML digest assembly & delivery
          ↓
   Beautiful personalized digest
```

## ✅ Acceptance Tests

Validates KPIs from the proposal:

```bash
pytest tests/test_pipeline.py -v
```

Tests include:
- **Retrieval Hit Rate**: ≥80% of expected articles retrieved
- **Task Success Rate**: ≥95% of agents complete without errors
- **Latency**: Full digest <10 seconds
- **HTML generation**: Valid structure with all preferences
- **Ranking**: Articles properly scored and distributed

## 📋 KPIs & Metrics

| KPI | Target | Status |
|-----|--------|--------|
| Retrieval Hit Rate | ≥80% | ✅ |
| Agent Task Success Rate | ≥95% | ✅ |
| Full Digest Latency | <10s | ✅ |
| Summary Accuracy | Factual (RAG-grounded) | ✅ |
| User Preference Coverage | All 3 focus areas | ✅ |

## 🔧 Project Structure

```
R^3/
├── app/
│   ├── agents/
│   │   ├── ingest.py         # RAG ingestion (JSONL → Chroma)
│   │   ├── retriever.py      # Semantic search
│   │   ├── summarizer.py     # Azure OpenAI summaries
│   │   ├── ranker.py         # Personalization & ranking
│   │   └── emailer.py        # HTML digest & email
│   ├── main.py
│   ├── models.py
│   ├── crud.py
│   └── api.py
├── scripts/
│   └── run_pipeline.py       # CLI runner
├── tests/
│   ├── test_api.py
│   └── test_pipeline.py      # Acceptance tests
├── chroma_db/                # Vector store (auto-created)
├── requirements.txt
├── .env.example
├── README.md
└── aithena_articles.jsonl    # Your RAG database
```

## 💬 Example Output

Generated digest includes:

```
📰 Your Personalized Digest
December 8, 2024

Good morning, Alice! ☀️

📰 Politics
- Congress Passes Infrastructure Bill
  Summary: Major legislation approved with bipartisan support...

💰 Finance
- Stock Market Hits New Record
  Summary: Tech stocks lead gains amid strong earnings...

🚀 Technology
- AI Breakthroughs in Machine Learning
  Summary: Researchers announce techniques advancing neural networks...
```

## 🔒 Security & Best Practices

- **Never commit `.env`** — it contains API keys
- Azure OpenAI API key is used only for summarization (cost-efficient)
- Embeddings are local (free, using sentence-transformers)
- Email credentials optional; digest can be saved as HTML file
- All processing happens locally (no 3rd-party logging)

## 📈 Cost Estimation

Using Azure OpenAI (gpt-4 or similar):
- ~15 articles/day × 30 days = $0.50-2/month (summarization only)
- Embeddings: FREE (local, sentence-transformers)
- Vector store: FREE (local Chroma)

## 🐛 Troubleshooting

### No articles retrieved
- Check `aithena_articles.jsonl` exists and is valid JSON Lines format
- Verify embeddings were generated during ingestion: `ls -la chroma_db/`
- Try adjusting retrieval query or `top_k` parameter

### Azure OpenAI errors
- Verify `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` in `.env`
- Check API quota and billing status
- Confirm deployment name matches actual Azure resource

### Email not sending
- Ensure SMTP credentials are correct in `.env`
- For Gmail, use an App Password (not your regular password)
- SMTP tests require all email env vars set

### Pipeline timeout
- Reduce `top_k` or number of articles per preference
- Use smaller embedding model or pre-computed embeddings

## 📚 References

- **RAG**: Retrieval-Augmented Generation for accurate, grounded summaries
- **Multi-Agent**: Coordinated agents for complex workflows (Retriever → Summarizer → Ranker → Emailer)
- **Vector Store**: Chromadb for semantic search on embeddings
- **Embeddings**: sentence-transformers all-MiniLM for efficient local embeddings

## 📝 Future Enhancements

- Direct Preference Optimization (DPO) for personalization
- Scheduling via cron or cloud functions
- Web UI for preference selection
- Advanced ranking (collaborative filtering)
- Multi-language support

## 📄 License

MIT License — see LICENSE file

## 👥 Contributing

Contributions welcome! Fork, create a branch, and submit a PR.

---

**Built with ❤️ for fast-paced professionals and students who value their time.**
