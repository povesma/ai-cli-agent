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

### Docker (not tested)
Build the Docker image:

```bash
docker build -t ai-agent-cli .
```

Run the container, providing the necessary environment variables from .env:

```bash
docker run --env-file ../.env ai-agent-cli
```

## Usage

Rename .env.example to .env and fill in the necessary values.

You may need to adjust the headers in the `agent.py` file to match your specific API requirements.

Run the AI agent by executing the following command:

```bash
env $(cat .env | xargs) python3 ./agent.py
```

You will be prompted to enter a task for the AI agent to perform.
The agent will then interact with the GPT model to determine the necessary actions and execute them.

For *non-interactive* mode, you can pass the task as a command line argument:

```bash
env $(cat .env | xargs) python3 ./agent.py "List all files in the current directory"
```

or use environment variable:

```bash
export AI_AGENT_TASK="List all files in the current directory"
env $(cat .env | xargs) python3 ./agent.py
```

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
1. Enable completely non-interactive mode (configurable)
1. Enable user interaction between the steps: sometimes GPT runs into the situation when it can't resolve a trivial problem, or the command output should be retrieved from a third-party service; in these cases the user can provide a valuable information, or at least to pause and fix something in the background, and then continue the script. Obvioustly, this should not require waiting for the user inout after each step, but the user should be able to do so.
1. When running this script, model may solve sub-tasks, and sub-sub-tasks (which a part of the big task) and so on. At each step we need to know what problem is being solved right now, and the relation to the big task / super-tasks (if any). 
1. Dockerize the agent (partially done, not tested)
1. When the messages exceed the context limit (tokens) of the model, the message with an initial task is cut off. This should be avoided regardless of our knowledge of the context window of the model.
1. Better logging and stats (time of execution, number of model calls, tokens used, etc.)
1. Save history of tasks, assessment of success
1. Support more APIs (what?)
1. Allow / encourage access to the Internet

## Changelog (Moved from TODO)
1. *DONE.* Enable passing the task as a command line argument / ENV var / file
