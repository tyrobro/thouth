# Thouth — Product Requirements Document

**Version:** 1.2\
**Status:** Active\
**Last Updated:** September 2026

---

## 1. Vision

Thouth is an AI-native personal study intelligence system. Named after Thoth — the Egyptian god of knowledge, writing, and wisdom — and rooted in the word *thought*, Thouth externalises, organises, and amplifies how a student learns.

It is not a chatbot wrapper. It is a living knowledge system with three integrated modules:

- **Knowledge Weaver** — a self-building semantic knowledge graph
- **Cognitive Mirror** — an adaptive mastery profiler and personalised tutor
- **Study Autopilot** — an agentic deadline tracker that reads your university portal so you don't have to

Together they form a single unified platform: one frontend, one backend, three AI brains — accessible on web now, mobile later.

---

## 2. Goals

| Goal | Detail |
| --- | --- |
| Zero cost to run | All infrastructure either free-tier cloud or local |
| Real AI internals | No shallow API wrappers — full RAG pipelines, graph retrieval, context management, agent orchestration |
| Deployed and usable | Live frontend on Vercel, backend served locally via Cloudflare Tunnel |
| Open source stack | Every tool is open source or has a permanently free tier |
| Extensible | Modular architecture — each module is independently swappable |
| Mobile-ready | Web frontend built with shared-logic patterns so Expo wrapping is a config job, not a rewrite |

---

## 3. User Persona

**Primary user:** A single student (you) at a university using the Quanta AWS portal (Google SSO login), studying AI/CS-adjacent subjects, who:

- Takes notes across multiple formats (typed, PDF, web articles, voice)
- Struggles to connect concepts across lectures and subjects
- Loses track of deadlines unless actively managing a calendar
- Wants to be quizzed and tested in a way that adapts to what they actually don't know
- Works primarily in WSL2 on Windows, pushes to GitHub after every feature sprint

---

## 4. System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   FRONTEND (Vercel)                      │
│               Next.js 14 + Tailwind CSS                  │
│          Supabase Auth (JWT + Google OAuth)              │
│     Mobile-ready components (Expo wrap — phase 2)       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / REST + WebSocket
                       │ (via Cloudflare Tunnel — free)
┌──────────────────────▼──────────────────────────────────┐
│              BACKEND (WSL2 — local machine)              │
│                  FastAPI (Python, async)                  │
│                                                          │
│  ┌──────────────┬─────────────────┬──────────────────┐  │
│  │  Knowledge   │    Cognitive    │  Study Autopilot │  │
│  │   Weaver     │     Mirror      │      Agent       │  │
│  │   Router     │     Router      │      Router      │  │
│  └──────┬───────┴────────┬────────┴────────┬─────────┘  │
│         │                │                 │              │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────────┐  │
│  │  LangChain  │  │  LangGraph  │  │   LangGraph     │  │
│  │  Graph RAG  │  │  Mastery    │  │   Scraper +     │  │
│  │  Pipeline   │  │  Agent      │  │   Planner Agent │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────────┘  │
│         │                │                 │              │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────────┐  │
│  │   Neo4j     │  │   Weaviate  │  │   Playwright    │  │
│  │  (local)    │  │  (cloud     │  │   (persistent   │  │
│  │             │  │   free)     │  │    session)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                          │
│   ┌─────────────────────────────────────────────────┐   │
│   │              Ollama (local LLM)                  │   │
│   │  Llama 3.1 8B (reasoning) · Mistral 7B (fast)   │   │
│   │  nomic-embed-text (embeddings)                   │   │
│   │  faster-whisper (voice transcription)            │   │
│   │  Runtime: CPU + 32GB RAM (Arc GPU: stretch goal) │   │
│   └─────────────────────────────────────────────────┘   │
│                                                          │
│         Supabase PostgreSQL + Auth + Storage             │
│         Celery + Redis (background jobs)                 │
│         APScheduler (cron — portal sync)                 │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Tech Stack

### Hardware Context

| Component | Spec | Notes |
| --- | --- | --- |
| CPU | Intel Core Ultra 9 (1st gen) | Primary compute for LLM inference |
| RAM | 32GB | Comfortably runs Llama 3.1 8B (\~10GB), leaves headroom |
| GPU | Intel Arc 140T | SYCL/OpenCL support — Ollama Arc offload is experimental, disabled by default. Revisit post-MVP |
| LLM speed estimate | \~3–5 tok/sec (CPU) | Usable for study sessions; not real-time chat |
| Dev environment | WSL2 + Ubuntu 24.04 | All backend tooling runs here |

