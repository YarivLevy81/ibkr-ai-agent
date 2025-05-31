"""
LangGraph agent implementation for interacting with IBKR assets using natural language.
"""
from typing import Dict, Any, List, Annotated, Sequence, TypedDict, cast, Tuple
import json
from typing import Union
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, FunctionMessage, HumanMessage
from langchain.tools import BaseTool, StructuredTool, Tool
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_community.chat_models import BedrockChat
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import AIMessage, HumanMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langgraph.graph import StateGraph, END
from langchain.agents import create_openai_functions_agent
from langchain_core.agents import AgentActionMessageLog, AgentFinish

class State(TypedDict):
    """State definition for the agent."""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    next: str

class IBKRAgent:
    """LangGraph agent for interacting with IBKR account."""
    
    def __init__(self, model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"):
        """Initialize the IBKR agent with specified model."""
        self.llm = BedrockChat(
            model_id=model_id,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            model_kwargs={"temperature": 0.1, "max_tokens": 2000}
        )
        
        self.tools = self._get_tools()
        self.prompt = self._create_prompt()
        
        # Create agent with function calling
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent graph
        self.workflow = self._create_workflow()

    def _get_tools(self) -> List[BaseTool]:
        """Create tools from MCP server capabilities."""
        from .mcp_server import get_server
        
        tools = []
        for name, info in get_server().get_tools().items():
            tools.append(
                Tool(
                    name=name,
                    description=info['description'],
                    func=lambda n=name, **kwargs: get_server().execute_tool(n, kwargs)
                )
            )
        return tools

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the agent prompt template."""
        template = """You are an AI assistant that helps users interact with their Interactive Brokers account.
You can help with tasks like checking account balance, viewing positions, getting asset information, and placing trades.

Previous conversation:
{chat_history}

Current question: {input}

You have access to these tools:

{tools}

Remember:
1. Always check account information before suggesting trades
2. Confirm trade details with users before execution
3. Provide clear explanations of market data
4. Be cautious with order placement
5. Use proper security types (STK for stocks, CASH for forex)

Think through the required steps carefully, then respond."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        return prompt

    def _create_workflow(self) -> StateGraph:
        """Create the agent workflow graph."""
        workflow = StateGraph(State)
        
        # Define the agent node that processes messages
        def agent_node(state: State) -> dict:
            # Get agent output
            output = self.agent.invoke(state)
            
            # If agent wants to use a tool
            if isinstance(output, AgentActionMessageLog):
                # Execute the tool
                tool_name = output.tool
                tool_args = output.tool_input
                tool = next(t for t in self.tools if t.name == tool_name)
                observation = tool.func(**tool_args)
                
                # Add tool result to messages
                state["messages"].append(
                    FunctionMessage(content=str(observation), name=tool_name)
                )
                return {"next": "agent"}
            
            # If agent is done
            elif isinstance(output, AgentFinish):
                state["messages"].append(AIMessage(content=output.return_values["output"]))
                return {"next": "end"}
            
            # Unexpected output
            else:
                raise ValueError(f"Unexpected output type: {type(output)}")
        
        # Add nodes and edges
        workflow.add_node("agent", agent_node)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", "agent")
        workflow.add_edge("agent", END)
        
        return workflow.compile()

    async def run(self, query: str) -> str:
        """Run the agent with a user query."""
        try:
            # Initialize state
            state = State(
                messages=[HumanMessage(content=query)],
                next="agent"
            )
            
            # Run the workflow
            result = await self.workflow.ainvoke(state)
            
            # Extract the final answer
            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                return final_message.content
            else:
                return str(final_message.content)
            
        except Exception as e:
            return f"Error: {str(e)}"
