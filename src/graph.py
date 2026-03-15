from langgraph.graph import StateGraph, END
from src.utils.state import AgentState
from src.agents.researcher import researcher_node, protocol_analyzer_node
from src.agents.designer import designer_node
from src.agents.critic import critic_node
from src.agents.reporter import reporter_node

def create_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("analyzer", protocol_analyzer_node)
    workflow.add_node("designer", designer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("reporter", reporter_node)

    # Define Flow
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyzer")
    workflow.add_edge("analyzer", "designer")
    workflow.add_edge("designer", "critic")
    
    # The Loop: Researcher -> Designer -> Critic -> Refine Designer
    # If invalid, go back to designer. If valid OR too many iterations, go to reporter.
    workflow.add_conditional_edges(
        "critic",
        lambda x: "designer" if not x.is_valid and x.iterations < 3 else "reporter"
    )
    
    # Final step: reporter to END
    workflow.add_edge("reporter", END)
    
    return workflow.compile()
