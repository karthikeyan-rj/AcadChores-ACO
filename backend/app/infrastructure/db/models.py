from datetime import datetime
from typing import List, Optional, Dict, Any
from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

class User(Document):
    email: str
    name: str
    avatar_url: Optional[str] = None
    role: str = "user"  # admin, user, guest
    hashed_password: Optional[str] = None
    google_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = ["email", "google_id"]

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "workflows"
        indexes = ["owner_id", "created_at"]

class WorkflowExecution(Document):
    workflow_id: PydanticObjectId
    user_id: PydanticObjectId
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled, waiting
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    current_step_index: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "workflow_executions"
        indexes = ["workflow_id", "status", "user_id", ("user_id", "started_at"), ("user_id", "status")]

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    last_indexed_at: datetime = Field(default_factory=datetime.utcnow)

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "index_configs"
        indexes = ["user_id", ("user_id",)]

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "index_jobs"
        indexes = ["user_id", "status", ("user_id", "status"), ("user_id", "created_at")]

class MemoryStore(Document):
    user_id: PydanticObjectId
    type: str  # knowledge, preference, long_term_action
    key: str
    value: str
    vector_embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "memory_store"
        indexes = ["user_id", "type", "key"]