### AI / ML Layer

| Component | Tool | Why |
| --- | --- | --- |
| LLM runtime | **Ollama** | Local, free, runs on CPU, Arc support experimental |
| Reasoning model | **Llama 3.1 8B** | Best open-source at its size, strong instruction following |
| Fast model | **Mistral 7B** | Faster inference for classification, planning, short tasks |
| Embeddings | **nomic-embed-text** via Ollama | Free, local, 768-dim, strong semantic similarity |
| Voice transcription | **faster-whisper** (local) | Runs on CPU, faster than original Whisper, no API cost |
| Orchestration | **LangChain + LangGraph** | Industry standard, RAG, agents, graph workflows |
| Graph RAG | **LangChain + Neo4j integration** | Native Graph RAG support built into LangChain |

### Storage Layer

| Component | Tool | Why |
| --- | --- | --- |
| Graph DB | **Neo4j Community Edition** (local) | Free, Cypher queries, LangChain native, runs in WSL2 |
| Vector DB | **Weaviate** (free cloud) | Hybrid search (BM25 + vector), free 14k objects |
| Relational DB | **Supabase PostgreSQL** (free cloud) | User data, sessions, tasks, deadlines |
| File storage | **Supabase Storage** (free 1GB) | Uploaded PDFs, lecture notes |

### Backend

| Component | Tool | Why |
| --- | --- | --- |
| Framework | **FastAPI** | Async, auto-docs, best Python LangChain integration |
| Task queue | **Celery + Redis** (local in WSL2) | Async background jobs — graph updates, scraping |
| Scraping | **Playwright** (headless, persistent session) | Handles Google SSO — session cookies reused after one manual login |
| Scheduling | **APScheduler** | Cron-style portal sync every 6 hours |
| Auth validation | **Supabase JWT** middleware | All FastAPI routes validate JWT |
| Tunneling | **Cloudflare Tunnel** (free) | Exposes WSL2 backend to Vercel frontend securely, no open ports |
| Rate limiting | **Slowapi** | Protects LLM-facing routes |
| Voice input | **faster-whisper** | Audio → text transcription, runs fully local |

### Frontend

| Component | Tool | Why |
| --- | --- | --- |
| Framework | **Next.js 14** (App Router) | Vercel-native, server components |
| Styling | **Tailwind CSS** | Utility-first, fast to build, works in Expo Web too |
| Auth | **Supabase Auth** | Google OAuth, JWT, free |
| Graph viz | **React Flow** | Interactive knowledge graph viewer |
| State | **Zustand** | Lightweight, no boilerplate |
| API client | **TanStack Query** | Caching, background refetch, optimistic updates |
| Realtime | **Supabase Realtime** | Live deadline updates, graph change notifications |
| Voice UI | **Web Audio API + MediaRecorder** | Capture mic input → stream to FastAPI Whisper endpoint |
| Mobile-ready | Component structure follows React Native Web patterns | Enables Expo wrap in phase 2 with minimal rework |

### Dev & CI/CD

| Component | Tool | Why |
| --- | --- | --- |
| Version control | **GitHub** | One sprint = one feature = one PR |
| CI | **GitHub Actions** (free tier) | Runs on every push: lint, type-check, test |
| Frontend deploy | **Vercel** (auto on main merge) | Free, Vercel-native Next.js |
| Backend | Local WSL2 + Cloudflare Tunnel | No cloud cost for compute |
| Secrets | `.env` in WSL2, Vercel env vars for frontend | Never committed to GitHub |

---

## 6. Dev Environment Setup (WSL2)

This section is the starting point before any code is written. Every team member (currently: you) must complete this before Phase 1.

### 6.1 WSL2 + Ubuntu 24.04

```bash
# In PowerShell (admin)
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2

# In Ubuntu shell
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git build-essential python3.12 python3-pip \
  python3-venv nodejs npm redis-server
```

### 6.2 Python environment

```bash
python3 -m venv ~/.venvs/thouth
source ~/.venvs/thouth/bin/activate
pip install fastapi uvicorn langchain langgraph langchain-community \
  langchain-ollama weaviate-client neo4j celery redis apscheduler \
  playwright faster-whisper python-dotenv supabase slowapi pytest
playwright install chromium
```

