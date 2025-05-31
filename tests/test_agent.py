"""
Tests for the IBKR AI agent implementation.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from langchain.schema import AgentAction, AgentFinish
from ibkr_ai_agent.agent import IBKRAgent, IBKRAgentPrompt, IBKROutputParser
from ibkr_ai_agent.mcp_server import IBKRMCPServer

@pytest.fixture
def mock_bedrock():
    """Mock BedrockChat."""
    from langchain_core.runnables import Runnable
    
    class MockRunnable(Runnable):
        def __init__(self):
            self.predict = AsyncMock()
            self.predict.return_value = '''```json
{
    "action": "Final Answer",
    "action_input": "Test response"
}
```'''

        def invoke(self, input, config=None, **kwargs):
            self.predict.call_args_list.append((input,))
            return self.predict.return_value
        
        async def ainvoke(self, input, config=None, **kwargs):
            self.predict.call_args_list.append((input,))
            return await self.predict(input)
    
    mock = MockRunnable()
    mock.predict.call_args_list = []  # Initialize empty call list for tracking
    
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
    return mock

@pytest.fixture
def agent(mock_bedrock, mock_server):
    """Create agent instance with mocked components."""
    with patch('ibkr_ai_agent.agent.BedrockChat', return_value=mock_bedrock), \
         patch('ibkr_ai_agent.mcp_server.get_server', return_value=mock_server), \
         patch('ibkr_ai_agent.mcp_server.IBKRMCPServer') as mock_ibkr:
        # Mock IBKR connection
        mock_ibkr.return_value.isConnected.return_value = True
        agent = IBKRAgent()
        return agent

def test_prompt_template():
    """Test prompt template formatting."""
    prompt = IBKRAgentPrompt(
        input_variables=["input", "chat_history", "tools"]
    )
    
    tools = [
        Mock(name="tool1", description="Tool 1 description"),
        Mock(name="tool2", description="Tool 2 description")
    ]
    
    result = prompt.format(
        input="What's my balance?",
        chat_history="Previous chat",
        tools=tools
    )
    
    assert "What's my balance?" in result
    assert "Previous chat" in result
    assert "Tool 1 description" in result
    assert "Tool 2 description" in result

def test_output_parser():
    """Test output parser functionality."""
    parser = IBKROutputParser()
    
    # Test final answer
    response = '''```json
{
    "action": "Final Answer",
    "action_input": "Your balance is $100,000"
}
```'''
    result = parser.parse(response)
    assert isinstance(result, AgentFinish)
    assert result.return_values["output"] == "Your balance is $100,000"
    
    # Test tool action
    response = '''```json
{
    "action": "get_account_summary",
    "action_input": {}
}
```'''
    result = parser.parse(response)
    assert isinstance(result, AgentAction)
    assert result.tool == "get_account_summary"
    assert result.tool_input == {}
    
    # Test invalid JSON
    response = "Invalid JSON"
    result = parser.parse(response)
    assert isinstance(result, AgentFinish)
    assert "error" in result.return_values["output"].lower()

@pytest.mark.asyncio
async def test_agent_execution(agent, mock_bedrock):
    """Test agent execution flow."""
    result = await agent.run("What's my balance?")
    assert result == "Test response"
    assert mock_bedrock.predict.called

@pytest.mark.asyncio
async def test_agent_error_handling(agent, mock_bedrock):
    """Test agent error handling."""
    mock_bedrock.predict.side_effect = Exception("API Error")
    result = await agent.run("What's my balance?")
    assert "Error" in result
    assert "API Error" in result

def test_tool_registration(agent):
    """Test tool registration."""
    tool_names = [tool.name for tool in agent.tools]
    assert 'tool1' in tool_names
    assert 'tool2' in tool_names

@pytest.mark.asyncio
async def test_memory_integration(agent, mock_bedrock):
    """Test memory integration."""
    # First interaction
    await agent.run("Question 1")
    
    # Second interaction
    await agent.run("Question 2")
    
    # Verify memory was used
    calls = mock_bedrock.predict.call_args_list
    # Find a call that contains both the first question and its response
    found_memory = False
    for call in calls:
        call_text = str(call[0])  # Convert the entire call tuple to string
        if "Question 1" in call_text and "Test response" in call_text:
            found_memory = True
            break
    assert found_memory, "Chat history not found in any LLM calls"
