from typing import List, Dict, Any

from .engagement_tool import _metadata_cache

def get_video_metadata(video_ids: List[str]) -> Dict[str, Any]:
    """Fetch stored metadata for videos"""
    
    results = {}
    
    for video_id in video_ids:
        metadata = _metadata_cache.get(video_id, {})
        
        results[video_id] = {
            'creator': metadata.get('creator', 'Unknown'),
            'follower_count': metadata.get('follower_count', 'N/A'),
            'upload_date': metadata.get('upload_date', 'Unknown'),
            'duration_seconds': metadata.get('duration_seconds', 0),
            'hashtags': metadata.get('hashtags', []),
            'title': metadata.get('title', '')
        }
    
    return results


def get_metadata_text(video_ids: List[str]) -> str:
    """Get formatted metadata text for LLM"""
    
    metadata = get_video_metadata(video_ids)
    
    text_parts = []
    for video_id, data in metadata.items():
        text_parts.append(
            f"Video {video_id}: Creator '{data['creator']}' "
            f"with {data['follower_count']} followers. "
            f"Uploaded {data['upload_date']}. "
            f"Hashtags: {', '.join(data['hashtags'][:5])}"
        )
    
    return "\n".join(text_parts)