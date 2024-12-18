# AI Agent CLI

This project contains an AI agent designed to perform tasks on a local computer using CLI commands.
The agent interacts with a GPT model to receive instructions and execute them accordingly.

## Features

- Executes CLI commands based on AI-generated instructions.
- Handles JSON-formatted responses for actions, requests for information, and task completion.
- Logs actions, explanations, and command outputs.
- Provides user confirmation for potentially destructive actions.

## Requirements

- Python 3.7+
- `requests` library
- `colorama` library

## Installation

Install the required dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Usage

Rename .env.example to .env and fill in the necessary values.

You may need to adjust the headers in the `agent.py` file to match your specific API requirements.

Run the AI agent by executing the following command:

```bash
env $(cat ../.env | xargs) python3 ./agent.py
```

You will be prompted to enter a task for the AI agent to perform.
The agent will then interact with the GPT model to determine the necessary actions and execute them.

## Example

```bash
Welcome to the AI Agent CLI.
Enter the task for the AI Agent: List all files in the current directory
```

The agent will process the task, generate the appropriate CLI command, and execute it.

## Logging

The agent logs actions, explanations, and command outputs to the console. It also handles errors and retries API calls if necessary.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## TODO
1. Better logging (time of execution, tokens used, etc.)
1. Save history of tasks, assessment of success
1. Support more APIs (what?)
1. Allow / encourage access to the Internet