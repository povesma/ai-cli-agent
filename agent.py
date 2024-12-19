import datetime
import os
import time
import atexit
import os
import sys
import requests
import json
import subprocess
import logging
import time
from colorama import Fore, Style, init
import re
import readline  # This enables line editing for input()
import uuid
import signal

# Initialize colorama for colored output
init()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# GPT API configuration
API_URL = os.environ.get('GPT_API_URL')
SUBSCRIPTION_KEY = os.environ.get('GPT_SUBSCRIPTION_KEY')
GPT_TOKEN = os.environ.get('GPT_TOKEN')
MAIN_MODEL = os.environ.get('GPT_MODEL') or "CLAUDE_3_SONNET_35"
HEADERS = os.environ.get('HEADERS') or ""  # example: "host:private_host,session:session_id"
# Parsed headers from HEADERS var:
PARSED_HEADERS = {k: v for k, v in [header.split(':') for header in HEADERS.split(',')]} if HEADERS else {}

# Interactive by default
NON_INTERACTIVE = os.environ.get("AI_AGENT_NON_INTERACTIVE", "false").lower() == "true"

# Maximum number of failed JSONs allowed in a row before exiting (TODO: pause instead of exit, ask for user input)
MAX_FAILED_JSONS_ALLOWED = int(os.environ.get('MAX_FAILED_JSONS_ALLOWED', 3))

# Message history configuration
MESSAGE_HISTORY_FILE = os.environ.get('MESSAGE_HISTORY_FILE', "message_history.json")
MAX_MESSAGES = int(os.environ.get('MAX_MESSAGES', 100))

# number oj jsons failed in a raw
failed_json_count = 0

def get_token():
    return input("Enter your GPT token: ").strip()

def get_headers():
    # merge the parsed headers with the default headers
    return {
        **PARSED_HEADERS, **{
            'Subscription-Key': SUBSCRIPTION_KEY,
            'Authorization': 'Bearer ' + GPT_TOKEN,
            'Content-Type': 'application/json',
            'jll-request-id': str(uuid.uuid4())  # Generate a new GUID for each request
        }
    }

def refresh_token():
    global GPT_TOKEN
    print(f"{Fore.YELLOW}The current token has expired. Please provide a new token.{Style.RESET_ALL}")
    GPT_TOKEN = get_token()
    logger.info(f"{Fore.GREEN}Token refreshed successfully.{Style.RESET_ALL}")

def extract_json_from_text(text):
    """
    Extracts JSON from text, even if it's surrounded by other content or formatted with markdown code blocks.
    """

    def esc(json_string):
        # Define the allowed escape sequences in JSON
        allowed_escapes = set('"\\/bfnrtu')
        def replace_invalid_escapes(matching):
            if match.group(1) in allowed_escapes:
                return matching.group(0)  # Keep valid escapes as they are
            else:
                return '\\\\'  # Replace invalid escapes with double backslash

        # Use regex to find all backslashes and process them
        return re.sub(r'\\(.)', replace_invalid_escapes, json_string)

    # Try to find JSON wrapped in code blocks
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        potential_json = match.group(1)
    else:
        # If no code blocks, try to find JSON-like structure
        match = re.search(r'(\{[\s\S]*\})', text)
        potential_json = match.group(1) if match else text

    # Clean up potential JSON string
    potential_json = potential_json.strip()
    global failed_json_count
    try:
        parsed_json = json.loads(potential_json)
        failed_json_count = 0
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Failed to parse JSON from text:{Style.RESET_ALL}\n{e}. Trying workaround...")
        try:
            potential_json2 = esc(potential_json)
            parsed_json=json.loads(potential_json2)
            failed_json_count = 0
            return parsed_json
        except json.JSONDecodeError as e2:
            print(f"{Fore.RED}COMPLETELY Failed to parse JSON...{Style.RESET_ALL}\n{e2}. Failed count in a row: {failed_json_count}")
            if failed_json_count >= MAX_FAILED_JSONS_ALLOWED:
                print(f"{Fore.RED}Too many failed JSONs in a row. Exiting...{Style.RESET_ALL}")
                raise json.JSONDecodeError("fail", "{}", 0)

        return None

