import time
from typing import List, Dict, Any, Optional, Tuple
from pinecone import Pinecone, ServerlessSpec
from ..config import config

class PineconeClient:
    """
    Pinecone vector database client for storing and retrieving chunk embeddings.
    Uses Pinecone v7+ API (modern syntax).
    
    Index Configuration:
    - Name: rag-chatbot
    - Dimension: 1024 (BGE-large)
    - Metric: cosine
    - Metadata indexed: video_id, chunk_level, start_time, end_time, section_type
    """
    
    _instance = None
    _pc = None
    _index = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PineconeClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pc is None:
            self._initialize()
    
    def _initialize(self):
        """Initialize Pinecone connection"""
        if not config.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not set in environment")
        
        try:
            # Initialize Pinecone v7+
            self._pc = Pinecone(api_key=config.PINECONE_API_KEY)
            
            # Create index if it doesn't exist
            self._create_index_if_not_exists()
            
            # Get index reference
            self._index = self._pc.Index(config.PINECONE_INDEX_NAME)
            
            print(f"Pinecone connected successfully. Index: {config.PINECONE_INDEX_NAME}")
            
        except Exception as e:
            raise Exception(f"Failed to initialize Pinecone: {str(e)}")
    
    def _create_index_if_not_exists(self):
        """Create index if it doesn't exist"""
        index_name = config.PINECONE_INDEX_NAME
        
        # List existing indexes
        existing_indexes = [idx.name for idx in self._pc.list_indexes()]
        
        if index_name not in existing_indexes:
            print(f"Creating Pinecone index: {index_name}")
            
            # Serverless spec for free tier
            self._pc.create_index(
                name=index_name,
                dimension=config.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"  # Free tier region
                )
            )
            
            # Wait for index to be ready
            while not self._pc.describe_index(index_name).status['ready']:
                time.sleep(1)
            print(f"Index {index_name} created successfully")
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]], video_id: str, namespace: str = "default") -> int:
        """
        Upload chunks with embeddings to Pinecone.
        
        Args:
            chunks: List of chunk dicts with 'embedding', 'text', and metadata fields
            video_id: 'A' or 'B'
            namespace: Pinecone namespace (default)
            
        Returns:
            Number of vectors upserted
        """
        if not chunks:
            return 0
        
        vectors = []
        
        for idx, chunk in enumerate(chunks):
            # Generate unique ID
            chunk_id = f"{video_id}_{chunk['chunk_level']}_{chunk['chunk_index']}_{int(chunk['start_time'])}"
            
            # Prepare metadata (Pinecone v7 expects dict)
            metadata = {
                'video_id': video_id,
                'chunk_level': chunk['chunk_level'],
                'chunk_index': chunk['chunk_index'],
                'start_time': chunk['start_time'],
                'end_time': chunk['end_time'],
                'text': chunk['text'][:1000],  # Truncate for metadata limit
                'section_type': chunk.get('section_type', 'unknown'),
                'duration': chunk.get('duration', 0),
                'segment_count': chunk.get('segment_count', 0)
            }
            
            # Add overlap context if present
            if chunk.get('prev_chunk_end') is not None:
                metadata['prev_chunk_end'] = chunk['prev_chunk_end']
            if chunk.get('next_chunk_start') is not None:
                metadata['next_chunk_start'] = chunk['next_chunk_start']
            
            # Create vector object
            vectors.append({
                'id': chunk_id,
                'values': chunk['embedding'],
                'metadata': metadata
            })
        
        # Upsert in batches of 100 (Pinecone free tier limit)
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            self._index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)
            print(f"Upserted {total_upserted}/{len(vectors)} chunks")
        
        print(f"Completed: {total_upserted} chunks stored for video {video_id}")
        return total_upserted
    
    def query(self, query_embedding: List[float], top_k: int = 5, 
              filters: Optional[Dict] = None, namespace: str = "default") -> List[Dict]:
        """
        Query the vector database for similar chunks.
        
        Args:
            query_embedding: Embedding vector of the query
            top_k: Number of results to return
            filters: Metadata filters (e.g., {'video_id': 'A', 'chunk_level': 'fine'})
            namespace: Pinecone namespace
            
        Returns:
            List of matching chunks with metadata and score
        """
        if not self._index:
            raise ValueError("Pinecone index not initialized")
        
        try:
            # Query with filters
            response = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filters or {},
                namespace=namespace
            )
            
            # Format results
            results = []
            for match in response.matches:
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata,
                    'video_id': match.metadata.get('video_id'),
                    'chunk_level': match.metadata.get('chunk_level'),
                    'start_time': match.metadata.get('start_time'),
                    'end_time': match.metadata.get('end_time'),
                    'text': match.metadata.get('text', '')
                })
            
            return results
            
        except Exception as e:
            print(f"Query error: {str(e)}")
            return []
    
    def query_by_time_range(self, video_id: str, start_time: float, end_time: float,
                            chunk_level: Optional[str] = None, top_k: int = 10,
                            namespace: str = "default") -> List[Dict]:
        """
        Query chunks that overlap with a specific time range.
        Uses metadata filtering for efficiency.
        
        Args:
            video_id: 'A' or 'B'
            start_time: Start time in seconds
            end_time: End time in seconds
            chunk_level: Optional filter by 'fine', 'medium', or 'coarse'
            top_k: Number of results
            namespace: Pinecone namespace
            
        Returns:
            List of chunks in the time range (sorted by start_time)
        """
        # Build filter
        filters = {
            'video_id': video_id,
            # Overlap condition: chunk_start < end_time AND chunk_end > start_time
            'start_time': {'$lt': end_time},
            'end_time': {'$gt': start_time}
        }
        
        if chunk_level:
            filters['chunk_level'] = chunk_level
        
        # Since Pinecone doesn't support complex overlap queries directly,
        # we query with a dummy vector (all zeros) to get candidates,
        # then filter results. For production, use a small embedding.
        dummy_embedding = [0.0] * config.EMBEDDING_DIMENSION
        
        try:
            response = self._index.query(
                vector=dummy_embedding,
                top_k=50,  # Get more candidates
                include_metadata=True,
                filter=filters,
                namespace=namespace
            )
            
            # Sort by start_time
            results = []
            for match in response.matches:
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'start_time': match.metadata.get('start_time'),
                    'end_time': match.metadata.get('end_time'),
                    'text': match.metadata.get('text', ''),
                    'chunk_level': match.metadata.get('chunk_level')
                })
            
            # Sort by start_time
            results.sort(key=lambda x: x['start_time'])
            
            # Limit to top_k
            return results[:top_k]
            
        except Exception as e:
            print(f"Time range query error: {str(e)}")
            return []
    
    def get_stats(self, namespace: str = "default") -> Dict:
        """Get index statistics"""
        try:
            stats = self._index.describe_index_stats()
            return {
                'total_vector_count': stats.total_vector_count,
                'namespaces': stats.namespaces,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness
            }
        except Exception as e:
            print(f"Error getting stats: {str(e)}")
            return {}
    
    def delete_video_chunks(self, video_id: str, namespace: str = "default") -> int:
        """
        Delete all chunks for a specific video.
        Useful for re-ingestion.
        """
        try:
            # Query to get all chunks for this video
            dummy_embedding = [0.0] * config.EMBEDDING_DIMENSION
            response = self._index.query(
                vector=dummy_embedding,
                top_k=10000,  # Get all
                include_metadata=True,
                filter={'video_id': video_id},
                namespace=namespace
            )
            
            # Extract IDs
            ids_to_delete = [match.id for match in response.matches]
            
            if ids_to_delete:
                self._index.delete(ids=ids_to_delete, namespace=namespace)
                print(f"Deleted {len(ids_to_delete)} chunks for video {video_id}")
                return len(ids_to_delete)
            
            return 0
            
        except Exception as e:
            print(f"Error deleting video chunks: {str(e)}")
            return 0


# Singleton instance
pinecone_client = PineconeClient()