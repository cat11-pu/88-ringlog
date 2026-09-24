"""ringlog.py：日志重放（基线：从头重放，无断点）。"""
from __future__ import annotations


class Journal:
    def __init__(self, capacity: int = 8):
        self.capacity = capacity
        self.records = []
        self.replayed = 0
        self.truncated = 0
        self.applied = set()

    def append(self, op_id: str, op: str) -> dict:
        """基线：只追加。"""
        self.records.append({"op_id": op_id, "op": op})
        return {"records": len(self.records)}

    def replay(self) -> dict:
        """基线：每次都从头重放全部记录。"""
        self.replayed = len(self.records)
        return {"replayed": self.replayed, "applied": sorted(self.applied)}

    def checkpoint(self) -> dict:
        raise NotImplementedError("重放断点还没实现")

    def truncate(self) -> dict:
        raise NotImplementedError("截断还没实现")

    def recover(self) -> dict:
        raise NotImplementedError("重启恢复还没实现")

    def stats(self) -> dict:
        return {"records": len(self.records), "replayed": self.replayed,
                "truncated": self.truncated, "applied": len(self.applied),
                "capacity": self.capacity}
