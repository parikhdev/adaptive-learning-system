# 🧠 Adaptive Learning System

> An AI-powered JEE/NEET preparation platform that adapts question difficulty in real-time using semantic similarity, vector embeddings, and RAG-based concept explanations.

![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase)
![pgvector](https://img.shields.io/badge/pgvector-Embeddings-blue?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.1-orange?style=flat-square)

---

## 📌 What Is This?

A full-stack AI learning platform built for JEE/NEET students. The system:

- Recommends questions using **semantic vector similarity** (not random selection)
- **Adapts difficulty** progressively as the student answers more questions
- Generates **concept reinforcement explanations** using RAG + Groq LLM after every answer
- Displays **live AI intelligence metrics** — relevance score, difficulty score, cosine distance
- Supports **topic-filtered sessions** across Physics, Chemistry, Maths, and Biology

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js 14)                   │
│   Auth → Dashboard → Subject/Topic Picker → Session Page    │
│   QuestionCard + IntelligencePanel + ExplanationPanel        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│                                                              │
│   POST /recommend/   →  ML Inference Layer                   │
│   POST /explain/     →  RAG Pipeline                         │
│   POST /sessions/    →  Session Management                   │
│                                                              │
│   ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│   │  Embedder   │    │ Difficulty   │    │  RAG Engine   │  │
│   │ BAAI/bge-   │    │  Adaptive    │    │  Retriever +  │  │
│   │ small-en    │    │  Escalation  │    │  Groq LLaMA   │  │
│   └─────────────┘    └──────────────┘    └───────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   SUPABASE (PostgreSQL)                      │
│                                                              │
│   questions (121,557 rows)    →  question_embeddings         │
│   sessions                   →  student_responses            │
│   pgvector cosine similarity search                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| Next.js 14 (App Router) | Full-stack React framework |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| shadcn/ui | Component library |
| Zustand | Session state management |
| KaTeX | LaTeX math rendering |
| Supabase Auth | Authentication (JWT) |

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | REST API framework |
| Python 3.11 | Runtime |
| BAAI/bge-small-en-v1.5 | 384-dim sentence embeddings |
| pgvector | Vector similarity search |
| Groq (LLaMA 3.1 8B) | RAG explanation generation |
| psycopg2 | PostgreSQL driver |
| Pydantic v2 | Request/response validation |

### Infrastructure
| Technology | Purpose |
|---|---|
| Supabase | PostgreSQL + pgvector + Auth |
| Vercel | Frontend deployment |
| Railway | Backend deployment |

---

## 📁 Project Structure

```
adaptive-learning-system/
│
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # App entry + CORS + lifespan
│   │   ├── config.py                 # Environment config
│   │   ├── db/
│   │   │   ├── connection.py         # psycopg2 connection pool
│   │   │   └── vector_search.py      # pgvector cosine search
│   │   ├── ml/
│   │   │   ├── embedder.py           # BAAI/bge sentence encoder
│   │   │   └── difficulty.py         # Adaptive difficulty logic
│   │   ├── rag/
│   │   │   ├── retriever.py          # Similar question retriever
│   │   │   ├── prompt_builder.py     # Concept reinforcement prompt
│   │   │   └── generator.py          # Groq API call
│   │   ├── routers/
│   │   │   ├── recommend.py          # POST /recommend/
│   │   │   ├── explain.py            # POST /explain/
│   │   │   └── sessions.py           # POST /sessions/start|answer
│   │   └── schemas/                  # Pydantic models
│   └── requirements.txt
│
├── frontend/                         # Next.js 14 frontend
│   ├── app/
│   │   ├── (auth)/                   # Login + Signup pages
│   │   ├── (dashboard)/              # Protected dashboard + session
│   │   └── auth/                     # Supabase callback routes
│   ├── components/
│   │   ├── QuestionCard.tsx          # MCQ renderer with KaTeX
│   │   ├── ExplanationPanel.tsx      # RAG explanation display
│   │   ├── IntelligencePanel.tsx     # Live AI metrics + Dev Mode
│   │   ├── SessionStats.tsx          # Answered/Skipped/Level stats
│   │   └── SubjectSelector.tsx       # 2-step subject + topic picker
│   ├── lib/
│   │   ├── api/                      # API client functions
│   │   └── store/session.ts          # Zustand session store
│   └── types/index.ts                # Shared TypeScript types
│
└── data_pipeline/                    # Offline data processing
    ├── 01_clean.py                   # Raw data cleaning
    ├── 02_score_difficulty.py        # Difficulty scoring (0–1)
    ├── 03_extract_topics.py          # Topic/subtopic extraction
    ├── 04_generate_embeddings.py     # BAAI/bge embedding generation
    └── 05_upload_supabase.py         # Supabase bulk upload
```

---

## ⚙️ How The AI Works

### 1. Question Recommendation (`POST /recommend/`)

```
Student starts session (subject + topic)
         ↓
Progress-based difficulty selection:
  Questions 0-2  → Beginner
  Questions 3-5  → Intermediate
  Questions 6+   → Advanced
         ↓
Query text embedded → 384-dim vector (BAAI/bge-small-en-v1.5)
         ↓
pgvector cosine similarity search:
  - Filter: subject + difficulty + NOT LIKE '%nan%'
  - Exclude: already answered question IDs
  - Return: top-10 candidates → pick lowest cosine distance
         ↓
Return question + cosine_distance + difficulty_score
```