### 6.3 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull nomic-embed-text
# Verify
ollama list
```

### 6.4 Neo4j Community Edition

```bash
# Add Neo4j repo
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor \
  -o /etc/apt/keyrings/neotechnology.gpg
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] \
  https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update && sudo apt install -y neo4j
sudo systemctl enable neo4j && sudo systemctl start neo4j
# Default: bolt://localhost:7687  user: neo4j  pass: (set on first run)
```

### 6.5 Redis (for Celery)

```bash
sudo systemctl enable redis-server && sudo systemctl start redis-server
redis-cli ping  # should return PONG
```

### 6.6 Cloudflare Tunnel

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/\
cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Authenticate (opens browser)
cloudflared tunnel login

# Create tunnel named "thouth"
cloudflared tunnel create thouth

# Config: ~/.cloudflared/config.yml
# tunnel: <TUNNEL_ID>
# credentials-file: /home/<user>/.cloudflared/<TUNNEL_ID>.json
# ingress:
#   - hostname: api.thouth.dev  (or any free subdomain)
#     service: http://localhost:8000
#   - service: http_status:404

cloudflared tunnel route dns thouth api.thouth.dev
cloudflared tunnel run thouth  # run as service
```

### 6.7 faster-whisper

```bash
pip install faster-whisper
# Model downloads on first use (~150MB for base.en)
# No further setup needed — called directly from FastAPI
```

### 6.8 GitHub Repository Structure

```
thouth/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml      # lint + test on push
│       └── frontend-ci.yml     # type-check + build on push
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── knowledge.py
│   │   │   ├── mastery.py
│   │   │   └── autopilot.py
│   │   ├── agents/
│   │   │   ├── graph_rag.py
│   │   │   ├── mastery_agent.py
│   │   │   └── scraper_agent.py
│   │   ├── pipelines/
│   │   │   ├── ingestion.py
│   │   │   ├── embedding.py
│   │   │   └── voice.py
│   │   ├── db/
│   │   │   ├── neo4j.py
│   │   │   ├── weaviate.py
│   │   │   └── supabase.py
│   │   └── core/
│   │       ├── config.py
│   │       ├── auth.py
│   │       └── context_manager.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/
│   │   ├── dashboard/
│   │   ├── knowledge/
│   │   ├── study/
│   │   ├── tasks/
│   │   └── settings/
│   ├── components/
│   │   ├── shared/             # Mobile-compatible components
│   │   ├── knowledge/
│   │   ├── study/
│   │   └── autopilot/
│   ├── lib/
│   ├── .env.example
│   └── package.json
├── docs/
│   ├── PRD.md                  # This document
│   └── sprints/                # Per-sprint notes
└── README.md
```

### 6.9 GitHub Actions — Backend CI

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest tests/ -v
      - run: cd backend && python -m ruff check app/
```

### 6.10 GitHub Actions — Frontend CI

```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run type-check
      - run: cd frontend && npm run build
```

---

## 7. Sprint Structure & GitHub Workflow

**One sprint = one feature.** Each sprint lives in its own branch, gets a PR, passes CI, then merges to `main`. Vercel auto-deploys on merge.

### Branch naming

```
feature/knowledge-ingestion-pipeline
feature/graph-rag-retrieval
feature/neo4j-entity-extraction
feature/mastery-bloom-classifier
feature/autopilot-playwright-session
feature/voice-whisper-endpoint
```

### Sprint checklist (every feature)

- [ ] Branch created from latest `main`
- [ ] Feature implemented with basic error handling
- [ ] At least one pytest test written
- [ ] `.env.example` updated if new env vars added
- [ ] `docs/sprints/SPRINT-<name>.md` written (what was built, decisions made, what's next)
- [ ] PR opened → CI passes → merge to `main`

---

## 8. Module Specifications

---

### 8.1 Module 1 — Knowledge Weaver

#### Purpose

A self-building semantic knowledge graph. You add content; Thouth extracts concepts, connects them to existing knowledge, and lets you retrieve them with natural language — including via voice.

#### How it works (AI internals)

**Ingestion pipeline:**

1. User submits content via text, PDF upload, URL, or **voice recording**
2. Voice: audio → FastAPI `/voice/transcribe` → faster-whisper → transcript text → continues as text
3. FastAPI → LangChain document loader (handles PDF, URL, plain text)
4. Chunked via RecursiveCharacterTextSplitter (512 tokens, 50 overlap)
5. Each chunk embedded via `nomic-embed-text` (Ollama) → stored in Weaviate
6. Simultaneously: Llama 3.1 8B extracts entities + relationships → structured JSON
7. Entities → Neo4j nodes; relationships → Neo4j edges
8. Deduplication agent: Weaviate semantic search finds similar existing nodes → LLM decides merge or link

**Retrieval pipeline (Graph RAG):**

1. User queries in natural language (text or voice)
2. Query embedded → Weaviate top-k semantic chunks retrieved
3. Entity names extracted → Neo4j 2-hop subgraph fetched via Cypher
4. Subgraph + chunks assembled into context window
5. Llama 3.1 8B generates grounded answer with source citations
6. Related concept suggestions returned alongside answer

#### Features

- Add note (text, PDF, URL, voice)
- Interactive knowledge graph viewer (React Flow)
- Natural language + voice search
- Concept detail panel with connections and review history
- Auto-tagging by subject/topic
- Merge suggestions for duplicate nodes
- Export as JSON or Markdown

#### Data model (Neo4j)

```cypher
(:Concept {id, title, summary, subject, created_at, last_reviewed, mastery_score})
(:Chunk {id, text, embedding_id, source, page})
(:Source {id, type, url_or_filename, added_at})

