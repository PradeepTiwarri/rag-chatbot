import os
import requests
from typing import List, Dict, Any, Optional
from ..config import config

class BGEEmbedder:
    """
    BGE-large embedding model loader with singleton pattern.
    Uses Hugging Face Inference API by default if HF_TOKEN is provided
    (saving ~1.3GB of RAM), otherwise lazy-loads local model on CPU/GPU.
    Dimension: 1024
    """
    
    _instance = None
    _model = None
    _use_api = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BGEEmbedder, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # We no longer load the model immediately on init to avoid OOM on startup.
        # Check if we should use HF Inference API
        self.hf_token = getattr(config, 'HF_TOKEN', os.getenv('HF_TOKEN'))
        self.is_render = os.getenv('RENDER', 'false').lower() == 'true'
        
        if self.hf_token:
            print("BGEEmbedder: HF_TOKEN found. Will use Hugging Face Inference API (Serverless).")
            self._use_api = True
        elif self.is_render:
            print("BGEEmbedder: Running on Render but no HF_TOKEN found. Will attempt API without token to save memory.")
            self._use_api = True
        else:
            print("BGEEmbedder: No HF_TOKEN found. Will lazy-load local PyTorch model on first use.")
            self._use_api = False
            
        self.api_url = f"https://api-inference.huggingface.co/models/{config.EMBEDDING_MODEL}"
    
    def _load_local_model(self):
        """Lazy load BGE-large model locally (requires ~1.3GB RAM)"""
        if self._model is not None:
            return
            
        try:
            # Lazy import torch and sentence_transformers so they don't bloat memory if unused
            import torch
            from sentence_transformers import SentenceTransformer
            
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Loading local BGE-large model on {self.device}...")
            
            self._model = SentenceTransformer(
                config.EMBEDDING_MODEL,
                device=self.device
            )
            self._model.eval()
            print(f"BGE-large model loaded successfully. Dimension: {self.get_embedding_dimension()}")
            
        except Exception as e:
            raise Exception(f"Failed to load local BGE-large model: {str(e)}")

    def _query_hf_api(self, payload: Dict) -> Any:
        """Query Hugging Face Inference API"""
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
            
        response = requests.post(self.api_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"HF API Error ({response.status_code}): {response.text}")
            
        return response.json()
    
    def get_embedding_dimension(self) -> int:
        return getattr(config, 'EMBEDDING_DIMENSION', 1024)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return [0.0] * self.get_embedding_dimension()
            
        if self._use_api:
            try:
                # HF API expects dict with inputs
                result = self._query_hf_api({"inputs": text})
                # Result is usually a list of floats for a single text
                if isinstance(result, list) and len(result) > 0 and isinstance(result[0], float):
                    return result
                elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                    return result[0]
                raise Exception("Unexpected API response format")
            except Exception as e:
                print(f"HF API failed: {e}. Falling back to local model if not on Render.")
                if self.is_render:
                    print("Running on Render - cannot fallback to local model (OOM risk). Returning zeros.")
                    return [0.0] * self.get_embedding_dimension()
                self._use_api = False # Permanently fallback
        
        # Local execution
        self._load_local_model()
        try:
            embedding = self._model.encode(text, normalize_embeddings=True, show_progress_bar=False)
            return embedding.tolist()
        except Exception as e:
            print(f"Error embedding text locally: {str(e)}")
            return [0.0] * self.get_embedding_dimension()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
            
        valid_texts = [t if t and t.strip() else " " for t in texts]
        
        if self._use_api:
            try:
                result = self._query_hf_api({"inputs": valid_texts})
                # HF API returns list of lists for multiple inputs
                if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                    return result
                elif isinstance(result, list) and len(result) == len(valid_texts):
                     return result
                raise Exception("Unexpected API response format")
            except Exception as e:
                print(f"HF API batch failed: {e}. Falling back to local model if not on Render.")
                if self.is_render:
                    return [[0.0] * self.get_embedding_dimension() for _ in texts]
                self._use_api = False
                
        # Local execution
        self._load_local_model()
        try:
            embeddings = self._model.encode(
                valid_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"Error embedding batch locally: {str(e)}")
            return [self.embed_text(t) for t in texts]
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return []
        texts = [chunk.get('text', '') for chunk in chunks]
        embeddings = self.embed_texts(texts)
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        return chunks
    
    def embed_chunks_parallel(self, chunks: List[Dict[str, Any]], chunk_level: str) -> List[Dict[str, Any]]:
        if not chunks:
            print(f"No {chunk_level} chunks to embed")
            return []
        print(f"Embedding {len(chunks)} {chunk_level} chunks...")
        embedded_chunks = self.embed_chunks(chunks)
        print(f"Completed {chunk_level} chunks embedding")
        return embedded_chunks

# Singleton instance - import this everywhere
bge_embedder = BGEEmbedder()