### 2. RAG Explanation (`POST /explain/`)

```
Student selects answer
         ↓
Embed question → retrieve 3 similar questions (pgvector)
         ↓
Build prompt:
  - System: "You are a JEE/NEET tutor..."
  - Context: 3 similar reference questions
  - Task: identify correct answer + explain core concept
         ↓
Groq LLaMA 3.1 8B → streamed explanation (~3s)
         ↓
Display: correct answer + concept + formula
```

### 3. AI Intelligence Panel

Every question displays live metrics:

| Metric | Source | Meaning |
|---|---|---|
| Difficulty | `difficulty_level` | Beginner / Intermediate / Advanced |
| Relevance | `1 - cosine_distance` | How semantically similar to query |
| Score | `difficulty_score` | Raw 0–1 difficulty from data pipeline |

Dev Mode reveals: `question_id`, `cosine_dist`, `difficulty_score`, `formula_present`, `keyword_density`, `est_time`

---

## 🗄️ Database Schema

```sql
-- Core tables
questions          (121,557 rows) -- JEE/NEET questions with metadata
question_embeddings               -- 384-dim pgvector embeddings
sessions                          -- Student sessions per subject
student_responses                 -- Per-question answers + skips

-- Key columns in questions
id               UUID PRIMARY KEY
original_text    TEXT             -- Full question + options
subject          TEXT             -- Physics | Chemistry | Maths | Biology
topic            TEXT             -- e.g. Mechanics, Organic Chemistry
difficulty_level TEXT             -- Beginner | Intermediate | Advanced
difficulty_score FLOAT            -- 0.0 to 1.0
formula_present  BOOLEAN
keyword_density  FLOAT
estimated_time   INTEGER          -- seconds
```

---

## 🛠️ Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account (free tier)
- Groq API key (free tier)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in project root:

```env
DB_HOST=your-supabase-host
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.your-project-ref
DB_PASSWORD=your-password
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
GROQ_MAX_TOKENS=512
GROQ_TEMPERATURE=0.3
```

Start backend:

```bash
uvicorn app.main:app --reload
# Running at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start frontend:

```bash
npm run dev
# Running at http://localhost:3000
```

---

## 🔑 API Reference

### `POST /recommend/`
Returns the next adaptive question for a session.

```json
// Request
{
  "session_id": "uuid",
  "student_id": "uuid",
  "subject": "Physics",
  "topic": "Mechanics"
}

// Response
{
  "session_id": "uuid",
  "recommended_difficulty": "Intermediate",
  "question": {
    "id": "uuid",
    "original_text": "...",
    "subject": "Physics",
    "topic": "Mechanics",
    "difficulty_level": "Intermediate",
    "difficulty_score": 0.42,
    "cosine_distance": 0.22
  }
}
```

### `POST /explain/`
Generates a concept reinforcement explanation using RAG.

```json
// Request
{
  "session_id": "uuid",
  "question_id": "uuid",
  "student_answer": "B",
  "subject": "Physics",
  "difficulty_level": "Intermediate"
}

// Response
{
  "explanation": "The correct answer is Option B...",
  "similar_questions_used": 3,
  "latency_ms": 2942
}
```

### `POST /sessions/start`
Creates a new learning session.

### `POST /sessions/answer`
Records a student response (answer or skip).

---

## 📊 Data Pipeline

The `data_pipeline/` folder contains the offline processing scripts used to build the question bank:

| Script | What It Does |
|---|---|
| `01_clean.py` | Removes duplicates, normalizes text |
| `02_score_difficulty.py` | Assigns 0–1 difficulty scores |
| `03_extract_topics.py` | Extracts subject/topic/subtopic |
| `04_generate_embeddings.py` | Generates 384-dim BAAI/bge embeddings |
| `05_upload_supabase.py` | Bulk uploads to Supabase + pgvector |

**Dataset:** 121,557 JEE/NEET questions across Physics, Chemistry, Maths, Biology

---

## 🚢 Deployment

### Frontend → Vercel
1. Connect GitHub repo to Vercel
2. Set root directory: `frontend`
3. Add environment variables (same as `.env.local`)
4. Deploy

### Backend → Railway
1. Connect GitHub repo to Railway
2. Set root directory: `backend`
3. Add environment variables (same as `.env`)
4. Railway auto-detects Python + `requirements.txt`

---

## 🔮 Roadmap

- [ ] **Phase 8:** HNSW index on pgvector (10x faster retrieval)
- [ ] **Phase 9:** Item Response Theory (IRT) for true adaptive difficulty
- [ ] **Phase 10:** `correct_answer` column via Groq batch extraction
- [ ] **Phase 11:** Student progress dashboard + performance analytics
- [ ] **Phase 12:** Spaced repetition scheduling
- [ ] **Phase 13:** Mobile app (React Native)

---

## 👤 Author

**Yash Parikh**
- GitHub: [@parikhdev](https://github.com/parikhdev)
- Project: Adaptive Learning System for JEE/NEET

---

## 📄 License

MIT License — free to use, modify, and distribute.
