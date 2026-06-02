import yt_dlp
import re
from typing import Dict, Any, Optional

class VideoExtractor:
    """Extract metadata from YouTube and Instagram Reels using yt-dlp"""
    
    def __init__(self, youtube_api_key: str = None):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        self.youtube_api_key = youtube_api_key
    
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
        channel_id = None
        
        if 'channel_follower_count' in info:
            follower_count = info['channel_follower_count']
        elif 'uploader_followers' in info:
            follower_count = info['uploader_followers']
        
        # Get channel ID for YouTube API fallback
        if platform == 'youtube':
            channel_id = info.get('channel_id') or info.get('uploader_id')
        
        # Extract hashtags from description
        description = info.get('description', '')
        hashtags = re.findall(r'#\w+', description)
        
        # Null-guard: yt-dlp returns None for hidden Instagram stats
        views = info.get('view_count') or 0
        likes = info.get('like_count') or 0
        comments = info.get('comment_count') or 0
        
        # For Instagram, estimate views from likes+comments when unavailable
        if platform == 'instagram' and views == 0:
            if likes > 0 or comments > 0:
                LIKES_MULTIPLIER = 14
                COMMENTS_MULTIPLIER = 300
                views = (likes * LIKES_MULTIPLIER) + (comments * COMMENTS_MULTIPLIER)
                print(f"Instagram views estimated: {views:,} (from {likes:,} likes, {comments:,} comments)")
            else:
                # Minimum floor when no engagement data at all
                views = 500
                print("Instagram views set to floor: 500 (no engagement data from yt-dlp)")
        
        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
        
        metadata = {
            'video_id': None,  # Will be set by caller (A or B)
            'platform': platform,
            'url': info.get('webpage_url', info.get('original_url', '')),
            'creator': info.get('uploader', info.get('channel', 'Unknown')),
            'creator_id': channel_id,  # Store channel ID for potential API fallback
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
            'video_url': info.get('url', ''),  # Direct video URL (works for Instagram reels)
            'description': description[:500]  # Truncate for storage
        }
        
        return metadata
    
    def fetch_follower_count_via_api(self, channel_id: str) -> Optional[int]:
        """
        Fallback: Fetch subscriber count using YouTube Data API v3.
        Returns None if API key not set or request fails.
        """
        if not self.youtube_api_key or not channel_id:
            return None
        
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            
            youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            request = youtube.channels().list(
                part='statistics',
                id=channel_id
            )
            response = request.execute()
            
            if response.get('items'):
                subscriber_count = response['items'][0]['statistics'].get('subscriberCount')
                if subscriber_count:
                    return int(subscriber_count)
            return None
            
        except HttpError as e:
            print(f"YouTube API error: {e}")
            return None
        except Exception as e:
            print(f"YouTube API fallback error: {e}")
            return None
    
    def enrich_with_api_follower_count(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich metadata with YouTube API follower count if yt-dlp failed.
        """
        # Only run for YouTube videos where follower_count is missing and we have channel_id
        if (metadata['platform'] == 'youtube' and 
            not metadata.get('follower_count') and 
            metadata.get('creator_id')):
            
            api_followers = self.fetch_follower_count_via_api(metadata['creator_id'])
            if api_followers:
                metadata['follower_count'] = api_followers
                print(f"✅ YouTube API fallback: Got {api_followers} subscribers for {metadata['creator']}")
        
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