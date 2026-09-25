"""ringlog.py：只追加日志 + 断点重放 + 截断 + 快照恢复。"""
from __future__ import annotations

import json
import os

SNAPSHOT_PATH = "ringlog.snapshot.json"


class Journal:
    def __init__(self, capacity: int = 8):
        self.capacity = capacity
        self.records = []
        self.base = 0          # records[0] 的绝对序号（已截断掉的条数）
        self.checkpoint_pos = 0    # 断点（绝对序号）：之前的记录视为已应用
        self.replayed = 0      # 累计实际应用的条数
        self.truncated = 0     # 累计丢弃的条数
        self.applied = set()   # 已应用的 op_id

    def append(self, op_id: str, op: str) -> dict:
        self.records.append({"op_id": op_id, "op": op})
        return {"records": len(self.records)}

    def replay(self) -> dict:
        """只处理断点之后且未应用过的记录（按 op_id 去重）。"""
        start = self.checkpoint_pos - self.base
        newly = 0
        for record in self.records[start:]:
            op_id = record["op_id"]
            if op_id not in self.applied:
                self.applied.add(op_id)
                newly += 1
        self.replayed += newly
        return {"replayed": newly, "applied": sorted(self.applied)}

    def checkpoint(self) -> dict:
        """把断点推进到当前日志末尾。"""
        self.checkpoint_pos = self.base + len(self.records)
        return {"checkpoint": self.checkpoint_pos}

    def truncate(self) -> dict:
        """丢掉断点之前的记录；断点之后的记录保留。"""
        cut = self.checkpoint_pos - self.base
        del self.records[:cut]
        self.base = self.checkpoint_pos
        self.truncated += cut
        return {"removed": cut, "checkpoint": self.checkpoint_pos}

    def persist(self, path: str = SNAPSHOT_PATH) -> dict:
        """落盘快照，返回 blob。"""
        blob = {
            "records": self.records,
            "base": self.base,
            "checkpoint": self.checkpoint_pos,
            "applied": sorted(self.applied),
            "replayed": self.replayed,
            "truncated": self.truncated,
            "capacity": self.capacity,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(blob, fh)
        return blob

    def restore(self, blob: dict) -> dict:
        """从 blob 恢复记录、断点、已应用集合与计数。"""
        self.records = [dict(record) for record in blob["records"]]
        self.base = blob["base"]
        self.checkpoint_pos = blob["checkpoint"]
        self.applied = set(blob["applied"])
        self.replayed = blob["replayed"]
        self.truncated = blob["truncated"]
        self.capacity = blob.get("capacity", self.capacity)
        return self.stats()

    def recover(self, path: str = SNAPSHOT_PATH) -> dict:
        """重启恢复：有快照则恢复，否则回到空日志。"""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self.restore(json.load(fh))
        else:
            self.__init__(self.capacity)
        return {"checkpoint": self.checkpoint_pos, "records": len(self.records),
                "applied": sorted(self.applied)}

    def stats(self) -> dict:
        return {"records": len(self.records), "replayed": self.replayed,
                "truncated": self.truncated, "applied": len(self.applied),
                "checkpoint": self.checkpoint_pos, "capacity": self.capacity}
