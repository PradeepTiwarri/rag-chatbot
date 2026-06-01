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
        
        follower_count = None
        channel_id = None
        
        if 'channel_follower_count' in info:
            follower_count = info['channel_follower_count']
        elif 'uploader_followers' in info:
            follower_count = info['uploader_followers']
        
        if platform == 'youtube':
            channel_id = info.get('channel_id') or info.get('uploader_id')
        
        description = info.get('description', '')
        hashtags = re.findall(r'#\w+', description)
        
        views = info.get('view_count', 0)
        if views is None:
            views = 0
        
        likes = info.get('like_count', 0)
        if likes is None:
            likes = 0
        
        comments = info.get('comment_count', 0)
        if comments is None:
            comments = 0
        
        # For Instagram, if views are missing or zero, estimate based on likes and comments
        if platform == 'instagram' and (views == 0 or views is None):
            if likes > 0 or comments > 0:
                # ADJUSTABLE PARAMETERS - Change these values based on your data
                # For normal engagement: likes_multiplier = 14, comments_multiplier = 300
                # For high engagement: likes_multiplier = 12, comments_multiplier = 250
                # For low engagement: likes_multiplier = 20, comments_multiplier = 500
                LIKES_MULTIPLIER = 14      # 1 like per X views (lower = higher engagement)
                COMMENTS_MULTIPLIER = 300   # 1 comment per X views (lower = higher engagement)
                
                # Base estimation
                estimated_views = (likes * LIKES_MULTIPLIER) + (comments * COMMENTS_MULTIPLIER)
                
                # Adjust based on like-to-comment ratio
                if likes > 0 and comments > 0:
                    like_comment_ratio = likes / comments
                    if like_comment_ratio > 300:
                        # Very high likes to comments ratio - viral content
                        estimated_views = int(estimated_views * 0.85)
                    elif like_comment_ratio < 100:
                        # Lower likes to comments ratio - niche/highly engaged audience
                        estimated_views = int(estimated_views * 1.15)
                
                # Scale based on total engagement volume
                total_engagement = likes + comments
                if total_engagement > 50000:
                    # Viral content often has lower engagement rates
                    estimated_views = int(estimated_views * 0.8)
                elif total_engagement < 1000:
                    # Small accounts may have higher engagement rates
                    estimated_views = int(estimated_views * 1.2)
                
                # Set reasonable min/max bounds
                if estimated_views < 100:
                    estimated_views = 100
                if estimated_views > 50000000:
                    estimated_views = 50000000
                
                views = estimated_views
                print(f"Instagram views estimated: {views:,} (using likes_multiplier={LIKES_MULTIPLIER}, comments_multiplier={COMMENTS_MULTIPLIER})")
            else:
                views = 500  # Minimum fallback for videos with no engagement
        
        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
        
        metadata = {
            'video_id': None,
            'platform': platform,
            'url': info.get('webpage_url', info.get('original_url', '')),
            'creator': info.get('uploader', info.get('channel', 'Unknown')),
            'creator_id': channel_id,
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
            'description': description[:500]
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
        if (metadata['platform'] == 'youtube' and 
            not metadata.get('follower_count') and 
            metadata.get('creator_id')):
            
            api_followers = self.fetch_follower_count_via_api(metadata['creator_id'])
            if api_followers:
                metadata['follower_count'] = api_followers
                print(f"YouTube API fallback: Got {api_followers} subscribers for {metadata['creator']}")
        
        return metadata
    
    def get_duration_seconds(self, url: str) -> int:
        """Quickly get duration without full metadata extraction"""
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('duration', 0)


class InstagramExtractor(VideoExtractor):
    """Specialized extractor for Instagram Reels with estimated views"""
    
    def __init__(self, youtube_api_key: str = None, cookies_file: str = None, 
                 likes_multiplier: int = 14, comments_multiplier: int = 300):
        """
        Initialize Instagram extractor with adjustable estimation parameters.
        
        Args:
            youtube_api_key: YouTube API key for fallback
            cookies_file: Path to Instagram cookies file
            likes_multiplier: Number of views per like (lower = higher engagement)
            comments_multiplier: Number of views per comment (lower = higher engagement)
        """
        super().__init__(youtube_api_key)
        self.cookies_file = cookies_file
        self.likes_multiplier = likes_multiplier
        self.comments_multiplier = comments_multiplier
    
    def _parse_metadata_with_estimation(self, info: Dict, platform: str) -> Dict[str, Any]:
        """Parse metadata with custom estimation parameters"""
        
        follower_count = None
        channel_id = None
        
        if 'channel_follower_count' in info:
            follower_count = info['channel_follower_count']
        elif 'uploader_followers' in info:
            follower_count = info['uploader_followers']
        
        if platform == 'youtube':
            channel_id = info.get('channel_id') or info.get('uploader_id')
        
        description = info.get('description', '')
        hashtags = re.findall(r'#\w+', description)
        
        views = info.get('view_count', 0)
        if views is None:
            views = 0
        
        likes = info.get('like_count', 0)
        if likes is None:
            likes = 0
        
        comments = info.get('comment_count', 0)
        if comments is None:
            comments = 0
        
        # For Instagram, if views are missing or zero, estimate using instance parameters
        if platform == 'instagram' and (views == 0 or views is None):
            if likes > 0 or comments > 0:
                # Use the instance-specific multipliers
                estimated_views = (likes * self.likes_multiplier) + (comments * self.comments_multiplier)
                
                # Adjust based on like-to-comment ratio
                if likes > 0 and comments > 0:
                    like_comment_ratio = likes / comments
                    if like_comment_ratio > 300:
                        estimated_views = int(estimated_views * 0.85)
                    elif like_comment_ratio < 100:
                        estimated_views = int(estimated_views * 1.15)
                
                # Scale based on total engagement volume
                total_engagement = likes + comments
                if total_engagement > 50000:
                    estimated_views = int(estimated_views * 0.8)
                elif total_engagement < 1000:
                    estimated_views = int(estimated_views * 1.2)
                
                if estimated_views < 100:
                    estimated_views = 100
                if estimated_views > 50000000:
                    estimated_views = 50000000
                
                views = estimated_views
                print(f"Instagram views estimated: {views:,} (likes_multiplier={self.likes_multiplier}, comments_multiplier={self.comments_multiplier})")
            else:
                views = 500
        
        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
        
        metadata = {
            'video_id': None,
            'platform': platform,
            'url': info.get('webpage_url', info.get('original_url', '')),
            'creator': info.get('uploader', info.get('channel', 'Unknown')),
            'creator_id': channel_id,
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
            'description': description[:500]
        }
        
        return metadata
    
    def extract_metadata(self, url: str, platform: str = "instagram") -> Dict[str, Any]:
        with yt_dlp.YoutubeDL({
            **self.ydl_opts,
            'cookiefile': self.cookies_file,
        }) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                metadata = self._parse_metadata_with_estimation(info, platform)
                
                if not metadata['follower_count'] and 'channel_id' in info:
                    try:
                        channel_info = ydl.extract_info(f"https://www.instagram.com/{info['channel_id']}/", download=False)
                        metadata['follower_count'] = channel_info.get('channel_follower_count')
                    except:
                        pass
                
                return metadata
            except Exception as e:
                raise Exception(f"Failed to extract Instagram metadata: {str(e)}")