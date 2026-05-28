# Verid-iq — Product Feature Document

> AI-Powered Test Intelligence | by Network Logic Limited

---

## 1. Product Overview

Verid-iq is an AI-assisted test artefact generation tool for software testers and QA professionals. It removes the repetitive drafting work from a tester's workflow — paste a user story or acceptance criteria, choose what to generate, and receive a professional first draft in seconds.

The tester always reviews, refines, and approves. Verid-iq accelerates expertise — it never replaces it.

**Tagline:** _AI drafts. You review. Your expertise, accelerated._

---

## 2. Core Value Proposition

| Problem | Verid-iq Solution |
|---|---|
| Writing test cases from scratch is slow and repetitive | Generate a structured first draft in seconds |
| Inconsistent test artefact quality across the team | AI applies professional testing standards every time |
| Testers context-switch between Jira and test tools | Generate directly inside Jira (via plugin) |
| Test documentation piles up before being written | Low friction drafting removes the procrastination barrier |

---

## 3. Generation Types

Verid-iq supports 8 professional test artefact types:

| # | Type | Icon | Description |
|---|---|---|---|
| 1 | **Test Cases** | ✅ | Step-by-step positive path test cases with preconditions, steps, and expected results |
| 2 | **BDD Scenarios** | 🥒 | Gherkin-format Given/When/Then scenarios for behaviour-driven development |
| 3 | **Negative Test Cases** | ❌ | Edge cases, error paths, boundary conditions, and failure scenarios |
| 4 | **Test Plan Summary** | 📋 | High-level test strategy including scope, approach, risks, and entry/exit criteria |
| 5 | **Defect Report** | 🐛 | Structured defect report with severity, steps to reproduce, actual vs expected results |
| 6 | **Exploratory Charter** | 🔍 | Mission-based exploratory testing charter with focus areas and heuristics |
| 7 | **Acceptance Criteria Review** | 🔎 | Analysis of AC completeness, ambiguity, and testability gaps |
| 8 | **Regression Impact Analysis** | 🔄 | Identifies areas of risk and regression scope from a described change |

### Batch Generation
Types 1, 2, 3, and 6 support quantity selection (1–20 artefacts per generation).

---

## 4. The 3-Layer Intelligence Engine

Verid-iq uses a tiered resolution system to optimise quality vs cost:

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — User Context (0 credits)                  │
│  "Has this user generated something similar before?" │
│  Confidence threshold: >0.75                          │
│  Source: user's own generation history               │
└────────────────────┬────────────────────────────────┘
                     │ miss
┌────────────────────▼────────────────────────────────┐
│  Layer 2 — Platform Knowledge (1 credit)             │
│  "Does the platform knowledge base have this?"       │
│  Confidence threshold: >0.65                          │
│  Source: curated testing knowledge volumes           │
└────────────────────┬────────────────────────────────┘
                     │ miss
┌────────────────────▼────────────────────────────────┐
│  Layer 3 — Full AI Generation (3–10 credits)         │
│  "Generate from scratch using Anthropic Claude"      │
│  Source: Claude claude-sonnet model + knowledge ctx  │
└─────────────────────────────────────────────────────┘
```

---

## 5. Credit System

### Credit Costs per Generation

| Layer | Cost | Trigger |
|---|---|---|
| Layer 1 (reuse) | 0 credits | High-confidence match in user history |
| Layer 2 (platform knowledge) | 1 credit | Match in platform knowledge base |
| Layer 3 — Simple types | 3 credits | Defect Report, AC Review, Exploratory Charter, Regression Impact |
| Layer 3 — Standard types | 4 credits | Test Cases, BDD Scenarios, Negative Test Cases |
| Layer 3 — Complex types | 6 credits | Test Plan Summary |
| Batch premium | +2 credits | Per additional artefact beyond 1 |

### Credit Packs (Pricing)

| Pack | Credits | Price | Per Credit |
|---|---|---|---|
| Small | 100 | £5 | 5p |
| Medium | 500 | £20 | 4p |
| Large | 2,000 | £65 | 3.25p |

### Welcome Credits
New users receive **50 free credits** on registration.

### Team Credits
Teams share a pooled credit balance. Team owners can top up on behalf of the team.

---

## 6. User Accounts & Authentication

### Registration
- Email + password registration
- Email verification required before full access
- LinkedIn OAuth (OpenID Connect) as alternative sign-in

### Security
- Bcrypt password hashing
- JWT access tokens (24-hour expiry)
- JWT refresh tokens (30-day expiry)
- TOTP-based Two-Factor Authentication (2FA) — optional, user-configurable
- Session management — view and revoke active sessions
- Password reset via email

---

## 7. Team Features

- Create a team with a name and optional description
- Invite members by email
- Role-based access: `owner`, `admin`, `member`
- Shared credit pool across team members
- Remove members / leave team
- Team owner can transfer ownership

---

## 8. Jira Integration

Verid-iq is designed as a **Jira Connect Plugin** (Atlassian Marketplace):
- Generates test artefacts directly from a Jira issue panel
- Pre-populates input from issue summary, description, and acceptance criteria
- Results surfaced within the issue view — no context switching
- Listed on the SmartBear/Xray marketplace

---

## 9. Knowledge Volumes

Verid-iq loads curated markdown knowledge volumes at startup. These inform AI generation with professional testing domain knowledge:

- Applied automatically in Layer 2 and as context in Layer 3
- Organised into 6 domain volumes
- Loaded from `knowledge_volumes/` directory
- Matched to generation type and user input using relevance scoring

---

## 10. Rate Limiting

- Default: 5 generations per day per IP (unauthenticated)
- Configurable via `RATE_LIMIT_PER_DAY` environment variable
- Enforced via `slowapi` middleware

---

## 11. Pages & Navigation

| Route | Page |
|---|---|
| `/` | Main generation interface |
| `/landing` | Marketing landing page |
| `/login` | Login |
| `/register` | Registration |
| `/dashboard` | User dashboard |
| `/profile` | Profile settings |
| `/credits` | Credit balance and top-up |
| `/security` | 2FA setup and session management |
| `/terms` | Terms of service |
| `/privacy` | Privacy policy |

---

## 12. Deployment

- Hosted on **Railway** (production)
- Domain: `veridiq.networklogic.uk`
- Docker containerised
- PostgreSQL database (Railway-managed)
- Environment variables injected by Railway at runtime
