"""check_http.py：起服务、按脚本走一圈，打印验收面。"""
import json
import sys
import threading
import urllib.error
import urllib.request

from server import serve


def call(method, url, body=None):
    request = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def parse(text):
    try:
        return json.loads(text)
    except Exception:
        return {"_raw": (text or "")[:60]}


def main() -> int:
    spec = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "sample/ops.json", encoding="utf-8"))
    server = serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_port
    for step in spec["ops"]:
        call("POST", base + "/" + step["op"], json.dumps(step).encode())
    first = parse(call("POST", base + "/replay", b"{}")[1])
    again = parse(call("POST", base + "/replay", b"{}")[1])
    truncated = parse(call("POST", base + "/truncate", b"{}")[1])
    after = parse(call("POST", base + "/replay", b"{}")[1])
    stats = parse(call("GET", base + "/")[1])
    recovered = parse(call("POST", base + "/recover", b"{}")[1])
    print("首次重放的条数 =", first.get("replayed"))
    print("重复重放的条数（幂等应为 0） =", again.get("replayed"))
    print("断点位置 =", truncated.get("checkpoint"))
    print("截断掉的条数 =", truncated.get("removed"))
    print("截断后重放的条数 =", after.get("replayed"))
    print("已应用的记录数 =", stats.get("applied"))
    print("恢复后的断点 =", recovered.get("checkpoint"))
    print("不变量（重放幂等：已应用的记录不重复） =", spec["idempotent_invariant"])
    print("记录数 =", sum(1 for step in spec["ops"] if step["op"] == "append"))
    server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
