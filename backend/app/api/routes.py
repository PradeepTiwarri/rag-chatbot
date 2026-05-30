from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json

from ..config import config
from ..tools import store_video_metadata
from ..ingestion.video_extractor import VideoExtractor, InstagramExtractor
from ..ingestion.transcript_fetcher import TranscriptFetcher
from ..chunking import hierarchical_chunker
from ..embedding import bge_embedder
from ..vector_store import pinecone_client

router = APIRouter()

# Session storage
session_memory: Dict[str, List[Dict]] = {}
_rag_agent = None

def get_agent():
    """Lazy import to avoid circular imports"""
    global _rag_agent
    if _rag_agent is None:
        from ..agent import rag_agent
        _rag_agent = rag_agent
    return _rag_agent

class ChatRequest(BaseModel):
    question: str
    session_id: str
    video_ids: List[str] = ['A', 'B']

class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str
    video_id_a: str = 'A'
    video_id_b: str = 'B'

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    
    async def generate():
        try:
            if request.session_id not in session_memory:
                session_memory[request.session_id] = []
            
            agent = get_agent()
            
            result = agent.invoke(
                question=request.question,
                session_id=request.session_id,
                video_ids=request.video_ids
            )
            
            if result.get('citations'):
                yield json.dumps({
                    'type': 'citations',
                    'data': result['citations']
                }) + '\n'
            
            answer = result.get('answer', 'No answer generated.')
            
            yield json.dumps({
                'type': 'start',
                'data': None
            }) + '\n'
            
            for char in answer:
                yield json.dumps({
                    'type': 'token',
                    'data': char
                }) + '\n'
                await asyncio.sleep(0.005)
            
            session_memory[request.session_id].append({
                'question': request.question,
                'answer': answer
            })
            
            yield json.dumps({
                'type': 'end',
                'data': None
            }) + '\n'
            
        except Exception as e:
            yield json.dumps({
                'type': 'error',
                'data': str(e)
            }) + '\n'
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@router.post("/ingest")
async def ingest_videos(request: IngestRequest):
    """Ingest YouTube and Instagram videos"""
    
    results = {}
    
    # Process YouTube (Video A) - WITH YouTube API fallback
    try:
        # Initialize with YouTube API key for fallback
        youtube_extractor = VideoExtractor(youtube_api_key=config.YOUTUBE_DATA_API_KEY)
        youtube_metadata = youtube_extractor.extract_metadata(request.youtube_url, "youtube")
        
        # Enrich with API follower count if needed
        youtube_metadata = youtube_extractor.enrich_with_api_follower_count(youtube_metadata)
        
        youtube_metadata['video_id'] = request.video_id_a
        
        transcript_fetcher = TranscriptFetcher()
        youtube_segments = transcript_fetcher.fetch_youtube_transcript(request.youtube_url)
        
        duration = youtube_metadata['duration_seconds']
        
        chunks = hierarchical_chunker.chunk_video(
            youtube_segments, duration, request.video_id_a
        )
        
        for level in ['fine', 'medium', 'coarse']:
            level_chunks = chunks[level]
            if level_chunks:
                embedded_chunks = bge_embedder.embed_chunks_parallel(level_chunks, level)
                pinecone_client.upsert_chunks(embedded_chunks, request.video_id_a)
        
        store_video_metadata(request.video_id_a, youtube_metadata)
        
        results[request.video_id_a] = {
            'status': 'success',
            'metadata': {
                'creator': youtube_metadata['creator'],
                'follower_count': youtube_metadata['follower_count'],
                'views': youtube_metadata['views'],
                'likes': youtube_metadata['likes'],
                'engagement_rate': youtube_metadata['engagement_rate']
            },
            'chunk_counts': {
                'fine': len(chunks['fine']),
                'medium': len(chunks['medium']),
                'coarse': len(chunks['coarse'])
            }
        }
        
    except Exception as e:
        results[request.video_id_a] = {'status': 'error', 'error': str(e)}
    
    # Process Instagram (Video B) - No YouTube API needed
    try:
        instagram_extractor = InstagramExtractor()
        instagram_metadata = instagram_extractor.extract_metadata(request.instagram_url, "instagram")
        instagram_metadata['video_id'] = request.video_id_b
        
        transcript_fetcher = TranscriptFetcher()
        instagram_segments = transcript_fetcher.fetch_instagram_transcript(request.instagram_url)
        
        duration = instagram_metadata['duration_seconds']
        
        chunks = hierarchical_chunker.chunk_video(
            instagram_segments, duration, request.video_id_b
        )
        
        for level in ['fine', 'medium', 'coarse']:
            level_chunks = chunks[level]
            if level_chunks:
                embedded_chunks = bge_embedder.embed_chunks_parallel(level_chunks, level)
                pinecone_client.upsert_chunks(embedded_chunks, request.video_id_b)
        
        store_video_metadata(request.video_id_b, instagram_metadata)
        
        results[request.video_id_b] = {
            'status': 'success',
            'metadata': {
                'creator': instagram_metadata['creator'],
                'follower_count': instagram_metadata['follower_count'],
                'views': instagram_metadata['views'],
                'likes': instagram_metadata['likes'],
                'engagement_rate': instagram_metadata['engagement_rate']
            },
            'chunk_counts': {
                'fine': len(chunks['fine']),
                'medium': len(chunks['medium']),
                'coarse': len(chunks['coarse'])
            }
        }
        
    except Exception as e:
        results[request.video_id_b] = {'status': 'error', 'error': str(e)}
    
    return results

@router.get("/video/{video_id}/metadata")
async def get_video_metadata_endpoint(video_id: str):
    from ..tools import get_video_metadata
    metadata = get_video_metadata([video_id])
    
    if video_id not in metadata:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    
    return metadata[video_id]

@router.get("/stats")
async def get_stats():
    return pinecone_client.get_stats()

@router.get("/health")
async def health_check():
    return {'status': 'healthy', 'service': 'RAG Chatbot'}