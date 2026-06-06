import json
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from groq import Groq

from ..config import config
from ..ingestion.time_parser import time_parser, TimeRange
from ..vector_store import pinecone_client
from ..embedding import bge_embedder
from .state import AgentState, get_initial_state

# Groq client
groq_client = Groq(api_key=config.GROQ_API_KEY)

class RAGAgent:
    """LangGraph agent with self-correction loop"""
    
    def __init__(self):
        self.graph = self._build_graph()
        self.memory = MemorySaver()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("classify", self.classify_question)
        workflow.add_node("extract_time", self.extract_time_range)
        workflow.add_node("retrieve", self.retrieve_chunks)
        workflow.add_node("grade", self.grade_retrieval)
        workflow.add_node("rewrite", self.rewrite_query)
        workflow.add_node("use_tools", self.execute_tools)
        workflow.add_node("generate", self.generate_answer)
        
        workflow.set_entry_point("classify")
        
        workflow.add_conditional_edges(
            "classify",
            self.after_classify,
            {
                "has_time": "extract_time",
                "no_time": "retrieve",
                "needs_tool": "use_tools"
            }
        )
        
        workflow.add_edge("extract_time", "retrieve")
        
        workflow.add_conditional_edges(
            "retrieve",
            self.after_retrieve,
            {
                "good": "generate",
                "partial": "generate",
                "poor": "rewrite"
            }
        )
        
        workflow.add_conditional_edges(
            "rewrite",
            self.after_rewrite,
            {
                "retry": "retrieve",
                "max_retries": "generate"
            }
        )
        
        workflow.add_edge("use_tools", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def classify_question(self, state: AgentState) -> AgentState:
        """Classify question type: time-based, tool-based, or RAG-based"""
        question = state['question'].lower()
        
        tool_keywords = {
            'engagement_rate': ['engagement rate', 'engagement', 'likes', 'comments', 'views'],
            'metadata': ['creator', 'follower count', 'who is', 'upload date', 'hashtags']
        }
        
        needs_tool = False
        if any(kw in question for kw in tool_keywords['engagement_rate']):
            needs_tool = True
            state['tool_calls'].append({'tool': 'engagement_rate', 'params': {}})
        elif any(kw in question for kw in tool_keywords['metadata']):
            needs_tool = True
            state['tool_calls'].append({'tool': 'metadata', 'params': {}})
        
        time_keywords = ['second', 'seconds', 'minute', 'minutes', 'timestamp', 
                         'at ', 'around', 'about', 'first', 'last', 'opening', 
                         'intro', 'middle', 'outro', 'between']
        
        has_time = any(kw in question for kw in time_keywords)
        
        state['has_time_component'] = has_time
        
        if needs_tool:
            state['next_action'] = 'needs_tool'
        elif has_time:
            state['next_action'] = 'has_time'
        else:
            state['next_action'] = 'no_time'
        
        return state
    
    def after_classify(self, state: AgentState) -> Literal["has_time", "no_time", "needs_tool"]:
        if state['next_action'] == 'needs_tool':
            return "needs_tool"
        elif state['next_action'] == 'has_time':
            return "has_time"
        return "no_time"
    
    def _get_video_duration(self, video_ids: List[str]) -> float:
        """Fetch actual video duration from stored metadata"""
        try:
            from ..tools.metadata_tool import get_video_metadata
            for video_id in video_ids:
                metadata = get_video_metadata([video_id])
                if video_id in metadata:
                    duration = metadata[video_id].get('duration_seconds', 0)
                    if duration and duration > 0:
                        return float(duration)
            return 0.0
        except Exception as e:
            print(f"Could not fetch video duration: {e}")
            return 0.0
    
    def extract_time_range(self, state: AgentState) -> AgentState:
        """Extract time range from question using time_parser with actual video duration"""
        
        # Get actual video duration from metadata
        video_duration = self._get_video_duration(state['video_ids'])
        
        # If no duration found, try to get from retrieved chunks or use a reasonable default
        if video_duration <= 0 and state.get('retrieved_chunks'):
            for chunk in state['retrieved_chunks']:
                chunk_duration = chunk.get('duration', 0)
                if chunk_duration > 0:
                    video_duration = chunk_duration
                    break
        
        # If still no duration, use 0 which will disable time-based filtering
        if video_duration <= 0:
            print("No video duration available, time-based queries may be inaccurate")
            video_duration = 0
        
        time_range = time_parser.parse(state['question'], video_duration) if video_duration > 0 else None
        
        if time_range:
            # Clamp to actual video duration
            clamped_start = max(0, min(time_range.start, video_duration))
            clamped_end = max(0, min(time_range.end, video_duration))
            
            state['time_range'] = {
                'start': clamped_start,
                'end': clamped_end,
                'fuzzy': time_range.fuzzy
            }
            print(f"Time range: {clamped_start:.1f}-{clamped_end:.1f}s (video duration: {video_duration:.1f}s)")
        
        return state
    
    def retrieve_chunks(self, state: AgentState) -> AgentState:
        """Retrieve relevant chunks from Pinecone"""
        
        question = state['question']
        video_ids = state['video_ids']
        time_range = state.get('time_range')
        
        question_embedding = bge_embedder.embed_text(question)
        
        all_chunks = []
        
        for video_id in video_ids:
            filters = {'video_id': video_id}
            
            if time_range:
                filters['start_time'] = {'$lt': time_range['end']}
                filters['end_time'] = {'$gt': time_range['start']}
            
            if time_range:
                range_duration = time_range['end'] - time_range['start']
                if range_duration <= 60:
                    filters['chunk_level'] = 'fine'
                elif range_duration <= 180:
                    filters['chunk_level'] = 'medium'
                else:
                    filters['chunk_level'] = 'coarse'
            
            results = pinecone_client.query(
                query_embedding=question_embedding,
                top_k=5,
                filters=filters
            )
            
            for result in results:
                result['video_id'] = video_id
                all_chunks.append(result)
        
        all_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        state['retrieved_chunks'] = all_chunks[:10]
        
        return state
    
    def grade_retrieval(self, state: AgentState) -> AgentState:
        """Grade quality of retrieved chunks"""
        
        chunks = state['retrieved_chunks']
        
        if not chunks:
            state['retrieval_quality'] = 'poor'
            state['next_action'] = 'poor'
            return state
        
        top_score = chunks[0].get('score', 0) if chunks else 0
        
        if top_score > 0.7:
            state['retrieval_quality'] = 'good'
        elif top_score > 0.4:
            state['retrieval_quality'] = 'partial'
        else:
            state['retrieval_quality'] = 'poor'
        
        return state
    
    def after_retrieve(self, state: AgentState) -> Literal["good", "partial", "poor"]:
        return state['retrieval_quality']
    
    def rewrite_query(self, state: AgentState) -> AgentState:
        """Rewrite poor query for better retrieval"""
        
        original_question = state['question']
        retry_count = state['retry_count']
        
        if retry_count >= 2:
            state['next_action'] = 'max_retries'
            return state
        
        if 'time' in original_question.lower():
            rewritten = f"What content is discussed {original_question}"
        else:
            rewritten = f"Main topics and key points about {original_question}"
        
        state['question'] = rewritten
        state['retry_count'] = retry_count + 1
        state['next_action'] = 'retry'
        
        return state
    
    def after_rewrite(self, state: AgentState) -> Literal["retry", "max_retries"]:
        if state['next_action'] == 'retry':
            return "retry"
        return "max_retries"
    
    def execute_tools(self, state: AgentState) -> AgentState:
        """Execute tool calls (engagement rate, metadata)"""
        
        from ..tools.engagement_tool import get_engagement_rates
        from ..tools.metadata_tool import get_video_metadata
        
        results = []
        
        for tool_call in state['tool_calls']:
            tool_name = tool_call['tool']
            
            if tool_name == 'engagement_rate':
                result = get_engagement_rates(state['video_ids'])
                results.append(result)
            elif tool_name == 'metadata':
                result = get_video_metadata(state['video_ids'])
                results.append(result)
        
        state['tool_results'] = results
        
        return state
    
    def generate_answer(self, state: AgentState) -> AgentState:
        """Generate final answer with citations - STRICTLY no hallucination"""
        
        context = ""
        citations = []
        videos_with_content = set()
        
        if state.get('tool_results'):
            context = str(state['tool_results'])
        elif state.get('retrieved_chunks'):
            for idx, chunk in enumerate(state['retrieved_chunks'][:5]):
                video_id = chunk.get('video_id', 'Unknown')
                start = chunk.get('start_time', 0)
                end = chunk.get('end_time', 0)
                text = chunk.get('text', '')
                
                if text and len(text.strip()) > 10:
                    context += f"\n[Video {video_id}, {start:.1f}-{end:.1f}s]: {text}\n"
                    videos_with_content.add(video_id)
                    
                    citations.append({
                        'video_id': video_id,
                        'timestamp': f"{start:.1f}-{end:.1f}s",
                        'text': text[:300]
                    })
        
        # Get video durations for context
        video_durations = {}
        try:
            from ..tools.metadata_tool import get_video_metadata
            for video_id in state['video_ids']:
                metadata = get_video_metadata([video_id])
                if video_id in metadata:
                    video_durations[video_id] = metadata[video_id].get('duration_seconds', 0)
        except Exception as e:
            print(f"Could not fetch durations: {e}")
        
        # Check which videos have no content
        missing_videos = [vid for vid in state['video_ids'] if vid not in videos_with_content]
        
        if not context or len(context.strip()) < 50:
            state['answer'] = "I don't have enough transcript data to answer this question. Please make sure videos have been ingested successfully."
            state['citations'] = []
            return state
        
        # Build duration info dynamically
        duration_info = "\n".join([f"- Video {vid}: {duration:.1f} seconds long" for vid, duration in video_durations.items() if duration > 0])
        
        missing_video_note = ""
        if missing_videos:
            missing_video_note = f"\nNOTE: No transcript data available for Videos {', '.join(missing_videos)}. Only answer based on available videos."
        
        # STRICT system prompt to prevent hallucination
        system_prompt = f"""You are a video analysis assistant. Your ONLY source of information is the context provided below.

VIDEO DURATIONS:
{duration_info}

CRITICAL RULES - VIOLATIONS WILL CAUSE INCORRECT ANSWERS:
1. ONLY use information that appears EXPLICITLY in the context.
2. If the context does not contain the answer, say "I cannot find that information in the video transcript."
3. DO NOT invent, assume, or hallucinate any information not in the context.
4. DO NOT use your general knowledge about any topics not explicitly mentioned in the context.
5. ONLY cite timestamps that appear in the context exactly as shown.
6. If the context has no information about a video, state that clearly.
7. Timestamps beyond the video duration (see above) are impossible - do not use them.
{missing_video_note}

You have access ONLY to these video transcripts. No other knowledge."""

        user_prompt = f"""CONTEXT (YOUR ONLY SOURCE OF TRUTH):
{context}

QUESTION: {state['question']}

INSTRUCTIONS:
- Answer ONLY using the context above.
- If the context doesn't have the answer, say "The transcript does not contain that information."
- Cite timestamps exactly as they appear in the context.
- Be brief and factual."""

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                stream=False
            )
            
            answer = response.choices[0].message.content
            state['answer'] = answer
            state['citations'] = citations
            
        except Exception as e:
            state['answer'] = f"Error generating answer: {str(e)}"
            state['error'] = str(e)
        
        return state
    
    def invoke(self, question: str, session_id: str, video_ids: List[str]) -> Dict:
        """Invoke the agent"""
        
        initial_state = get_initial_state(question, session_id, video_ids)
        
        result = self.graph.invoke(initial_state)
        
        return {
            'answer': result['answer'],
            'citations': result['citations'],
            'error': result.get('error')
        }


rag_agent = RAGAgent()
