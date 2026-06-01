from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re
from typing import List, Dict, Any, Optional
import groq
import warnings
from ..config import config

# Suppress yt-dlp JS runtime warnings
warnings.filterwarnings("ignore", category=UserWarning)

class TranscriptFetcher:
    """Fetch transcripts from YouTube or via Groq Whisper for Instagram"""
    
    def __init__(self):
        self.groq_client = groq.Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None
    
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
            
            return segments
        
        except Exception as e:
            print(f"No YouTube captions found for {video_id}, falling back to Whisper...")
            return self._fetch_via_whisper(url)
    
    def fetch_instagram_transcript(self, url: str) -> List[Dict[str, Any]]:
        """Fetch transcript from Instagram Reels via Whisper"""
        return self._fetch_via_whisper(url)
    
    def _fetch_via_whisper(self, url: str) -> List[Dict[str, Any]]:
        """Download audio and transcribe with Groq Whisper"""
        import yt_dlp
        import tempfile
        import os
        
        if not self.groq_client:
            raise Exception("Groq API key not configured for Whisper transcription")
        
        temp_audio = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                temp_audio = tmp.name
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_audio.replace('.mp3', ''),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            
            actual_mp3 = temp_audio.replace('.mp3', '.mp3')
            if not os.path.exists(actual_mp3):
                actual_mp3 = temp_audio + '.mp3'
            
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
            else:
                segments.append({
                    'text': transcription.text,
                    'start': 0,
                    'end': 0,
                    'duration': 0
                })
            
            return segments
            
        except Exception as e:
            raise Exception(f"Whisper transcription failed: {str(e)}")
        finally:
            if temp_audio and os.path.exists(temp_audio):
                try:
                    os.unlink(temp_audio)
                except:
                    pass
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([\w-]+)',
            r'(?:youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/embed\/)([\w-]+)',
            r'(?:youtube\.com\/v\/)([\w-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_full_transcript_text(self, segments: List[Dict]) -> str:
        """Combine segments into single string"""
        return ' '.join([seg['text'] for seg in segments])