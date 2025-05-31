"""
IBKR AI Agent - Natural language interface for Interactive Brokers
"""
from .agent import IBKRAgent
from .cli import main

__version__ = "0.1.0"
__all__ = ["IBKRAgent", "main"]
