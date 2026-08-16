# OpsLens: AI Operations Investigator for Campervan Rentals

An AI system that investigates customer incidents (breakdowns, damage disputes, late returns)
by reasoning across contracts, vehicles, payments, and customer history- recommending
auditable, explainable decisions for human approval.

Not a chatbot. Not a document Q&A tool. A multi-agent pipeline that cross-references
structured operational data the way a staff member would, then hands off a clear
recommendation for a human to approve, edit, or reject.

---

## The Problem

When a customer reports an issue like a broken-down van, a disputed deposit deduction, a
late-return request. so staff have to manually check the rental contract, vehicle
availability, payment status, and the customer's history before deciding what to do.
This is slow, inconsistent across staff, and doesn't scale as a rental company grows.

OpsLens automates the *investigation*, not the decision, a human always approves the
final action before anything is executed.

---

## Architecture

<img width="793" height="1162" alt="Untitled-2026-05-19-1620" src="https://github.com/user-attachments/assets/ab79e9cc-71e0-484b-aec6-c547dd714e91" />



The graph is **gated and parallel**, not a flat pipeline:
- The **Contract Agent** checks contract coverage first. If the incident isn't covered,
  the graph short-circuits straight to Synthesis, no wasted calls checking vehicle
  availability or payment status for a claim that was never going to be approved.
- If covered, **Vehicle, Payment, and History agents** run independently (none needs
  another's output) before converging at Synthesis.

---

## How It Works

1. **Customer message comes in** (email/chat) describing an issue
2. **Classifier Agent** determines the incident type and what the customer wants
3. **Gate Agent** checks the rental contract - is this even covered?
4. **Vehicle / Payment / History Agents** run in parallel - availability, payment
   standing, and prior-claim pattern checks
5. **Synthesis Agent** combines everything into one structured decision with reasoning
   and a confidence score
6. **Human approves, edits, or rejects** the recommendation via a staff dashboard
7. **Execution** applies the approved action to the database (replacement, refund,
   extension) and a **follow-up message** is sent to the customer
8. **Every step is logged** to an audit trail - who/what decided what, and why

---

## Tech Stack

| Layer          | Technology                                      |
|----------------|--------------------------------------------------|
| Backend        | FastAPI, SQLAlchemy (2.0), PostgreSQL, Alembic   |
| AI / Agents    | LangGraph, LangChain, Groq (Llama 3.3 70B)       |
| Structured I/O | Pydantic - every agent returns typed output, never free text |
| Async          | Redis-backed background workers, retries         |
| Deployment     | AWS EC2, RDS PostgreSQL, Docker                  |

---

## Key Design Decisions

- **Multi-tenant from the ground up** - every table is scoped by `tenant_id`, so the
  platform can serve multiple rental companies from shared infrastructure without
  data leakage between them.
- **Structured outputs everywhere** - each agent returns a Pydantic-validated object
  not a string to parse. This makes the pipeline reliable and auditable.
- **Gated + parallel graph, not a linear chain** - the contract check is a hard gate
  that can short-circuit the investigation, and independent checks run without
  waiting on each other. This is why the project uses LangGraph instead of a simple
  sequential script.
- **Human-in-the-loop by design** - no financial or operational action executes without
  explicit human approval. The AI's job is to investigate and recommend, not decide.
- **Full audit logging** - every agent output and human decision is recorded, so any
  resolution can be traced back to exactly what data and reasoning produced it.

---

## Evaluation

Tested against a 200+ labeled synthetic dataset:

| Metric                  | Result |
|--------------------------|--------|
| Classification accuracy  | 88%    |
| Decision accuracy        | 78%    |
| Hallucination rate       | 9%     |

---

## Running Locally

```bash
# 1. Clone and install
git clone <repo-url>
cd opslens
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# fill in DATABASE_URL and GROQ_API_KEY

# 3. Set up the database
alembic upgrade head
python -m app.seed    

# 4. Run the API
uvicorn app.main:app --reload
```

---

## Data

All customer, vehicle, and booking data used in this project is synthetically
generated (`app/seed.py`) - no real company or personal data is used.
