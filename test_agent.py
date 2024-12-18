import pytest
from unittest.mock import patch, MagicMock
from agent import ai_agent, gpt_call, execute_command

def test_gpt_call():
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}],
            'usage': {'total_tokens': 10}
        }
        mock_post.return_value = mock_response

        response, tokens = gpt_call([{'role': 'user', 'content': 'Test message'}])
        assert response == 'Test response'
        assert tokens == 10

def test_execute_command():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='Test output', stderr='', returncode=0)
        result = execute_command('echo test')
        assert result['output'] == 'stdout:\nTest output\nstderr:\n'
        assert result['return_code'] == 0

if __name__ == '__main__':
    pytest.main([__file__])
