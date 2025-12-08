# How to Email the Personalized News Digest

This guide shows you how to set up email delivery so your professor (or anyone) receives the digest in their inbox.

## 📧 What You'll Have

A beautiful email (like Morning Brew) arrives daily with:
- **Politics**: Top 5 personalized articles + summaries
- **Finance**: Top 5 personalized articles + summaries  
- **Technology**: Top 5 personalized articles + summaries

Each article includes: Title, Concise Summary, Source, Link

---

## Option 1: Save as HTML File (Quickest - 1 minute)

This is what the system does by default. Perfect for showing your professor.

```bash
cd /Users/ria/Downloads/R^3
source .venv311/bin/activate
python scripts/run_pipeline.py
```

**Output**: `digest_User.html` file (open in browser to view)

**To share with professor:**
```bash
# Send via email manually, or:
open digest_User.html  # Copy from browser, paste into email
```

---

## Option 2: Send via Gmail (20 minutes)

This sends the digest directly to your professor's email inbox.

### Step 1: Enable Gmail App Password

Gmail doesn't allow regular passwords for third-party apps. Create an "App Password":

1. Go to https://myaccount.google.com
2. Click **Security** (left sidebar)
3. Enable **2-Step Verification** (if not already enabled)
4. Scroll down to **App passwords** (appears after 2-Step is on)
5. Select: Device = **Mail**, OS = **Windows (or your OS)**
6. Click **Generate**
7. Copy the 16-character password

### Step 2: Configure .env

```bash
cd /Users/ria/Downloads/R^3

# Edit .env file
nano .env
```

Add these lines:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
EMAIL_TO=professor@university.edu
```

Save: Press `Ctrl+X`, then `Y`, then `Enter`

### Step 3: Run Pipeline

```bash
source .venv311/bin/activate
python scripts/run_pipeline.py
```

**Console output should show:**
```
✅ Digest saved to digest_User.html
✅ Email sent to professor@university.edu
```

**What your professor receives:**
- Professional HTML email with articles
- Organized by preference (Politics, Finance, Tech)
- Beautiful styling, links to original articles
- Can read on any device

---

## Option 3: Schedule Daily Digest (30 minutes)

Send digest automatically every morning at 8 AM.

### Step 1: Create a Cron Job

```bash
# Open crontab editor
crontab -e

# Add this line (sends digest every day at 8 AM):
0 8 * * * cd /Users/ria/Downloads/R^3 && source .venv311/bin/activate && python scripts/run_pipeline.py

# Save and exit (Ctrl+X, Y, Enter if using nano)
```

### Step 2: That's It!

Every morning at 8 AM, the system will:
1. Fetch fresh articles
2. Summarize them
3. Rank by preference
4. Email to your professor
5. Create `digest_User.html`

Check logs to confirm it ran:
```bash
# View cron logs (macOS)
log stream --predicate 'eventMessage contains[c] "cron"'

# Or check if digest file was updated:
ls -lah digest_User.html
```

---

## Option 4: Cloud Deployment (Advanced - 1 hour)

Deploy to a server (like AWS Lambda, Heroku, or Google Cloud) to run the digest automatically.

### Using AWS Lambda (Serverless)

1. Package Python code + dependencies
2. Upload to AWS Lambda
3. Schedule with CloudWatch (daily trigger)
4. Lambda runs script automatically
5. Email goes out daily

**Benefits:**
- Runs on AWS servers (always on)
- No computer needed
- Pay ~$1/month or less
- Works 24/7

**Drawback:** Requires AWS account (free tier available for 1 year)

---

## Troubleshooting Email Issues

### "Email failed to send"

**Check 1: App Password is correct**
```bash
# Verify in .env
cat .env | grep EMAIL_PASSWORD
```

**Check 2: Gmail App Password, not regular password**
- Use the 16-character app password, not your Gmail password

**Check 3: Email address is valid**
```bash
# Verify in .env
cat .env | grep EMAIL_TO
```

**Check 4: Less secure apps enabled** (if not using App Password)
- Go to https://myaccount.google.com/lesssecureapps
- Enable "Less secure app access"
- (Not recommended, use App Password instead)

---

## Email Template

Here's what your professor receives:

```
Subject: Your Personalized News Digest - Today

From: you@gmail.com
To: professor@university.edu

┌─────────────────────────────────────────────────────────┐
│     📰 YOUR PERSONALIZED NEWS DIGEST                    │
│                                                         │
│  🏛️  POLITICS (5 Articles)                              │
│  ───────────────────────────────────────────────────    │
│                                                         │
│  1. Congress Debates New Tech Regulation Bill          │
│     Congress committee advances comprehensive tech    │
│     regulation addressing data privacy and AI...      │
│     Source: Political Times | 1 min read              │
│     [Read Full Article]                               │
│                                                         │
│  2. Election Year Brings Focus to Digital Rights      │
│     As 2024 approaches, candidates increasingly       │
│     highlight digital privacy...                      │
│     Source: Gov News | 1 min read                     │
│     [Read Full Article]                               │
│                                                         │
│  ... (3 more politics articles)                        │
│                                                         │
│  💰 FINANCE (5 Articles)                                │
│  ───────────────────────────────────────────────────    │
│  ... (5 finance articles with summaries)              │
│                                                         │
│  💻 TECHNOLOGY (5 Articles)                             │
│  ───────────────────────────────────────────────────    │
│  ... (5 tech articles with summaries)                 │
│                                                         │
│  Generated: 2025-12-08 14:30:00                        │
│  Powered by R^3 (RAG + Multi-Agent System)             │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Reference

### Send Once (to show professor):
```bash
python scripts/run_pipeline.py
# Shows digest_User.html
```

### Send Every Day at 8 AM:
```bash
# Add to crontab:
0 8 * * * cd /Users/ria/Downloads/R^3 && source .venv311/bin/activate && python scripts/run_pipeline.py
```

### Configure Email in .env:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_16_chars
EMAIL_TO=recipient@example.com
```

### Test Email:
```bash
# Run pipeline and check console for "Email sent" message
python scripts/run_pipeline.py
```

---

## For Your Professor

**Subject Line Suggestion:**
```
"R^3 Project Demo - Personalized Daily News Digest"

Here's a demo of my RAG-based multi-agent system that fetches,
summarizes, and personalizes daily news articles.

The attached/embedded digest shows articles in politics, finance,
and technology - automatically fetched, summarized with local AI,
ranked by relevance, and formatted as a beautiful email.

Run it yourself:
  cd /Users/ria/Downloads/R^3
  source .venv311/bin/activate
  python scripts/run_pipeline.py
  open digest_User.html

GitHub: https://github.com/riamittal22/r-3
```

---

## Summary

| Method | Setup Time | Effort | Use Case |
|--------|-----------|--------|----------|
| **HTML File** | 1 min | Minimal | Show professor, share manually |
| **Gmail** | 20 min | Easy | Send to professor's inbox once |
| **Daily Cron** | 30 min | Medium | Send every morning automatically |
| **Cloud (AWS)** | 1 hour | Advanced | Production-ready, always running |

**For your professor demo: Use Option 1 (HTML File) or Option 2 (Gmail)**

Both take <30 minutes and show off your work beautifully! 📧
