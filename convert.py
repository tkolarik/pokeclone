import re
import json
import os

TODO_FILE = os.path.join(os.path.dirname(__file__), 'ToDo.md')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'tasks.json')

def parse_todo():
    if not os.path.exists(TODO_FILE):
        print(f"File {TODO_FILE} not found.")
        return []

    with open(TODO_FILE, 'r') as f:
        lines = f.readlines()

    tasks = []
    current_section = "To Do"
    current_task = None

    # Regex for section headers (e.g., ## To Do)
    section_re = re.compile(r'^##\s+(.+)')
    # Regex for task lines: * **[ID] Title**
    task_re = re.compile(r'^\*\s+(?:~~)?\*\*\[(.*?)\]\s+(.*?)\*\*(?:~~)?')
    # Regex for attributes: * **Key:** Value
    attr_re = re.compile(r'^\s+\*\s+\*\*(.*?):\*\*\s+(.*)')

    for line in lines:
        line = line.strip()
        
        # Check for section
        section_match = section_re.match(line)
        if section_match:
            raw_section = section_match.group(1).strip()
            if "To Do" in raw_section: current_section = "To Do"
            elif "In Progress" in raw_section: current_section = "In Progress"
            elif "On Hold" in raw_section: current_section = "On Hold"
            elif "Done" in raw_section: current_section = "Done"
            continue

        # Check for task start
        task_match = task_re.match(line)
        if task_match:
            if current_task:
                tasks.append(current_task)
            
            task_id = task_match.group(1)
            title = task_match.group(2).replace("(Completed)", "").strip()
            
            current_task = {
                "id": task_id,
                "title": title,
                "status": current_section,
                "priority": "Medium", # Default
                "type": "Task",
                "labels": []
            }
            continue

        # Check for attributes if inside a task
        if current_task:
            attr_match = attr_re.match(line)
            if attr_match:
                key = attr_match.group(1).lower()
                value = attr_match.group(2).strip()
                if key == "priority": current_task["priority"] = value
                elif key == "type": current_task["type"] = value
                elif key == "labels": current_task["labels"] = [l.strip(" `") for l in value.split(',')]

    if current_task:
        tasks.append(current_task)

    return tasks

if __name__ == "__main__":
    tasks = parse_todo()
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)
    print(f"Converted {len(tasks)} tasks to {OUTPUT_FILE}")