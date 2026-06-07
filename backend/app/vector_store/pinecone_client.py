import time
from typing import List, Dict, Any, Optional, Tuple
from pinecone import Pinecone, ServerlessSpec
from ..config import config

class PineconeClient:
    """
    Pinecone vector database client for storing and retrieving chunk embeddings.
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
            self._pc = Pinecone(api_key=config.PINECONE_API_KEY)
            self._create_index_if_not_exists()
            self._index = self._pc.Index(config.PINECONE_INDEX_NAME)
            print(f"Pinecone connected successfully. Index: {config.PINECONE_INDEX_NAME}")
            
        except Exception as e:
            raise Exception(f"Failed to initialize Pinecone: {str(e)}")
    
    def _create_index_if_not_exists(self):
        """Create index if it doesn't exist"""
        index_name = config.PINECONE_INDEX_NAME
        
        existing_indexes = [idx.name for idx in self._pc.list_indexes()]
        
        if index_name not in existing_indexes:
            print(f"Creating Pinecone index: {index_name}")
            
            self._pc.create_index(
                name=index_name,
                dimension=config.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            
            while not self._pc.describe_index(index_name).status['ready']:
                time.sleep(1)
            print(f"Index {index_name} created successfully")
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]], video_id: str, namespace: str = "default") -> int:
        """Upload chunks with embeddings to Pinecone"""
        if not chunks:
            return 0
        
        vectors = []
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{video_id}_{chunk['chunk_level']}_{chunk['chunk_index']}_{int(chunk['start_time'])}"
            
            metadata = {
                'video_id': video_id,
                'chunk_level': chunk['chunk_level'],
                'chunk_index': chunk['chunk_index'],
                'start_time': chunk['start_time'],
                'end_time': chunk['end_time'],
                'text': chunk['text'][:1000],
                'section_type': chunk.get('section_type', 'unknown'),
                'duration': chunk.get('duration', 0),
                'segment_count': chunk.get('segment_count', 0)
            }
            
            if chunk.get('prev_chunk_end') is not None:
                metadata['prev_chunk_end'] = chunk['prev_chunk_end']
            if chunk.get('next_chunk_start') is not None:
                metadata['next_chunk_start'] = chunk['next_chunk_start']
            
            vectors.append({
                'id': chunk_id,
                'values': chunk['embedding'],
                'metadata': metadata
            })
        
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
        """Query the vector database for similar chunks"""
        if not self._index:
            raise ValueError("Pinecone index not initialized")
        
        try:
            # Ensure filters is a dict
            filter_dict = filters or {}
            
            # Log query for debugging
            print(f"Query filters: {filter_dict}")
            
            response = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict,
                namespace=namespace
            )
            
            results = []
            for match in response.matches:
                metadata = match.metadata or {}
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'video_id': metadata.get('video_id', 'unknown'),
                    'chunk_level': metadata.get('chunk_level'),
                    'start_time': metadata.get('start_time'),
                    'end_time': metadata.get('end_time'),
                    'text': metadata.get('text', ''),
                    'metadata': metadata
                })
            
            return results
            
        except Exception as e:
            print(f"Query error: {str(e)}")
            return []
    
    def query_by_video(self, query_embedding: List[float], video_id: str, 
                       top_k: int = 5, namespace: str = "default") -> List[Dict]:
        """Query chunks from a specific video only"""
        return self.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filters={'video_id': video_id},
            namespace=namespace
        )
    
    def query_all_videos(self, query_embedding: List[float], top_k: int = 5, 
                         namespace: str = "default") -> List[Dict]:
        """Query chunks from all videos (no video filter)"""
        return self.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=None,
            namespace=namespace
        )
    
    def query_by_time_range(self, video_id: str, start_time: float, end_time: float,
                            chunk_level: Optional[str] = None, top_k: int = 10,
                            namespace: str = "default") -> List[Dict]:
        """Query chunks that overlap with a specific time range"""
        
        # Build filter - simplified for better compatibility
        filters = {
            'video_id': video_id,
            'start_time': {'$lt': end_time},
            'end_time': {'$gt': start_time}
        }
        
        if chunk_level:
            filters['chunk_level'] = chunk_level
        
        # Use dummy embedding for time-based queries
        dummy_embedding = [0.0] * config.EMBEDDING_DIMENSION
        
        try:
            response = self._index.query(
                vector=dummy_embedding,
                top_k=50,
                include_metadata=True,
                filter=filters,
                namespace=namespace
            )
            
            results = []
            for match in response.matches:
                metadata = match.metadata or {}
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'start_time': metadata.get('start_time'),
                    'end_time': metadata.get('end_time'),
                    'text': metadata.get('text', ''),
                    'chunk_level': metadata.get('chunk_level'),
                    'video_id': metadata.get('video_id')
                })
            
            results.sort(key=lambda x: x['start_time'] or 0)
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
    
    def debug_get_all_chunks(self, video_id: str = None, limit: int = 10, namespace: str = "default") -> List[Dict]:
        """Debug method to fetch chunks directly"""
        try:
            dummy_embedding = [0.0] * config.EMBEDDING_DIMENSION
            filters = {}
            if video_id:
                filters = {'video_id': video_id}
            
            response = self._index.query(
                vector=dummy_embedding,
                top_k=limit,
                include_metadata=True,
                filter=filters or None,
                namespace=namespace
            )
            
            results = []
            for match in response.matches:
                metadata = match.metadata or {}
                results.append({
                    'id': match.id,
                    'video_id': metadata.get('video_id'),
                    'text': metadata.get('text', '')[:100],
                    'start_time': metadata.get('start_time'),
                    'chunk_level': metadata.get('chunk_level')
                })
            return results
        except Exception as e:
            print(f"Debug query error: {e}")
            return []


pinecone_client = PineconeClient()
