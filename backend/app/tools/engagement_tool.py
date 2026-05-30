from typing import List, Dict, Any

# In production, this would fetch from database
# For now, store in memory during session
_metadata_cache = {}

def store_video_metadata(video_id: str, metadata: Dict):
    """Store video metadata for tool access"""
    _metadata_cache[video_id] = metadata

def get_engagement_rates(video_ids: List[str]) -> Dict[str, Any]:
    """Calculate engagement rates for videos"""
    
    results = {}
    
    for video_id in video_ids:
        metadata = _metadata_cache.get(video_id, {})
        
        views = metadata.get('views', 0)
        likes = metadata.get('likes', 0)
        comments = metadata.get('comments', 0)
        
        if views > 0:
            engagement_rate = ((likes + comments) / views) * 100
        else:
            engagement_rate = 0
        
        results[video_id] = {
            'views': views,
            'likes': likes,
            'comments': comments,
            'engagement_rate': round(engagement_rate, 2)
        }
    
    return results


def get_engagement_rate_text(video_ids: List[str]) -> str:
    """Get formatted engagement rate text for LLM"""
    
    rates = get_engagement_rates(video_ids)
    
    text_parts = []
    for video_id, data in rates.items():
        text_parts.append(
            f"Video {video_id}: {data['engagement_rate']}% "
            f"({data['likes']} likes, {data['comments']} comments on {data['views']} views)"
        )
    
    return "\n".join(text_parts)