from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class RunRequest(BaseModel):
    prompt: str


class RunResponse(BaseModel):
    run_id: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    errors: List[str]
    output_markdown: Optional[str] = None
