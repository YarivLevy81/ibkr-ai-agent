"""
Command-line interface for the IBKR AI agent.
"""
import os
import click
import asyncio
from pathlib import Path
from typing import Optional
import json
from dotenv import load_dotenv

from .agent import IBKRAgent

def setup_config(ctx: click.Context, update_existing: bool = False) -> None:
    """Set up or update configuration."""
    try:
        config_dir = Path.home() / '.ibkr-ai-agent'
        config_dir.mkdir(exist_ok=True)
        
        env_file = config_dir / '.env'
        existing_config = {}
        
        # Load existing config if available
        if env_file.exists():
            load_dotenv(env_file)
            if not update_existing:
                return
            
            # Load existing values as defaults if updating
            with env_file.open() as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        existing_config[key] = value
            
        if not env_file.exists() or update_existing:
            click.echo("Configuring IBKR connection...")
            
            host = click.prompt("IBKR TWS/Gateway host", 
                               default=existing_config.get('IBKR_HOST', '127.0.0.1'))
            port = click.prompt("IBKR TWS/Gateway port", 
                               default=existing_config.get('IBKR_PORT', '7497'),
                               help="7497 for TWS, 4001 for IB Gateway")
            client_id = click.prompt("Client ID", 
                                   default=existing_config.get('IBKR_CLIENT_ID', '1'))
            
            env_content = f"""# Interactive Brokers Configuration
IBKR_HOST={host}
IBKR_PORT={port}
IBKR_CLIENT_ID={client_id}

# AWS Bedrock Configuration
AWS_DEFAULT_REGION=us-east-1
# Uncomment and set these if not using AWS CLI configuration
#AWS_ACCESS_KEY_ID=your_access_key
#AWS_SECRET_ACCESS_KEY=your_secret_key
"""
            env_file.write_text(env_content)
            click.echo(f"\nConfiguration saved to {env_file}")
            click.echo("\nIMPORTANT: Before using this tool, ensure:")
            click.echo("1. TWS or IB Gateway is running and configured to accept API connections")
            click.echo("2. AWS credentials are configured (either via AWS CLI or in .env file)")
            click.echo("3. You have enabled Claude models in AWS Bedrock")
        
        load_dotenv(env_file)
    except Exception as e:
        if not ctx.obj or not ctx.obj.get('testing'):
            raise

@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    AI agent for interacting with Interactive Brokers through natural language.
    
    This tool allows you to manage your IBKR account using natural language commands.
    It connects to TWS (Trader Workstation) or IB Gateway and uses AWS Bedrock
    with Claude for natural language understanding.
    
    First-time setup will create a configuration file at ~/.ibkr-ai-agent/.env
    
    Examples:
    
        # Check account balance
        ibkr-agent chat "What's my current account balance?"
        
        # Get stock information
        ibkr-agent chat "What's the current price of AAPL?"
        
        # View positions
        ibkr-agent chat "Show me my current positions"
        
        # Place a trade (will ask for confirmation)
        ibkr-agent chat "Buy 100 shares of MSFT at market price"
    """
    if ctx is None:
        ctx = click.get_current_context()
    # Skip initial setup in testing mode
    if not ctx.obj or not ctx.obj.get('testing'):
        try:
            setup_config(ctx)
        except Exception as e:
            click.echo(f"Error during setup: {str(e)}", err=True)
            ctx.exit(1)

@cli.command()
@click.argument('query')
@click.option('--model', '-m', default="anthropic.claude-sonnet-4-20250514-v1:0",
              help="Bedrock model ID to use")
def chat(query: str, model: str) -> None:
    """
    Chat with your IBKR AI agent.
    
    Send a natural language query to interact with your IBKR account.
    The agent will interpret your request and perform the appropriate actions.
    
    Examples:
        ibkr-agent chat "What's my account balance?"
        ibkr-agent chat "Show me AAPL's current price"
        ibkr-agent chat "List my open positions"
    """
    try:
        agent = IBKRAgent(model_id=model)
        response = asyncio.run(agent.run(query))
        click.echo(response)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
def configure() -> None:
    """
    Update IBKR connection settings.
    
    This will prompt for new TWS/Gateway connection settings
    and update the configuration file.
    """
    try:
        setup_config(click.get_current_context(), update_existing=True)
        click.echo("Configuration updated successfully")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

def main() -> None:
    """Main entry point for the CLI."""
    cli(obj={})

if __name__ == '__main__':
    main()
