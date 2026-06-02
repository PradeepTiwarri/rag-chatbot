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
        video_duration = 0.0
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                temp_audio = tmp.name

            # First pass: get metadata (including duration) without downloading
            meta_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            try:
                with yt_dlp.YoutubeDL(meta_opts) as ydl_meta:
                    info = ydl_meta.extract_info(url, download=False)
                    video_duration = float(info.get('duration') or 0)
            except Exception:
                pass

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
                # No segment timestamps — split text into evenly-spaced segments
                # distributed across the real video duration so the overlap_manager
                # can create fine and medium time-window chunks.
                # (end=0 / duration=0 causes seg_end > current_start to be False
                # for every window, resulting in 0 fine/medium chunks.)
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
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([\w-]+)',
            r'(?:youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/embed\/)([\w-]+)',
            r'(?:youtube\.com\/v\/)([\w-]+)',
            r'(?:youtube\.com\/shorts\/)([\w-]+)',   # YouTube Shorts
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

        Each segment covers ~words_per_seg words.  Timestamps are estimated by
        distributing words uniformly across duration_hint.  If duration_hint==0
        we assume 2 seconds per word (typical speech pace).
        """
        words = text.split()
        if not words:
            return [{'text': text, 'start': 0.0, 'end': max(duration_hint, 1.0),
                     'duration': max(duration_hint, 1.0)}]

        # Estimate duration from word count when we have no real duration
        if duration_hint <= 0:
            duration_hint = len(words) * 2.0  # ~150 wpm → 0.4 s/word; use 2 s to be safe

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
        return segments

    def get_full_transcript_text(self, segments: List[Dict]) -> str:
        """Combine segments into single string"""
        return ' '.join([seg['text'] for seg in segments])