from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RunRecord:
    run_id: str
    prompt: str
    status: str = "queued"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    output_markdown: Optional[str] = None
    artifacts_dir: Optional[str] = None
    log_path: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
