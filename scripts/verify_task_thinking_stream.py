"""
手工验证 /task-thinking/{task_id} SSE 事件。

用法：
1) 先启动 API 服务
2) 设置环境变量：
   - API_BASE_URL (默认 http://127.0.0.1:8000)
   - API_KEY
   - MODEL_BASE_URL
3) 执行：python scripts/verify_task_thinking_stream.py
"""

import json
import os
import time

import requests


def main() -> None:
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    api_key = os.getenv("API_KEY", "")
    model_base_url = os.getenv("MODEL_BASE_URL", "")

    if not api_key or not model_base_url:
        raise RuntimeError("请先设置 API_KEY 和 MODEL_BASE_URL")

    submit_resp = requests.post(
        f"{base_url}/run-agent-async",
        json={
            "instruction": "打开系统设置并返回",
            "api_key": api_key,
            "base_url": model_base_url,
            "model_name": "autoglm-phone",
            "max_steps": 2,
            "agent_type": "phone-agent",
            "lang": "cn",
        },
        timeout=30,
    )
    submit_resp.raise_for_status()
    task_id = submit_resp.json()["task_id"]
    print("task_id:", task_id)

    seen = {"start": False, "thinking": False, "complete_or_error": False}
    deadline = time.time() + 180

    with requests.get(
        f"{base_url}/task-thinking/{task_id}",
        stream=True,
        timeout=190,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if time.time() > deadline:
                break
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            event_type = payload.get("event_type")
            print(json.dumps(payload, ensure_ascii=False))
            if event_type == "start":
                seen["start"] = True
            elif event_type == "thinking":
                seen["thinking"] = True
            elif event_type in {"complete", "error"}:
                seen["complete_or_error"] = True
                break

    print("事件覆盖:", seen)
    if not seen["start"]:
        raise RuntimeError("未收到 start 事件")
    if not seen["complete_or_error"]:
        raise RuntimeError("未收到 complete/error 终止事件")


if __name__ == "__main__":
    main()
