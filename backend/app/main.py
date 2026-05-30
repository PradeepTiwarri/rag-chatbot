from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import config
# Import agent when needed (lazy import to avoid circular)
# We'll import inside the endpoint instead

app = FastAPI(
    title="RAG Chatbot API",
    description="Video Analysis RAG Chatbot with LangGraph",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "RAG Chatbot API",
        "endpoints": [
            "POST /api/chat/stream - Streaming chat",
            "POST /api/ingest - Ingest videos",
            "GET /api/video/{video_id}/metadata - Get video metadata",
            "GET /api/stats - Pinecone statistics",
            "GET /api/health - Health check"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )