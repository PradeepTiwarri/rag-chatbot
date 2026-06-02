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
        """
        Upload chunks with embeddings to Pinecone.
        
        Args:
            chunks: List of chunk dicts with 'embedding', 'text', and metadata fields
            video_id: 'A' or 'B'
            namespace: Pinecone namespace (default)
            
        Returns:
            Number of vectors upserted
        """
        print(f"\n=== UPSERTING CHUNKS FOR VIDEO {video_id} ===")
        print(f"Total chunks received: {len(chunks)}")
        
        if not chunks:
            print(f"No chunks to upsert for video {video_id}")
            return 0
        
        # Count by level
        level_counts = {}
        for chunk in chunks:
            level = chunk.get('chunk_level', 'unknown')
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print(f"Chunk breakdown: {level_counts}")
        
        for chunk in chunks[:5]:
            print(f"  - {chunk['chunk_level']} chunk {chunk['chunk_index']}: {chunk['start_time']:.1f}-{chunk['end_time']:.1f}s")
        
        if len(chunks) > 5:
            print(f"  ... and {len(chunks) - 5} more chunks")
        
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
        """
        Query the vector database for similar chunks.
        """
        if not self._index:
            raise ValueError("Pinecone index not initialized")
        
        try:
            response = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filters or {},
                namespace=namespace
            )
            
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
        """
        filters = {
            'video_id': video_id,
            'start_time': {'$lt': end_time},
            'end_time': {'$gt': start_time}
        }
        
        if chunk_level:
            filters['chunk_level'] = chunk_level
        
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
                results.append({
                    'id': match.id,
                    'score': match.score,
                    'start_time': match.metadata.get('start_time'),
                    'end_time': match.metadata.get('end_time'),
                    'text': match.metadata.get('text', ''),
                    'chunk_level': match.metadata.get('chunk_level')
                })
            
            results.sort(key=lambda x: x['start_time'])
            
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
        """
        try:
            dummy_embedding = [0.0] * config.EMBEDDING_DIMENSION
            response = self._index.query(
                vector=dummy_embedding,
                top_k=10000,
                include_metadata=True,
                filter={'video_id': video_id},
                namespace=namespace
            )
            
            ids_to_delete = [match.id for match in response.matches]
            
            if ids_to_delete:
                self._index.delete(ids=ids_to_delete, namespace=namespace)
                print(f"Deleted {len(ids_to_delete)} chunks for video {video_id}")
                return len(ids_to_delete)
            
            return 0
            
        except Exception as e:
            print(f"Error deleting video chunks: {str(e)}")
            return 0


pinecone_client = PineconeClient()
