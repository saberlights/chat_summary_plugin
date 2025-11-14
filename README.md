# 聊天记录总结插件 (Chat Summary Plugin)

## 功能介绍

智能分析QQ群聊天记录并生成总结，支持精美图片输出。采用AI驱动，根据机器人人设生成个性化总结内容。

### 核心特性

- **群聊整体总结** - 分析群聊整体聊天内容，生成连贯的总结报告
- **单个用户总结** - 针对特定用户的聊天内容进行分析和总结
- **时间范围支持** - 支持查询今天/昨天的聊天记录
- **智能群友称号** - 基于聊天行为分析，为群友生成有趣的称号
- **群聊金句提取** - 从聊天记录中提取精彩语录（群圣经）
- **精美图片输出** - 自动生成包含统计信息、装饰元素的精美总结图片
- **每日自动总结** - 支持每天定时自动生成群聊总结
- **智能降级机制** - 图片生成失败时自动降级为文本输出
- **时区支持** - 支持自定义时区配置，适应不同地区
- **发言分布统计** - 24小时发言活跃度分布图表

## 依赖要求

### Python 依赖

- **Pillow** (>=8.0.0, 必需) - 用于生成总结图片
- **pytz** (>=2021.1, 可选) - 用于时区支持（自动总结功能建议安装）

### MaiBot 要求

- **最低版本**: 0.11.0

### 安装依赖

```bash
# 安装必需依赖
pip install Pillow

# 安装可选依赖（建议安装以支持时区功能）
pip install pytz
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

## 安装和配置

1. 将插件放置到 `plugins/chat_summary_plugin/` 目录
2. 安装必需依赖（见上方）
3. 编辑 `config.toml` 文件，将 `plugin.enabled` 设置为 `true`
4. 根据需要调整其他配置项（见下方配置选项）
5. 重启 MaiBot

## 使用方法

### 基本命令

```
/summary              # 今天的群聊总结
/summary 今天          # 今天的群聊总结（显式指定）
/summary 昨天          # 昨天的群聊总结
/summary @用户名       # 某用户今天的总结
/summary @用户名 昨天   # 某用户昨天的总结
/summary QQ号         # 通过QQ号查询用户今天的总结
/summary QQ号 昨天     # 通过QQ号查询用户昨天的总结
```

### 用户识别方式

支持以下三种方式识别用户：

1. **QQ @提及** - 使用 QQ 的 @ 功能提及用户（CQ码格式）
2. **文本 @昵称** - 直接输入 `@昵称` 的文本格式
3. **直接输入QQ号** - 输入纯数字的QQ号

## 配置选项

编辑 `config.toml`：

```toml
# 插件基本配置
[plugin]
config_version = "1.0.0"     # 配置文件版本
enabled = true               # 是否启用插件

# 总结功能配置
[summary]
group_summary_max_words = 600      # 群聊总结字数限制
user_summary_max_words = 400       # 用户总结字数限制
enable_user_summary = true         # 是否启用用户总结功能
enable_user_titles = true          # 是否启用群友称号分析
enable_golden_quotes = true        # 是否启用金句提取

