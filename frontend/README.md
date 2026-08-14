# Mentora Frontend

A modern web frontend for the Mentora AI tutoring platform, built with:

- **React 18** — UI library
- **Vite** — Build tool
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling
- **React Router** — Client-side routing
- **Zustand** — State management
- **Axios** — HTTP client
- **Recharts** — Charts & analytics
- **Framer Motion** — Animations
- **Socket.IO Client** — Real-time communication

---

## Prerequisites

Install these before setting up the project:

| Requirement      | Version |
|------------------|---------|
| Node.js          | >= 18   |
| npm              | >= 9    |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Abhishek2146/Mentora.git
cd Mentora/frontend

# 2. Install dependencies
npm install

# 3. Configure environment variables
cp .env.example .env.local
# Edit .env.local with your backend API URL
```

---

## Environment Variables

Create a `.env.local` file from `.env.example`:

```
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Mentora
```

- `VITE_API_URL` — The backend API base URL.
- `VITE_APP_NAME` — The application name displayed in the UI.

---

## Development

```bash
npm run dev
```

This starts the Vite dev server at `http://localhost:5173`.

---

## Build

```bash
npm run build
```

This runs the TypeScript compiler and produces an optimized production build in the `dist/` directory.

---

## Available Scripts

| Command             | Description                          |
|---------------------|--------------------------------------|
| `npm run dev`       | Start the development server         |
| `npm run build`     | Build for production                 |
| `npm run preview`   | Preview the production build locally |
| `npm run typecheck` | Run TypeScript type checking         |
| `npm run lint`      | Run ESLint                           |

---

## Docker

The frontend can be run via Docker:

```bash
docker compose up frontend --build
```

The frontend will be available at `http://localhost:8080`.
