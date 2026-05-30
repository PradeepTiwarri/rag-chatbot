from typing import List, Dict, Any, Tuple

class OverlapManager:
    """
    Manages temporal overlap between chunks to ensure no sentence is cut at boundaries.
    Implements the overlap logic from the execution plan:
    - Fine chunks: 30s size, 10s overlap (20s new content each)
    - Medium chunks: 120s size, 30s overlap (90s new content each)
    """
    
    def __init__(self, chunk_size_sec: int, overlap_sec: int):
        self.chunk_size_sec = chunk_size_sec
        self.overlap_sec = overlap_sec
        self.step_sec = chunk_size_sec - overlap_sec  # New content per chunk
    
    def create_overlapping_chunks(self, segments: List[Dict[str, Any]], duration: float) -> List[Dict[str, Any]]:
        """
        Create overlapping time-based chunks from transcript segments.
        
        Args:
            segments: List of transcript segments with 'start', 'end', 'text'
            duration: Total video duration in seconds
        
        Returns:
            List of chunks with 'start', 'end', 'text', 'segment_indices'
        """
        if not segments:
            return []
        
        chunks = []
        current_start = 0.0
        
        while current_start < duration:
            chunk_end = min(current_start + self.chunk_size_sec, duration)
            
            # Get segments that overlap with this time window
            segments_in_chunk = []
            for idx, seg in enumerate(segments):
                seg_start = seg['start']
                seg_end = seg.get('end', seg_start + seg.get('duration', 2))
                
                # Check if segment overlaps with chunk window
                if seg_end > current_start and seg_start < chunk_end:
                    segments_in_chunk.append({
                        'index': idx,
                        'text': seg['text'],
                        'start': seg_start,
                        'end': seg_end
                    })
            
            if segments_in_chunk:
                # Combine text from all segments in this chunk
                chunk_text = ' '.join([s['text'] for s in segments_in_chunk])
                
                chunks.append({
                    'start': current_start,
                    'end': chunk_end,
                    'text': chunk_text,
                    'segment_indices': [s['index'] for s in segments_in_chunk],
                    'segment_count': len(segments_in_chunk)
                })
            
            # Move to next chunk with overlap
            current_start += self.step_sec
            
            # Prevent infinite loop
            if current_start >= chunk_end and self.step_sec <= 0:
                break
        
        return chunks
    
    def get_overlap_context(self, chunks: List[Dict], index: int) -> Dict[str, Any]:
        """
        Get overlap context for a specific chunk (previous chunk end, next chunk start).
        Used for metadata storage as specified in the plan.
        """
        context = {
            'prev_chunk_end': None,
            'next_chunk_start': None,
            'has_prev_overlap': False,
            'has_next_overlap': False
        }
        
        if index > 0:
            prev_chunk = chunks[index - 1]
            context['prev_chunk_end'] = prev_chunk['end']
            # Check if this chunk overlaps with previous
            if chunks[index]['start'] < prev_chunk['end']:
                context['has_prev_overlap'] = True
        
        if index < len(chunks) - 1:
            next_chunk = chunks[index + 1]
            context['next_chunk_start'] = next_chunk['start']
            # Check if next chunk overlaps with this one
            if next_chunk['start'] < chunks[index]['end']:
                context['has_next_overlap'] = True
        
        return context


# Pre-configured overlap managers
fine_overlap_manager = OverlapManager(chunk_size_sec=30, overlap_sec=10)
medium_overlap_manager = OverlapManager(chunk_size_sec=120, overlap_sec=30)