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

CLI arguments:
`--task` - specify the task for the AI agent to perform.

```bash

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

This project is proprietary and should not be shared.

## TODO
1. On each GPT request we send the full conversation (including the full output of the commands). 
On lengthy tasks it consumes a lot of tokens. 
The token usage should be reduced dramatically. Possible approaches:
    1. Once the subtask is completed, often there's no much need to send the full conversation related to this subtask to the model (just the summary).
    1. Big outputs should be (if possible) summarized and replaced with the summary as soon as possible.
    1. All summaries should be explicitly marked as summaries, so the model can distinguish them from the full outputs.
    1. Utilize the model's ability to remember the context of the conversation and send only the new parts of the conversation (check if it is possible).
    1. Use separate conversation threads for the subtasks (when possible) to avoid sending the full conversation. 
1. Some CLI programs that are run by this script, run longer or produce and informative output that the user should see earlier. Do not wait for the program to finish, but show the output as it comes (by default). This should be configurable.
1. Some CLI programs that are run by this script, require user input (e.g. confirmation of a destructive action). This should be handled by the script, either by auto-accepting, asking for confirmation, or failing the task. This should be configurable.
1. Some CLI programs that are run by this script, never end (e.g. `tail -f`) on their own. This should be handled by the script, either by setting a timeout, or by detecting the end of the output (by some criteria), or allow user to intervene. 
1. Some CLI programs that are run by this script, produce a streaming output (e.g. `ffmpeg` when converting the files shows progress). This output can be huge and mostly unnecessary. This should be handled by the script by sending to GPT just the summary, not each and every line of the progress output. Possible solutions: for the commands that may produce progress output, query GPT in a separate thread with the output and ask for the summary. This summary to be used in main thread instead of the full output. 
1. When asking for the confirmation of a destructive action, allow the user to give not just y/n answer, but also to provide a comment (which should mean "NO" with the explanation). This comment should be sent to GPT to define the further steps.
1. Save history of tasks, steps taken, assessment of success for future use: display for user, browse and re-run, etc.
1. Based on the history, be able to start from the specific step, or re-run the task from the beginning.
1. Enable completely non-interactive mode (configurable): it's partially implemented with passing task as ENV var file name / CLI argument, but script still may ask for user input (e.g. confirmation of a destructive action). This should be configurable - FAIL on destructive action attempt, or auto accept, or ask for confirmation.
1. Enable user interaction between the steps: sometimes GPT runs into the situation when it can't resolve 
a trivial problem, or the command output should be retrieved from a third-party service; in these cases the user can 
provide valuable information, or at least to pause and fix something in the background, and then continue the script. 
Obviously, this should not require waiting for the user input after each step, but the user should be able to do so.
1. When the messages exceed the context limit (tokens) of the model, the message with an initial task is cut off. This should be avoided regardless of our knowledge of the context window of the model.
1. Support more APIs (what?)
1. Allow / ban / encourage access to the Internet via configuration

## Changelog (Moved from TODO)
1. *DONE.* When running this script, model may solve sub-tasks, and sub-sub-tasks (which a part of the big task) and so on. At each step we need to know what problem is being solved right now, and the relation to the big task / super-tasks (if any). This should be included in the model response where relevant (requires prompt modification).
1. *DONE.* Enable passing the task as a command line argument / ENV var / file
1. *DONE.* Better logging and stats (time of execution, number of model calls (+), tokens used (+), etc.). Show statistics on program completion, including when it was aborted / terminated by the user
1. *DONE.* Dockerize the agent (not tested)
