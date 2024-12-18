from unittest.mock import patch
from unittest.mock import patch, MagicMock
from agent import ai_agent, gpt_call, execute_command, extract_json_from_text


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

def test_ai_agent():
    with patch("agent.gpt_call") as mock_gpt_call, \
          patch("agent.execute_command") as mock_execute_command, \
     patch("builtins.input", return_value="y"):
        # action = action_data["action"]
        # explanation = action_data["explanation"]
        # expected_outcome = action_data["expected_outcome"]
        # is_destructive = action_data["is_destructive"]

        mock_gpt_call.side_effect = [
            ('{"action": "echo hello", "explanation": "Print out hello", "expected_outcome": "hello on the screen", "is_destructive": false}', 10),
            ('{"task_complete": true, "summary": "Task completed successfully"}', 5)
        ]
        ai_agent('Show the list of files')
        assert mock_gpt_call.call_count == 2
        assert mock_execute_command.call_count == 1
        mock_execute_command.assert_called_with('echo hello')

def test_extract_json():
    response = """
    {
  "action": "sed -i '' '/if action_data is None:/,/continue$/c\\nif",
  "explanation": "Update the error handling and user interaction part of the ai_agent function.",
  "expected_outcome": "The error handling and user interaction part will be updated.",
  "is_destructive": false
}
"""
    action_data = extract_json_from_text(response)
    assert action_data is not None