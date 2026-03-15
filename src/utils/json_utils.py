import re
import json

def repair_truncated_json(s):
    """Closes all open braces and brackets in the correct order."""
    stack = []
    in_string = False
    escape = False
    for i, char in enumerate(s):
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char == '}':
                if stack and stack[-1] == '}':
                    stack.pop()
            elif char == ']':
                if stack and stack[-1] == ']':
                    stack.pop()
    
    # If we are in a string, close it first
    res = s
    if in_string:
        res += '"'
    
    # Close everything else in reverse order
    while stack:
        res += stack.pop()
    return res

def extract_json(text: str):
    """Robustly extracts JSON from a string, handling markdown blocks and nested structures."""
    if not text:
        return None
        
    # 1. Try to find content within ```json ... ```
    json_block = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_block:
        content = json_block.group(1)
    else:
        # 2. If no block, find the first '{' and try to use everything after it
        start = text.find('{')
        if start != -1:
            content = text[start:]
        else:
            # Maybe it's a list
            start = text.find('[')
            if start != -1:
                content = text[start:]
            else:
                return None

    # 3. Basic cleanup
    # Remove control characters
    content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)

    # 4. Aggressive Repair
    # Fix missing commas between objects in a list or fields
    content = re.sub(r'\}\s*\{', '},{', content)
    content = re.sub(r'\]\s*\{', '],{', content)
    
    # Fix missing commas between key-value pairs
    content = re.sub(r'("[^"]*")\s*("[^"]*")\s*:', r'\1, \2:', content)
    
    # Fix trailing commas
    content = re.sub(r',\s*\}', '}', content)
    content = re.sub(r',\s*\]', ']', content)

    # 5. Handle Truncated JSON
    repaired = repair_truncated_json(content)
    
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        # Fallback to iterative removal if still failing
        temp_content = repaired
        while len(temp_content) > 1:
            try:
                return json.loads(temp_content)
            except:
                temp_content = temp_content[:-1]
                # Re-run repair on the smaller piece
                temp_repaired = repair_truncated_json(temp_content)
                try:
                    return json.loads(temp_repaired)
                except:
                    pass
        return None
