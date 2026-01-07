from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml


def load_prompts(path: str) -> Dict[str, str]:
    prompt_path = Path(path)
    if not prompt_path.exists():
        return {}
    data = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}
