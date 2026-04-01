"""
Pydantic 数据模型和 Schemas

定义所有 API 请求和响应的数据模型。
字段设计与 AgentDroid 项目的 AgentRequest 保持一致。
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal


class AdbConnectionConfig(BaseModel):
    """
    ADB 连接配置

    支持两种连接方式：
    1. local（默认）：本地 ADB 连接，无需额外参数
    2. direct：直连远程 ADB
       - params.address: ADB 地址，如 "192.168.1.100:5555"
    """

    type: str = "local"
    params: Dict[str, Any] = {}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "direct",
                    "params": {
                        "address": "192.168.1.100:5555",
                    },
                },
            ]
        }


class AgentRequest(BaseModel):
    """
    Agent 执行请求（同步/异步）

    Attributes:
        instruction: 任务指令
        max_steps: 最大执行步数
        api_key: API 密钥
        base_url: API 基础 URL
        model_name: 模型名称
        callback_url: 回调 URL（可选，仅用于异步请求）
        agent_type: Agent 类型
        adb_config: ADB 连接配置（可选）
        context_history: 上下文历史记录（可选），格式 [{"role": "user", "content": "..."}, ...]
        lang: Agent 输出语言，仅支持 "cn" 或 "en"，默认 "cn"
    """

    instruction: str
    max_steps: int = 50
    api_key: str
    base_url: str
    model_name: str = "autoglm-phone"
    callback_url: Optional[str] = None
    agent_type: str = "phone-agent"
    adb_config: Optional[AdbConnectionConfig] = None
    context_history: Optional[List[Dict[str, str]]] = None
    lang: Literal["cn", "en"] = "cn"
