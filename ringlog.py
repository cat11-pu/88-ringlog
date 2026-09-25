"""ringlog.py：只追加日志，支持断点重放、截断与快照恢复。"""
from __future__ import annotations

import json
import os


class Journal:
    def __init__(self, capacity: int = 8, state_path: str | None = None):
        self.capacity = capacity
        self.state_path = state_path or os.path.join(os.getcwd(), "ringlog.state.json")
        self.records: list[dict] = []
        self.offset = 0          # records[0] 在整条日志中的绝对下标
        self.checkpoint_pos = 0  # 断点位置（= 断点之前的记录条数）
        self.applied: set[str] = set()
        self.replayed = 0        # 最近一次 replay 实际应用的条数
        self.truncated = 0       # 累计截断条数

    def append(self, op_id: str, op: str) -> dict:
        """追加一条记录。"""
        self.records.append({"op_id": op_id, "op": op})
        return {"records": len(self.records)}

    def replay(self) -> dict:
        """只重放断点之后、且未应用过的记录（按 op_id 去重）。"""
        start = max(self.checkpoint_pos - self.offset, 0)
        count = 0
        for record in self.records[start:]:
            op_id = record["op_id"]
            if op_id in self.applied:
                continue
            self.applied.add(op_id)
            count += 1
        self.replayed = count
        return {"replayed": count, "applied": sorted(self.applied)}

    def checkpoint(self) -> dict:
        """把断点推进到当前日志末尾（到此为止都已应用）。"""
        self.checkpoint_pos = self.offset + len(self.records)
        return {"checkpoint": self.checkpoint_pos}

    def truncate(self) -> dict:
        """丢掉断点之前的记录；断点之后的记录保留，断点绝对位置不变。"""
        removed = max(self.checkpoint_pos - self.offset, 0)
        del self.records[:removed]
        self.offset += removed
        self.truncated += removed
        return {"removed": removed, "checkpoint": self.checkpoint_pos}

    def persist(self) -> dict:
        """把记录、断点、已应用集合与计数落盘，返回快照 blob。"""
        blob = json.dumps({
            "version": 1,
            "capacity": self.capacity,
            "records": self.records,
            "offset": self.offset,
            "checkpoint": self.checkpoint_pos,
            "applied": sorted(self.applied),
            "replayed": self.replayed,
            "truncated": self.truncated,
        }, ensure_ascii=False).encode("utf-8")
        tmp_path = self.state_path + ".tmp"
        with open(tmp_path, "wb") as handle:
            handle.write(blob)
        os.replace(tmp_path, self.state_path)
        return {"blob": blob.decode("utf-8"), "checkpoint": self.checkpoint_pos}

    def restore(self, blob) -> dict:
        """从快照恢复：记录、断点、已应用集合与计数与落盘前一致。"""
        if isinstance(blob, (bytes, bytearray)):
            blob = blob.decode("utf-8")
        data = json.loads(blob) if isinstance(blob, str) else blob
        self.capacity = data["capacity"]
        self.records = [dict(record) for record in data["records"]]
        self.offset = data["offset"]
        self.checkpoint_pos = data["checkpoint"]
        self.applied = set(data["applied"])
        self.replayed = data["replayed"]
        self.truncated = data["truncated"]
        return self.stats()

    def recover(self) -> dict:
        """模拟重启：有落盘快照则恢复，否则回到空白日志。"""
        if os.path.exists(self.state_path):
            with open(self.state_path, "rb") as handle:
                self.restore(handle.read())
            restored = True
        else:
            self.records = []
            self.offset = 0
            self.checkpoint_pos = 0
            self.applied = set()
            self.replayed = 0
            self.truncated = 0
            restored = False
        return {"checkpoint": self.checkpoint_pos, "records": len(self.records),
                "restored": restored}

    def stats(self) -> dict:
        return {"records": len(self.records), "replayed": self.replayed,
                "truncated": self.truncated, "applied": len(self.applied),
                "capacity": self.capacity, "checkpoint": self.checkpoint_pos}
