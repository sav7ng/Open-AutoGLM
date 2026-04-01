## ADDED Requirements

### Requirement: 任务思考日志字段
系统 SHALL 在任务状态记录中维护 `thinking_logs` 字段，类型为数组，初始值为空数组。`thinking_logs` 的生命周期 SHALL 与任务记录一致。

#### Scenario: 创建任务时初始化思考日志
- **WHEN** 系统创建新的任务记录
- **THEN** 返回的任务记录 SHALL 包含 `thinking_logs: []`

### Requirement: 思考日志追加接口
系统 SHALL 提供线程安全的思考日志追加能力，用于按步骤写入任务执行过程中的思考和状态日志。

#### Scenario: 写入普通思考日志
- **WHEN** 执行链路为存在的任务追加一条思考日志
- **THEN** 系统 SHALL 将日志以追加方式写入对应任务的 `thinking_logs`，并保留 `step`、`log_type`、`thinking`、`timestamp`

#### Scenario: 写入不存在任务
- **WHEN** 执行链路尝试向不存在的任务写入思考日志
- **THEN** 系统 SHALL 不抛出未处理异常，并返回可识别的失败结果

### Requirement: 思考日志并发一致性
系统 MUST 在任务状态读写与思考日志写入路径上复用同一并发保护机制，确保多线程场景下日志不会丢失或发生结构损坏。

#### Scenario: 并发追加日志
- **WHEN** 多个执行线程同时向不同任务追加思考日志
- **THEN** 所有任务的 `thinking_logs` SHALL 保持顺序追加语义且无交叉污染