def gpt_call(messages, model=MAIN_MODEL):

    system_message = """You are an AI agent designed to perform tasks on a local computer using CLI commands. The commands you execute should be well considered: if you lack some data to run a proper command - first you should run a "research" command to gather the necessary information about the system and its configuration.
    I case you need to access the Internet (with curl or other tools) be sure not to expose any sensitive information (in case of doubt mark it destructive).
    Your responses must strictly adhere to the one of the following JSON formats, with no additional text before or after, exactly one valid JSON:

    {
    "action": "The CLI command to execute",
    "explanation": "A brief explanation of what this command does and why it's necessary",
    "expected_outcome": "What you expect this command to achieve",
    "subtask": "Brief description of the subtask of the main task, which is now being solved",
    "is_destructive": true/false
    }
    All actions that change the system state or write something to the disk (including rm, mv, cp, mkdir, zip etc. - explicitly or implicitly, except `v2` directory) should have "is_destructive" set to true. 
    EXCEPTION: all actions with and within `v2` directory or running a `docker` (when mounting only `v2` and not in privileged mode) directory should be considered as NON-destructive. 
    Or, if you need more information or clarification, use only this format:

    {
    "request_info": "The specific information or clarification you need"
    "subtask": "Brief description of the subtask of the main task, which is now being solved",
    }

    Or, if the main task is complete and there's absolutely nothing to do, respond only with:

    {
    "task_complete": true,
    "summary": "A brief summary of what was accomplished"
    }

    Do not include any text outside of these JSON structures. Your entire response should be a single, valid JSON.
    All your responses are processed automatically by the script, any human will never see them, so please ensure they are in the correct JSON format.
    If you do not provide exactly what is required, your job is useless and a total waste."""

    # Ensure the system message is only at the beginning
    if messages[0]['role'] != 'system':
        messages = [{"role": "system", "content": system_message}] + messages
    else:
        messages[0]['content'] = system_message

    payload = {
        "messages": messages,
        "model": model,
        "temperature": 0.7,
        "choiceCount": 1,
    }

    try:
        headers = get_headers()  # Get fresh headers with a new GUID for each call
        response = requests.post(API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return data.get("choices")[0]["message"]["content"], tokens
        elif response.status_code == 401:
            logger.error(f"{Fore.RED}Token expired. Refreshing token...{Style.RESET_ALL}")
            refresh_token()
            return None, 0
        else:
            logger.error(f'API Error: Status Code: {response.status_code}, Response: {response.text}')
            return None, 0
    except requests.exceptions.RequestException as e:
        logger.error(f'HTTP Request failed: {e}')
        return None, 0

def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        output = 'stdout:\n' + result.stdout + '\nstderr:\n' + result.stderr
        return {
            'output': output,
            'return_code': result.returncode
        }
    except Exception as e:
        logger.error(f"{Fore.RED}Error during command execution: {e}{Style.RESET_ALL}")
        return {
            'output': str(e),
            'return_code': -1
        }

def log_action(action, explanation, expected_outcome = "", subtask = ""):
    logger.info(f"{Fore.CYAN}Action:{Style.RESET_ALL} {action}")
    logger.info(f"{Fore.GREEN}Explanation:{Style.RESET_ALL} {explanation}")
    if expected_outcome:
        print(f"{Fore.YELLOW}Expected outcome:{Style.RESET_ALL} {expected_outcome}")
    if subtask:
        print(f"{Fore.MAGENTA}Subtask:{Style.RESET_ALL} {subtask}")

def get_user_confirmation(action, expected_outcome, non_interactive=False):
    print(f"{Fore.YELLOW}Proposed action:{Style.RESET_ALL} {action}")
    print(f"{Fore.YELLOW}Expected outcome:{Style.RESET_ALL} {expected_outcome}")
    if non_interactive:
        print("Running in non-interactive mode. Automatically proceeding.")
        return True
    return input("Do you want to proceed? (y/n): ").lower() == "y"


def ai_agent(task, non_interactive=False):
    logger.info(f'Starting task: {task}')
    conversation = [{'role': 'user', 'content': f'Task: {task}'}]
    total_tokens_used = 0
    gpt_calls = 0
    try:
        while True:
            response, tokens = gpt_call(conversation)
            total_tokens_used += tokens
            update_stats(tokens)
            gpt_calls += 1
            if response is None:
                logger.error(f'{Fore.RED}Failed to get a response from GPT. Retrying...{Style.RESET_ALL}')
                time.sleep(0.25)
                continue
            conversation.append({'role': 'assistant', 'content': response})
            action_data = extract_json_from_text(response)
            if action_data is None:
                logger.error(f'{Fore.RED}Failed to extract valid JSON from GPT response. Raw response:\n{Style.RESET_ALL}{response}')
                conversation.append({'role': 'user', 'content': 'Your last response did not match the requested format. Please provide your response in the correct JSON format.'})
                continue
            if 'request_info' in action_data:
                if non_interactive:
                    logger.info(f'Skipping user input request in non-interactive mode: {action_data["request_info"]}')
                    conversation.append({'role': 'user', 'content': 'Skipped due to non-interactive mode. Please continue with the task using available information.'})
                else:
                    user_input = input(f'{action_data["request_info"]}Your response: ')
                    conversation.append({'role': 'user', 'content': user_input})
                continue
            if 'task_complete' in action_data and action_data['task_complete']:
                logger.info(f'{Fore.GREEN}Task completed:{Style.RESET_ALL} {action_data["summary"]}')
                break
            if not all(key in action_data for key in ['action', 'explanation', 'expected_outcome', 'is_destructive']):
                logger.error(f'{Fore.RED}GPT response is missing required fields. Response:\n{Style.RESET_ALL}{action_data}')
                conversation.append({'role': 'user', 'content': 'Your last response was missing required fields. Please ensure all required fields are included.'})
                continue
            action = action_data['action']
            explanation = action_data['explanation']
            subtask = action_data.get('subtask', '-NO-SUBTASK-')
            expected_outcome = action_data['expected_outcome']
            is_destructive = action_data['is_destructive']
            log_action(action, explanation, expected_outcome, subtask)
            if is_destructive:
                if non_interactive:
                    logger.warning(f'{Fore.RED}Potentially destructive action detected:{Style.RESET_ALL} {action}')
                    logger.info('Running in non-interactive mode. Automatically proceeding.')
                else:
                    logger.warning(f'{Fore.RED}Potentially destructive action detected:{Style.RESET_ALL} {action}')
                    if not get_user_confirmation(action, expected_outcome, non_interactive):
                        logger.info('Action aborted by user.')
                        conversation.append({'role': 'user', 'content': 'The last action was aborted by the user. Please suggest an alternative approach or continue with other actions.'})
                        continue
            result = execute_command(action)
            output = result['output']
            return_code = result['return_code']
            if return_code == 0:
                logger.info(f'{Fore.GREEN}Command executed successfully (return code 0){Style.RESET_ALL}')
            else:
                logger.warning(f'{Fore.YELLOW}Command completed with non-zero return code: {return_code}{Style.RESET_ALL}')
            logger.info(f'Command output:\n{output}')
            conversation.append({'role': 'user', 'content': f'OK, I ran the suggested command.\nReturn code: {return_code}\nFull command output:\n{output}\n\nDoes this meet the expectations of the initial task? What\'s the next step?'})
    finally:
        display_stats()
        return conversation


def load_message_history():
    try:
        with open(MESSAGE_HISTORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding {MESSAGE_HISTORY_FILE}. Starting with empty history.")
        return []

def save_message_history(history):
    try:
        with open(MESSAGE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        logging.error(f"Failed to save message history to {MESSAGE_HISTORY_FILE}: {e}")
    except TypeError as e:
        logging.error(f"Failed to serialize message history: {e}")

def update_message_history(messages):
    # Load the existing message history from file / DB
    history = load_message_history()
    history.extend(messages)
    # Trim the history to the last MAX_MESSAGES
    if len(history) > MAX_MESSAGES:
        history = history[-MAX_MESSAGES:]
    save_message_history(history)
    return history

def signal_handler(signum, frame):
    print("Interrupt received, stopping the agent...")
    display_stats()
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, signal_handler)

# Statistics tracking
start_time = time.time()
model_calls = 0
tokens_used = 0

def update_stats(tokens):
    global model_calls, tokens_used
    model_calls += 1
    tokens_used += tokens

def display_stats():
    end_time = time.time()
    print(f"Execution Statistics:")
    print(f"Time elapsed: {end_time - start_time:.2f} seconds")
    print(f"Number of model calls: {model_calls}")
    print(f"Total tokens used: {tokens_used}")
    print(f"Task completed at : {datetime.datetime.now().isoformat()}")

def get_task():
    # Check for command-line argument
    if len(sys.argv) > 1:
        task = sys.argv[1]
    # Check for environment variable
    elif "AI_AGENT_TASK" in os.environ:
        task = os.environ["AI_AGENT_TASK"]
    elif "AI_AGENT_TASK_FILE" in os.environ:
        task_file = os.environ["AI_AGENT_TASK_FILE"]
        with open(task_file, 'r') as f:
            task = f.read()
            print(f"Task loaded from file '{task_file}")
    else:
        task = input('Enter the task for the AI Agent: ')
    return task

def main():
    global start_time, model_calls, tokens_used
    start_time = time.time()
    model_calls = 0
    tokens_used = 0
    task = get_task()
    print(f"Task: {task}")
    conversation = ai_agent(task, non_interactive=NON_INTERACTIVE)
    update_message_history(conversation)

if __name__ == "__main__":
    main()
