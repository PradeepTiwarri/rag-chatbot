from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re
from typing import List, Dict, Any, Optional
import groq
import warnings
import os
from ..config import config

# Suppress yt-dlp JS runtime warnings
warnings.filterwarnings("ignore", category=UserWarning)

class TranscriptFetcher:
    """Fetch transcripts from YouTube or via Groq Whisper for Instagram"""
    
    def __init__(self):
        self.groq_client = groq.Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None
        self.cookies_file = self._get_cookies_file_path()
        self._validate_cookies_file()
    
    def _get_cookies_file_path(self) -> Optional[str]:
        """Get the correct cookies file path for the environment"""
        possible_paths = [
            '/app/youtube_cookies.txt',
            os.path.join(os.path.dirname(__file__), '..', '..', 'youtube_cookies.txt'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'cookies.txt'),
            'youtube_cookies.txt',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found cookies file at: {path}")
                return path
        
        print("No cookies file found in any location")
        return None
    
    def _validate_cookies_file(self) -> bool:
        """Validate that cookies file exists and is in correct Netscape format"""
        if not self.cookies_file:
            print("No cookies file configured")
            return False
        
        if not os.path.exists(self.cookies_file):
            print(f"Cookies file not found: {self.cookies_file}")
            return False
        
        file_size = os.path.getsize(self.cookies_file)
        if file_size < 500:
            print(f"Cookies file too small ({file_size} bytes) - likely invalid or empty")
            return False
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if '# Netscape HTTP Cookie File' not in first_line:
                    print("WARNING: Cookies file missing Netscape format header")
                    return False
        except Exception as e:
            print(f"Error reading cookies file: {e}")
            return False
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '.youtube.com' not in content and 'youtube.com' not in content:
                    print("WARNING: No YouTube cookies found in cookies file")
                    return False
        except Exception as e:
            print(f"Error searching for YouTube cookies: {e}")
            return False
        
        print(f"Cookies file validated successfully: {self.cookies_file} ({file_size} bytes)")
        return True
    
    def _get_ydl_opts_with_cookies(self, extra_opts: Dict = None) -> Dict:
        """Build yt-dlp options with validated cookies, Deno, and remote components"""
        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'js_runtimes': {'deno': {'path': '/root/.deno/bin/deno'}},
            'remote_components': ['ejs:github'],
        }
        
        if extra_opts:
            base_opts.update(extra_opts)
        
        if self.cookies_file and self._validate_cookies_file():
            base_opts['cookiefile'] = self.cookies_file
            print(f"Using cookies file: {self.cookies_file}")
        else:
            print("No valid cookies file found, proceeding without authentication")
        
        return base_opts
    
    def fetch_youtube_transcript(self, url: str) -> List[Dict[str, Any]]:
        """Fetch transcript from YouTube with timestamps"""
        video_id = self._extract_youtube_id(url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: {url}")
        
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            segments = []
            for item in transcript_list:
                segments.append({
                    'text': item['text'],
                    'start': item['start'],
                    'end': item['start'] + item['duration'],
                    'duration': item['duration']
                })
            
            print(f"Retrieved {len(segments)} transcript segments via YouTube API")
            return segments
        
        except Exception as e:
            print(f"No YouTube captions found for {video_id}: {e}")
            print("Falling back to Whisper audio transcription...")
            return self._fetch_via_whisper(url)
    
    def fetch_instagram_transcript(self, url: str) -> List[Dict[str, Any]]:
        """Fetch transcript from Instagram Reels via Whisper"""
        return self._fetch_via_whisper(url)
    
    def _fetch_via_whisper(self, url: str) -> List[Dict[str, Any]]:
        """Download audio and transcribe with Groq Whisper"""
        import yt_dlp
        import tempfile
        
        if not self.groq_client:
            raise Exception("Groq API key not configured for Whisper transcription")
        
        temp_audio = None
        video_duration = 0.0
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                temp_audio = tmp.name

            # First pass: get metadata (including duration) without downloading
            meta_opts = self._get_ydl_opts_with_cookies({'skip_download': True})
            try:
                with yt_dlp.YoutubeDL(meta_opts) as ydl_meta:
                    info = ydl_meta.extract_info(url, download=False)
                    video_duration = float(info.get('duration') or 0)
                    print(f"Video duration detected: {video_duration}s")
            except Exception as e:
                print(f"Could not fetch video duration: {e}")

            # Second pass: download audio with format fallback
            # Try format 140 first (universal m4a), then fallback to bestaudio
            ydl_opts = self._get_ydl_opts_with_cookies({
                'format': '140/bestaudio',
                'outtmpl': temp_audio.replace('.mp3', ''),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],
                        'player_client': ['android', 'ios', 'web'],
                    }
                }
            })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            actual_mp3 = temp_audio.replace('.mp3', '.mp3')
            if not os.path.exists(actual_mp3):
                actual_mp3 = temp_audio + '.mp3'

            if not os.path.exists(actual_mp3):
                raise Exception(f"Audio file not found at {actual_mp3}")

            file_size = os.path.getsize(actual_mp3) / (1024 * 1024)
            print(f"Audio downloaded: {file_size:.2f} MB")

            with open(actual_mp3, 'rb') as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )

            segments = []
            if hasattr(transcription, 'segments') and transcription.segments:
                for seg in transcription.segments:
                    segments.append({
                        'text': seg.text,
                        'start': seg.start,
                        'end': seg.end,
                        'duration': seg.end - seg.start
                    })
                print(f"Whisper returned {len(segments)} timestamped segments")
            else:
                print("No timestamps in Whisper response, creating estimated segments")
                segments = self._split_flat_transcript(
                    transcription.text, duration_hint=video_duration
                )
            
            return segments
            
        except Exception as e:
            raise Exception(f"Whisper transcription failed: {str(e)}")
        finally:
            if temp_audio and os.path.exists(temp_audio):
                try:
                    os.unlink(temp_audio)
                except:
                    pass
            if temp_audio and os.path.exists(temp_audio + '.mp3'):
                try:
                    os.unlink(temp_audio + '.mp3')
                except:
                    pass
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([\w-]+)',
            r'(?:youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/embed\/)([\w-]+)',
            r'(?:youtube\.com\/v\/)([\w-]+)',
            r'(?:youtube\.com\/shorts\/)([\w-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _split_flat_transcript(
        self, text: str, duration_hint: float, words_per_seg: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Split a flat (no-timestamp) transcript into evenly-spaced pseudo-segments
        so the HierarchicalChunker's overlap_manager can produce fine and medium
        chunks based on time windows.
        """
        words = text.split()
        if not words:
            return [{'text': text, 'start': 0.0, 'end': max(duration_hint, 1.0),
                     'duration': max(duration_hint, 1.0)}]

        if duration_hint <= 0:
            duration_hint = len(words) * 2.0
            print(f"Estimated duration from word count: {duration_hint}s")

        secs_per_word = duration_hint / len(words)
        segments = []
        for i in range(0, len(words), words_per_seg):
            chunk_words = words[i: i + words_per_seg]
            start = i * secs_per_word
            end = min((i + len(chunk_words)) * secs_per_word, duration_hint)
            segments.append({
                'text': ' '.join(chunk_words),
                'start': round(start, 2),
                'end': round(end, 2),
                'duration': round(end - start, 2),
            })
        
        print(f"Created {len(segments)} estimated segments from flat transcript")
        return segments

    def get_full_transcript_text(self, segments: List[Dict]) -> str:
        """Combine segments into single string"""
        return ' '.join([seg['text'] for seg in segments])
