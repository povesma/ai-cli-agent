import os
import requests
import json
import subprocess
import logging
from colorama import Fore, Style, init
import re
import readline  # This enables line editing for input()
import uuid

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

    try:
        return json.loads(potential_json)
    except json.JSONDecodeError:
        return None

def gpt_call(messages, model=MAIN_MODEL):
    system_message = """You are an AI agent designed to perform tasks on a local computer using CLI commands. The commands you execute should be well considered: if you lack some data to run a proper command - first you should run a "research" command to gather the necessary information about the system and its configuration.
    I case you need to access the Internet (with curl or other tools) be sure not to expose any sensitive information (in case of doubt mark it destructive).
    Your responses must strictly adhere to the one of the following JSON formats, with no additional text before or after, exactly one valid JSON:

    {
    "action": "The CLI command to execute",
    "explanation": "A brief explanation of what this command does and why it's necessary",
    "expected_outcome": "What you expect this command to achieve",
    "is_destructive": true/false
    }
    All actions that change the system state or write something to the disk (including rm, mv, cp, mkdir, zip etc. - explicitly or implicitly) should have "is_destructive" set to true.
    Or, if you need more information or clarification, use only this format:

    {
    "request_info": "The specific information or clarification you need"
    }

    Or, if the task is complete, respond only with:

    {
    "task_complete": true,
    "summary": "A brief summary of what was accomplished"
    }

    Do not include any text outside of these JSON structures. Your entire response should be a single, valid JSON.
    All your responses are processes automatically, human will never see them, so please ensure they are in the correct JSON format.
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
            return data.get("choices")[0]['message']['content']
        elif response.status_code == 401:
            logger.error(f"{Fore.RED}Token expired. Refreshing token...{Style.RESET_ALL}")
            refresh_token()
            return None  # Return None to trigger a retry in the main loop
        else:
            logger.error(f'API Error: Status Code: {response.status_code}, Response: {response.text}')
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f'HTTP Request failed: {e}')
        return None

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

def log_action(action, explanation):
    logger.info(f"{Fore.CYAN}Action:{Style.RESET_ALL} {action}")
    logger.info(f"{Fore.GREEN}Explanation:{Style.RESET_ALL} {explanation}")

def get_user_confirmation(action, expected_outcome):
    print(f"\n{Fore.YELLOW}Proposed action:{Style.RESET_ALL} {action}")
    print(f"{Fore.YELLOW}Expected outcome:{Style.RESET_ALL} {expected_outcome}")
    return input("Do you want to proceed? (y/n): ").lower() == 'y'

def ai_agent(task):
    logger.info(f"Starting task: {task}")

    conversation = [
        {"role": "user", "content": f"Task: {task}"}
    ]

    while True:
        # For debugging: print the conversation structure before each API call
        logger.debug("Current conversation structure:")
        for message in conversation:
            logger.debug(f"Role: {message['role']}, Content: {message['content'][:50]}...")

        response = gpt_call(conversation)

        if response is None:
            logger.error(f"{Fore.RED}Failed to get a response from GPT. Retrying...{Style.RESET_ALL}")
            continue

        # Add the assistant's response to the conversation
        conversation.append({"role": "assistant", "content": response})

        action_data = extract_json_from_text(response)

        if action_data is None:
            logger.error(f"{Fore.RED}Failed to extract valid JSON from GPT response. Raw response:{Style.RESET_ALL}\n{response}")
            conversation.append({"role": "user", "content": "Your last response did not match the requested format - only contain a single valid JSON. Please provide your response in the correct JSON format (absolutely no additional text)."})
            continue

        if "request_info" in action_data:
            user_input = input(f"{action_data['request_info']}\nYour response: ")
            conversation.append({"role": "user", "content": user_input})
            continue

        if "task_complete" in action_data and action_data["task_complete"]:
            logger.info(f"{Fore.GREEN}Task completed:{Style.RESET_ALL} {action_data['summary']}")
            break

        if not all(key in action_data for key in ["action", "explanation", "expected_outcome", "is_destructive"]):
            logger.error(f"{Fore.RED}GPT response is missing required fields. Response:{Style.RESET_ALL}\n{action_data}")
            conversation.append({"role": "user", "content": "Your last response was missing required fields. Please ensure all required fields are included."})
            continue

        action = action_data['action']
        explanation = action_data['explanation']
        expected_outcome = action_data['expected_outcome']
        is_destructive = action_data['is_destructive']

        log_action(action, explanation)

        if is_destructive:
            logger.warning(f"{Fore.RED}Potentially destructive action detected:{Style.RESET_ALL} {action}")
            if not get_user_confirmation(action, expected_outcome):
                logger.info("Action aborted by user.")
                conversation.append({"role": "user", "content": "The last action was aborted by the user, so, most probably the user does not believe that it's helpful. Please suggest an alternative approach, or continue with other actions."})
                continue

        result = execute_command(action)

        output = result['output']
        return_code = result['return_code']

        if return_code == 0:
            logger.info(f"{Fore.GREEN}Command executed successfully (return code 0){Style.RESET_ALL}")
        else:
            logger.warning(f"{Fore.YELLOW}Command completed with non-zero return code: {return_code}{Style.RESET_ALL}")

        logger.info(f"Command output:\n{output}")

        # Add the result of the command execution to the conversation
        conversation.append({"role": "user", "content": f"OK, I ran the suggested command. \nReturn code: {return_code}\nFull command output:\n{output}\n\nDoes this meet the expectations of the initial task? What's the next step?"})

if __name__ == "__main__":
    print("Welcome to the AI Agent CLI.")
    task = input("Enter the task for the AI Agent: ")
    ai_agent(task)
