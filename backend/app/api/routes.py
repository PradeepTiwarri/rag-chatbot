from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import re
import os
import uuid
import threading

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
ingestion_tasks: Dict[str, Dict[str, Any]] = {}
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

def create_manual_chunks(segments: List[Dict], duration: float, video_id: str) -> Dict[str, List[Dict]]:
    """
    Create manual chunks for fine, medium, and coarse levels.
    """
    print(f"MANUAL_CHUNKS: Starting for video {video_id}")
    print(f"MANUAL_CHUNKS: Segments: {len(segments)}, Duration: {duration}")
    
    chunks = {'fine': [], 'medium': [], 'coarse': []}
    
    if not segments:
        print("MANUAL_CHUNKS: No segments")
        return chunks
    
    full_text = ' '.join([seg.get('text', '') for seg in segments])
    text_length = len(full_text)
    print(f"MANUAL_CHUNKS: Text length: {text_length}")
    
    if text_length == 0:
        print("MANUAL_CHUNKS: Empty text")
        return chunks
    
    if duration <= 0:
        duration = max(60, text_length / 10)
        print(f"MANUAL_CHUNKS: Estimated duration: {duration}")
    
    # Create fine chunks (500 chars)
    fine_chunk_size = 500
    for i in range(0, text_length, fine_chunk_size):
        chunk_text = full_text[i:i+fine_chunk_size]
        if chunk_text.strip():
            start_pct = i / text_length
            end_pct = (i + len(chunk_text)) / text_length
            estimated_start = start_pct * duration
            estimated_end = end_pct * duration
            
            chunks['fine'].append({
                'video_id': video_id,
                'chunk_level': 'fine',
                'chunk_index': len(chunks['fine']),
                'start_time': estimated_start,
                'end_time': estimated_end,
                'text': chunk_text,
                'duration': estimated_end - estimated_start,
                'segment_count': 1,
                'section_type': 'body',
            })
    
    # Create medium chunks (1500 chars)
    medium_chunk_size = 1500
    for i in range(0, text_length, medium_chunk_size):
        chunk_text = full_text[i:i+medium_chunk_size]
        if chunk_text.strip():
            start_pct = i / text_length
            end_pct = (i + len(chunk_text)) / text_length
            estimated_start = start_pct * duration
            estimated_end = end_pct * duration
            
            chunks['medium'].append({
                'video_id': video_id,
                'chunk_level': 'medium',
                'chunk_index': len(chunks['medium']),
                'start_time': estimated_start,
                'end_time': estimated_end,
                'text': chunk_text,
                'duration': estimated_end - estimated_start,
                'segment_count': 1,
                'section_type': 'body',
            })
    
    # Create coarse chunk
    chunks['coarse'].append({
        'video_id': video_id,
        'chunk_level': 'coarse',
        'chunk_index': 0,
        'start_time': 0.0,
        'end_time': duration,
        'text': full_text,
        'duration': duration,
        'segment_count': len(segments),
        'section_type': 'full',
    })
    
    print(f"MANUAL_CHUNKS: Created fine:{len(chunks['fine'])}, medium:{len(chunks['medium'])}, coarse:{len(chunks['coarse'])}")
    return chunks

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
    """Start async ingestion of YouTube and Instagram videos. Returns a task_id for polling."""
    
    task_id = str(uuid.uuid4())[:8]
    ingestion_tasks[task_id] = {
        "status": "processing",
        "step": "starting",
        "results": None,
    }
    
    # Run heavy ingestion work in a background thread
    thread = threading.Thread(
        target=_run_ingestion,
        args=(task_id, request.youtube_url, request.instagram_url,
              request.video_id_a, request.video_id_b),
        daemon=True,
    )
    thread.start()
    
    return {"task_id": task_id}


