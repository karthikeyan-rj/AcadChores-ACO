from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


def _utcnow():
    return datetime.now(timezone.utc)


class User(Document):
    email: str
    name: str
    avatar_url: Optional[str] = None
    role: str = "user"  # admin, user, guest
    hashed_password: Optional[str] = None
    google_id: Optional[str] = None
    account_status: str = "active"  # active, suspended, deactivated
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "users"
        indexes = [
            "google_id",
            IndexModel([("email", ASCENDING)], unique=True, name="email_unique_idx"),
        ]

class Step(BaseModel):
    step_id: str
    name: str
    action: str
    parameters: Dict[str, Any] = {}
    agent_type: str

class Trigger(BaseModel):
    trigger_type: str = "manual"  # manual, schedule, webhook
    cron_expression: Optional[str] = None

class Workflow(Document):
    title: str
    description: str
    owner_id: PydanticObjectId
    steps: List[Step] = []
    trigger: Trigger = Field(default_factory=Trigger)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "workflows"
        indexes = ["owner_id", "created_at"]

class WorkflowExecution(Document):
    workflow_id: PydanticObjectId
    user_id: PydanticObjectId
    conversation_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "pending"
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    current_step_index: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    result: Optional[str] = None
    result_type: Optional[str] = None
    last_completed_step: Optional[str] = None
    partial_result: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "workflow_executions"
        indexes = ["workflow_id", "status", "user_id", "conversation_id", ("user_id", "started_at"), ("user_id", "status")]

class TaskLog(Document):
    execution_id: PydanticObjectId
    user_id: Optional[PydanticObjectId] = None
    step_id: str
    agent_name: str
    action: str
    status: str  # success, failure
    logs: str
    screenshot_path: Optional[str] = None
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "task_logs"
        indexes = ["execution_id", "created_at", "user_id", ("user_id", "execution_id")]

class Rule(BaseModel):
    agent: str
    action: str
    policy: str  # allow, block, ask

class PermissionPolicy(Document):
    role: str
    rules: List[Rule] = []
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "permission_policies"
        indexes = ["role"]

class FileIndex(Document):
    file_path: str
    file_name: str
    extension: str
    size_bytes: int
    modified_at: datetime
    user_id: Optional[PydanticObjectId] = None
    last_indexed_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "file_index"
        indexes = ["file_name", "file_path", "user_id", ("user_id", "file_path"), ("user_id", "extension")]

class IndexConfig(Document):
    user_id: PydanticObjectId
    roots: List[str] = Field(default_factory=list)
    enabled: bool = True
    interval_seconds: int = 3600
    max_file_size_mb: int = 100
    exclude_extensions: List[str] = Field(default_factory=lambda: [".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o"])
    exclude_dirs: List[str] = Field(default_factory=lambda: ["node_modules", ".git", "__pycache__", ".venv", "venv", "AppData", "Windows", "Program Files", "Program Files (x86)"])
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "index_configs"
        indexes = ["user_id"]

class IndexJob(Document):
    user_id: PydanticObjectId
    status: str = "pending"  # pending, running, completed, failed
    roots: List[str] = Field(default_factory=list)
    files_indexed: int = 0
    files_updated: int = 0
    files_removed: int = 0
    errors: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "index_jobs"
        indexes = ["user_id", "status", ("user_id", "status"), ("user_id", "created_at")]

class MemoryStore(Document):
    user_id: PydanticObjectId
    type: str  # knowledge, preference, long_term_action
    key: str
    value: str
    vector_embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "memory_store"
        indexes = ["user_id", "type", "key"]


class UserApiKey(Document):
    user_id: PydanticObjectId
    provider: str  # openai, anthropic, gemini, groq, mistral, openrouter, cohere
    encrypted_key: str
    key_hint: str = ""  # masked display like "••••••••abcd"
    label: str = ""  # user-friendly label e.g. "Work OpenAI key"
    is_active: bool = True
    is_default: bool = False
    validated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "user_api_keys"
        indexes = ["user_id", ("user_id", "provider"), ("user_id", "is_active")]


class FallbackUsage(Document):
    user_id: PydanticObjectId
    provider: str
    model: str
    timestamp: datetime = Field(default_factory=_utcnow)
    fallback_reason: str
    planner_source: str  # rule_based, ollama, ollama_repair, cloud_fallback
    local_attempts: int = 0
    quality_score: float = 0.0
    success: bool = True
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0

    class Settings:
        name = "fallback_usage"
        indexes = ["user_id", "timestamp", ("user_id", "timestamp")]


class UserSettings(Document):
    user_id: PydanticObjectId
    ai_local_only: bool = True
    fallback_to_local: bool = True
    default_provider: str = "ollama"
    default_model: str = ""
    default_credential_id: Optional[str] = None
    default_reasoning_level: str = "balanced"
    cloud_fallback_enabled: bool = False
    cloud_provider: str = "openai"
    cloud_model: str = "gpt-4o-mini"
    workflow_quality_threshold: int = 70
    local_planner_retry_count: int = 1
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "user_settings"
        indexes = ["user_id"]


class ChatMessage(Document):
    user_id: PydanticObjectId
    conversation_id: str
    role: str  # user, assistant
    message_type: str  # user, assistant, workflow_plan, workflow_status, system, error
    content: str
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "chat_messages"
        indexes = ["user_id", "conversation_id", ("user_id", "conversation_id"), ("user_id", "created_at")]


class Conversation(Document):
    conversation_id: str
    user_id: PydanticObjectId
    title: Optional[str] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    preferred_credential_id: Optional[str] = None
    reasoning_level: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    last_message_at: Optional[datetime] = None

    class Settings:
        name = "conversations"
        indexes = [
            "user_id",
            IndexModel([("user_id", ASCENDING), ("conversation_id", ASCENDING)], unique=True, name="user_conversation_idx"),
            IndexModel([("user_id", ASCENDING), ("last_message_at", ASCENDING)], name="user_last_msg_idx"),
        ]
