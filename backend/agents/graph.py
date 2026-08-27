from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    detect_and_translate_node,
    classify_intent_node,
    retrieve_documents_node,
    generate_answer_node,
    validate_answer_node,
    query_rewrite_node,
    format_and_translate_response_node
)

def build_self_rag_graph():
    """
    Constructs and compiles the Self-RAG state graph workflow.
    """
    workflow = StateGraph(AgentState)
    
    # 1. Register Nodes
    workflow.add_node("detect_and_translate", detect_and_translate_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("retrieve_documents", retrieve_documents_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("validate_answer", validate_answer_node)
    workflow.add_node("query_rewrite", query_rewrite_node)
    workflow.add_node("format_response", format_and_translate_response_node)
    
    # 2. Add Transitions
    workflow.set_entry_point("detect_and_translate")
    
    workflow.add_edge("detect_and_translate", "classify_intent")
    workflow.add_edge("classify_intent", "retrieve_documents")
    workflow.add_edge("retrieve_documents", "generate_answer")
    workflow.add_edge("generate_answer", "validate_answer")
    workflow.add_edge("query_rewrite", "retrieve_documents")
    workflow.add_edge("format_response", END)
    
    # 3. Conditional reflection routing logic
    def should_reflect(state: AgentState) -> str:
        validation = state.get("validation_result", "pass")
        loop_count = state.get("loop_count", 0)
        
        # Stop and compile response if validation passes, or if retry limit is reached
        if validation == "pass" or loop_count >= 3:
            return "format_and_translate"
        else:
            return "rewrite_query"
            
    workflow.add_conditional_edges(
        "validate_answer",
        should_reflect,
        {
            "format_and_translate": "format_response",
            "rewrite_query": "query_rewrite"
        }
    )
    
    # 4. Compile the graph
    app = workflow.compile()
    print("[LangGraph] Self-RAG Agent workflow successfully compiled.")
    return app

# Expose compiled app
self_rag_agent = build_self_rag_graph()
