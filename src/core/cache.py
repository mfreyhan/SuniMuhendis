import json
import hashlib
from typing import Dict, Any, Optional
from .types import EvaluationResult

class SimpleCache:
    """
    Aynı task ve design parametreleri geldiğinde sonucu hatırlayan basit bir bellek içi cache.
    """
    def __init__(self):
        self._cache: Dict[str, EvaluationResult] = {}
        
    def _generate_key(self, task_params: Dict[str, Any], design_params: Dict[str, Any]) -> str:
        task_str = json.dumps(task_params, sort_keys=True)
        design_str = json.dumps(design_params, sort_keys=True)
        combined = f"{task_str}_{design_str}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
        
    def get(self, task_params: Dict[str, Any], design_params: Dict[str, Any]) -> Optional[EvaluationResult]:
        key = self._generate_key(task_params, design_params)
        return self._cache.get(key)
        
    def set(self, task_params: Dict[str, Any], design_params: Dict[str, Any], result: EvaluationResult):
        key = self._generate_key(task_params, design_params)
        self._cache[key] = result
        
    def clear(self):
        self._cache.clear()
