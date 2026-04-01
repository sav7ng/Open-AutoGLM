# Model Client and Actions

## Purpose

描述视觉-语言模型客户端（OpenAI 兼容、流式解析）与动作 DSL 的契约：`ModelConfig` / `ModelClient`、`parse_action`、`ActionHandler` / `IOSActionHandler` 支持的 `action` 名称及坐标约定。

## Requirements

### Requirement: ModelConfig 字段

`ModelConfig`（`phone_agent/model/client.py`）SHALL 包含：`base_url`、`api_key`、`model_name`、`max_tokens`、`temperature`、`top_p`、`frequency_penalty`、`extra_body`、`lang`（`cn` | `en`，用于 UI 消息）。默认值 SHALL 与模块中 dataclass 定义一致。

#### Scenario: 自定义推理参数

- **GIVEN** 调用方设置 `temperature` 与 `extra_body`
- **WHEN** `ModelClient.request` 调用 `chat.completions.create`
- **THEN** 上述字段 SHALL 传入 SDK

### Requirement: 流式响应与解析

`ModelClient.request` SHALL 使用 `stream=True` 消费增量；SHALL 在输出中识别进入动作阶段的标记（实现中使用 `finish(message=` 与 `do(action=` 等）；SHALL 返回 `ModelResponse(thinking, action, raw_content, ...)`，其中 `action` 为供 `parse_action` 使用的字符串。

#### Scenario: 思考与动作分段

- **GIVEN** 模型先输出自然语言再输出 `do(...)` 或 `finish(...)`
- **WHEN** 流结束
- **THEN** `thinking` 与 `action` 字符串 SHALL 被分离填充至 `ModelResponse`

### Requirement: 多模态消息构建

`MessageBuilder` SHALL 提供创建 system/user/assistant 消息及 `build_screen_info(current_app)`；用户消息 SHALL 支持 `text` 与 `image_base64`（与 OpenAI 兼容的多模态 content 格式一致）。

#### Scenario: 每步用户消息

- **GIVEN** 非首步
- **WHEN** 构建用户消息
- **THEN** 文本 SHALL 包含 `** Screen Info **` 与当前应用信息，并附带最新截图

### Requirement: 动作解析 parse_action

`parse_action(response: str)`（`phone_agent/actions/handler.py`）SHALL：

- 对以 `do(action="Type"` 或 `do(action="Type_Name"` 开头的响应走专用分支，抽取 `text` 并返回 `{"_metadata": "do", "action": "Type", "text": ...}`
- 对以 `do` 开头的其它响应使用 `ast.parse` + `ast.literal_eval` 解析关键字参数，并设置 `_metadata` 为 `do`
- 对 `finish` 响应设置 `_metadata` 为 `finish` 并抽取 `message`
- 无法解析时抛出 `ValueError`

#### Scenario: 安全解析 do

- **GIVEN** 模型输出合法 `do(action="Tap", element=[500, 500])` 形式
- **WHEN** 调用 `parse_action`
- **THEN** 结果字典 SHALL 含 `action`、`element` 与 `_metadata: "do"`，且 SHALL 不使用 `eval`

### Requirement: ActionHandler 路由与坐标

`ActionHandler.execute` SHALL 根据 `action["_metadata"]` 区分：`finish` 直接返回 `should_finish=True`；`do` 则根据 `action["action"]` 分发。未知 `_metadata` SHALL 导致结束并带错误信息；未知 `action` 名称 SHALL 返回失败且默认不结束（与当前实现一致）。

Android/HarmonyOS 路径 SHALL 将模型给出的 `element` 视为 0–1000 归一化坐标，通过 `_convert_relative_to_absolute` 转为像素。

#### Scenario: Tap 坐标换算

- **GIVEN** 截图宽高为 1080×2400，`element` 为 `[500, 500]`
- **WHEN** 执行 `Tap`
- **THEN** 点击坐标 SHALL 为 `(int(500/1000*1080), int(500/1000*2400))`

