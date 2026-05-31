export interface VideoMetadata {
  video_id: string;
  platform: 'youtube' | 'instagram';
  url: string;  // Add this property
  creator: string;
  follower_count: number | null;
  title: string;
  views: number;
  likes: number;
  comments: number;
  engagement_rate: number;
  thumbnail: string;
  duration_seconds: number;
  hashtags: string[];
}

export interface Citation {
  video_id: string;
  timestamp: string;
  text: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

export interface IngestResponse {
  A: {
    status: 'success' | 'error';
    metadata?: VideoMetadata;
    error?: string;
    chunk_counts?: {
      fine: number;
      medium: number;
      coarse: number;
    };
  };
  B: {
    status: 'success' | 'error';
    metadata?: VideoMetadata;
    error?: string;
    chunk_counts?: {
      fine: number;
      medium: number;
      coarse: number;
    };
  };
}