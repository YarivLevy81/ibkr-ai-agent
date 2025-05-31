"""
MCP server implementation for Interactive Brokers API integration.
Provides tools for interacting with IBKR accounts and assets.
"""
import os
from typing import Any, Dict

from dotenv import load_dotenv
from ib_insync import IB, Forex, Stock

# Load environment variables
load_dotenv()

class IBKRMCPServer:
    """MCP server for Interactive Brokers API integration."""
    
    def __init__(self):
        """Initialize IBKR connection and tools."""
        self.ib = IB()
        self._connect()
        
    def _connect(self):
        """Connect to IBKR TWS/Gateway."""
        host = os.getenv('IBKR_HOST', '127.0.0.1')
        port = int(os.getenv('IBKR_PORT', '7497'))  # 7497 for TWS, 4001 for Gateway
        client_id = int(os.getenv('IBKR_CLIENT_ID', '1'))
        
        try:
            self.ib.connect(host, port, clientId=client_id)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to IBKR: {str(e)}")

    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Return available MCP tools."""
        return {
            'get_account_summary': {
                'description': 'Get account summary including cash balance and portfolio value',
                'input_schema': {},
            },
            'get_positions': {
                'description': 'Get current positions in the account',
                'input_schema': {},
            },
            'get_asset_info': {
                'description': 'Get detailed information about a specific asset',
                'input_schema': {
                    'symbol': {'type': 'string', 'description': 'Asset symbol (e.g., AAPL, EUR.USD)'},
                    'sec_type': {'type': 'string', 'description': 'Security type (STK for stocks, CASH for forex)', 'default': 'STK'},
                },
            },
            'place_order': {
                'description': 'Place a new order',
                'input_schema': {
                    'symbol': {'type': 'string', 'description': 'Asset symbol'},
                    'sec_type': {'type': 'string', 'description': 'Security type (STK, CASH)', 'default': 'STK'},
                    'action': {'type': 'string', 'description': 'BUY or SELL'},
                    'quantity': {'type': 'number', 'description': 'Order quantity'},
                    'order_type': {'type': 'string', 'description': 'Order type (MKT, LMT)', 'default': 'MKT'},
                    'limit_price': {'type': 'number', 'description': 'Limit price for LMT orders', 'optional': True},
                },
            },
        }

    def get_resources(self) -> Dict[str, Dict[str, Any]]:
        """Return available MCP resources."""
        return {}

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool."""
        if not self.ib.isConnected():
            self._connect()

        if tool_name == 'get_account_summary':
            return await self._get_account_summary()
        elif tool_name == 'get_positions':
            return await self._get_positions()
        elif tool_name == 'get_asset_info':
            return await self._get_asset_info(arguments)
        elif tool_name == 'place_order':
            return await self._place_order(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _get_account_summary(self) -> Dict[str, Any]:
        """Get account summary."""
        account = self.ib.accountSummary()
        return {
            'net_liquidation': next((item.value for item in account if item.tag == 'NetLiquidation'), None),
            'cash_balance': next((item.value for item in account if item.tag == 'TotalCashValue'), None),
            'buying_power': next((item.value for item in account if item.tag == 'BuyingPower'), None),
        }

    async def _get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        positions = self.ib.positions()
        return {
            'positions': [
                {
                    'symbol': pos.contract.symbol,
                    'sec_type': pos.contract.secType,
                    'position': pos.position,
                    'avg_cost': pos.avgCost,
                    'market_value': pos.marketValue if hasattr(pos, 'marketValue') else None,
                }
                for pos in positions
            ]
        }

    async def _get_asset_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed asset information."""
        symbol = arguments['symbol']
        sec_type = arguments.get('sec_type', 'STK')
        
        if sec_type == 'STK':
            contract = Stock(symbol, 'SMART', 'USD')
        elif sec_type == 'CASH':
            base, quote = symbol.split('.')
            contract = Forex(base + quote)
        else:
            raise ValueError(f"Unsupported security type: {sec_type}")

        self.ib.qualifyContracts(contract)
        [ticker] = self.ib.reqMktData(contract)
        await ticker.marketDataEvent

        return {
            'symbol': contract.symbol,
            'sec_type': contract.secType,
            'exchange': contract.exchange,
            'currency': contract.currency,
            'last_price': ticker.last if hasattr(ticker, 'last') else None,
            'bid': ticker.bid if hasattr(ticker, 'bid') else None,
            'ask': ticker.ask if hasattr(ticker, 'ask') else None,
            'volume': ticker.volume if hasattr(ticker, 'volume') else None,
        }

    async def _place_order(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order."""
        symbol = arguments['symbol']
        sec_type = arguments.get('sec_type', 'STK')
        action = arguments['action']
        quantity = arguments['quantity']
        order_type = arguments.get('order_type', 'MKT')
        limit_price = arguments.get('limit_price')

        # Create contract
        if sec_type == 'STK':
            contract = Stock(symbol, 'SMART', 'USD')
        elif sec_type == 'CASH':
            base, quote = symbol.split('.')
            contract = Forex(base + quote)
        else:
            raise ValueError(f"Unsupported security type: {sec_type}")

        # Create order
        order = self.ib.order()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = order_type
        if order_type == 'LMT' and limit_price is not None:
            order.lmtPrice = limit_price

        # Place order
        trade = self.ib.placeOrder(contract, order)
        await trade.filledEvent

        return {
            'order_id': trade.order.orderId,
            'status': trade.orderStatus.status,
            'filled': trade.orderStatus.filled,
            'remaining': trade.orderStatus.remaining,
            'avg_fill_price': trade.orderStatus.avgFillPrice,
        }

# Server instance will be created when needed
server = None

def get_server():
    """Get or create the server instance."""
    global server
    if server is None:
        server = IBKRMCPServer()
    return server