@router.get("/ingest/status/{task_id}")
async def ingest_status(task_id: str):
    """Poll the status of an ingestion task."""
    task = ingestion_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _run_ingestion(task_id: str, youtube_url: str, instagram_url: str,
                   video_id_a: str, video_id_b: str):
    """Background worker that performs the actual ingestion."""
    
    task = ingestion_tasks[task_id]
    results = {}
    
    # ── Process YouTube (Video A) ──
    try:
        task["step"] = "youtube_transcript"
        print("\n========== YOUTUBE ==========")
        print(f"URL: {youtube_url}")
        
        youtube_extractor = VideoExtractor(youtube_api_key=config.YOUTUBE_DATA_API_KEY)
        youtube_metadata = youtube_extractor.extract_metadata(youtube_url, "youtube")
        youtube_metadata = youtube_extractor.enrich_with_api_follower_count(youtube_metadata)
        youtube_metadata['video_id'] = video_id_a
        
        transcript_fetcher = TranscriptFetcher()
        youtube_segments = transcript_fetcher.fetch_youtube_transcript(youtube_url)
        duration = youtube_metadata['duration_seconds']
        
        print(f"YOUTUBE: {len(youtube_segments)} segments, duration={duration}s")
        
        # Use manual chunks
        task["step"] = "youtube_embeddings"
        chunks = create_manual_chunks(youtube_segments, duration, video_id_a)
        
        for level in ['fine', 'medium', 'coarse']:
            level_chunks = chunks[level]
            if level_chunks:
                print(f"YOUTUBE: Embedding {len(level_chunks)} {level} chunks...")
                for chunk in level_chunks:
                    chunk['embedding'] = bge_embedder.embed_text(chunk['text'])
                pinecone_client.upsert_chunks(level_chunks, video_id_a)
        
        store_video_metadata(video_id_a, youtube_metadata)
        
        results["A"] = {
            'status': 'success',
            'metadata': youtube_metadata,
            'chunk_counts': {k: len(v) for k, v in chunks.items()}
        }
        
    except Exception as e:
        print(f"YouTube error: {e}")
        results["A"] = {
            'status': 'error',
            'error': str(e)
        }
    
    # ── Process Instagram (Video B) ──
    try:
        task["step"] = "instagram_transcript"
        print("\n========== INSTAGRAM ==========")
        print(f"URL: {instagram_url}")
        
        transcript_fetcher = TranscriptFetcher()
        
        # Step 1: Always try Playwright first for engagement data
        playwright_data = None
        try:
            from ..ingestion.instagram_playwright import InstagramPlaywrightExtractor
            pw = InstagramPlaywrightExtractor()
            playwright_data = pw.extract(instagram_url)
            print(f"Playwright data: creator={playwright_data.get('creator')}, "
                  f"likes={playwright_data.get('likes')}, comments={playwright_data.get('comments')}")
        except Exception as pw_error:
            print(f"Playwright extraction failed: {pw_error}")
        
        # Step 2: Try yt-dlp for full metadata (may fail due to auth)
        instagram_metadata = None
        try:
            instagram_extractor = InstagramExtractor()
            instagram_metadata = instagram_extractor.extract_metadata(instagram_url, "instagram")
            print("yt-dlp extraction succeeded")
        except Exception as ytdlp_error:
            print(f"yt-dlp Instagram failed (auth issue): {ytdlp_error}")
        
        # Step 3: Build final metadata from best available source
        if instagram_metadata:
            # yt-dlp worked — enrich with Playwright data where yt-dlp is missing
            if playwright_data:
                if playwright_data.get("creator"):
                    instagram_metadata["creator"] = playwright_data["creator"]
                if playwright_data.get("follower_count"):
                    instagram_metadata["follower_count"] = playwright_data["follower_count"]
                if playwright_data.get("likes", 0) > instagram_metadata.get("likes", 0):
                    instagram_metadata["likes"] = playwright_data["likes"]
                if playwright_data.get("comments", 0) > instagram_metadata.get("comments", 0):
                    instagram_metadata["comments"] = playwright_data["comments"]
                if playwright_data.get("views"):
                    instagram_metadata["views"] = playwright_data["views"]
        elif playwright_data:
            # yt-dlp failed but Playwright got data — build synthetic metadata
            print("Building metadata from Playwright data (yt-dlp unavailable)")
            pw_likes = playwright_data.get("likes", 0) or 0
            pw_comments = playwright_data.get("comments", 0) or 0
            pw_views = playwright_data.get("views")
            
            # Estimate views if not available
            if not pw_views and pw_likes > 0:
                pw_views = (pw_likes * 14) + (pw_comments * 300)
            elif not pw_views:
                pw_views = 500
            
            engagement_rate = ((pw_likes + pw_comments) / pw_views * 100) if pw_views > 0 else 0
            
            # Extract reel ID from URL for hashtag/description fallback
            reel_id_match = re.search(r'/reel/([^/?]+)', instagram_url)
            reel_id = reel_id_match.group(1) if reel_id_match else "unknown"
            
            instagram_metadata = {
                'video_id': None,
                'platform': 'instagram',
                'url': instagram_url,
                'creator': playwright_data.get("creator", "Unknown"),
                'creator_id': playwright_data.get("creator_id"),
                'follower_count': playwright_data.get("follower_count"),
                'title': f"Instagram Reel by @{playwright_data.get('creator', 'Unknown')}",
                'views': pw_views,
                'likes': pw_likes,
                'comments': pw_comments,
                'engagement_rate': engagement_rate,
                'upload_date': None,
                'duration_seconds': 0,
                'hashtags': [],
                'thumbnail': '',
                'video_url': instagram_url,
                'description': '',
            }
        else:
            # Both failed completely
            raise Exception("Both Playwright and yt-dlp failed to extract Instagram metadata")
        
        # Recalculate engagement if we have updated likes/comments
        final_likes = instagram_metadata.get("likes") or 0
        final_comments = instagram_metadata.get("comments") or 0
        if final_likes > 0:
            estimated_views = instagram_metadata.get("views") or (final_likes * 14) + (final_comments * 300)
            instagram_metadata["views"] = estimated_views
            instagram_metadata["engagement_rate"] = ((final_likes + final_comments) / estimated_views * 100)
            print(f"Final views: {estimated_views:,}, engagement: {instagram_metadata['engagement_rate']:.1f}%")
        
        instagram_metadata["video_id"] = video_id_b
        
        # Get transcript
        instagram_segments = transcript_fetcher.fetch_instagram_transcript(instagram_url)
        duration = instagram_metadata.get("duration_seconds", 0)
        
        if duration == 0 and instagram_segments:
            last_seg = instagram_segments[-1]
            duration = last_seg.get('end', last_seg.get('start', 0)) + 2
        
        print(f"INSTAGRAM: {len(instagram_segments)} segments, duration={duration}s")
        
        # Use manual chunks
        task["step"] = "instagram_embeddings"
        chunks = create_manual_chunks(instagram_segments, duration, video_id_b)
        print(f"INSTAGRAM CHUNKS: fine={len(chunks['fine'])}, medium={len(chunks['medium'])}, coarse={len(chunks['coarse'])}")
        
        for level in ['fine', 'medium', 'coarse']:
            level_chunks = chunks[level]
            if level_chunks:
                print(f"INSTAGRAM: Embedding {len(level_chunks)} {level} chunks...")
                for chunk in level_chunks:
                    chunk['embedding'] = bge_embedder.embed_text(chunk['text'])
                pinecone_client.upsert_chunks(level_chunks, video_id_b)
        
        task["step"] = "storage"
        store_video_metadata(video_id_b, instagram_metadata)
        
        results["B"] = {
            'status': 'success',
            'metadata': instagram_metadata,
            'chunk_counts': {k: len(v) for k, v in chunks.items()}
        }
        
    except Exception as e:
        print(f"Instagram error: {e}")
        import traceback
        traceback.print_exc()
        results["B"] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Mark task as completed
    task["status"] = "completed"
    task["step"] = "done"
    task["results"] = results
    print(f"\n===== INGESTION TASK {task_id} COMPLETED =====")

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
