# Frontend

React + Vite app for the AI-Powered Personal Finance Advisor.

## Setup

```bash
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and proxies `/api/*` to the backend
on http://localhost:8000 (see `vite.config.js`), so the backend (`backend/api/`)
must be running for Login/Register to work. To call a backend elsewhere, copy
`.env.example` to `.env` and set `VITE_API_BASE_URL`.

## Structure

- `src/lib/apiClient.js` - fetch wrapper (base URL, JSON, auth header, error handling)
- `src/lib/auth.js` - register/login/logout, JWT storage (localStorage)
- `src/components/Layout.jsx` - sidebar/nav shell for authenticated pages
- `src/components/ProtectedRoute.jsx` - redirects to `/login` if not authenticated
- `src/pages/` - Login, Register, Dashboard, Transactions, Chat, AI Insights,
  Profile, Settings
- `src/components/` - shared UI (top bar, summary cards, savings suggestions, etc.)
