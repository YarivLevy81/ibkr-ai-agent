"""
Tests for the IBKR AI agent implementation.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, call
from langchain_core.messages import AIMessage, HumanMessage, FunctionMessage
from langchain_core.agents import AgentFinish, AgentActionMessageLog
from ibkr_ai_agent.agent import IBKRAgent, State
from ibkr_ai_agent.mcp_server import IBKRMCPServer

@pytest.fixture
def mock_bedrock():
    """Mock BedrockChat."""
    mock = Mock()
    mock.predict = AsyncMock()
    mock.predict.return_value = AIMessage(content="Test response")
    return mock

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    mock = Mock()
    mock.get_tools.return_value = {
        'tool1': {
            'description': 'Tool 1 description',
            'input_schema': {}
        },
        'tool2': {
            'description': 'Tool 2 description',
            'input_schema': {}
        }
    }
    mock.execute_tool = Mock(return_value="Tool executed")
    return mock

@pytest.fixture
def mock_functions_agent():
    """Mock OpenAI functions agent."""
    mock = Mock()
    # First call tries to use tool1, second call finishes
    mock.invoke.side_effect = [
        AgentActionMessageLog(
            tool="tool1",
            tool_input={},
            log="Using tool1",
            message_log=[AIMessage(content="Using tool1")]
        ),
        AgentFinish(
            return_values={"output": "Tool execution complete"},
            log="Tool executed successfully"
        )
    ]
    return mock

@pytest.fixture
def mock_workflow():
    """Mock LangGraph workflow."""
    mock = Mock()
    mock.ainvoke = AsyncMock()
    mock.ainvoke.return_value = {
        "messages": [
            HumanMessage(content="What's my balance?"),
            AIMessage(content="Test response")
        ],
        "next": "end"
    }
    return mock

@pytest.fixture
def agent(mock_bedrock, mock_server, mock_functions_agent, mock_workflow):
    """Create agent instance with mocked components."""
    with patch('ibkr_ai_agent.agent.BedrockChat', return_value=mock_bedrock), \
         patch('ibkr_ai_agent.mcp_server.get_server', return_value=mock_server), \
         patch('ibkr_ai_agent.mcp_server.IBKRMCPServer') as mock_ibkr, \
         patch('langchain.agents.create_openai_functions_agent', return_value=mock_functions_agent), \
         patch('langgraph.graph.StateGraph.compile', return_value=mock_workflow):
        # Mock IBKR connection
        mock_ibkr.return_value.isConnected.return_value = True
        agent = IBKRAgent()
        agent.workflow = mock_workflow  # Directly set the mocked workflow
        return agent

@pytest.mark.asyncio
async def test_agent_execution(agent, mock_workflow):
    """Test agent execution flow."""
    result = await agent.run("What's my balance?")
    assert result == "Test response"
    assert mock_workflow.ainvoke.called
    
    # Verify state structure without using isinstance
    call_args = mock_workflow.ainvoke.call_args[0][0]
    assert "messages" in call_args
    assert "next" in call_args
    assert len(call_args["messages"]) == 1
    assert call_args["messages"][0].content == "What's my balance?"
    assert call_args["next"] == "agent"

@pytest.mark.asyncio
async def test_agent_error_handling(agent, mock_workflow):
    """Test agent error handling."""
    mock_workflow.ainvoke.side_effect = Exception("API Error")
    result = await agent.run("What's my balance?")
    assert "Error" in result
    assert "API Error" in result

def test_tool_registration(agent):
    """Test tool registration."""
    tool_names = [tool.name for tool in agent.tools]
    assert 'tool1' in tool_names
    assert 'tool2' in tool_names

def test_prompt_creation(agent):
    """Test prompt creation."""
    prompt = agent.prompt
    assert "Interactive Brokers account" in str(prompt)
    assert "{chat_history}" in str(prompt)
    assert "{input}" in str(prompt)
    assert "{tools}" in str(prompt)
    assert "agent_scratchpad" in str(prompt)

@pytest.mark.asyncio
async def test_agent_tool_execution(agent, mock_functions_agent, mock_workflow, mock_server):
    """Test agent tool execution flow."""
    # Setup workflow to simulate the full execution cycle
    def mock_ainvoke(state):
        # First call - agent decides to use tool1
        result1 = mock_functions_agent.invoke(state)
        if isinstance(result1, AgentActionMessageLog):
            # Execute the tool
            tool_result = mock_server.execute_tool(result1.tool, result1.tool_input)
            state["messages"].extend([
                AIMessage(content=result1.log),
                FunctionMessage(content=str(tool_result), name=result1.tool)
            ])
            # Second call - agent processes tool result and finishes
            result2 = mock_functions_agent.invoke(state)
            state["messages"].append(AIMessage(content=result2.return_values["output"]))
        
        return {
            "messages": state["messages"],
            "next": "end"
        }
    
    mock_workflow.ainvoke.side_effect = mock_ainvoke
    
    result = await agent.run("Execute tool1")
    assert result == "Tool execution complete"
    assert mock_functions_agent.invoke.call_count == 2  # First to use tool, second to finish
    assert mock_server.execute_tool.called  # Verify tool was executed
