# R^3 System Architecture

## High-Level Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ User Defines Preferences (politics, finance, technology, etc.)  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│          RETRIEVER AGENT: Fetch & Update Database               │
├──────────────────────────────────────────────────────────────────┤
│  1. fetch_fresh_articles(topics)                                 │
│     - Query NewsAPI.org with user preferences                   │
│     - Or use mock articles if API key not available             │
│     - Returns: List[Dict] with id, title, text, metadata        │
│                                                                  │
│  2. update_database_with_articles(articles)                     │
│     - Embed articles using SentenceTransformer                  │
│     - Index into Chroma vector store                            │
│     - Skip duplicates (check if article ID exists)              │
│                                                                  │
│  3. retrieve_by_preference(user_preferences)                    │
│     - Query vector store: "news about {preference}"             │
│     - Return top-K most relevant articles                       │
│     - Score based on semantic similarity                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼ (15 articles for 3 preferences)
┌──────────────────────────────────────────────────────────────────┐
│         SUMMARIZER AGENT: Generate Concise Summaries            │
├──────────────────────────────────────────────────────────────────┤
│  - Use facebook/bart-large-cnn (Hugging Face)                   │
│  - Local model (no API keys needed)                             │
│  - RAG-grounded: summarize retrieved article content            │
│  - Batch processing for efficiency                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼ (15 summaries)
┌──────────────────────────────────────────────────────────────────┐
│         RANKER AGENT: Personalize & Rank Content                │
├──────────────────────────────────────────────────────────────────┤
│  - TF-IDF vectorization of summaries                            │
│  - Cosine similarity with preference keywords                   │
│  - Rank within each preference category                         │
│  - Distribute articles per preference                           │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼ (Ranked articles per preference)
┌──────────────────────────────────────────────────────────────────┐
│         EMAIL AGENT: Assemble & Deliver Digest                  │
├──────────────────────────────────────────────────────────────────┤
│  - Create HTML template with article summaries                  │
│  - Organize by user preferences                                 │
│  - Option 1: Save to digest_USER.html (local)                   │
│  - Option 2: Send via SMTP email (if configured)                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    Beautiful Digest Ready! 📰
```

## Component Details

### RetrieverAgent (`app/agents/retriever.py`)

**Purpose**: Fetch fresh articles and maintain vector database

**Key Methods**:
- `fetch_fresh_articles(topics: List[str])` → List[Dict]
  - Calls NewsAPI.org (if NEWS_API_KEY in .env)
  - Falls back to mock articles for demo/offline mode
  - Returns articles with id, title, text, date, source, url
  
- `update_database_with_articles(articles: List[Dict])` → int
  - Embeds articles using sentence-transformers
  - Stores in Chroma with metadata
  - Skips existing articles (duplicate check)
  - Returns count of added articles
  
- `retrieve_by_preference(user_preferences: List[str])` → Dict[str, List[Dict]]
  - **Main entry point for RAG workflow**
  - Orchestrates: fetch → embed → index → query
  - Returns articles grouped by preference

**Configuration**:
- `NEWS_API_KEY` (optional, from .env)
- Collection name: "aithena_articles"
- Embedding model: all-MiniLM-L6-v2 (local)
- Vector store: Chroma (local/persistent)

### SummarizerAgent (`app/agents/summarizer.py`)

**Purpose**: Generate RAG-grounded summaries

**Key Methods**:
- `summarize(article: Dict)` → str
  - Takes article content
  - Returns concise summary (40-60 tokens)
  - Uses facebook/bart-large-cnn model
  
- `summarize_batch(articles: List[Dict])` → Dict[str, str]
  - Summarizes multiple articles
  - Returns mapping of article_id → summary

**Configuration**:
- Model: facebook/bart-large-cnn (Hugging Face)
- Device: CPU (default) or GPU if available
- Max length: 60 tokens, Min length: 40 tokens
- No API keys needed

### RankerAgent (`app/agents/ranker.py`)

**Purpose**: Personalize and rank summaries

**Key Methods**:
- `rank_by_preference(articles_dict, user_preferences)` → Dict
  - Ranks articles within each preference
  - Uses TF-IDF + cosine similarity
  - Returns ranked articles with scores
  
- `distribute_by_preference(articles, user_preferences)` → Dict
  - Distributes articles across preferences
  - Balances articles per category

**Configuration**:
- Vectorizer: TfidfVectorizer (scikit-learn)
- Similarity metric: Cosine similarity
- No external dependencies needed

### EmailAgent (`app/agents/emailer.py`)

**Purpose**: Assemble and deliver digest

**Key Methods**:
- `create_html_digest(articles_dict, user_name)` → str
  - Generates HTML template
  - Organizes articles by preference
  - Includes article titles, summaries, links
  
- `save_digest(html, filename)` → str
  - Saves HTML to file
  - Default: digest_USER.html
  
- `send_email(html, recipient, subject)` → bool
  - Sends via SMTP (if configured)
  - Optional feature

**Configuration**:
- SMTP_SERVER, SMTP_PORT (optional, from .env)
- EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD (optional)
- All email settings are optional

## Data Flow

```
NewsAPI.org (or mock articles)
            │
            ▼
    [JSON articles]
            │
            ▼
    SentenceTransformer (embedding)
            │
            ▼
    Chroma Vector Store (persistence)
            │
            ▼
    Semantic Search (user preferences)
            │
            ▼
    Retrieved Articles
            │
            ├──────────────────────────┐
            ▼                          ▼
        BART Summarizer          TF-IDF Ranking
            │                          │
            ▼                          ▼
        Summaries    +    Ranked Articles
            │                          │
            └──────────────┬───────────┘
                           ▼
                    HTML Template
                           │
                           ▼
            Save to File / Send via SMTP
