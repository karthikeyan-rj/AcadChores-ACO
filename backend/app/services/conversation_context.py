"""Builds conversation context for the planner and classifier.

Extracts structured entity metadata (file paths, destinations, etc.) from
previous messages and workflow results so that ambiguous references like
"that file" or "delete it" can be resolved to concrete values.
"""
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

REFERENCE_PATTERNS = {
    "that file": "last_file",
    "the file": "last_file",
    "the previous file": "last_file",
    "the last file": "last_file",
    "that document": "last_file",
    "the document": "last_file",
    "delete it": "last_file",
    "remove it": "last_file",
    "move it": "last_file",
    "rename it": "last_file",
    "open it": "last_file",
    "run it": "last_task",
    "do it again": "last_task",
    "repeat that": "last_task",
    "run the previous task": "last_task",
    "run the previous task again": "last_task",
    "that folder": "last_destination",
    "the folder": "last_destination",
    "the destination": "last_destination",
    "that destination": "last_destination",
    "move that to": "last_file",
    "rename the file i created": "last_file",
    "rename the file": "last_file",
    "the file i just created": "last_file",
    "the file i created": "last_file",
    "the file we created": "last_file",
    "the one i just made": "last_file",
    "the one we just made": "last_file",
}

# Ordered by length (longest first) to prefer more specific matches
_REFERENCE_PATTERNS_SORTED = sorted(REFERENCE_PATTERNS.keys(), key=len, reverse=True)

# Patterns to extract entities from task results
FILE_PATH_PATTERN = re.compile(r'[A-Z]:\\[^\s"\'<>:|*?]+|[~]/[^\s"\'<>:|*?]+|/[a-zA-Z][^\s"\'<>:|*?]+')


def build_entity_context(messages: List[dict]) -> Dict[str, Any]:
    """Extract structured entities from conversation messages.

    Scans messages in chronological order and tracks:
    - last_created_file: most recently created file path
    - last_deleted_file: most recently deleted file path
    - last_moved_file: most recently moved source path
    - last_destination_folder: most recently used destination
    - last_modified_file: most recently renamed/modified path
    - last_task_description: description of the last workflow
    - last_workflow_id: ID of the last workflow
    - active_workflow_id: ID of the currently active workflow (if any)
    - last_workflow_result: result of the most recent workflow
    - last_workflow_state: state of the most recent workflow
    - last_stop_reason: reason the last workflow was stopped
    """
    entities: Dict[str, Any] = {
        "last_created_file": None,
        "last_deleted_file": None,
        "last_moved_file": None,
        "last_destination_folder": None,
        "last_modified_file": None,
        "last_file": None,
        "last_task_description": None,
        "last_workflow_id": None,
        "active_workflow_id": None,
        "last_workflow_result": None,
        "last_workflow_state": None,
        "last_stop_reason": None,
    }

    for msg in messages:
        content = msg.get("content", "")
        msg_type = msg.get("message_type", "")
        metadata = msg.get("metadata", {}) or {}
        execution_id = msg.get("execution_id")
        workflow_state = metadata.get("workflow_state")

        # Track active workflow from execution_id in messages
        if execution_id and workflow_state in (None, "Planning", "Executing", "Waiting", "Retry", "Stopping"):
            entities["active_workflow_id"] = execution_id

        # Track completed/stopped/failed workflow results
        if workflow_state in ("Completed", "Failed", "Cancelled"):
            entities["last_workflow_state"] = workflow_state
            entities["last_workflow_result"] = content[:500]
            if workflow_state == "Cancelled":
                entities["last_stop_reason"] = content[:300]
            entities["active_workflow_id"] = None

        # Extract file paths from content
        paths = FILE_PATH_PATTERN.findall(content)
        task_results = metadata.get("task_results", {})
        entity_updates = metadata.get("entities", {})

        # Merge explicit entity metadata
        for key, val in entity_updates.items():
            if val and key in entities:
                entities[key] = val

        # Extract entities from workflow plan metadata
        if msg_type == "workflow_plan":
            wf_id = msg.get("workflow_id")
            if wf_id:
                entities["last_workflow_id"] = wf_id
            entities["last_task_description"] = content[:200]

        # Extract entities from task completion results (use dict keys directly
        # instead of regex on str(task_results) which doubles backslashes)
        if task_results:
            if task_results.get("deleted"):
                path = task_results.get("path")
                if path:
                    entities["last_deleted_file"] = path
                    entities["last_file"] = path

            if task_results.get("created") or (task_results.get("path") and not task_results.get("deleted")):
                path = task_results.get("path")
                if path:
                    entities["last_created_file"] = path
                    entities["last_file"] = path

            if task_results.get("moved"):
                source = task_results.get("source")
                if source:
                    entities["last_moved_file"] = source
                    entities["last_file"] = source
                destination = task_results.get("destination")
                if destination:
                    entities["last_destination_folder"] = destination

            if task_results.get("renamed"):
                old_path = task_results.get("old_path") or task_results.get("path")
                if old_path:
                    entities["last_modified_file"] = old_path
                    entities["last_file"] = old_path

        # Scan plain content for file creation/deletion patterns.
        # Also scan assistant messages that report actual results (e.g. "File saved: C:\...")
        is_user_message = msg_type in ("user", "") or msg.get("role") == "user"
        has_task_results = bool(task_results)
        if "file saved:" in content.lower() or "created" in content.lower():
            for p in paths:
                entities["last_created_file"] = p
                entities["last_file"] = p
        if "deleted" in content.lower():
            for p in paths:
                entities["last_deleted_file"] = p
                entities["last_file"] = p
        if "moved:" in content.lower():
            for p in paths:
                entities["last_moved_file"] = p
                entities["last_file"] = p

    return entities


