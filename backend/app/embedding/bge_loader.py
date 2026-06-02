import torch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import numpy as np
from ..config import config

class BGEEmbedder:
    """
    BGE-large embedding model loader with singleton pattern.
    Uses local model (100% free, MIT licensed, runs on CPU).
    Dimension: 1024
    
    Singleton pattern ensures model loaded once at startup,
    not repeatedly for each embedding request.
    """
    
    # Singleton pattern - ensure only one instance
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BGEEmbedder, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load BGE-large model locally"""
        try:
            # Check if CUDA available (GPU acceleration)
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Loading BGE-large model on {self.device}...")
            
            # Load model - BAAI/bge-large-en-v1.5 
            self._model = SentenceTransformer(
                config.EMBEDDING_MODEL,
                device=self.device
            )
            
            # Set to evaluation mode
            self._model.eval()
            
            print(f"BGE-large model loaded successfully. Dimension: {self.get_embedding_dimension()}")
            
        except Exception as e:
            raise Exception(f"Failed to load BGE-large model: {str(e)}")
    
    def get_embedding_dimension(self) -> int:
        """Return embedding dimension (1024 for BGE-large)"""
        if self._model:
            return self._model.get_embedding_dimension()
        return config.EMBEDDING_DIMENSION
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats (embedding vector)
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.get_embedding_dimension()
        
        try:
            # Normalize embeddings for cosine similarity
            embedding = self._model.encode(
                text,
                normalize_embeddings=True,  # Enables cosine similarity
                show_progress_bar=False
            )
            return embedding.tolist()
        except Exception as e:
            print(f"Error embedding text: {str(e)}")
            return [0.0] * self.get_embedding_dimension()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).
        More efficient than calling embed_text individually.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter empty texts
        valid_texts = [t if t and t.strip() else " " for t in texts]
        
        try:
            embeddings = self._model.encode(
                valid_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32  # Process 32 at a time
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"Error embedding batch: {str(e)}")
            # Fallback to individual embedding
            return [self.embed_text(t) for t in texts]
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of chunk dictionaries.
        Adds 'embedding' field to each chunk.
        
        Args:
            chunks: List of chunk dicts with 'text' field
            
        Returns:
            Same chunks with 'embedding' added
        """
        if not chunks:
            return []
        
        # Extract texts
        texts = [chunk.get('text', '') for chunk in chunks]
        
        # Generate embeddings in batch
        embeddings = self.embed_texts(texts)
        
        # Add embeddings back to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        return chunks
    
    def embed_chunks_parallel(self, chunks: List[Dict[str, Any]], chunk_level: str) -> List[Dict[str, Any]]:
        """
        Embed chunks with level-specific logging.
        
        Args:
            chunks: List of chunk dicts
            chunk_level: 'fine', 'medium', or 'coarse'
            
        Returns:
            Chunks with embeddings
        """
        if not chunks:
            print(f"No {chunk_level} chunks to embed")
            return []
        
        print(f"Embedding {len(chunks)} {chunk_level} chunks...")
        embedded_chunks = self.embed_chunks(chunks)
        print(f"Completed {chunk_level} chunks embedding")
        
        return embedded_chunks


# Singleton instance - import this everywher

bge_embedder = BGEEmbedder()