```

## Key Design Decisions

### 1. **Fresh Article Fetching**
- Retriever actively fetches articles on each run
- Ensures up-to-date content in digest
- Handles duplicates gracefully (skips if article ID exists)

### 2. **Mock Data Fallback**
- System works offline without API keys
- Perfect for demos and development
- Users can optionally configure NewsAPI.org for production

### 3. **Local LLMs**
- No Azure OpenAI or paid APIs required
- facebook/bart-large-cnn for summarization
- sentence-transformers for embeddings
- Zero cost to operate

### 4. **Vector Store Persistence**
- Chroma stores articles locally
- Can query historical data
- Combined with fresh articles for comprehensive coverage

### 5. **Preference-Based Ranking**
- TF-IDF scores articles by preference
- Distributes content fairly across interests
- Customizable per user

## Running the Pipeline

### Basic Usage (with mock articles):
```bash
cd /Users/ria/Downloads/R^3
source .venv311/bin/activate
python scripts/run_pipeline.py
```

### With NewsAPI Key:
```bash
# Update .env
echo "NEWS_API_KEY=your_key_here" >> .env

# Run
python scripts/run_pipeline.py
```

### Output:
- `digest_User.html` — HTML file with personalized digest
- Console logs showing:
  - Articles fetched (fresh count)
  - Articles added to database
  - Articles retrieved per preference
  - Articles summarized
  - Articles ranked
  - Digest saved/emailed

## Performance Characteristics

- **Fetch**: ~1-2s (NewsAPI) or instant (mock)
- **Embed & Index**: ~5-10s for 6 articles
- **Retrieve**: ~0.5s per preference query
- **Summarize**: ~1-2s per article (GPU: faster, CPU: normal)
- **Rank**: ~0.1s
- **Total**: ~30-50s for full pipeline (CPU)

## Future Enhancements

1. **Batch Processing**: Queue articles for asynchronous processing
2. **Cron Integration**: Schedule digest generation daily/weekly
3. **User Management**: Store user preferences and digest history
4. **Advanced Ranking**: Machine learning-based preference learning
5. **Mobile Support**: Generate mobile-friendly digests
6. **Real-time Updates**: WebSocket integration for live digests
7. **A/B Testing**: Compare different ranking strategies
8. **Analytics**: Track engagement with articles
