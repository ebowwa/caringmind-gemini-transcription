import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import audio_llm

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS with specific ngrok domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "https://*.ngrok-free.app",
        "*"  # Be cautious with this in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers with tags
app.include_router(
    audio_llm.router,
    prefix="/api/v1",
    tags=["audio-processing"]
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
