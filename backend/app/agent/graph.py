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
    
    def extract_time_range(self, state: AgentState) -> AgentState:
        """Extract time range from question using time_parser"""
        video_duration = 300.0
        
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
        
        print(f"\n=== RETRIEVING CHUNKS ===")
        print(f"Question: {question}")
        print(f"Video IDs requested: {video_ids}")
        
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
            
            print(f"Querying for video_id: {video_id} with filters: {filters}")
            
            results = pinecone_client.query(
                query_embedding=question_embedding,
                top_k=10,
                filters=filters
            )
            
            print(f"Raw results count for {video_id}: {len(results)}")
            
            for result in results:
                result_video_id = result.get('video_id')
                if result_video_id and result_video_id.upper() == video_id.upper():
                    result['video_id'] = video_id
                    all_chunks.append(result)
                    print(f"  Added chunk with score={result.get('score', 0):.4f}")
            
            print(f"Filtered results for {video_id}: {len([r for r in results if r.get('video_id') == video_id])}")
        
        # Fallback for missing video
        video_b_chunks = [c for c in all_chunks if c.get('video_id') == 'B']
        if len(video_b_chunks) == 0 and 'B' in video_ids:
            print("\nWARNING: No results for Video B. Attempting query without video_id filter...")
            
            results = pinecone_client.query(
                query_embedding=question_embedding,
                top_k=10,
                filters=None
            )
            
            for result in results:
                result_video_id = result.get('video_id')
                if result_video_id and result_video_id.upper() == 'B':
                    result['video_id'] = 'B'
                    all_chunks.append(result)
                    print(f"Fallback: Added Video B chunk")
        
        all_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        chunks_by_video = {}
        for chunk in all_chunks:
            vid = chunk.get('video_id', 'unknown')
            chunks_by_video[vid] = chunks_by_video.get(vid, 0) + 1
        
        print(f"\n=== RETRIEVAL SUMMARY ===")
        for vid, count in chunks_by_video.items():
            print(f"Video {vid}: {count} chunks")
        
        state['retrieved_chunks'] = all_chunks[:10]
        
        return state
    
    def grade_retrieval(self, state: AgentState) -> AgentState:
        """Grade quality of retrieved chunks"""
        
        chunks = state['retrieved_chunks']
        
        if not chunks:
            state['retrieval_quality'] = 'poor'
            state['next_action'] = 'poor'
            return state
        
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
        
        context = ""
        citations = []
        videos_with_data = set()
        
        if state.get('tool_results'):
            context = str(state['tool_results'])
        elif state.get('retrieved_chunks'):
            for idx, chunk in enumerate(state['retrieved_chunks'][:5]):
                video_id = chunk.get('video_id', 'Unknown')
                start = chunk.get('start_time', 0)
                end = chunk.get('end_time', 0)
                text = chunk.get('text', '')
                
                videos_with_data.add(video_id)
                
                start_rounded = round(start, 1)
                end_rounded = round(end, 1)
                
                context += f"\n[Video {video_id}, {start_rounded}-{end_rounded}s]: {text}\n"
                
                citations.append({
                    'video_id': video_id,
                    'timestamp': f"{start_rounded}-{end_rounded}s",
                    'text': text[:200]
                })
            
            for video_id in state['video_ids']:
                if video_id not in videos_with_data:
                    context += f"\n[Video {video_id}]: No transcript data available for this video.\n"
                    print(f"WARNING: No data for Video {video_id}")
        else:
            context = "No relevant information found."
        
        missing_videos = [vid for vid in state['video_ids'] if vid not in videos_with_data]
        availability_note = ""
        if missing_videos:
            availability_note = f"\nNOTE: Videos {', '.join(missing_videos)} have no transcript data available. Only answer based on available videos."
        
        system_prompt = f"""You are a video analysis expert. Answer questions about video content, engagement metrics, and creator information.

Always cite your sources using [Video A] or [Video B] with timestamps.

If comparing videos, highlight differences clearly.

Be concise but informative.

If a video is mentioned in the question but no data is available for that video, state clearly: "No information available for Video X."

{availability_note}
"""

        user_prompt = f"""Context:
{context}

Question: {state['question']}

Provide a clear answer with citations."""

        try:
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


rag_agent = RAGAgent()
