from collections import OrderedDict
from typing import Any, Optional
import threading

class LRUCache:
    def __init__(self, capacity: int) -> None:
        # bug1 : validate dict
        if capacity <= 0 :
            raise ValueError("Bad input for capacity") 
        
        # bug2 : lock is a class instance
        self._lock = threading.RLock()
        self._capacity = capacity
        self._cache: OrderedDict[Any, Any] = OrderedDict()

    def get(self, key: Any) -> Optional[Any]: 
        if key in self._cache:
            with self._lock :
                if key not in self._cache:
                    return None
                
                self._cache.move_to_end(key)
                return self._cache[key]

    def put(self, key: Any, value: Any) -> None: 
        with self._lock:
            self._cache[key]=value
            self._cache.move_to_end(key)

            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)

    def __len__(self): 
        with self._lock:
            return len(self._cache)

    def __repr__(self) -> str:
        with self._lock:
            return f"LRUCache(capacity={self._capacity}, size={len(self._cache)})"

    def __contains__(self, item: Any) -> bool:
        with self._lock:
            return item in self._cache
