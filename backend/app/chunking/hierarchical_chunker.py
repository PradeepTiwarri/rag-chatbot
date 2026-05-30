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
        if not segments:
            return {'fine': [], 'medium': [], 'coarse': []}
        
        # Create fine chunks (30s with 10s overlap)
        fine_chunks = fine_overlap_manager.create_overlapping_chunks(segments, duration)
        fine_chunks = self._enrich_chunks(fine_chunks, video_id, 'fine', duration)
        
        # Create medium chunks (2 min with 30s overlap)
        medium_chunks = medium_overlap_manager.create_overlapping_chunks(segments, duration)
        medium_chunks = self._enrich_chunks(medium_chunks, video_id, 'medium', duration)
        
        # Create coarse chunk (full video)
        coarse_chunk = self._create_coarse_chunk(segments, duration, video_id)
        coarse_chunks = [coarse_chunk] if coarse_chunk else []
        
        return {
            'fine': fine_chunks,
            'medium': medium_chunks,
            'coarse': coarse_chunks
        }
    
    def _enrich_chunks(self, chunks: List[Dict], video_id: str, level: str, duration: float) -> List[Dict]:
        """Add metadata to chunks including section type and overlap context"""
        enriched_chunks = []
        
        for idx, chunk in enumerate(chunks):
            # Get overlap context
            if level == 'fine':
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
        
        full_text = ' '.join([seg['text'] for seg in segments])
        
        return {
            'video_id': video_id,
            'chunk_level': 'coarse',
            'chunk_index': 0,
            'start_time': 0.0,
            'end_time': duration,
            'text': full_text,
            'duration': duration,
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
            
            # Check for overlap
            chunk_start = chunk['start_time']
            chunk_end = chunk['end_time']
            
            if chunk_end > start and chunk_start < end:
                filtered.append(chunk)
        
        # Sort by start time
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
            
            if range_duration <= 60:  # 1 minute or less
                return 'fine'
            elif range_duration <= 180:  # 3 minutes or less
                return 'medium'
            else:
                return 'coarse'
        
        # No time range - check for specificity in query
        query_lower = query.lower()
        
        # Specific time indicators
        if any(word in query_lower for word in ['second', 'seconds', 'timestamp', 'exactly', 'precise']):
            return 'fine'
        elif any(word in query_lower for word in ['minute', 'minutes', 'segment', 'part', 'section']):
            return 'medium'
        else:
            return 'coarse'  # General questions use coarse chunks



hierarchical_chunker = HierarchicalChunker()