# R^3: 5-Minute Quick Start (For Professor Demo)

## What This Does

Generates a personalized email digest with news articles from the past day in **politics, finance, and technology**.

## Prerequisites

- Python 3.11 installed
- 5 minutes of your time
- No API keys needed (works offline with mock articles)

## Run It (3 Commands)

```bash
# 1. Go to project folder
cd /Users/ria/Downloads/R^3

# 2. Activate Python environment
source .venv311/bin/activate

# 3. Generate digest (takes ~40-50 seconds)
python scripts/run_pipeline.py
```

## View the Result

```bash
# Open the generated email in your browser
open digest_User.html
```

That's it! You now have a beautiful email-ready digest with:
- **5 Politics articles** (summarized)
- **5 Finance articles** (summarized)
- **5 Technology articles** (summarized)

All ranked by relevance to each preference.

---

## What Happens Behind the Scenes

1. **Retriever Agent** fetches 6 fresh articles (mock data)
2. **Embedding** converts articles to semantic vectors
3. **Vector Search** finds relevant articles for each preference
4. **Summarizer Agent** summarizes all 15 articles using BART
5. **Ranker Agent** scores articles by preference relevance
6. **Email Agent** assembles beautiful HTML email

---

## For Real Articles (Optional)

Want real articles instead of mock data?

1. Go to https://newsapi.org and sign up (free, takes 2 minutes)
2. Copy your API key
3. Add to `.env`:
   ```bash
   echo "NEWS_API_KEY=your_key_here" >> .env
   ```
4. Run again:
   ```bash
   python scripts/run_pipeline.py
   ```

Same output, but with real articles from NewsAPI!

---

## Show Your Professor

1. Run the three commands above
2. Open `digest_User.html` in browser
3. Show the beautiful HTML email with articles and summaries
4. Show console output (demonstrates each step)
5. Explain: "This is a RAG-based multi-agent system that fetches, summarizes, ranks, and delivers personalized news"

**That's your demo!** 🎉
