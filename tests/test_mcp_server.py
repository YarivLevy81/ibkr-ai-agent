"""
Tests for the IBKR MCP server implementation.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from ib_insync import IB, Stock, Forex
from ibkr_ai_agent.mcp_server import IBKRMCPServer

@pytest.fixture
def mock_ib():
    """Mock IB connection."""
    mock = Mock(spec=IB)
    mock.isConnected.return_value = True
    mock.connect = Mock()
    mock.order = Mock()
    return mock

@pytest.fixture
def server():
    """Create server instance with mocked IB."""
    with patch('ibkr_ai_agent.mcp_server.IB') as mock_ib_class:
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True
        mock_ib.connect = Mock()
        mock_ib.order = Mock()
        mock_ib_class.return_value = mock_ib
        
        # Create server without connecting
        server = IBKRMCPServer()
        server.ib = mock_ib
        
        # Mock the connect method to prevent actual connection attempts
        server._connect = Mock()
        
        return server, mock_ib

def test_connection(server):
    """Test IBKR connection setup."""
    server, mock_ib = server
    mock_ib.connect.assert_called_once()
    assert mock_ib.isConnected()

def test_get_tools(server):
    """Test available tools listing."""
    server, _ = server
    tools = server.get_tools()
    assert 'get_account_summary' in tools
    assert 'get_positions' in tools
    assert 'get_asset_info' in tools
    assert 'place_order' in tools

@pytest.mark.asyncio
async def test_get_account_summary(server):
    """Test account summary retrieval."""
    server, mock_ib = server
    mock_ib.accountSummary.return_value = [
        Mock(tag='NetLiquidation', value='100000'),
        Mock(tag='TotalCashValue', value='50000'),
        Mock(tag='BuyingPower', value='200000')
    ]
    
    result = await server._get_account_summary()
    assert result['net_liquidation'] == '100000'
    assert result['cash_balance'] == '50000'
    assert result['buying_power'] == '200000'

@pytest.mark.asyncio
async def test_get_positions(server):
    """Test positions retrieval."""
    server, mock_ib = server
    mock_position = Mock()
    mock_position.contract.symbol = 'AAPL'
    mock_position.contract.secType = 'STK'
    mock_position.position = 100
    mock_position.avgCost = 150.0
    mock_position.marketValue = 16000.0
    
    mock_ib.positions.return_value = [mock_position]
    
    result = await server._get_positions()
    positions = result['positions']
    assert len(positions) == 1
    assert positions[0]['symbol'] == 'AAPL'
    assert positions[0]['position'] == 100
    assert positions[0]['avg_cost'] == 150.0

@pytest.mark.asyncio
async def test_get_asset_info(server):
    """Test asset information retrieval."""
    server, mock_ib = server
    mock_contract = Mock(spec=Stock)
    mock_contract.symbol = 'AAPL'
    mock_contract.secType = 'STK'
    mock_contract.exchange = 'SMART'
    mock_contract.currency = 'USD'
    
    mock_ticker = Mock()
    mock_ticker.last = 150.0
    mock_ticker.bid = 149.95
    mock_ticker.ask = 150.05
    mock_ticker.volume = 1000000
    
    # Create an async coroutine for marketDataEvent
    async def market_data_event():
        return None
    mock_ticker.marketDataEvent = market_data_event()
    
    mock_ib.qualifyContracts.return_value = [mock_contract]
    mock_ib.reqMktData.return_value = [mock_ticker]
    
    result = await server._get_asset_info({'symbol': 'AAPL'})
    assert result['symbol'] == 'AAPL'
    assert result['last_price'] == 150.0
    assert result['volume'] == 1000000

@pytest.mark.asyncio
async def test_place_order(server):
    """Test order placement."""
    server, mock_ib = server
    mock_trade = Mock()
    mock_trade.order.orderId = 12345
    mock_trade.orderStatus.status = 'Filled'
    mock_trade.orderStatus.filled = 100
    mock_trade.orderStatus.remaining = 0
    mock_trade.orderStatus.avgFillPrice = 150.0
    
    # Create an async coroutine for filledEvent
    async def filled_event():
        return None
    mock_trade.filledEvent = filled_event()
    
    mock_order = Mock()
    mock_ib.order.return_value = mock_order
    mock_ib.placeOrder.return_value = mock_trade
    
    result = await server._place_order({
        'symbol': 'AAPL',
        'action': 'BUY',
        'quantity': 100,
        'order_type': 'MKT'
    })
    
    assert result['order_id'] == 12345
    assert result['status'] == 'Filled'
    assert result['filled'] == 100
    assert result['avg_fill_price'] == 150.0

@pytest.mark.asyncio
async def test_forex_contract_creation(server):
    """Test forex contract creation."""
    server, mock_ib = server
    mock_contract = Mock(spec=Forex)
    mock_ticker = Mock()
    
    # Create an async coroutine for marketDataEvent
    async def market_data_event():
        return None
    mock_ticker.marketDataEvent = market_data_event()
    
    with patch('ibkr_ai_agent.mcp_server.Forex') as mock_forex:
        mock_forex.return_value = mock_contract
        mock_ib.reqMktData.return_value = [mock_ticker]
        await server._get_asset_info({'symbol': 'EUR.USD', 'sec_type': 'CASH'})
        mock_forex.assert_called_with('EURUSD')
