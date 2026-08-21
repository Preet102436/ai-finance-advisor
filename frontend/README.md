# Frontend

React + Vite app for the AI-Powered Personal Finance Advisor.

## Setup

```bash
cp .env.example .env   # adjust VITE_API_BASE_URL if the backend isn't on localhost:8000
npm install
npm run dev
```

The dev server runs on http://localhost:5173. The backend (`backend/api/`, see its
README) must be running for Login/Register to work, and must allow this origin via
CORS (already configured for `http://localhost:5173`).

## Structure

- `src/lib/apiClient.js` - fetch wrapper (base URL, JSON, auth header, error handling)
- `src/lib/auth.js` - register/login/logout, JWT storage (localStorage)
- `src/components/Layout.jsx` - sidebar/nav shell for authenticated pages
- `src/components/ProtectedRoute.jsx` - redirects to `/login` if not authenticated
- `src/pages/` - Login, Register (working), Dashboard, Transactions, Chat, Settings
  (placeholders for later phases)
