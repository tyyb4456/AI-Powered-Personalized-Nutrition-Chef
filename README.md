# **`🥗 Nutrition AI`**

> A full-stack, AI-powered nutrition and meal planning application — personalized recipes, 7-day meal plans, calorie tracking, food image analysis, and an adaptive learning loop that evolves with every user interaction.

---

## ✨ Features

- 🍽️ **AI Recipe Generation** — Personalized recipes powered by Gemini 2.5 Flash + LangGraph agents, with allergen substitution, macro validation, and explainability
- 📅 **7-Day Meal Planning** — Complete weekly plans with grocery lists and optimized meal prep schedules
- 📷 **Food Camera** — Identify food from photos and instantly estimate nutritional content
- 📊 **Analytics & Progress Tracking** — Log meals, track calorie adherence, and generate AI-written weekly progress reports
- 🧠 **Adaptive Learning Loop** — Preferences evolve automatically from user feedback (liked ingredients, cuisines, spice levels, etc.)
- 🔒 **JWT Authentication** — Secure per-user data isolation with protected routes
- 🌗 **Dark / Light Mode** — Fully themed UI with smooth transitions

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI |
| AI / Agents | LangGraph + LangChain |
| LLM | Google Gemini 2.5 Flash |
| Database | PostgreSQL 16 |
| Cache / Rate Limiting | Redis 7 |
| Auth | JWT (python-jose) |
| Migrations | Alembic |
| Testing | Pytest |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 + Vite |
| Routing | React Router v6 |
| Data Fetching | TanStack Query (React Query) |
| Forms | React Hook Form + Zod |
| Styling | Tailwind CSS |
| Icons | Lucide React |
| Notifications | React Hot Toast |

---

## 📁 Project Structure

```
nutrition-ai/
├── api/                        # FastAPI backend
│   ├── agents/                 # LangGraph AI agents
│   │   ├── recipe_agent.py
│   │   ├── weekly_plan_agent.py
│   │   ├── macro_adjustment_agent.py
│   │   ├── substitution_agent.py
│   │   ├── explainability_agent.py
│   │   ├── followup_agent.py
│   │   ├── progress_agent.py
│   │   ├── learning_loop_agent.py
│   │   └── meal_prep_agent.py
│   ├── db/
│   │   ├── models.py
│   │   ├── database.py
│   │   ├── repositories.py
│   │   └── migrations/
│   ├── services/               # Business logic
│   ├── schemas/                # Pydantic schemas
│   ├── cache/                  # Redis client
│   ├── memory/                 # RAG / recipe context store
│   ├── tests/
│   ├── app.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── state.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── project/                    # React frontend
    ├── src/
    │   ├── pages/
    │   │   ├── DashboardPage.jsx
    │   │   ├── GenerateRecipePage.jsx
    │   │   ├── RecipesPage.jsx
    │   │   ├── MealPlanPage.jsx
    │   │   ├── MealLogPage.jsx
    │   │   ├── FoodCameraPage.jsx
    │   │   ├── AnalyticsPage.jsx
    │   │   └── ProfilePage.jsx
    │   ├── components/
    │   ├── api/
    │   ├── store/
    │   └── App.jsx
    ├── package.json
    └── vite.config.js
```

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- A **Google AI API Key** (Gemini 2.5 Flash) — get one at [aistudio.google.com](https://aistudio.google.com)
- Node.js 18+ (for local frontend dev)

---

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/nutrition-ai.git
cd nutrition-ai
```

---

### 2. Backend Setup (Docker)

#### Create the `.env` file inside the `api/` directory:

```env
# Required
SECRET_KEY=your_super_secret_key_here
GOOGLE_API_KEY=your_google_gemini_api_key

# Database (defaults work with Docker Compose)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=nutrition_ai

# Optional
ENV=development
CORS_ORIGINS=http://localhost:5173
ACCESS_TOKEN_EXPIRE_MINUTES=1440
RATE_LIMIT_MAX_CALLS=20
RATE_LIMIT_WINDOW_SEC=3600
LOG_LEVEL=info
```

#### Start all services:

```bash
cd api
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`
- **FastAPI** on port `8000`

#### Run database migrations:

```bash
docker compose exec api alembic upgrade head
```

#### Verify the API is running:

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

---

### 3. Frontend Setup

```bash
cd project
npm install
```

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

The app will be available at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Running Tests

```bash
# Inside the api/ directory
docker compose exec api python -m pytest tests/ -v

# Or locally (requires a running DB)
cd api
pytest tests/ -v
```

Test files:
- `tests/test_phase1_auth.py` — Auth & user profile
- `tests/test_phase4_tracking.py` — Feedback & meal logging

---

## 🔌 API Overview

All endpoints (except `/auth/register` and `/auth/login`) require a `Bearer` JWT in the `Authorization` header.

| Tag | Endpoint | Description |
|---|---|---|
| Auth | `POST /auth/register` | Create a new account |
| Auth | `POST /auth/login` | Get a JWT token |
| Users | `GET /users/me` | Get your profile |
| Users | `PATCH /users/me` | Update your profile |
| Recipes | `POST /recipes/generate` | Generate a personalized recipe |
| Recipes | `POST /recipes/{id}/followup` | Chat-style follow-up on a recipe |
| Meal Plans | `POST /meal-plans/generate` | Generate a 7-day meal plan |
| Meal Plans | `GET /meal-plans/active` | Get your active plan |
| Feedback | `POST /feedback` | Rate and comment on a recipe |
| Meal Logs | `POST /meal-logs` | Log a consumed meal |
| Meal Logs | `GET /meal-logs` | Get your meal history |
| Analytics | `POST /analytics/report` | Generate a weekly AI progress report |
| Analytics | `GET /analytics/preferences` | View your learned preferences |
| Food Image | `POST /food-image/analyze` | Analyze a food photo |

> Full interactive docs: `http://localhost:8000/docs`

---

## ⚙️ AI Agent Pipeline

Recipe generation flows through a LangGraph multi-agent pipeline:

```
Health Goal Agent
      ↓
Recipe Agent  ←──────────────────────────────┐
      ↓                                       │
Substitution Agent                           │
      ↓                                       │
Validation Agent                             │
      ↓                                       │
Macro Adjustment Agent ──── (retry loop) ────┘
      ↓
Explainability Agent
      ↓
Follow-up Agent  (chat interface)
```

Weekly planning uses a separate pipeline:

```
Weekly Plan Agent → Grocery List Agent → Meal Prep Agent
```

Progress & learning:

```
Meal Logs → Progress Agent (LLM report)
Feedback  → Learning Loop Agent (preference updates)
```

---

## 🔒 Rate Limiting

LLM-powered endpoints are rate-limited to **20 calls/hour** per user (configurable via env vars). Check the `X-RateLimit-Remaining` response header to monitor usage.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — LLM backbone
- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [Vite](https://vitejs.dev/) + [React](https://react.dev/) — Frontend stack