# 每日自动总结配置
[auto_summary]
enabled = false                    # 是否启用每日自动总结
time = "23:00"                     # 自动总结时间（HH:MM格式，24小时制）
timezone = "Asia/Shanghai"         # 时区设置（需安装 pytz）
min_messages = 10                  # 生成总结所需的最少消息数量
target_chats = []                  # 目标群聊QQ号列表（为空则对所有群聊生效）
```

### 自动总结功能说明

启用 `auto_summary.enabled = true` 后：

- **精确调度** - 每天在指定时间自动生成总结，采用精确计算等待时间的方式，不使用轮询
- **时区支持** - 支持自定义时区（需安装 `pytz`），默认为 `Asia/Shanghai`
- **智能过滤** - 只为达到最小消息数（`min_messages`）的群聊生成总结
- **目标群聊** - 可通过 `target_chats` 指定特定群聊，留空则为所有符合条件的群聊生成
- **避免重复** - 每天只执行一次，避免重复生成

配置示例（仅为指定群聊生成）：

```toml
[auto_summary]
enabled = true
time = "23:00"
timezone = "Asia/Shanghai"
min_messages = 10
target_chats = [123456789, 987654321]  # 只为这些群生成总结
```

配置示例（为所有活跃群聊生成）：

```toml
[auto_summary]
enabled = true
time = "23:00"
timezone = "Asia/Shanghai"
min_messages = 10
target_chats = []  # 留空 = 为所有活跃群聊生成
```

## 图片输出特性

总结将以精美图片形式输出，包含以下元素：

- **标题和时间** - 总结标题和日期信息
- **总结内容** - AI生成的个性化总结文本
- **统计信息** - 消息数量、参与人数等
- **群友称号** - 智能分析的群友特色称号（群聊总结）
- **金句语录** - 提取的群聊精彩语录（群聊总结）
- **发言分布** - 24小时发言活跃度分布图（群聊总结）
- **装饰元素** - 精美的装饰图案，提升视觉效果

图片生成失败时会自动降级为文本输出，确保功能可用性。

## 技术实现

### 架构设计

- **命令处理** - 使用 `BaseCommand` 处理 `/summary` 命令
- **事件处理** - 使用 `BaseEventHandler` 实现定时任务（`ON_START` 事件）
- **调度器** - `SummaryScheduler` 管理每日自动总结，采用精确等待时间计算
- **数据查询** - 通过 `database_api` 查询聊天记录
- **AI生成** - 使用 `llm_api` 生成智能总结，注入机器人人设确保输出符合角色特点
- **图片生成** - `SummaryImageGenerator` 生成精美总结图片
- **聊天分析** - `ChatAnalysisUtils` 提供用户统计、称号分析、金句提取等功能

### 模块结构

```
chat_summary_plugin/
├── plugin.py                 # 插件主文件
├── config.toml              # 配置文件
├── core/                    # 核心功能模块
│   ├── image_generator.py  # 图片生成器
│   └── chat_analysis.py    # 聊天分析工具
├── decorations/            # 装饰图片资源
└── requirements.txt        # Python依赖
```

## 注意事项

1. **生成时间** - 总结生成需要几秒钟时间（取决于消息数量和AI响应速度），请耐心等待
2. **消息过滤** - 仅统计普通聊天消息，不包括命令消息和系统通知
3. **时间范围** - 目前仅支持查询今天和昨天的记录
4. **自动总结** - 每天只执行一次，避免重复
5. **图片输出** - 图片生成失败会自动降级为文本输出，不影响核心功能
6. **字体支持** - 系统需要中文字体支持（通常 Linux/Windows 已自带）
7. **人设注入** - 总结内容会根据 MaiBot 的人设和回复风格生成，确保符合机器人角色特点

## 权限要求

插件需要以下权限：

- `database.messages.read` - 读取聊天消息记录
- `llm.generate` - 调用 LLM 生成总结
- `send.image` - 发送图片消息
- `send.text` - 发送文本消息

## 开发信息

- **版本**: 1.0.0
- **作者**: 久远 ([saberlights](https://github.com/saberlights))
- **许可证**: GPL-3.0-or-later
- **仓库**: [github.com/saberlights/chat_summary_plugin](https://github.com/saberlights/chat_summary_plugin)
- **类别**: Utilities, Analysis, AI
- **关键词**: chat, summary, analysis, ai, 群聊, 总结, 分析, 图片生成, 定时任务

## 更新日志

### v1.0.0 (2025-11-12)

- ✨ 初始版本发布
- ✨ 支持群聊整体总结
- ✨ 支持单个用户总结
- ✨ 支持今天/昨天时间范围
- ✨ 支持智能群友称号分析
- ✨ 支持群聊金句提取
- ✨ 支持精美图片输出
- ✨ 支持每日定时自动总结

## 故障排除

### 图片生成失败

如果图片生成失败，插件会自动降级为文本输出。常见原因：

- Pillow 未安装：`pip install Pillow`
- 缺少字体文件：确保系统有中文字体支持
- 装饰图片缺失：检查 `decorations/` 目录是否完整

### 自动总结不执行

检查以下配置：

- `plugin.enabled` 和 `auto_summary.enabled` 都需要为 `true`
- 时间格式正确：`HH:MM`（24小时制）
- 如果使用时区功能，确保已安装 `pytz`
- 群聊消息数量是否达到 `min_messages` 要求

### 用户识别失败

- 确保使用正确的识别方式（@提及、@昵称、QQ号）
- QQ号必须是纯数字
- 昵称/群名片需要在聊天记录中存在

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目采用 GPL-3.0-or-later 许可证。详见 LICENSE 文件。
