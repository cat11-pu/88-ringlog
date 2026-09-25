# ringlog

纯 Python 标准库的本机服务。

## 起服务

    python3 server.py 8000

浏览器打开 http://127.0.0.1:8000/ 看结果。

## 接口

- `POST /append` `{id, op}`：追加一条记录
- `POST /replay`：只重放断点之后且未应用过的记录（按 `op_id` 去重，幂等）
- `POST /checkpoint`：把断点推进到日志末尾
- `POST /truncate`：丢弃断点之前的记录（断点之后的保留）
- `POST /persist` / `POST /recover`：快照落盘 / 重启恢复

## 测试

    python3 -m unittest discover -s tests -v

## 验收自检

    python3 check_http.py
