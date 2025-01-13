import logging
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from routers import audio_llm, speaker_profiles
from fastapi import Request
from fastapi.responses import RedirectResponse
from typing import Optional
from fastapi.requests import Request
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Update CORS config for iOS client
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "https://*.ngrok-free.app",
        "https://*.ts.net",  # Allow Tailscale domains
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["*"]
)

# Include routers - remove all prefixes
app.include_router(audio_llm.router, prefix="/api/v1")
app.include_router(speaker_profiles.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
