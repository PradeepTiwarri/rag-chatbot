import yt_dlp
import re
import os
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
        self.cookies_file = self._get_cookies_file_path()
        self._validate_cookies_file()
    
    def _get_cookies_file_path(self) -> Optional[str]:
        """Get the correct cookies file path for the environment"""
        possible_paths = [
            '/app/youtube_cookies.txt',
            os.path.join(os.path.dirname(__file__), '..', '..', 'youtube_cookies.txt'),
            'youtube_cookies.txt',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found cookies file at: {path}")
                return path
        return None
    
    def _validate_cookies_file(self) -> bool:
        """Validate that cookies file exists and is usable"""
        if not self.cookies_file:
            return False
        if not os.path.exists(self.cookies_file):
            return False
        file_size = os.path.getsize(self.cookies_file)
        if file_size < 500:
            print(f"Cookies file too small ({file_size} bytes)")
            return False
        return True
    
    def _get_ydl_opts(self, extra_opts: Dict = None) -> Dict:
        """Build yt-dlp options with cookies and Deno"""
        base_opts = self.ydl_opts.copy()
        
        if extra_opts:
            base_opts.update(extra_opts)
        
        if self.cookies_file and self._validate_cookies_file():
            base_opts['cookiefile'] = self.cookies_file
            base_opts['js_runtimes'] = {'deno': {'path': '/root/.deno/bin/deno'}}
            base_opts['remote_components'] = ['ejs:github']
            print(f"Using cookies file for metadata: {self.cookies_file}")
        
        return base_opts
    
    def extract_metadata(self, url: str, platform: str) -> Dict[str, Any]:
        """Extract all metadata from video URL"""
        with yt_dlp.YoutubeDL(self._get_ydl_opts()) as ydl:
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
        
        views = info.get('view_count')
        if views is None:
            views = 0
        
        likes = info.get('like_count')
        if likes is None:
            likes = 0
        
        comments = info.get('comment_count')
        if comments is None:
            comments = 0
        
        if platform == 'instagram' and views == 0:
            if likes > 0 or comments > 0:
                LIKES_MULTIPLIER = 14
                COMMENTS_MULTIPLIER = 300
                views = (likes * LIKES_MULTIPLIER) + (comments * COMMENTS_MULTIPLIER)
                print(f"Instagram views estimated: {views:,} (from {likes:,} likes, {comments:,} comments)")
            else:
                views = 500
                print("Instagram views set to floor: 500")
        
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
            'video_url': info.get('url', ''),
            'description': description[:500]
        }
        
        return metadata
    
    def fetch_follower_count_via_api(self, channel_id: str) -> Optional[int]:
        """Fetch subscriber count using YouTube Data API v3"""
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
        """Enrich metadata with YouTube API follower count if yt-dlp failed"""
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
        with yt_dlp.YoutubeDL(self._get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('duration', 0)


class InstagramExtractor(VideoExtractor):
    """Specialized extractor for Instagram Reels with follower count from profile"""
    
    def extract_metadata(self, url: str, platform: str = "instagram") -> Dict[str, Any]:
        with yt_dlp.YoutubeDL(self._get_ydl_opts()) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                metadata = self._parse_metadata(info, platform)
                
                if not metadata['follower_count'] and 'channel_id' in info and info['channel_id']:
                    try:
                        channel_info = ydl.extract_info(f"https://www.instagram.com/{info['channel_id']}/", download=False)
                        metadata['follower_count'] = channel_info.get('channel_follower_count')
                    except:
                        pass
                
                return metadata
            except Exception as e:
                raise Exception(f"Failed to extract Instagram metadata: {str(e)}")
