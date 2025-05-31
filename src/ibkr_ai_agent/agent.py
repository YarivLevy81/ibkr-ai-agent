"""
LangChain agent implementation for interacting with IBKR assets using natural language.
"""
from typing import Dict, Any, List
import json
from typing import Union
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish, BaseOutputParser
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import BedrockChat
from langchain.chains import LLMChain
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from langchain.agents import AgentOutputParser

class IBKROutputParser(AgentOutputParser):
    """Parser for IBKR agent output."""
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        """Parse text into agent action or finish."""
        try:
            response = text.strip()
            # Extract JSON from markdown code block if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            
            response_json = json.loads(response)
            action = response_json["action"]
            action_input = response_json["action_input"]
            
            if action == "Final Answer":
                return AgentFinish(
                    return_values={"output": action_input},
                    log=text
                )
            
            return AgentAction(
                tool=action,
                tool_input=action_input,
                log=text
            )
        except Exception as e:
            return AgentFinish(
                return_values={
                    "output": f"I encountered an error: {str(e)}. Please rephrase your request."
                },
                log=text
            )

class IBKRAgentPrompt(StringPromptTemplate):
    """Custom prompt template for IBKR agent."""
    
    template: str = """You are an AI assistant that helps users interact with their Interactive Brokers account.
You can help with tasks like checking account balance, viewing positions, getting asset information, and placing trades.

Previous conversation:
{chat_history}

Current question: {input}

You have access to these tools:

{tools}

To use a tool, respond with:
```json
{{
    "action": "tool_name",
    "action_input": {{tool parameters}}
}}
```

To provide a direct response without using tools, respond with:
```json
{{
    "action": "Final Answer",
    "action_input": "Your response here"
}}
```

Remember:
1. Always check account information before suggesting trades
2. Confirm trade details with users before execution
3. Provide clear explanations of market data
4. Be cautious with order placement
5. Use proper security types (STK for stocks, CASH for forex)

Think through the required steps carefully, then respond:"""

    def format(self, **kwargs) -> str:
        """Format the prompt template."""
        # Format tools list before template formatting
        tools = kwargs.get("tools", [])
        if isinstance(tools, list):
            tools_str = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
            kwargs["tools"] = tools_str
            
        # Format chat history
        chat_history = kwargs.get("chat_history", "")
        if isinstance(chat_history, list):
            chat_history = "\n".join([f"Human: {m.content}" if m.type == "human" else f"Assistant: {m.content}" for m in chat_history])
            kwargs["chat_history"] = chat_history
            
        return self.template.format(**kwargs)

class IBKRAgent:
    """LangChain agent for interacting with IBKR account."""
    
    def __init__(self, model_id: str = "anthropic.claude-v2"):
        """Initialize the IBKR agent with specified model."""
        self.llm = BedrockChat(
            model_id=model_id,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            model_kwargs={"temperature": 0.1, "max_tokens": 2000}
        )
        
        self.tools = self._get_tools()
        self.prompt = IBKRAgentPrompt(
            input_variables=["input", "chat_history", "tools"]
        )
        
        self.output_parser = IBKROutputParser()
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            input_key="input"
        )
        
        # Create LLMChain with prompt and llm
        self.llm_chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory
        )
        
        self.agent = LLMSingleActionAgent(
            llm_chain=self.llm_chain,
            output_parser=self.output_parser,
            stop=["\nObservation:"],
            allowed_tools=[tool.name for tool in self.tools]
        )
        
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5
        )

    def _get_tools(self) -> List[Tool]:
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


    async def run(self, query: str) -> str:
        """Run the agent with a user query."""
        try:
            # Run the agent with the query
            response = await self.agent_executor.arun(
                input=query,
                tools=self.tools
            )
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"
