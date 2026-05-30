import yt_dlp
import re
from typing import Dict, Any, Optional

class VideoExtractor:
    """Extract metadata from YouTube and Instagram Reels using yt-dlp"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def extract_metadata(self, url: str, platform: str) -> Dict[str, Any]:
        """Extract all metadata from video URL"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return self._parse_metadata(info, platform)
            except Exception as e:
                raise Exception(f"Failed to extract metadata from {platform}: {str(e)}")
    
    def _parse_metadata(self, info: Dict, platform: str) -> Dict[str, Any]:
        """Parse raw yt-dlp output into structured metadata"""
        
        # Extract follower count (yt-dlp may not have this for all platforms)
        follower_count = None
        if 'channel_follower_count' in info:
            follower_count = info['channel_follower_count']
        elif 'uploader_followers' in info:
            follower_count = info['uploader_followers']
        
        # Extract hashtags from description
        description = info.get('description', '')
        hashtags = re.findall(r'#\w+', description)
        
        # Calculate engagement rate (will be recomputed with actual likes/comments)
        views = info.get('view_count', 0)
        likes = info.get('like_count', 0)
        comments = info.get('comment_count', 0)
        
        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
        
        metadata = {
            'video_id': None,  # Will be set by caller (A or B)
            'platform': platform,
            'url': info.get('webpage_url', info.get('original_url', '')),
            'creator': info.get('uploader', info.get('channel', 'Unknown')),
            'follower_count': follower_count,
            'title': info.get('title', ''),
            'views': views,
            'likes': likes,
            'comments': comments,
            'engagement_rate': engagement_rate,
            'upload_date': info.get('upload_date'),
            'duration_seconds': info.get('duration', 0),
            'hashtags': hashtags,
            'thumbnail': info.get('thumbnail', ''),
            'description': description[:500]  # Truncate for storage
        }
        
        return metadata
    
    def get_duration_seconds(self, url: str) -> int:
        """Quickly get duration without full metadata extraction"""
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('duration', 0)


# For Instagram Reels - Instagram-specific extraction
class InstagramExtractor(VideoExtractor):
    """Specialized extractor for Instagram Reels with follower count from profile"""
    
    def extract_metadata(self, url: str, platform: str = "instagram") -> Dict[str, Any]:
        with yt_dlp.YoutubeDL({
            **self.ydl_opts,
            'cookiefile': None,  # Instagram may require cookies for some data
        }) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                metadata = self._parse_metadata(info, platform)
                
                # Instagram: try to get follower count from channel info
                if not metadata['follower_count'] and 'channel_id' in info:
                    try:
                        channel_info = ydl.extract_info(f"https://www.instagram.com/{info['channel_id']}/", download=False)
                        metadata['follower_count'] = channel_info.get('channel_follower_count')
                    except:
                        pass
                
                return metadata
            except Exception as e:
                raise Exception(f"Failed to extract Instagram metadata: {str(e)}")