def resolve_references(prompt: str, entities: Dict[str, Any]) -> str:
    """Replace ambiguous references in a prompt with concrete entity values.

    For patterns like "delete it", preserves the verb and only replaces the pronoun.
    For patterns like "that file", replaces the entire phrase.
    """
    lower = prompt.lower().strip()

    for pattern in _REFERENCE_PATTERNS_SORTED:
        entity_key = REFERENCE_PATTERNS[pattern]
        if pattern in lower:
            value = entities.get(entity_key)
            if value:
                idx = lower.find(pattern)
                if idx >= 0:
                    # For verb+pronoun patterns (e.g., "delete it"), keep the verb
                    parts = pattern.split()
                    if len(parts) == 2 and parts[1] in ("it", "that"):
                        # Replace only the pronoun, keep the original verb casing
                        original_verb = prompt[idx:idx + len(parts[0])]
                        pronoun_end = idx + len(pattern)
                        resolved = prompt[:idx] + original_verb + " " + value + prompt[pronoun_end:]
                    else:
                        # Replace the entire pattern
                        resolved = prompt[:idx] + value + prompt[idx + len(pattern):]
                    logger.info(f"Resolved reference '{pattern}' -> '{value}'")
                    return resolved

    return prompt


def check_reference_validity(prompt: str, entities: Dict[str, Any]) -> Optional[str]:
    """Check if a reference points to a deleted/nonexistent file.

    Returns a clarification message if the reference is invalid, or None if OK.
    """
    lower = prompt.lower().strip()

    # Check if user is trying to reference a deleted file
    if any(p in lower for p in ["delete it", "remove it", "that file", "the file"]):
        deleted = entities.get("last_deleted_file")
        last_file = entities.get("last_file")
        if deleted and last_file == deleted:
            return (f"The last file you referenced ({deleted}) was already deleted. "
                    "Please provide a specific file name or path.")

    return None


def build_context_summary(entities: Dict[str, Any], recent_messages: List[dict]) -> str:
    """Build a human-readable context summary for the LLM planner."""
    lines = []

    if entities.get("last_created_file"):
        lines.append(f"Last created file: {entities['last_created_file']}")
    if entities.get("last_deleted_file"):
        lines.append(f"Last deleted file: {entities['last_deleted_file']}")
    if entities.get("last_moved_file"):
        lines.append(f"Last moved file: {entities['last_moved_file']}")
    if entities.get("last_destination_folder"):
        lines.append(f"Last destination: {entities['last_destination_folder']}")
    if entities.get("last_modified_file"):
        lines.append(f"Last renamed file: {entities['last_modified_file']}")
    if entities.get("last_task_description"):
        lines.append(f"Last task: {entities['last_task_description'][:100]}")

    if entities.get("active_workflow_id"):
        lines.append(f"Active workflow: {entities['active_workflow_id']}")

    if entities.get("last_workflow_state"):
        state = entities["last_workflow_state"]
        result = entities.get("last_workflow_result", "")
        if state == "Completed" and result:
            lines.append(f"Last workflow completed successfully. Result: {result[:200]}")
        elif state == "Failed" and result:
            lines.append(f"Last workflow failed. Error: {result[:200]}")
        elif state == "Cancelled":
            reason = entities.get("last_stop_reason", "")
            lines.append(f"Last workflow was stopped by the user. Reason: {reason[:200] if reason else 'No reason given'}")

    if recent_messages:
        lines.append("\nRecent conversation:")
        for m in recent_messages[-6:]:
            role = m.get("role", "unknown")
            content = m.get("content", "")[:120]
            lines.append(f"  {role}: {content}")

    return "\n".join(lines) if lines else ""
