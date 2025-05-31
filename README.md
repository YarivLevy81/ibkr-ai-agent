# IBKR AI Agent

An AI-powered command-line tool for interacting with your Interactive Brokers account using natural language. Built with LangChain and AWS Bedrock (Claude), this tool allows you to manage your investments through simple conversations.

## Features

- 🤖 Natural language interface for IBKR account management
- 💼 Account balance and portfolio overview
- 📊 Real-time market data and asset information
- 📈 Position monitoring and trade execution
- 🔒 Secure local configuration
- 🤝 Integration with TWS or IB Gateway

## Prerequisites

1. **Interactive Brokers Account**
   - Active IBKR account
   - TWS (Trader Workstation) or IB Gateway installed and running
   - API access enabled in TWS/Gateway settings

2. **AWS Account**
   - AWS account with Bedrock access
   - Claude model enabled in Bedrock
   - AWS credentials configured

3. **Python Environment**
   - Python 3.9 or higher
   - pip package manager

## Installation

### Using uv (Recommended)

1. Install uv:
   ```bash
   pip install uv
   ```

2. Install the package:
   ```bash
   uv pip install ibkr-ai-agent
   ```

   Or install from source:
   ```bash
   git clone https://github.com/yourusername/ibkr-ai-agent.git
   cd ibkr-ai-agent
   uv pip install -e .
   ```

### Using pip (Alternative)

```bash
pip install ibkr-ai-agent
```

### First-time Setup

After installation, run:
```bash
ibkr-agent configure
```
This will create a configuration file at `~/.ibkr-ai-agent/.env`

## Configuration

### Interactive Brokers Setup

1. Open TWS or IB Gateway
2. Go to File -> Global Configuration -> API -> Settings
3. Enable "Enable ActiveX and Socket Clients"
4. Set "Socket port" (default: 7497 for TWS, 4001 for Gateway)
5. Allow connections from localhost (127.0.0.1)

### AWS Bedrock Setup

1. Ensure you have AWS credentials configured either:
   - Through AWS CLI (`aws configure`)
   - Or by setting credentials in `~/.ibkr-ai-agent/.env`:
     ```
     AWS_ACCESS_KEY_ID=your_access_key
     AWS_SECRET_ACCESS_KEY=your_secret_key
     AWS_DEFAULT_REGION=us-east-1
     ```

2. Enable Claude model in AWS Bedrock console

## Usage

### Basic Commands

```bash
# Check account balance
ibkr-agent chat "What's my current account balance?"

# Get stock information
ibkr-agent chat "What's the current price of AAPL?"

# View positions
ibkr-agent chat "Show me my current positions"

# Place a trade (will ask for confirmation)
ibkr-agent chat "Buy 100 shares of MSFT at market price"

# Get forex rates
ibkr-agent chat "What's the current EUR/USD rate?"

# Update configuration
ibkr-agent configure
```

### Example Conversations

```bash
# Complex queries
ibkr-agent chat "Show me tech stocks in my portfolio with unrealized losses"

# Market analysis
ibkr-agent chat "What's AAPL's current price and volume today?"

# Order management
ibkr-agent chat "Place a limit order to sell 50 shares of TSLA at $250"
```

## Security Considerations

1. **API Access**
   - Keep TWS/Gateway API port restricted to localhost
   - Use a unique client ID for each application
   - Regularly review API connections in TWS/Gateway

2. **Credentials**
   - Store .env file securely
   - Never share or commit credentials
   - Use AWS IAM best practices for Bedrock access

3. **Trading Safety**
   - The agent will always confirm trades before execution
   - Set appropriate trading permissions in TWS/Gateway
   - Monitor TWS/Gateway logs for API activity

## Error Handling

Common issues and solutions:

1. **Connection Errors**
   - Ensure TWS/Gateway is running
   - Verify API settings in TWS/Gateway
   - Check port numbers in configuration

2. **Authentication Errors**
   - Verify AWS credentials
   - Ensure Bedrock access is enabled
   - Check region settings

3. **Trading Errors**
   - Confirm sufficient buying power
   - Verify trading permissions
   - Check market hours

## Development

To contribute or modify:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ibkr-ai-agent.git
   cd ibkr-ai-agent
   ```

2. Install development dependencies:
   ```bash
   # Using uv (recommended)
   uv pip install -e ".[dev]"
   
   # Or using pip
   pip install -e ".[dev]"
   ```

3. Install dependencies from requirements.txt:
   ```bash
   # Using uv (recommended)
   uv pip install -r requirements.txt
   
   # Or using pip
   pip install -r requirements.txt
   ```

4. Run tests:
   ```bash
   pytest
   ```

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for educational and convenience purposes only. Always verify trades and account actions in your TWS/Gateway platform. The authors are not responsible for trading losses or API-related issues.
