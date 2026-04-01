# Async Task Management

## Purpose

描述异步任务生命周期管理：task_id 生成、内存状态表、状态转换、查询与取消，与 `app/core/task_manager.py` 对齐。

## Requirements

### Requirement: 任务 ID 生成

系统 SHALL 使用 `uuid.uuid4()` 生成全局唯一的任务 ID（字符串形式），在异步任务提交时分配。

#### Scenario: 任务 ID 格式

- **WHEN** 提交一个异步任务
- **THEN** 返回的 `task_id` SHALL 为合法的 UUID v4 字符串

### Requirement: 任务状态生命周期

系统 SHALL 维护内存任务状态表，每个任务 SHALL 经历以下状态转换：

```
accepted → running → completed
                   → failed
                   → cancelled
```

状态表 SHALL 记录：`task_id`、`status`、`instruction`、`agent_type`、`max_steps`、`callback_url`、`created_at`、`updated_at`、`result`、`error`。

#### Scenario: 正常完成

- **WHEN** 任务提交后被线程池执行并成功完成
- **THEN** 状态 SHALL 依次经历 `accepted` → `running` → `completed`，`result` 字段 SHALL 包含 Agent 执行结果

#### Scenario: 执行失败

- **WHEN** 任务执行过程中抛出异常
- **THEN** 状态 SHALL 变为 `failed`，`error` 字段 SHALL 包含异常信息

### Requirement: 任务状态查询

系统 SHALL 提供 `get_task_status(task_id)` 函数，返回指定任务的完整状态记录。任务不存在时 SHALL 返回 `None`。

#### Scenario: 查询存在的任务

- **WHEN** 以有效的 `task_id` 查询
- **THEN** 返回 SHALL 包含该任务的所有状态字段

#### Scenario: 查询不存在的任务

- **WHEN** 以不存在的 `task_id` 查询
- **THEN** 返回 SHALL 为 `None`

### Requirement: 任务取消

系统 SHALL 支持通过 `cancel_task(task_id)` 设置取消标志。执行线程 SHALL 在每步开始前检查取消标志，若已设置则终止执行并将状态更新为 `cancelled`。

#### Scenario: 取消运行中的任务

- **WHEN** 调用 `cancel_task(task_id)` 且任务正在运行
- **THEN** 任务 SHALL 在下一个检查点终止并更新状态为 `cancelled`

#### Scenario: 取消已完成的任务

- **WHEN** 调用 `cancel_task(task_id)` 且任务已完成
- **THEN** 操作 SHALL 无效果，状态保持 `completed`

### Requirement: 线程安全

任务状态表的所有读写操作 SHALL 通过 `threading.Lock` 保护，确保多线程并发访问时数据一致性。

#### Scenario: 并发更新

- **WHEN** 多个线程同时更新不同任务的状态
- **THEN** 所有更新 SHALL 正确持久化，无数据丢失或覆盖
