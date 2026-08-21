"""Stub router for /chat - not implemented yet.

TODO:
- POST /chat/messages        send a user message, get an assistant reply (RAG-backed),
                              persist both to chat_messages
- GET  /chat/messages         fetch current user's chat history
"""

from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])
