# 聊天记录总结插件

## 功能介绍

智能分析QQ群聊天记录并生成总结，支持精美图片输出。

功能特性：
- 生成群聊整体总结
- 生成单个用户聊天总结
- 支持今天/昨天时间范围
- 智能群友称号分析
- 群聊金句提取
- 每日定时自动总结
- 精美图片输出（失败时自动降级为文本）

## 依赖要求

### Python 依赖

- **Pillow** (必需) - 用于生成图片
- **pytz** (可选) - 用于时区支持

### 安装依赖

```bash
# 安装必需依赖
pip install Pillow

# 安装可选依赖（如需时区支持）
pip install pytz
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

## 安装和配置

1. 将插件放置到 `plugins/chat_summary_plugin/` 目录
2. 安装必需依赖（见上方）
3. 编辑 `config.toml` 文件，将 `enabled` 设置为 `true`
4. 重启 MaiBot

## 使用方法

### 基本命令

```
/summary              # 今天的群聊总结
/summary 昨天         # 昨天的群聊总结
/summary @用户名       # 某用户今天的总结
/summary @用户名 昨天   # 某用户昨天的总结
/summary QQ号         # 通过QQ号查询
```

支持的用户识别方式：
- QQ @提及（CQ码）
- 文本 @昵称
- 直接输入QQ号

## 配置选项

编辑 `config.toml`：

```toml
[plugin]
enabled = true                    # 是否启用插件

[summary]
group_summary_max_words = 400     # 群聊总结字数限制
user_summary_max_words = 300      # 用户总结字数限制
enable_user_summary = true        # 是否启用用户总结
enable_user_titles = true         # 是否启用群友称号
enable_golden_quotes = true       # 是否启用金句提取

[auto_summary]
enabled = false                   # 是否启用每日自动总结
time = "23:00"                    # 自动总结时间（24小时制）
timezone = "Asia/Shanghai"        # 时区（需安装 pytz）
min_messages = 10                 # 最少消息数量要求
target_chats = []                 # 目标群聊QQ号列表（为空则全部群聊）
```

### 自动总结说明

启用 `auto_summary.enabled = true` 后：
- 每天指定时间自动生成总结
- 采用精确计算等待时间，不轮询
- 支持时区配置（需 `pip install pytz`）
- 只为达到最小消息数的群聊生成
- 可通过 `target_chats` 指定特定群聊

配置示例：
```toml
[auto_summary]
enabled = true
time = "23:00"
timezone = "Asia/Shanghai"
min_messages = 10
target_chats = [123456789, 987654321]  # 只为这些群生成，留空=全部
```

## 注意事项

1. 总结生成需要几秒钟时间，请耐心等待
2. 仅统计普通聊天消息，不包括命令和系统通知
3. 目前仅支持查询今天和昨天的记录
4. 自动总结功能每天只执行一次
5. 图片生成失败会自动降级为文本输出
6. 系统需要中文字体支持（通常 Linux/Windows 已自带）

## 技术实现

- 使用 `BaseCommand` 处理命令
- 使用 `BaseEventHandler` 实现定时任务
- 采用精确计算等待时间的调度方式，避免轮询
- 通过 `database_api` 查询聊天记录
- 使用 `llm_api` 生成智能总结
- 注入机器人人设，确保总结符合角色特点

## 开发信息

- 版本: 1.0.0
- 作者: MaiBot Team
