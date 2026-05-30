from typing import List, Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from enum import Enum

class AgentState(TypedDict):
    """State schema for LangGraph agent"""
    
    # Input
    question: str
    session_id: str
    video_ids: List[str]  # ['A', 'B']
    
    # Time parsing
    has_time_component: bool
    time_range: Optional[Dict[str, float]]  # {'start': 0, 'end': 5}
    
    # Retrieval
    retrieved_chunks: List[Dict[str, Any]]
    retrieval_quality: str  # 'good', 'partial', 'poor'
    retry_count: int
    
    # Tools
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # Generation
    answer: str
    citations: List[Dict[str, Any]]  # [{'video_id': 'A', 'timestamp': '0:00-0:05', 'text': '...'}]
    
    # Memory
    conversation_history: List[Dict[str, str]]
    
    # Control
    next_action: str  # 'retrieve', 'grade', 'rewrite', 'use_tool', 'generate', 'end'
    error: Optional[str]


class RetrievalQuality(Enum):
    GOOD = "good"
    PARTIAL = "partial"
    POOR = "poor"


# Initial state template
def get_initial_state(question: str, session_id: str, video_ids: List[str]) -> AgentState:
    return {
        'question': question,
        'session_id': session_id,
        'video_ids': video_ids,
        'has_time_component': False,
        'time_range': None,
        'retrieved_chunks': [],
        'retrieval_quality': 'poor',
        'retry_count': 0,
        'tool_calls': [],
        'tool_results': [],
        'answer': '',
        'citations': [],
        'conversation_history': [],
        'next_action': 'classify',
        'error': None
    }