(:Concept)-[:RELATES_TO {strength, type}]->(:Concept)
(:Concept)-[:CONTAINS]->(:Chunk)
(:Chunk)-[:FROM]->(:Source)
```

---

### 8.2 Module 2 — Cognitive Mirror

#### Purpose

Tracks not just *what* you know but *how deeply* you know it. Adapts study sessions to your actual weak spots using Bloom's taxonomy as a mastery framework. Accepts voice answers.

#### How it works (AI internals)

**Mastery profiling:**

- Every interaction logged to Supabase
- LangGraph agent post-session:
  1. Pulls recent responses for a concept
  2. Classifies against Bloom's 6 levels (Remember → Understand → Apply → Analyse → Evaluate → Create)
  3. Updates mastery score (0–100) on Neo4j concept node
  4. Concepts below threshold (default 60) flagged as weak spots

**Adaptive tutoring:**

- LangGraph planner fetches weak spots → retrieves chunks from Weaviate → plans session
- Questions generated at next Bloom level above current score
- LLM evaluates answers (text or voice-transcribed), explains what was right/wrong with reference to your own notes
- `ConversationSummaryBufferMemory` keeps compressed history → tutor never re-explains known concepts

#### Features

- Mastery dashboard (heatmap by Bloom level + score)
- Adaptive study session with voice answer support
- Weak spot highlights
- Progress charts over time
- Custom quiz builder
- Explanation mode calibrated to current mastery level

#### Data model (Supabase)

```sql
mastery_scores (id, user_id, concept_id, bloom_level INT, score FLOAT, updated_at)
study_sessions (id, user_id, started_at, ended_at, concepts_covered TEXT[])
interactions (id, session_id, concept_id, question TEXT, user_answer TEXT,
              input_mode TEXT,  -- 'text' or 'voice'
              bloom_level_assessed INT, score_delta FLOAT, llm_feedback TEXT, created_at)
```

---

### 8.3 Module 3 — Study Autopilot

#### Purpose

An agentic system that logs into Quanta AWS (via persistent Google SSO session), reads your course pages, extracts deadlines, reasons about your workload cross-referenced with your knowledge gaps and mastery scores, and delivers a prioritised daily plan.

#### How it works (AI internals)

**Google SSO — persistent session approach:**

- On first setup, user manually completes Google login in a visible Playwright browser window
- Playwright saves the authenticated browser context (cookies + local storage) to disk
- All subsequent scraping runs reuse this saved context — no re-authentication
- If session expires, FastAPI returns a `401 SESSION_EXPIRED` signal → frontend prompts user to re-authenticate via the settings page

**Scraping agent (LangGraph):**

- APScheduler triggers every 6 hours
- LangGraph nodes: `LoadSessionNode` → `NavigateCoursesNode` → `ExtractorNode` → `DiffNode` → `StoreNode`
- `ExtractorNode`: raw HTML → Llama 3.1 8B → structured JSON of assignments, deadlines, quiz dates
- `DiffNode`: compares with existing Supabase records → only writes new/changed items
- Celery handles the scraping job asynchronously so FastAPI stays responsive

**Planning agent (LangGraph):**

- Triggers every morning at 8am via APScheduler
- Fetches pending tasks → estimates effort by type → checks Knowledge Weaver for concept gaps → checks Cognitive Mirror for mastery scores → outputs ranked daily plan
- Plan pushed to frontend via Supabase Realtime

#### Features

- Auto-sync every 6 hours (Quanta AWS)
- Task inbox with manual add
- AI-generated prioritised daily plan
- Knowledge gap alerts cross-referenced with upcoming deadlines
- Completion tracking
- Deadline calendar view
- One-time re-auth flow for expired Google sessions

#### Data model (Supabase)

```sql
tasks (id, user_id, title TEXT, course TEXT, type TEXT, due_date TIMESTAMPTZ,
       source_url TEXT, status TEXT, created_at, updated_at)
