"""
Tests for the IBKR AI agent CLI.
"""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from ibkr_ai_agent.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()

@pytest.fixture
def mock_agent():
    """Mock IBKRAgent."""
    mock = Mock()
    mock.run = Mock(return_value="Test response")
    return mock

def test_cli_help(runner):
    """Test CLI help output."""
    result = runner.invoke(cli, ['--help'])
    assert 'AI agent for interacting with Interactive Brokers' in result.output

def test_chat_command_help(runner):
    """Test chat command help output."""
    result = runner.invoke(cli, ['chat', '--help'])
    assert 'Chat with your IBKR AI agent' in result.output

def test_configure_command_help(runner):
    """Test configure command help output."""
    result = runner.invoke(cli, ['configure', '--help'])
    assert 'Update IBKR connection settings' in result.output

def test_first_time_setup(runner):
    """Test first-time configuration setup."""
    with runner.isolated_filesystem() as fs:
        config_dir = Path(fs) / '.ibkr-ai-agent'
        config_dir.mkdir(exist_ok=True)
        
        with patch('pathlib.Path.home', return_value=Path(fs)), \
             patch('click.prompt') as mock_prompt, \
             patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('click.echo') as mock_echo:
            mock_prompt.side_effect = ['localhost', '7497', '1']
            result = runner.invoke(cli, ['configure'], obj={'testing': True})
            assert result.exit_code == 0
            assert mock_prompt.call_count == 3
            
            # Verify config file was created
            env_file = config_dir / '.env'
            assert env_file.exists()
            content = env_file.read_text()
            assert 'IBKR_HOST=localhost' in content
            assert 'IBKR_PORT=7497' in content
            assert 'IBKR_CLIENT_ID=1' in content

def test_update_existing_config(runner):
    """Test updating existing configuration."""
    with runner.isolated_filesystem() as fs:
        config_dir = Path(fs) / '.ibkr-ai-agent'
        config_dir.mkdir(exist_ok=True)
        
        # Create initial config
        env_file = config_dir / '.env'
        env_file.write_text(
            "IBKR_HOST=localhost\n"
            "IBKR_PORT=7497\n"
            "IBKR_CLIENT_ID=1\n"
        )
        
        with patch('pathlib.Path.home', return_value=Path(fs)), \
             patch('click.prompt') as mock_prompt, \
             patch('click.confirm') as mock_confirm, \
             patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('click.echo') as mock_echo:
            mock_prompt.side_effect = ['127.0.0.1', '4001', '2']
            mock_confirm.return_value = True
            
            result = runner.invoke(cli, ['configure'], obj={'testing': True})
            assert result.exit_code == 0
            
            # Verify config was updated
            content = env_file.read_text()
            assert 'IBKR_HOST=127.0.0.1' in content
            assert 'IBKR_PORT=4001' in content
            assert 'IBKR_CLIENT_ID=2' in content

def test_chat_command_success(runner, mock_agent):
    """Test successful chat command execution."""
    with patch('ibkr_ai_agent.cli.IBKRAgent', return_value=mock_agent):
        result = runner.invoke(cli, ['chat', 'What is my balance?'])
        
        assert result.exit_code == 0
        assert 'Test response' in result.output
        mock_agent.run.assert_called_once_with('What is my balance?')

def test_chat_command_with_model_option(runner, mock_agent):
    """Test chat command with custom model option."""
    with patch('ibkr_ai_agent.cli.IBKRAgent', return_value=mock_agent) as mock_agent_class:
        result = runner.invoke(cli, [
            'chat',
            '--model', 'custom-model',
            'What is my balance?'
        ])
        
        assert result.exit_code == 0
        mock_agent_class.assert_called_once_with(model_id='custom-model')

def test_chat_command_error(runner, mock_agent):
    """Test chat command error handling."""
    mock_agent.run.side_effect = Exception("Test error")
    
    with patch('ibkr_ai_agent.cli.IBKRAgent', return_value=mock_agent):
        result = runner.invoke(cli, ['chat', 'What is my balance?'])
        
        assert result.exit_code == 0  # CLI should handle errors gracefully
        assert 'Error: Test error' in result.output

def test_config_file_permissions(runner):
    """Test configuration file has appropriate permissions."""
    with runner.isolated_filesystem():
        with patch('click.prompt') as mock_prompt:
            mock_prompt.side_effect = ['localhost', '7497', '1']
            
            runner.invoke(cli, ['configure'])
            
            config_dir = Path.home() / '.ibkr-ai-agent'
            env_file = config_dir / '.env'
            
            # Check file exists and has appropriate permissions
            assert env_file.exists()
            mode = oct(env_file.stat().st_mode)[-3:]
            assert mode in ['600', '640', '644']  # Common secure file permissions
