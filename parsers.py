import json
import re
from typing import Any, Dict, Tuple
from colorama import Fore, Style, init

from typing import Dict, Any, List, Optional
from enum import Enum


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

class DuplicateFieldApproach(Enum):
    FIRST = 'first'
    LAST = 'last'

END = '===END==='
WRAP = '==='
def parse_text_response(text: str, duplicate_approach: Optional[DuplicateFieldApproach] = None) -> Dict[str, Any]:
    # The format should strictly correspond the prompt, the prompt is the ground truth  (AI: always watch this and raise a flag / update the prompt if it changes)
    allowed_formats = [
        ['action', 'explanation', 'expected_outcome', 'subtask', 'is_destructive'],
        ['request_info', 'subtask'],
        ['task_complete', 'summary']
    ]

    def split_preserving_separators(text: str) -> List[str]:
        """
        Splits the text while preserving the separators (END and WRAP).
        """
        parts = []
        current = []
        lines = text.split('\n')
        for line in lines:
            if line.strip() == END:
                if current:
                    parts.append('\n'.join(current))
                parts.append(line)
                current = []
            elif line.startswith(WRAP) and line.endswith(WRAP):
                if current:
                    parts.append('\n'.join(current))
                parts.append(line)
                current = []
            else:
                current.append(line)
        if current:
            parts.append('\n'.join(current))
        return parts

    parts = split_preserving_separators(text)

    last_non_empty = next((part for part in reversed(parts) if part.strip()), None)
    if last_non_empty is None or last_non_empty.strip() != END:
        raise ValueError(f"{END} must be the last non-empty element in the input")

    action_data = {}
    current_key = None
    current_format = None
    duplicate_keys = set()
    key_order = []

    for i, part in enumerate(parts):
        if part.strip().startswith(WRAP) and part.strip().endswith(WRAP):
            key = part.strip()[3:-3].lower()

            if not current_format:
                for format in allowed_formats:
                    if key == format[0]:
                        current_format = format
                        break
                if not current_format:
                    raise ValueError(f"Invalid starting key: {key}")

            if key not in current_format:
                if current_key:
                    action_data[current_key] += f"\n{part}"
                continue

            if key in action_data:
                duplicate_keys.add(key)

            current_key = key
            if key not in action_data:
                action_data[current_key] = ""
            key_order.append(key)
        elif current_key and part.strip() != END:
            action_data[current_key] += part

    # Handle duplicates
    if duplicate_keys:
        if duplicate_approach is None:
            raise ValueError(f"Duplicate fields found: {', '.join(duplicate_keys)}. Specify a duplicate_approach to handle this.")
        elif duplicate_approach == DuplicateFieldApproach.FIRST:
            new_result = {}
            for key in key_order:
                if key not in new_result:
                    new_result[key] = action_data[key]
                else:
                    new_result[key] += f"\n{WRAP}{key.upper()}{WRAP}\n{action_data[key]}"
            action_data = new_result
        elif duplicate_approach == DuplicateFieldApproach.LAST:
            new_result = {}
            prev_key = None
            for key in key_order:
                if key in new_result and key in duplicate_keys:
                    if prev_key:
                        new_result[prev_key] += f"\n{WRAP}{key.upper()}{WRAP}\n{new_result[key]}"
                    new_result[key] = action_data[key]
                else:
                    new_result[key] = action_data[key]
                prev_key = key
            action_data = new_result

    # Post-processing
    if 'is_destructive' in action_data:
        action_data['is_destructive'] = action_data['is_destructive'].strip().lower() == 'true'
    if 'task_complete' in action_data:
        action_data['task_complete'] = action_data['task_complete'].strip().lower() == 'true'

    # Validate that all required fields for the format are present
    if current_format:
        if not all(key in action_data for key in current_format):
            missing = [key for key in current_format if key not in action_data]
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
    else:
        raise ValueError("No valid format was identified in the input")

    return action_data
