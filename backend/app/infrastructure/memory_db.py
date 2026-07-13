import json
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4
from bson import ObjectId

logger = logging.getLogger(__name__)

PERSIST_DIR = os.path.join(os.path.expanduser("~"), ".aco_data")
PERSIST_FILE = os.path.join(PERSIST_DIR, "persist.json")

_in_memory_collections: Dict[str, Dict[str, Any]] = {
    "workflows": {},
    "workflow_executions": {},
    "task_logs": {},
    "users": {},
    "permission_policies": {},
    "file_index": {},
    "memory_store": {},
    "index_configs": {},
    "index_jobs": {},
}

def _load_from_disk():
    """Load persisted data from disk on startup."""
    if not os.path.exists(PERSIST_FILE):
        return
    try:
        with open(PERSIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for coll_name, docs in data.items():
            if coll_name in _in_memory_collections:
                for doc_id, doc in docs.items():
                    # Rehydrate ObjectId strings back to ObjectId objects
                    if "_id" in doc and isinstance(doc["_id"], str):
                        try:
                            doc["_id"] = ObjectId(doc["_id"])
                        except Exception:
                            doc["_id"] = ObjectId()
                _in_memory_collections[coll_name] = docs
        logger.info(f"MemoryDB: loaded {sum(len(d) for d in _in_memory_collections.values())} documents from disk")
    except Exception as e:
        logger.warning(f"MemoryDB: failed to load persisted data: {e}")

def _save_to_disk():
    """Save all collections to disk. Called after every write operation."""
    try:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        # Convert ObjectId values to strings for JSON serialization
        serializable = {}
        for coll_name, docs in _in_memory_collections.items():
            serializable[coll_name] = {}
            for doc_id, doc in docs.items():
                sdoc = {}
                for k, v in doc.items():
                    if isinstance(v, ObjectId):
                        sdoc[k] = str(v)
                    elif isinstance(v, datetime):
                        sdoc[k] = v.isoformat()
                    else:
                        sdoc[k] = v
                serializable[coll_name][doc_id] = sdoc
        # Atomic write: write to temp file then rename
        tmp_file = PERSIST_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
        # Replace original file
        if os.path.exists(PERSIST_FILE):
            os.replace(tmp_file, PERSIST_FILE)
        else:
            os.rename(tmp_file, PERSIST_FILE)
    except Exception as e:
        logger.error(f"MemoryDB: failed to persist data: {e}")

# Load on module import
_load_from_disk()


def _to_doc(data: dict) -> dict:
    if "_id" not in data:
        data["_id"] = ObjectId()
    data["updated_at"] = datetime.utcnow().isoformat()
    return data


def _serialize_doc(doc: dict) -> dict:
    """Convert ObjectId and datetime values to JSON-safe strings."""
    if doc is None:
        return None
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out

class MemoryDB:
    @staticmethod
    async def insert(collection: str, data: dict) -> ObjectId:
        doc = _to_doc(data)
        _in_memory_collections[collection][str(doc["_id"])] = doc
        logger.info(f"MemoryDB: inserted into {collection}, id={doc['_id']}")
        _save_to_disk()
        return doc["_id"]

    @staticmethod
    async def find_one(collection: str, filter_dict: dict) -> Optional[dict]:
        for doc in _in_memory_collections[collection].values():
            match = all(
                doc.get(k) == v or str(doc.get(k, "")) == str(v)
                for k, v in filter_dict.items()
            )
            if match:
                return _serialize_doc(doc)
        return None

    @staticmethod
    async def find(collection: str, filter_dict: dict = None) -> List[dict]:
        if not filter_dict:
            return [_serialize_doc(d) for d in _in_memory_collections[collection].values()]
        results = []
        for doc in _in_memory_collections[collection].values():
            match = all(
                doc.get(k) == v or str(doc.get(k, "")) == str(v)
                for k, v in filter_dict.items()
            )
            if match:
                results.append(_serialize_doc(doc))
        return results

    @staticmethod
    async def update(collection: str, filter_dict: dict, update_data: dict) -> bool:
        for doc_id, doc in _in_memory_collections[collection].items():
            match = all(
                doc.get(k) == v or str(doc.get(k, "")) == str(v)
                for k, v in filter_dict.items()
            )
            if match:
                safe_update = {}
                for uk, uv in update_data.items():
                    if isinstance(uv, datetime):
                        safe_update[uk] = uv.isoformat()
                    else:
                        safe_update[uk] = uv
                doc.update(safe_update)
                doc["updated_at"] = datetime.utcnow().isoformat()
                _save_to_disk()
                return True
        return False

    @staticmethod
    async def count(collection: str) -> int:
        return len(_in_memory_collections[collection])

    @staticmethod
    async def find_sorted(collection: str, sort_key: str, limit: int = 10, reverse: bool = True) -> List[dict]:
        docs = list(_in_memory_collections[collection].values())
        docs.sort(key=lambda d: d.get(sort_key, ""), reverse=reverse)
        return [_serialize_doc(d) for d in docs[:limit]]

memory_db = MemoryDB()
