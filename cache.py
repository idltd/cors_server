import time
import random
import math
from pathlib import Path
from typing import Union

from config import CACHE_DIR, DEFAULT_CACHE_DURATION

class Cache:
    def __init__(self, cache_duration: int = DEFAULT_CACHE_DURATION):
        self.cache_duration = cache_duration

    def get_cache_file(self, url: str) -> Path:
        return CACHE_DIR / url.replace('://', '_').replace('/', '_')

    def should_refetch(self, file_path: Path) -> bool:
        if not file_path.exists():
            return True
        
        file_age = time.time() - file_path.stat().st_mtime
        if file_age >= self.cache_duration:
            return True
        
        probability = math.log(file_age / self.cache_duration + 1) / math.log(2)
        return random.random() < probability

    def read_cache(self, url: str) -> Union[bytes, None]:
        cache_file = self.get_cache_file(url)
        if not self.should_refetch(cache_file):
            return cache_file.read_bytes()
        return None

    def write_cache(self, url: str, content: bytes) -> None:
        cache_file = self.get_cache_file(url)
        cache_file.write_bytes(content)