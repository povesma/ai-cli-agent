import json
import re
from typing import Any, Dict, Tuple
from colorama import Fore, Style, init


def extract_json_from_text(text: str, failed_json_count: int, MAX_FAILED_JSONS_ALLOWED: int) -> Tuple[Any, int]:
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
            return parsed_json, failed_json_count
        except json.JSONDecodeError as e2:
            print(f"{Fore.RED}COMPLETELY Failed to parse JSON...{Style.RESET_ALL}\n{e2}. Failed count in a row: {failed_json_count}")
            failed_json_count += 1
            if failed_json_count >= MAX_FAILED_JSONS_ALLOWED:
                print(f"{Fore.RED}Too many failed JSONs in a row. Exiting...{Style.RESET_ALL}")
                raise json.JSONDecodeError("fail", "{}", 0)

        return {}, failed_json_count

def parse_text_response(text: str) -> Dict[str, Any]:
    sections = text.split('===')
    action_data = {}
    for i in range(1, len(sections), 2):
        key = sections[i].strip().lower()
        value = sections[i+1].strip()
        if key == 'is_destructive':
            value = value.lower() == 'true'
        action_data[key] = value
    return action_data
