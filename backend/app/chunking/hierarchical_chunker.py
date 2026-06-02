from typing import List, Dict, Any, Tuple, Optional
from ..config import config
from .overlap_manager import fine_overlap_manager, medium_overlap_manager

class HierarchicalChunker:
    """
    Implements 3-level hierarchical chunking as specified in the plan:
    - Level 1 (Fine): 30-second chunks with 10-second overlap
    - Level 2 (Medium): 2-minute chunks with 30-second overlap  
    - Level 3 (Coarse): Full video chunk
    
    Each level stores different metadata for different query types.
    """
    
    def __init__(self):
        self.fine_chunk_size = config.FINE_CHUNK_SIZE_SEC
        self.fine_overlap = config.FINE_OVERLAP_SEC
        self.medium_chunk_size = config.MEDIUM_CHUNK_SIZE_SEC
        self.medium_overlap = config.MEDIUM_OVERLAP_SEC
        self.intro_sec = config.INTRO_SEC
        self.outro_sec = config.OUTRO_SEC
    
    def chunk_video(self, segments: List[Dict[str, Any]], duration: float, video_id: str) -> Dict[str, List[Dict]]:
        """
        Create all three levels of chunks for a video.
        
        Returns:
            Dictionary with keys 'fine', 'medium', 'coarse' containing chunk lists
        """
        print(f"\n[Chunker] Processing video {video_id}: duration={duration}s, segments={len(segments)}")
        
        if not segments:
            print(f"[Chunker] No segments for video {video_id}")
            return {'fine': [], 'medium': [], 'coarse': []}
        
        # Debug: Check segment structure
        if segments:
            first_seg = segments[0]
            print(f"[Chunker] First segment: start={first_seg.get('start')}, end={first_seg.get('end')}, text_len={len(first_seg.get('text', ''))}")
        
        full_text = ' '.join([seg.get('text', '') for seg in segments])
        
        # Create fine chunks
        fine_chunks = []
        if duration <= 120:
            # For short videos, create fine chunks based on text length
            text_length = len(full_text)
            chunk_size = 500  # characters per chunk
            
            if text_length > 0:
                num_chunks = max(1, (text_length + chunk_size - 1) // chunk_size)
                chars_per_chunk = text_length / num_chunks
                
                for i in range(num_chunks):
                    start_char = int(i * chars_per_chunk)
                    end_char = int(min((i + 1) * chars_per_chunk, text_length))
                    chunk_text = full_text[start_char:end_char]
                    
                    if chunk_text:
                        estimated_start = (start_char / text_length) * duration
                        estimated_end = (end_char / text_length) * duration
                        fine_chunks.append({
                            'start': estimated_start,
                            'end': estimated_end,
                            'text': chunk_text,
                            'segment_count': 1,
                            'segment_indices': []
                        })
        else:
            # Use overlap manager for longer videos
            fine_chunks = fine_overlap_manager.create_overlapping_chunks(segments, duration)
        
        print(f"[Chunker] Fine chunks created: {len(fine_chunks)}")
        
        # Create medium chunks
        medium_chunks = []
        if duration <= self.medium_chunk_size:
            # For videos shorter than medium chunk size, use text-based chunking
            text_length = len(full_text)
            if text_length > 0:
                num_medium_chunks = max(1, text_length // 1500)  # ~1500 chars per medium chunk
                chars_per_medium = text_length / num_medium_chunks
                
                for i in range(num_medium_chunks):
                    start_char = int(i * chars_per_medium)
                    end_char = int(min((i + 1) * chars_per_medium, text_length))
                    chunk_text = full_text[start_char:end_char]
                    
                    if chunk_text:
                        estimated_start = (start_char / text_length) * duration
                        estimated_end = (end_char / text_length) * duration
                        medium_chunks.append({
                            'start': estimated_start,
                            'end': estimated_end,
                            'text': chunk_text,
                            'segment_count': 1,
                            'segment_indices': []
                        })
            else:
                medium_chunks = [{
                    'start': 0.0,
                    'end': duration,
                    'text': full_text,
                    'segment_count': len(segments),
                    'segment_indices': list(range(len(segments)))
                }]
        else:
            medium_chunks = medium_overlap_manager.create_overlapping_chunks(segments, duration)
        
        print(f"[Chunker] Medium chunks created: {len(medium_chunks)}")
        
        # Enrich chunks with metadata
        fine_chunks = self._enrich_chunks(fine_chunks, video_id, 'fine', duration)
        medium_chunks = self._enrich_chunks(medium_chunks, video_id, 'medium', duration)
        
        # Create coarse chunk (full video)
        coarse_chunk = self._create_coarse_chunk(segments, duration, video_id)
        coarse_chunks = [coarse_chunk] if coarse_chunk else []
        print(f"[Chunker] Coarse chunks created: {len(coarse_chunks)}")
        
        print(f"[Chunker] Final totals - fine: {len(fine_chunks)}, medium: {len(medium_chunks)}, coarse: {len(coarse_chunks)}")
        
        return {
            'fine': fine_chunks,
            'medium': medium_chunks,
            'coarse': coarse_chunks
        }
    
    def _enrich_chunks(self, chunks: List[Dict], video_id: str, level: str, duration: float) -> List[Dict]:
        """Add metadata to chunks including section type and overlap context"""
        enriched_chunks = []
        
        for idx, chunk in enumerate(chunks):
            # Get overlap context (safe for empty or single chunk)
            if len(chunks) <= 1:
                overlap_ctx = {
                    'prev_chunk_end': None,
                    'next_chunk_start': None,
                    'has_prev_overlap': False,
                    'has_next_overlap': False
                }
            elif level == 'fine':
                overlap_ctx = fine_overlap_manager.get_overlap_context(chunks, idx)
            else:
                overlap_ctx = medium_overlap_manager.get_overlap_context(chunks, idx)
            
            # Determine section type (intro, body, outro)
            section_type = self._get_section_type(chunk['start'], chunk['end'], duration)
            
            enriched_chunk = {
                'video_id': video_id,
                'chunk_level': level,
                'chunk_index': idx,
                'start_time': chunk['start'],
                'end_time': chunk['end'],
                'text': chunk['text'],
                'duration': chunk['end'] - chunk['start'],
                'segment_count': chunk.get('segment_count', 0),
                'section_type': section_type,
                'prev_chunk_end': overlap_ctx['prev_chunk_end'],
                'next_chunk_start': overlap_ctx['next_chunk_start'],
                'has_prev_overlap': overlap_ctx['has_prev_overlap'],
                'has_next_overlap': overlap_ctx['has_next_overlap']
            }
            
            enriched_chunks.append(enriched_chunk)
        
        return enriched_chunks
    
    def _get_section_type(self, start: float, end: float, duration: float) -> str:
        """Determine if chunk is in intro, body, or outro"""
        if duration <= 0:
            return 'full'
        if start < self.intro_sec:
            return 'intro'
        elif end > duration - self.outro_sec:
            return 'outro'
        else:
            return 'body'
    
    def _create_coarse_chunk(self, segments: List[Dict], duration: float, video_id: str) -> Optional[Dict]:
        """Create a single coarse chunk for the entire video"""
        if not segments:
            return None
        
        full_text = ' '.join([seg.get('text', '') for seg in segments])
        
        return {
            'video_id': video_id,
            'chunk_level': 'coarse',
            'chunk_index': 0,
            'start_time': 0.0,
            'end_time': duration if duration > 0 else 60,
            'text': full_text,
            'duration': duration if duration > 0 else 60,
            'segment_count': len(segments),
            'section_type': 'full',
            'prev_chunk_end': None,
            'next_chunk_start': None,
            'has_prev_overlap': False,
            'has_next_overlap': False
        }
    
    def get_chunks_by_time_range(self, all_chunks: List[Dict], start: float, end: float, level: Optional[str] = None) -> List[Dict]:
        """
        Filter chunks that overlap with a specific time range.
        
        Args:
            all_chunks: List of chunks from one level
            start: Start time in seconds
            end: End time in seconds
            level: Optional filter by chunk level ('fine', 'medium', 'coarse')
        
        Returns:
            List of chunks overlapping the time range
        """
        filtered = []
        
        for chunk in all_chunks:
            if level and chunk['chunk_level'] != level:
                continue
            
            chunk_start = chunk['start_time']
            chunk_end = chunk['end_time']
            
            if chunk_end > start and chunk_start < end:
                filtered.append(chunk)
        
        filtered.sort(key=lambda x: x['start_time'])
        
        return filtered
    
    def get_best_chunk_level_for_query(self, query: str, time_range: Optional[Tuple[float, float]] = None) -> str:
        """
        Determine which chunk level to use based on query specificity.
        
        - Exact timestamps with small range (< 60s) → fine chunks
        - Medium ranges (60-180s) → medium chunks  
        - General/summary questions → coarse chunks
        """
        if time_range:
            start, end = time_range
            range_duration = end - start
            
            if range_duration <= 60:
                return 'fine'
            elif range_duration <= 180:
                return 'medium'
            else:
                return 'coarse'
        
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['second', 'seconds', 'timestamp', 'exactly', 'precise']):
            return 'fine'
        elif any(word in query_lower for word in ['minute', 'minutes', 'segment', 'part', 'section']):
            return 'medium'
        else:
            return 'coarse'


hierarchical_chunker = HierarchicalChunker()
