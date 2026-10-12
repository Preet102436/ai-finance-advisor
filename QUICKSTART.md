# Try it on your own computer

This runs the whole app - database, backend, and frontend - with one command,
using Docker. You don't need Python, Node.js, or PostgreSQL installed on your
machine at all, just Docker.

## 1. Install Docker Desktop

Download it from https://www.docker.com/products/docker-desktop/ (free for
personal use). Install it, then open it once so it's running in the
background - you'll see a whale icon in your system tray / menu bar when
it's ready.

## 2. Get the project folder

Copy or clone the whole `ai-finance-advisor` folder onto your computer.

> If you're already running this app the "normal" way (your own backend/
> frontend servers in PowerShell), stop those first - Ctrl+C in each window.
> Docker uses the same ports (8000 and 5173) and they'll clash otherwise.

## 3. Start everything

Open a terminal in the `ai-finance-advisor` folder (the one with
`docker-compose.yml` in it) and run:

    docker compose up --build

The first run takes a few minutes - it's downloading and building the
database, backend, and frontend. Leave this terminal window open while
you're using the app; closing it stops everything.

## 4. Open the app

Once the logs settle down (you'll see the frontend mention
`localhost:5173`), open this in your browser:

    http://localhost:5173

Click Register, create an account, and try it out. Your account and data
live in a database on your own computer only - nobody else can see them.

## Stopping it

Press `Ctrl+C` in that terminal, or run `docker compose down` from the
project folder in another terminal. Your account and data are kept for
next time.

To wipe everything and start completely fresh (new empty database), run
`docker compose down -v` instead.

## Good to know

- The AI chat works immediately with no setup - it uses the app's own
  built-in reasoning over your data. If you happen to have an OpenAI API
  key and want LLM-written replies too, set it before starting:
  `$env:OPENAI_API_KEY="sk-..."` (PowerShell) or `export OPENAI_API_KEY=sk-...`
  (Mac/Linux terminal), then run `docker compose up --build`.
- Receipt photo upload (OCR) works out of the box too - the text-recognition
  engine is already included in the Docker image.
- This setup is for trying the app out locally, not for hosting it publicly -
  the login secret and database password are shared placeholders, not
  private ones.