### Requirement: 已注册的 do 动作名

`ActionHandler` 与 `IOSActionHandler` 的处理器映射 SHALL 至少包含且名称一致：`Launch`、`Tap`、`Type`、`Type_Name`（映射到与 `Type` 相同处理）、`Swipe`、`Back`、`Home`、`Double Tap`、`Long Press`、`Wait`、`Take_over`、`Note`、`Call_API`、`Interact`。

#### Scenario: 新增动作

- **GIVEN** 需求要求新动作 `Foo`
- **WHEN** 实现变更
- **THEN** 须在 `ActionHandler._get_handler` 与 `IOSActionHandler._get_handler` 中同步注册（除非平台故意不支持），并更新本 spec 与模型侧提示词约定

### Requirement: 敏感操作与接管

`Take_over` SHALL 在**交互模式**下触发 `takeover_callback`（与实现一致：默认可为控制台阻塞实现）。**非交互模式**下 SHALL **不**调用 `takeover_callback`；SHALL 返回 `ActionResult`，使 Agent 结束本任务，且结束消息 SHALL 取自该动作 `message` 字段；若缺失 SHALL 使用与实现一致的默认字符串（与交互路径下 `Take_over` 所用默认一致）。

需要确认的敏感操作（当前实现为带 `message` 的 `Tap`，与 `handler` 一致）在**交互模式**下 SHALL 在继续前调用 `confirmation_callback`；若返回 False，SHALL 中止该动作并返回相应 `ActionResult`。在**非交互模式**下 SHALL **不**调用 `confirmation_callback`、SHALL **不**执行点击；SHALL 返回 `ActionResult`，使 Agent 结束本任务，结束消息 SHALL 取自该动作 `message` 字段（缺失时同上默认）。

交互模式与非交互模式由运行时传入 `ActionHandler` / `IOSActionHandler` 的配置区分（与 agent-runtime spec 中的 `interactive_human` 对齐）；默认 SHALL 为交互模式，与历史行为一致。

#### Scenario: 用户拒绝确认

- **GIVEN** `interactive_human` 为 True（默认）且 `confirmation_callback` 返回 False
- **WHEN** 执行需确认的敏感 `Tap`
- **THEN** `ActionResult` SHALL 反映未执行且不应视为成功完成，且 SHALL 结束任务（与当前实现一致）

#### Scenario: 非交互模式下 Take_over

- **GIVEN** `interactive_human` 为 False
- **WHEN** 执行 `Take_over` 且动作含 `message="需要登录"`
- **THEN** SHALL **不**调用 `takeover_callback`；Agent SHALL 结束任务；返回给用户/上层的结束消息 SHALL 为 `需要登录`（或实现默认 fallback）

#### Scenario: 非交互模式下敏感 Tap

- **GIVEN** `interactive_human` 为 False
- **WHEN** 执行带 `message` 的敏感 `Tap`
- **THEN** SHALL **不**调用 `confirmation_callback`；SHALL **不**执行点击；Agent SHALL 结束任务；结束消息 SHALL 为该动作 `message` 字段（或默认 fallback）

#### Scenario: 交互模式下 Take_over 仍调用接管回调

- **GIVEN** `interactive_human` 为 True 且调用方注入 `takeover_callback`
- **WHEN** 执行 `Take_over`
- **THEN** SHALL 调用 `takeover_callback`（行为与变更前一致）

### Requirement: 设备后端差异

`ActionHandler` SHALL 通过 `get_device_factory()` 调用 ADB 或 HDC 模块执行底层输入。`IOSActionHandler` SHALL 通过 WDA / HTTP 与会话 ID 执行等价语义动作，不依赖 `DeviceFactory`。

#### Scenario: 同一 DSL 双端

- **GIVEN** 模型输出同一 `do(action="Tap", ...)`
- **WHEN** 在 Android 与 iOS 上分别执行
- **THEN** 各自 handler SHALL 将语义映射到对应平台 API，坐标换算规则保持一致（0–1000）
