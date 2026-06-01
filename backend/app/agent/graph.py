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

#  Groq client
groq_client = Groq(api_key=config.GROQ_API_KEY)

class RAGAgent:
    """LangGraph agent with self-correction loop"""
    
    def __init__(self):
        self.graph = self._build_graph()
        self.memory = MemorySaver()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # nodes
        workflow.add_node("classify", self.classify_question)
        workflow.add_node("extract_time", self.extract_time_range)
        workflow.add_node("retrieve", self.retrieve_chunks)
        workflow.add_node("grade", self.grade_retrieval)
        workflow.add_node("rewrite", self.rewrite_query)
        workflow.add_node("use_tools", self.execute_tools)
        workflow.add_node("generate", self.generate_answer)
        
        # entry point
        workflow.set_entry_point("classify")
        
        # conditional edges
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
                "partial": "generate",  #Generate but note limitation
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
        
        # Check for tool-based questions
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
        
        # Check time-component
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
    
    def extract_time_range(self, state: AgentState) -> AgentState:
        """Extract time range from question using time_parser"""
        
        # Need video duration to parse percentage-based queries
        # For now, use default 300 seconds (5 min)
        # In production, fetch from stored metadata
        video_duration = 300.0  # Default
        
        time_range = time_parser.parse(state['question'], video_duration)
        
        if time_range:
            state['time_range'] = {
                'start': time_range.start,
                'end': time_range.end,
                'fuzzy': time_range.fuzzy
            }
        
        return state
    
    def retrieve_chunks(self, state: AgentState) -> AgentState:
        """Retrieve relevant chunks from Pinecone"""
        
        question = state['question']
        video_ids = state['video_ids']
        time_range = state.get('time_range')
        
        # Generate embedding for question
        question_embedding = bge_embedder.embed_text(question)
        
        all_chunks = []
        
        for video_id in video_ids:
            # Build filters
            filters = {'video_id': video_id}
            
            # Add time filter if present
            if time_range:
                filters['start_time'] = {'$lt': time_range['end']}
                filters['end_time'] = {'$gt': time_range['start']}
            
            # Determine chunk level based on time range
            if time_range:
                range_duration = time_range['end'] - time_range['start']
                if range_duration <= 60:
                    filters['chunk_level'] = 'fine'
                elif range_duration <= 180:
                    filters['chunk_level'] = 'medium'
                else:
                    filters['chunk_level'] = 'coarse'
            
            # Query Pinecone
            results = pinecone_client.query(
                query_embedding=question_embedding,
                top_k=5,
                filters=filters
            )
            
            for result in results:
                result['video_id'] = video_id
                all_chunks.append(result)
        
        # Sort by score (relevance)
        all_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        state['retrieved_chunks'] = all_chunks[:10]  # Keep top 10
        
        return state
    
    def grade_retrieval(self, state: AgentState) -> AgentState:
        """Grade quality of retrieved chunks"""
        
        chunks = state['retrieved_chunks']
        question = state['question']
        
        if not chunks:
            state['retrieval_quality'] = 'poor'
            state['next_action'] = 'poor'
            return state
        
        # Check if chunks are relevant
        # Use LLM to grade (simplified for now)
        top_score = chunks[0]['score'] if chunks else 0
        
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
        
        # Simple query expansion
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
        """Generate final answer with citations"""
        
        # Prepare context
        context = ""
        citations = []
        
        if state.get('tool_results'):
            # Use tool results directly
            context = str(state['tool_results'])
        elif state.get('retrieved_chunks'):
            # Build context from retrieved chunks
            for idx, chunk in enumerate(state['retrieved_chunks'][:5]):
                video_id = chunk['video_id']
                start = chunk.get('start_time', 0)
                end = chunk.get('end_time', 0)
                text = chunk.get('text', '')
                
                context += f"\n[Video {video_id}, {start:.0f}-{end:.0f}s]: {text}\n"
                
                citations.append({
                    'video_id': video_id,
                    'timestamp': f"{start:.0f}-{end:.0f}s",
                    'text': text[:200]
                })
        else:
            context = "No relevant information found."
        
        # Build prompt
        system_prompt = """You are a video analysis expert. Answer questions about video content, engagement metrics, and creator information.

Always cite your sources using [Video A] or [Video B] with timestamps.

If comparing videos, highlight differences clearly.

Be concise but informative."""

        user_prompt = f"""Context:
{context}

Question: {state['question']}

Provide a clear answer with citations."""

        try:
            # Generate with Groq
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
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


# Singleton instance
rag_agent = RAGAgent()