daily_plans (id, user_id, date DATE, plan_json JSONB, generated_at)
portal_sessions (id, user_id, session_path TEXT, last_valid TIMESTAMPTZ, status TEXT)
-- Note: no plaintext credentials stored; session cookie file path only
```

---

## 9. Voice Input (Cross-Module)

Voice is a first-class input method across all three modules, not an afterthought.

### Pipeline

```
Browser mic (MediaRecorder API)
  → WAV blob streamed to POST /api/v1/voice/transcribe
  → faster-whisper (base.en model, local CPU)
  → transcript text returned
  → routed to whichever module endpoint the user is in
```

### Frontend behaviour

- Mic button present on: note input, search bar, study session answer box
- Recording indicator (animated) while capturing
- Transcript shown inline before submission — user can edit before sending
- Graceful fallback to text input if mic permission denied

### Backend

```python
# POST /api/v1/voice/transcribe
# Accepts: multipart/form-data with audio file
# Returns: { transcript: str, confidence: float, duration: float }
```

---

## 10. Cross-Module AI Features

### 10.1 Unified Context Manager

Every LLM call shares a context manager (`app/core/context_manager.py`) that assembles:

- User's mastery state per concept (Cognitive Mirror)
- Relevant graph subgraph (Knowledge Weaver)
- Upcoming deadlines in next 7 days (Autopilot)

This means: the tutor knows your exam is tomorrow. The graph knows what you haven't studied. The planner knows what you already understand well.

### 10.2 Cross-Module Trigger System

| Trigger | Action |
| --- | --- |
| New task scraped with topic X | Knowledge Weaver checks if concept X exists; if not, flags it for ingestion |
| Mastery score for concept X drops below 60 | Autopilot bumps related tasks up in priority |
| New concept added to graph | Cognitive Mirror schedules a baseline mastery check |
| Exam deadline within 48hrs | Cognitive Mirror enters exam mode — rapid-fire recall questions |
| Voice note ingested | Treated identically to text note post-transcription |

### 10.3 Shared Embedding Pipeline

All three modules share one embedding pipeline (nomic-embed-text via Ollama). Notes, concepts, tasks, and session logs are all embedded, enabling cross-module semantic search: "find everything related to transformers" returns notes, mastery scores, and upcoming tasks in one query.

---

## 11. Security

| Concern | Approach |
| --- | --- |
| Auth | Supabase Auth (JWT + Google OAuth) — all FastAPI routes validate JWT in middleware |
| Row-level security | Supabase RLS — users only ever access their own data |
| Portal session | Playwright session cookie file stored locally in WSL2, path reference in Supabase only |
| No plaintext credentials | Google SSO means no username/password ever stored |
| Backend exposure | Cloudflare Tunnel — no open ports, no public IP, zero-trust |
| CORS | FastAPI CORS middleware — only Vercel domain allowed |
| Rate limiting | Slowapi on all LLM-facing routes |
| Environment secrets | `.env` in WSL2 (gitignored), Vercel env vars for frontend |
| LLM prompt injection | Input sanitisation layer before all LLM calls |
| Audio data | Voice audio is transcribed in-memory and immediately discarded — never persisted |

---

## 12. API Design (FastAPI)

All routes prefixed `/api/v1/` and require Bearer JWT.

### Knowledge Weaver

```
POST   /knowledge/ingest          # Upload note / PDF / URL / voice
GET    /knowledge/graph           # Full graph for React Flow
GET    /knowledge/search?q=       # Graph RAG query
GET    /knowledge/concept/{id}    # Single concept detail
DELETE /knowledge/concept/{id}    # Remove concept
POST   /knowledge/merge           # Merge two concepts
```

### Cognitive Mirror

```
GET    /mastery/dashboard         # All concept mastery scores
POST   /mastery/session/start     # Begin adaptive study session
POST   /mastery/session/respond   # Submit answer (text or voice), get feedback
GET    /mastery/session/{id}      # Session history
GET    /mastery/weakspots         # Concepts below threshold
POST   /mastery/quiz              # Generate custom quiz
```

### Study Autopilot

```
GET    /autopilot/tasks           # All tasks from portal
POST   /autopilot/tasks           # Manually add task
PATCH  /autopilot/tasks/{id}      # Mark complete / update
GET    /autopilot/plan/today      # Today's AI-generated plan
POST   /autopilot/sync            # Trigger manual portal sync
GET    /autopilot/calendar        # All deadlines as calendar events
POST   /autopilot/session/init    # Initiate one-time Playwright Google login
GET    /autopilot/session/status  # Check session validity
```

### Voice

```
POST   /voice/transcribe          # Audio → transcript (faster-whisper)
```

### System

```
GET    /health                    # Health check
GET    /models                    # Available Ollama models
POST   /models/pull               # Pull a new Ollama model
```

---

## 13. Frontend Pages

| Route | Page | Module |
| --- | --- | --- |
| `/` | Dashboard — mastery heatmap, today's plan, recent concepts | All |
| `/knowledge` | Knowledge graph viewer (React Flow) + search | Weaver |
| `/knowledge/add` | Add note / upload / URL / voice ingest | Weaver |
| `/knowledge/[id]` | Concept detail page | Weaver |
| `/study` | Start adaptive study session (text + voice) | Mirror |
| `/study/quiz` | Custom quiz builder | Mirror |
| `/study/progress` | Progress charts over time | Mirror |
| `/tasks` | Task inbox + manual add | Autopilot |
| `/tasks/calendar` | Calendar view of deadlines | Autopilot |
| `/plan` | Today's AI plan (detailed) | Autopilot |
| `/settings` | Portal session setup, model selection, sync config, mic test | System |

---

## 14. Mobile Strategy (Phase 2)

The web frontend is built mobile-ready from day one so the Expo wrap is minimal work.

### Principles applied during web build

- All components use Tailwind responsive classes — no fixed pixel widths
- No web-only APIs used in shared component logic (no `window`, `document` in components)
- Navigation structure maps 1:1 to React Navigation tab structure
- Zustand state and TanStack Query hooks are platform-agnostic

### Phase 2 plan (after web + local deployment is complete)

1. Add `expo` and `react-native-web` to the frontend
2. Create `app.json` Expo config pointing to existing Next.js components
3. Replace Next.js `<Link>` with React Navigation where needed
4. Add native mic permission handling for voice input (replaces Web Audio API)
5. Build and test on Android first (free) via Expo Go
6. iOS via Expo Go (no Apple developer account needed for testing)

---

## 15. Sprint Roadmap

Each row is one sprint, one GitHub branch, one PR.

### Foundation Sprints

| Sprint | Feature | Branch |
| --- | --- | --- |
| F-1 | WSL2 dev environment + all services running | `feature/dev-environment` |
| F-2 | FastAPI skeleton + Supabase auth middleware | `feature/fastapi-auth-skeleton` |
| F-3 | Supabase DB schema + RLS policies | `feature/supabase-schema` |
| F-4 | Next.js scaffold + Supabase Auth + Vercel deploy | `feature/nextjs-auth-scaffold` |
| F-5 | Cloudflare Tunnel configured + health check end-to-end | `feature/cloudflare-tunnel` |
| F-6 | Ollama + Neo4j + Weaviate connected to FastAPI | `feature/ai-services-connection` |

### Knowledge Weaver Sprints

| Sprint | Feature | Branch |
| --- | --- | --- |
| KW-1 | Document ingestion pipeline (text, PDF, URL) | `feature/knowledge-ingestion` |
| KW-2 | Chunking + nomic-embed-text embedding pipeline | `feature/embedding-pipeline` |
| KW-3 | LLM entity + relationship extraction → Neo4j | `feature/entity-extraction` |
| KW-4 | Weaviate vector storage + hybrid search | `feature/weaviate-storage` |
| KW-5 | Graph RAG retrieval pipeline | `feature/graph-rag` |
| KW-6 | Deduplication agent | `feature/dedup-agent` |
| KW-7 | React Flow graph viewer frontend | `feature/graph-viewer-ui` |
| KW-8 | Natural language search UI | `feature/search-ui` |

### Voice Sprints

| Sprint | Feature | Branch |
| --- | --- | --- |
| V-1 | faster-whisper transcription endpoint | `feature/voice-transcribe` |
| V-2 | Browser mic capture + transcript UI | `feature/voice-ui` |

### Cognitive Mirror Sprints

| Sprint | Feature | Branch |
| --- | --- | --- |
| CM-1 | Bloom's taxonomy classifier prompt + LangGraph agent | `feature/bloom-classifier` |
| CM-2 | Mastery scoring + Neo4j score writes | `feature/mastery-scoring` |
| CM-3 | Adaptive session planner (LangGraph) | `feature/session-planner` |
| CM-4 | ConversationSummaryBufferMemory integration | `feature/conversation-memory` |
| CM-5 | Study session UI (Q&A loop + voice answer) | `feature/study-session-ui` |
| CM-6 | Mastery dashboard + progress charts frontend | `feature/mastery-dashboard-ui` |

### Study Autopilot Sprints

| Sprint | Feature | Branch |
| --- | --- | --- |
| AP-1 | Playwright persistent Google SSO session setup | `feature/playwright-google-sso` |
| AP-2 | Quanta AWS scraping + LLM extractor | `feature/quanta-scraper` |
| AP-3 | LangGraph scraping workflow (Diff + Store) | `feature/scraper-langgraph` |
| AP-4 | APScheduler cron jobs + Celery background tasks | `feature/scheduler-celery` |
| AP-5 | Planning agent (LangGraph multi-factor reasoning) | `feature/planning-agent` |
| AP-6 | Task inbox + calendar frontend | `feature/tasks-ui` |
| AP-7 | Supabase Realtime — live plan updates | `feature/realtime-plan` |

### Integration Sprints

| Sprint | Feature | Branch |
| --- | --- | --- |
| I-1 | Unified context manager | `feature/context-manager` |
| I-2 | Cross-module trigger system | `feature/cross-module-triggers` |
| I-3 | Shared embedding pipeline across modules | `feature/shared-embedding` |
| I-4 | Rate limiting + security hardening | `feature/security-hardening` |
| I-5 | End-to-end testing suite | `feature/e2e-tests` |
| I-6 | Frontend design pass | `feature/design-pass` |
| I-7 | Documentation + README | `feature/documentation` |

---

## 16. Constraints Summary

| Constraint | Solution |
| --- | --- |
| Zero cost | Ollama (local), Neo4j Community (local), Weaviate free tier, Supabase free tier, Vercel free, Cloudflare Tunnel free |
| No shallow API calls | Full LangChain RAG, LangGraph agents, Graph RAG, ConversationMemory, faster-whisper |
| Intel Arc GPU | Disabled by default; Ollama runs on CPU with 32GB RAM. Arc SYCL offload is a post-MVP experiment |
| Google SSO portal | Playwright persistent session — one-time manual login, reused across all scraping runs |
| Voice input | faster-whisper local transcription, audio never persisted |
| Mobile later | Web components built with React Native Web patterns; Expo wrap is phase 2 |
| WSL2 dev | All backend services (Neo4j, Redis, Ollama, FastAPI) run in Ubuntu 24.04 WSL2 |
| GitHub CI | GitHub Actions on every push — lint, type-check, test |

---

*Thouth — Think once. Thouth remembers.*

---

## 17. Mobile App (Phase 2 — Expo / React Native)

### Platform & Build

| Decision | Choice | Reason |
| --- | --- | --- |
| Framework | **Expo (React Native)** | Shares logic with Next.js frontend, single codebase |
| Platform | **Android only** (phase 2) | iOS can be added later with zero codebase changes |
| Testing | **Expo Go** | Instant live reload on device, no build step during dev |
| Production builds | **EAS Build free tier** | When ready to distribute an APK |
| Navigation | **React Navigation — Stack only** | Clean push/pop flow, no persistent tab bar |
| Theme | **Dark mode only** | Hardcoded — no system or user toggle needed |
| Language | **English only** | No i18n library needed |

### Shared Logic Architecture

The mobile app is a separate Expo project inside the monorepo but shares the following with the web frontend via a `packages/shared` workspace:

```
thouth/
├── packages/
│   └── shared/
│       ├── api/          # TanStack Query hooks — same endpoints, same logic
│       ├── store/        # Zustand stores — identical state shape
│       ├── types/        # TypeScript types shared across web + mobile
│       └── utils/        # Date formatting, text truncation, etc.
├── frontend/             # Next.js web app
├── mobile/               # Expo React Native app
└── backend/              # FastAPI
```

Nothing in `packages/shared` imports from `react-dom`, `next`, or any web-only API — it is strictly platform-agnostic business logic.

### Mobile-Specific Replacements

| Web component | Mobile equivalent |
| --- | --- |
| React Flow graph viewer | `react-native-svg` + `d3-force` for force-directed graph |
| Web Audio API + MediaRecorder | `expo-av` for mic recording |
| Supabase Realtime (WebSocket) | Same — works in React Native |
| Tailwind CSS | `nativewind` (Tailwind syntax for React Native) |
| Next.js `<Link>` | React Navigation `navigation.navigate()` |
| Browser push (future) | `expo-notifications` |

### Notifications

Both push and in-app alerts are implemented:

**In-app:** A persistent notification bell in the mobile stack header. Unread count badge. Tapping opens a notifications screen showing deadline alerts, weak-spot flags, and daily plan availability.

**Push notifications:** Via `expo-notifications`. The planning agent (APScheduler, 8am daily) calls a FastAPI endpoint that sends a push notification via Expo's free push service — no Firebase setup required for Expo Go testing.

```
POST /api/v1/notifications/push
Body: { expo_push_token: str, title: str, body: str, data: dict }
```

Push token is collected on first app launch and stored in Supabase against the user's profile.

```sql
-- Added to Supabase users profile table
ALTER TABLE profiles ADD COLUMN expo_push_token TEXT;
```

### Mobile Screen Map

All screens are stack-navigated — each screen pushes onto the stack and back arrow pops it.

| Screen | Maps to web route | Notes |
| --- | --- | --- |
| `HomeScreen` | `/` | Dashboard — today's plan, mastery summary, recent concepts |
| `KnowledgeScreen` | `/knowledge` | Searchable concept list (graph view simplified for mobile) |
| `ConceptDetailScreen` | `/knowledge/[id]` | Concept content, connections, mastery score |
| `AddNoteScreen` | `/knowledge/add` | Text input + voice record + file pick |
| `GraphScreen` | `/knowledge` (graph tab) | SVG force-directed graph — tap node to navigate |
| `StudyScreen` | `/study` | Adaptive Q&A session with voice answer |
| `QuizScreen` | `/study/quiz` | Custom quiz flow |
| `ProgressScreen` | `/study/progress` | Mastery charts |
| `TasksScreen` | `/tasks` | Task inbox |
| `CalendarScreen` | `/tasks/calendar` | Deadline calendar |
| `PlanScreen` | `/plan` | Today's AI plan detail |
| `NotificationsScreen` | — | In-app alerts (web has Supabase Realtime banner) |
| `SettingsScreen` | `/settings` | Portal session, sync config, mic test, push token |

### Mobile Sprint Roadmap (Phase 2)

Begins after web + local deployment is complete and stable.

| Sprint | Feature | Branch |
| --- | --- | --- |
| M-1 | Expo project scaffold + React Navigation stack + nativewind | `feature/mobile-scaffold` |
| M-2 | Supabase Auth (Google OAuth) in Expo | `feature/mobile-auth` |
| M-3 | Shared `packages/shared` workspace setup | `feature/shared-package` |
| M-4 | Home + Tasks + Plan screens (read-only first) | `feature/mobile-core-screens` |
| M-5 | Knowledge list + Concept detail screens | `feature/mobile-knowledge-screens` |
| M-6 | SVG graph viewer (react-native-svg + d3-force) | `feature/mobile-graph-viewer` |
| M-7 | expo-av voice recording + Whisper integration | `feature/mobile-voice` |
| M-8 | Study session screen (text + voice answer) | `feature/mobile-study-session` |
| M-9 | expo-notifications push setup + in-app bell | `feature/mobile-notifications` |
| M-10 | Add note screen (text + voice + file) | `feature/mobile-add-note` |
| M-11 | Settings screen + portal session re-auth | `feature/mobile-settings` |
| M-12 | Polish pass — dark theme consistency, loading states, error boundaries | `feature/mobile-polish` |