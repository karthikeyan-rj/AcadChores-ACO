import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

ACTION_PATTERNS = [
    (r'\b(open|launch|start|run|execute)\s+(calculator|notepad|chrome|firefox|edge|explorer|cmd|powershell|terminal|code|vscode|word|excel|outlook)', "action", "Application launch request"),
    (r'\b(send|email|mail|write to)\b.*\b(to|subject|body|dear|hi|hello)\b', "action", "Email send request"),
    (r'\b(navigate|go to|visit|open)\s+(https?://|www\.|[\w]+\.(com|org|net|io|dev))', "action", "URL navigation request"),
    (r'\b(search|google|look up|find|query)\s+(for|about|on)?\s*["\']?.{3,}', "action", "Web search request"),
    (r'\b(download|upload|save|export)\s+', "action", "File transfer request"),
    (r'\b(install|uninstall|setup|configure)\s+', "action", "Software operation request"),
    (r'\b(click|type|fill|press|select|scroll|drag)\s+', "action", "UI interaction request"),
    (r'\b(delete|remove|rm|erase)\s+(the\s+)?(file|folder|directory|document)\b', "action", "File deletion request"),
    (r'\b(delete|remove|rm|erase)\s+\S+\.\S+', "action", "File deletion request"),
    (r'\b(move|copy|rename)\s+(the\s+)?(file|folder|document)\b', "action", "File operation request"),
    (r'\b(move|copy|rename)\s+\S+\.\S+\s+(to|into|as)\s+', "action", "File operation request"),
    (r'\b(create|make|mkdir)\s+(a\s+)?(folder|directory|file)', "action", "File creation request"),
    (r'\b(move|copy)\s+(all\s+)?(.{2,})\s+(files?|documents?)?\s*(to|into|in)\s+', "action", "Bulk file move request"),
    (r'\b(list|show|display)\s+(all\s+)?(.{2,})\s*(files?|documents?|items?|contents?)', "action", "Directory listing request"),
    (r'\b(find|get|locate)\s+(all\s+)?(.{2,})\s*(files?|documents?)', "action", "File search request"),
    (r'\b(read|open|show)\s+(file|document)\s+', "action", "File read request"),
    (r'\b(summarize|summarise|tldr)\s+', "action", "Summarization request"),
    (r'\b(ping|test connection|check connection)\s+', "action", "Network test request"),
]

CLARIFICATION_PATTERNS = [
    (r'^(delete|remove)\s+(that|it|this)\s*$', "clarification_required", "Ambiguous deletion target — which file?"),
    (r'^(move|copy)\s+(everything|all)\s*$', "clarification_required", "Ambiguous move scope — which files and where?"),
    (r'^(send|open)\s+(it|them|that)\s*$', "clarification_required", "Ambiguous reference — what specifically?"),
    (r'^(organize|sort|clean)\s*(up)?\s*(my|the)?\s*(files?|folder|desktop)?\s*$', "clarification_required", "Ambiguous organization request — what criteria?"),
]

UNSUPPORTED_PATTERNS = [
    (r'^[\d\s\W]{0,2}$', "Input too short or meaningless"),
    (r'^(asdf|qwer|zxcv|test123|aaa+|bbb+|xxx+)\s*$', "Gibberish input"),
    (r'^(hack|exploit|bypass security|crack password|steal data)\b', "Potentially harmful request"),
]


def classify_intent(message: str) -> Dict[str, Any]:
    text = message.strip()
    lower = text.lower()

    if len(text) < 2:
        return {"intent": "clarification_required", "confidence": 1.0, "reason": "Empty or very short input"}

    for pattern, intent, reason in CLARIFICATION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return {"intent": intent, "confidence": 0.95, "reason": reason}

    for pattern, intent, reason in ACTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return {"intent": intent, "confidence": 0.90, "reason": reason}

    greeting = re.match(r'^(hi|hello|hey|howdy|yo|hola|good\s*(morning|afternoon|evening)|namaste|vanakkam|thanks|thank you|bye|goodbye|ok|okay|sure|cool|nice|great)\b', lower)
    if greeting:
        return {"intent": "conversation", "confidence": 0.95, "reason": "Greeting or social message"}

    question = re.match(r'^(what|how|why|when|where|who|which|can you|could you|would you|explain|describe|tell me|help me|what is|what are|how does|how do)\b', lower)
    if question:
        return {"intent": "conversation", "confidence": 0.85, "reason": "Question or informational request"}

    chitchat = re.search(r'(how are you|what\'?s? (your name|up|going on)|who (are|r) you|what can you do|what do you know)', lower)
    if chitchat:
        return {"intent": "conversation", "confidence": 0.90, "reason": "Conversational chitchat"}

    for pattern, reason in UNSUPPORTED_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return {"intent": "unsupported", "confidence": 0.90, "reason": reason}

    return {"intent": "conversation", "confidence": 0.60, "reason": "No action pattern matched — defaulting to conversation"}
