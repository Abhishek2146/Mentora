# Mentora AI Learning Companion

AI-powered personalized learning platform with a FastAPI backend and Vite + React frontend.

## Project Structure

```
Mentora/
├── backend/              # FastAPI backend
│   ├── app/              # Application code (API routes, models, schemas, services)
│   ├── requirements.txt  # Python dependencies
│   └── .env              # Backend environment variables
├── frontend/             # Vite + React frontend
│   ├── src/              # Source code (pages, components, hooks, services)
│   ├── package.json      # Node dependencies
│   ├── .env.example      # Frontend environment variables
│   └── README.md         # Frontend-specific docs
├── docker/               # Dockerfiles
│   ├── frontend.Dockerfile
│   ├── backend.Dockerfile
│   └── nginx.conf
├── docker-compose.yml    # Multi-service orchestration
├── .env.example          # Root environment variables (for Docker)
└── README.md             # This file
```

---

## Prerequisites

| Tool      | Version  |
|-----------|----------|
| Node.js   | >= 18    |
| npm       | >= 9     |
| Python    | >= 3.12  |
| Docker    | >= 24    |

---

## Quick Start (Docker)

```bash
# 1. Clone and enter the repo
git clone https://github.com/Abhishek2146/Mentora.git
cd Mentora

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your API keys and configuration
# (set OPENAI_API_KEY, DATABASE_URL, etc.)

# 4. Build and start all services
docker compose up --build

# Services will be available at:
# - Frontend:  http://localhost:8080
# - Backend API: http://localhost:8000
# - API Docs:    http://localhost:8000/api/v1/docs
```

---

## Local Development (Without Docker)

### Backend

```bash
# 1. Create and activate a virtual environment
python -m venv backend/venv
source backend/venv/bin       # Linux/macOS
backend\venv\Scripts\activate # Windows

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

See [frontend/README.md](frontend/README.md) for detailed instructions.

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env.local
# Edit .env.local (set VITE_API_URL=http://localhost:8000)

# 3. Start the development server
npm run dev

# Frontend available at http://localhost:5173
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable             | Description                     | Default                          |
|----------------------|---------------------------------|----------------------------------|
| `DATABASE_URL`       | PostgreSQL connection string    | `postgresql+asyncpg://mentora:mentora123@postgres:5432/mentora` |
| `REDIS_URL`          | Redis connection string         | `redis://redis:6379/0`           |
| `OPENAI_API_KEY`     | OpenAI API key                  | (empty)                          |
| `SECRET_KEY`         | JWT secret key                  | `supersecretkeychangeinproduction`|
| `ALLOWED_ORIGINS`    | CORS allowed origins            | `http://localhost:5173`          |

---

## Scripts

```bash
# Full stack with Docker
docker compose up --build

# Frontend only
cd frontend && npm run dev

# Backend only
cd backend && uvicorn app.main:app --reload

# Run tests
cd backend && pytest
```
