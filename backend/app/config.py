import os
from dotenv import load_dotenv

# Load .env from backend folder (parent of app)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
print("ENV PATH:", env_path)
print("ENV EXISTS:", os.path.exists(env_path))
load_dotenv(env_path)

class Config:
    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "rag-chatbot")
    
    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # YouTube Data API (for follower count fallback)
    YOUTUBE_DATA_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY", "")
    
    # Apify API (for Instagram view count fallback)
    APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")
    
    # SerpAPI (for Instagram follower count)
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
    
    # Optional OpenAI fallback
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Hugging Face (optional, for better rate limits)
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    
    # Embedding
    EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMENSION = 1024
    
    # Chunking (Hierarchical)
    FINE_CHUNK_SIZE_SEC = 30
    FINE_OVERLAP_SEC = 10
    MEDIUM_CHUNK_SIZE_SEC = 120
    MEDIUM_OVERLAP_SEC = 30
    
    # Video sections (pre-computed)
    INTRO_SEC = 15
    OUTRO_SEC = 15
    
config = Config()
