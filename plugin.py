"""
聊天记录总结插件

功能:
- 生成群聊整体的聊天记录总结
- 生成单个群员的聊天记录总结
- 支持选择日期范围
- 支持每日定时自动生成总结

命令格式:
- /summary - 生成今天整个群聊的总结
- /summary 今天 - 生成今天整个群聊的总结
- /summary 昨天 - 生成昨天整个群聊的总结
- /summary @用户名 - 生成某个用户今天的聊天总结
- /summary @用户名 昨天 - 生成某个用户昨天的聊天总结
- /summary QQ号 - 生成某个QQ用户今天的聊天总结
- /summary QQ号 昨天 - 生成某个QQ用户昨天的聊天总结
"""

import re
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from collections import Counter
from PIL import Image

from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseCommand,
    BaseEventHandler,
    EventType,
    MaiMessages,
    ConfigField,
    database_api,
    llm_api,
    send_api,
    get_logger,
)
from src.common.database.database_model import Messages
from src.config.config import model_config
from .core import SummaryImageGenerator, ChatAnalysisUtils

logger = get_logger("chat_summary_plugin")


class ChatSummaryCommand(BaseCommand):
    """聊天记录总结命令"""

    command_name = "chat_summary"
    command_description = "生成聊天记录总结"
    command_pattern = r"^/summary\s*(.*)$"

    async def execute(self) -> Tuple[bool, str, bool]:
        """执行聊天记录总结"""
        try:
            # 获取命令参数
            match = re.match(self.command_pattern, self.message.raw_message)
            if not match:
                await self.send_text("用法: /summary [今天|昨天] 或 /summary @用户名/QQ号 [今天|昨天]")
                return True, "已发送使用说明", True

            args = match.group(1).strip()

            # 解析参数
            target_user = None
            time_range = "今天"

            # 检查是否指定了用户
            # 处理 CQ 码格式的 at，例如: [CQ:at,qq=123456]
            at_match = re.search(r'\[CQ:at,qq=(\d+)\]', args)
            if at_match:
                # 从消息中提取被at的用户QQ号，然后从消息历史中查找对应的昵称
                # 这里先移除CQ码，保留剩余的时间参数
                args_without_at = re.sub(r'\[CQ:at,qq=\d+\]\s*', '', args).strip()
                # 暂时使用QQ号作为target_user，后续在查询时会匹配user_id
                target_user = at_match.group(1)
                time_range = args_without_at if args_without_at else "今天"
            elif args.startswith("@"):
                parts = args.split(maxsplit=1)
                target_user = parts[0][1:]  # 去掉@符号
                time_range = parts[1] if len(parts) > 1 else "今天"
            else:
                # 检查是否为纯数字（QQ号）
                parts = args.split(maxsplit=1)
                if parts and parts[0].isdigit():
                    target_user = parts[0]
                    time_range = parts[1] if len(parts) > 1 else "今天"
                elif args:
                    time_range = args

            # 获取时间范围
            start_time, end_time = self._parse_time_range(time_range)
            if start_time is None or end_time is None:
                await self.send_text(f"只支持查询今天或昨天的记录哦")
                return False, f"不支持的时间范围: {time_range}", False

            # 获取聊天记录
            messages = await self._get_messages(start_time, end_time, target_user)

            if not messages:
                user_info = f"@{target_user} " if target_user else ""
                await self.send_text(f"{user_info}{time_range}没有聊天记录呢")
                return True, "没有聊天记录", True

            # 发送等候提示
            user_info = f"@{target_user} " if target_user else ""
            await self.send_text(f"⏳ 正在分析{user_info}{time_range}的聊天记录，请稍候...")

            # 生成总结
            summary = await self._generate_summary(messages, target_user, time_range)

            if summary:
                # 生成并发送图片
                try:
                    # 准备图片信息
                    if target_user:
                        # 从消息记录中获取用户的实际昵称或群名片
                        user_display_name = target_user  # 默认使用传入的值
                        if messages:
                            # 优先使用群名片，其次使用昵称
                            first_msg = messages[0]
                            user_display_name = (
                                first_msg.get("user_cardname") or
                                first_msg.get("user_nickname") or
                                target_user
                            )
                        title = f"{user_display_name} {time_range}的聊天总结"
                    else:
                        title = f"{time_range}的群聊总结"

                    # 统计信息
                    participant_count = 0
                    user_titles = []
                    golden_quotes = []
                    depression_index = []
                    hourly_distribution = {}
                    user_profile = None

                    if not target_user:
                        participants = set()
                        for msg in messages:
                            nickname = msg.get("user_nickname", "")
                            if nickname:
                                participants.add(nickname)
                        participant_count = len(participants)

                        # 分析用户统计（仅群聊总结时）
                        user_stats = ChatAnalysisUtils.analyze_user_stats(messages)

                        # 计算24小时发言分布
                        from collections import Counter
                        hourly_distribution = Counter()
                        for msg in messages:
                            timestamp = msg.get("time", 0)
                            hour = datetime.fromtimestamp(timestamp).hour
                            hourly_distribution[hour] += 1
                        # 转换为普通字典
                        hourly_distribution = dict(hourly_distribution)

                        # 分析群友称号（如果启用）
                        if self.get_config("summary.enable_user_titles", True):
                            user_titles = await ChatAnalysisUtils.analyze_user_titles(messages, user_stats) or []

                        # 分析金句（如果启用）
                        if self.get_config("summary.enable_golden_quotes", True):
                            golden_quotes = await ChatAnalysisUtils.analyze_golden_quotes(messages) or []

                        # 分析炫压抑指数（如果启用）
                        depression_index = []
                        if self.get_config("summary.enable_depression_index", True):
                            depression_index = await ChatAnalysisUtils.analyze_depression_index(messages, user_stats) or []
                    else:
                        # 单个用户模式：分析用户画像
                        if self.get_config("summary.enable_user_summary", True):
                            user_profile = await ChatAnalysisUtils.analyze_user_profile(messages, user_display_name) or None

                    # 生成图片并获取临时文件路径
                    img_path = await SummaryImageGenerator.generate_summary_image(
                        title=title,
                        summary_text=summary,
                        time_info=datetime.now().strftime("%Y-%m-%d"),
                        message_count=len(messages),
                        participant_count=participant_count,
                        user_titles=user_titles,
                        golden_quotes=golden_quotes,
                        depression_index=depression_index,
                        hourly_distribution=hourly_distribution,
                        user_profile=user_profile
                    )

                    # 发送图片
                    try:
                        if not os.path.exists(img_path):
                            raise FileNotFoundError(f"图片文件不存在: {img_path}")

                        with open(img_path, 'rb') as f:
                            img_data = f.read()

                        import base64
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        await self.send_custom("image", img_base64)
                        await asyncio.sleep(2)
                    finally:
                        try:
                            if os.path.exists(img_path):
                                os.remove(img_path)
                        except Exception as e:
                            logger.warning(f"清理临时图片失败: {e}")

                except Exception as e:
                    logger.error(f"生成图片失败，使用文本输出: {e}", exc_info=True)
                    # 降级到文本输出
                    await self.send_text(summary)

                return True, "已生成聊天记录总结", True
            else:
                await self.send_text("生成总结失败了，等会再试试吧")
                return False, "生成总结失败", False

        except Exception as e:
            logger.error(f"执行聊天记录总结命令时出错: {e}", exc_info=True)
            await self.send_text(f"出错了: {str(e)}")
            return False, f"执行命令时出错: {str(e)}", False

    def _parse_time_range(self, time_range: str) -> Tuple[Optional[float], Optional[float]]:
        """解析时间范围

        Args:
            time_range: 时间范围字符串

        Returns:
            (start_time, end_time) 时间戳元组，失败返回 (None, None)
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)

        try:
            if time_range == "今天" or time_range == "":
                start_time = today_start
                end_time = now
            elif time_range == "昨天":
                start_time = today_start - timedelta(days=1)
                end_time = today_start
            else:
                # 不支持的时间范围
                return None, None

            return start_time.timestamp(), end_time.timestamp()

        except Exception as e:
            logger.error(f"解析时间范围出错: {e}")
            return None, None

    async def _get_messages(
        self, start_time: float, end_time: float, target_user: Optional[str] = None
    ) -> List[dict]:
        """获取聊天记录

        Args:
            start_time: 起始时间戳
            end_time: 结束时间戳
            target_user: 目标用户昵称（可选）

        Returns:
            聊天记录列表
        """
        try:
            # 获取当前聊天ID
            if not self.message.chat_stream:
                logger.error("chat_stream 为空")
                return []

            chat_id = self.message.chat_stream.stream_id

            # 查询消息
            # 注意：由于peewee的限制，我们需要分两步查询
            # 1. 先查询所有符合chat_id和时间范围的消息
            all_messages = await database_api.db_query(
                Messages,
                query_type="get",
                filters={"chat_id": chat_id},
                order_by=["-time"],
            )

            # 检查查询结果 - db_query 可能返回 None 或空列表
            if not all_messages or all_messages is None:
                return []

            # 2. 在内存中过滤时间范围和用户
            filtered_messages = []

            for msg in all_messages:
                # 检查时间范围
                msg_time = msg.get("time", 0)
                if not (start_time <= msg_time < end_time):
                    continue

                # 检查是否为命令或通知（排除这些消息）
                if msg.get("is_command") or msg.get("is_notify"):
                    continue

                # 如果指定了目标用户，则过滤
                if target_user:
                    user_nickname = msg.get("user_nickname") or ""
                    user_cardname = msg.get("user_cardname") or ""
                    user_id = str(msg.get("user_id") or "")

                    # 匹配昵称、群名片或用户ID（用于CQ码at）
                    if (target_user not in user_nickname and
                        target_user not in user_cardname and
                        target_user != user_id):
                        continue

                filtered_messages.append(msg)

            # 按时间正序排序（旧到新）
            filtered_messages.sort(key=lambda x: x.get("time", 0))

            return filtered_messages

        except Exception as e:
            logger.error(f"获取聊天记录出错: {e}", exc_info=True)
            return []

    async def _generate_summary(
        self, messages: List[dict], target_user: Optional[str], time_range: str
    ) -> Optional[str]:
        """生成聊天记录总结

        Args:
            messages: 聊天记录列表
            target_user: 目标用户昵称（可选）
            time_range: 时间范围描述

        Returns:
            总结文本，失败返回None
        """
        try:
            # 构建聊天记录文本
            chat_text = ChatAnalysisUtils.format_messages(messages)

            # 获取人设和回复风格
            from src.config.config import global_config

            bot_name = global_config.bot.nickname
            personality = global_config.personality.personality
            reply_style = global_config.personality.reply_style

            # 构建提示词
            if target_user:
                # 获取单个用户总结的字数限制
                max_words = self.get_config("summary.user_summary_max_words", 300)

                prompt = f"""你是{bot_name}。{personality}
{reply_style}

以下是这个用户的聊天记录（{len(messages)}条消息）：
{chat_text}

请用你自己的说话方式，自然地讲讲这个人今天都在群里说了什么，聊了哪些事。不要列点，不要分段标题，就像你在给朋友复述一样。

【重要约束】字数必须严格控制在{max_words}字以内！这是硬性要求！

要求：
- 用口语化、轻松的语气
- 把有意思的话题和细节自然地穿插进去
- 可以适当加点你自己的评论或感受
- 不要用"首先""其次""总之"这种生硬的词
- 总字数不得超过{max_words}字

直接开始讲，想怎么说就怎么说。记住：必须在{max_words}字以内完成！"""
            else:
                # 获取群聊总结的字数限制
                max_words = self.get_config("summary.group_summary_max_words", 400)

                # 统计参与用户
                participants = set()
                for msg in messages:
                    nickname = msg.get("user_nickname", "")
                    if nickname:
                        participants.add(nickname)

                prompt = f"""你是{bot_name}。{personality}
{reply_style}

以下是群聊记录（{len(messages)}条消息，{len(participants)}人参与）：
{chat_text}

请像给朋友讲故事一样复述群里发生了什么。

【重要约束】字数必须严格控制在{max_words}字以内！这是硬性要求！

要求：
1. 按时间顺序讲，保持连贯性
2. 精彩内容详细说，平淡内容略过
3. 对话要说清谁说了什么、谁怎么回的
4. 必须有具体人名和具体内容，不要抽象描述
5. 口语化，不要用"首先""其次""然后""总之"这类词
6. 总字数不得超过{max_words}字

直接开始，不要标题。记住：必须在{max_words}字以内完成！"""

            # 使用LLM生成总结
            # 使用主回复模型 (replyer)
            model_task_config = model_config.model_task_config.replyer

            success, summary, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_task_config,
                request_type="plugin.chat_summary",
            )

            if not success:
                logger.error(f"LLM生成总结失败: {summary}")
                return None

            # 返回总结内容
            return summary.strip()

        except Exception as e:
            logger.error(f"生成聊天记录总结出错: {e}", exc_info=True)
            return None


class SummaryScheduler:
    """聊天总结定时任务调度器

    负责管理每日自动总结的定时任务，采用精确计算等待时间的方式，
    避免轮询检查，提高效率并减少资源消耗。
    """

    def __init__(self, config_getter):
        """初始化调度器

        Args:
            config_getter: 配置获取函数
        """
        self.get_config = config_getter
        self.is_running = False
        self.task = None
        self.last_execution_date = None

    def _get_timezone_now(self):
        """获取配置时区的当前时间"""
        timezone_str = self.get_config("auto_summary.timezone", "Asia/Shanghai")
        try:
            import pytz
            tz = pytz.timezone(timezone_str)
            return datetime.now(tz)
        except ImportError:
            logger.warning("pytz模块未安装，使用系统时间")
            return datetime.now()
        except Exception as e:
            logger.warning(f"时区处理出错: {e}，使用系统时间")
            return datetime.now()

    async def start(self, summary_generator):
        """启动定时任务

        Args:
            summary_generator: 总结生成协程函数
        """
        if self.is_running:
            return

        enabled = self.get_config("plugin.enabled", True)
        auto_summary_enabled = self.get_config("auto_summary.enabled", False)

        if not enabled or not auto_summary_enabled:
            return

        self.is_running = True
        self.task = asyncio.create_task(self._schedule_loop(summary_generator))

        summary_time = self.get_config("auto_summary.time", "23:00")
        target_chats = self.get_config("auto_summary.target_chats", [])

        if target_chats:
            logger.info(f"✅ 定时任务已启动 - 执行时间: {summary_time}, 目标群聊: {len(target_chats)}个")
        else:
            logger.info(f"✅ 定时任务已启动 - 执行时间: {summary_time}, 目标: 所有群聊")

    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("定时任务已停止")

    async def _schedule_loop(self, summary_generator):
        """定时任务循环

        Args:
            summary_generator: 总结生成协程函数
        """
        while self.is_running:
            try:
                now = self._get_timezone_now()
                summary_time_str = self.get_config("auto_summary.time", "23:00")

                # 解析执行时间
                try:
                    hour, minute = map(int, summary_time_str.split(":"))
                except ValueError:
                    logger.error(f"无效的时间格式: {summary_time_str}，使用默认值 23:00")
                    hour, minute = 23, 0

                # 计算今天的执行时间点
                today_schedule = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # 如果今天的时间点已过，则计算明天的时间点
                if now >= today_schedule:
                    today_schedule += timedelta(days=1)

                # 计算等待秒数
                wait_seconds = (today_schedule - now).total_seconds()
                logger.info(f"⏰ 下次总结生成时间: {today_schedule.strftime('%Y-%m-%d %H:%M:%S')} (等待 {int(wait_seconds/3600)}小时{int((wait_seconds%3600)/60)}分钟)")

                # 等待到执行时间
                await asyncio.sleep(wait_seconds)

                # 检查是否还在运行
                if not self.is_running:
                    break

                # 检查今天是否已执行（避免重复）
                current_date = self._get_timezone_now().date()
                if self.last_execution_date == current_date:
                    continue

                # 执行总结生成
                logger.info(f"⏰ 开始执行每日自动总结 - {current_date}")
                await summary_generator()
                self.last_execution_date = current_date
                logger.info("✅ 每日自动总结执行完成")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 定时任务执行出错: {e}", exc_info=True)
                # 出错后等待1分钟再重试
                await asyncio.sleep(60)


class DailySummaryEventHandler(BaseEventHandler):
    """每日自动总结事件处理器"""

    event_type = EventType.ON_START
    handler_name = "daily_summary_handler"
    handler_description = "每日定时自动生成群聊总结"
    weight = 10
    intercept_message = False

    # 类变量：确保只启动一个调度器
    _scheduler = None
    _scheduler_started = False

    def __init__(self):
        super().__init__()

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[any], Optional[MaiMessages]]:
        """执行事件处理"""
        # 确保只启动一个调度器实例
        if not DailySummaryEventHandler._scheduler_started:
            DailySummaryEventHandler._scheduler_started = True
            DailySummaryEventHandler._scheduler = SummaryScheduler(self.get_config)
            await DailySummaryEventHandler._scheduler.start(self._generate_daily_summaries)

        return True, True, None, None, None

    async def _generate_daily_summaries(self):
        """为所有群聊生成今日总结"""
        try:
            # 计算今天的时间范围
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day)
            start_time = today_start.timestamp()
            end_time = now.timestamp()

            # 获取今天有消息的所有群聊ID
            all_messages = await database_api.db_query(
                Messages,
                query_type="get",
                filters={},
                order_by=["-time"],
            )

            if not all_messages:
                return

            # 提取唯一的 chat_id 并建立 chat_id -> group_id 的映射
            chat_id_to_group_id = {}
            today_message_count = 0

            for msg in all_messages:
                msg_time = msg.get("time", 0)
                if start_time <= msg_time < end_time:
                    today_message_count += 1
                    chat_id = msg.get("chat_id")
                    group_id = msg.get("chat_info_group_id")

                    if chat_id and chat_id not in chat_id_to_group_id:
                        chat_id_to_group_id[chat_id] = group_id

            if not chat_id_to_group_id:
                return

            # 获取配置
            target_chats = self.get_config("auto_summary.target_chats", [])
            min_messages = self.get_config("auto_summary.min_messages", 10)

            # 过滤目标群聊（使用实际的 group_id 进行匹配）
            if target_chats:
                target_group_ids = set(str(gid) for gid in target_chats)
                filtered_chat_ids = {}

                for chat_id, group_id in chat_id_to_group_id.items():
                    if str(group_id) in target_group_ids:
                        filtered_chat_ids[chat_id] = group_id

                chat_id_to_group_id = filtered_chat_ids

            # 为每个群聊生成总结
            for chat_id, group_id in chat_id_to_group_id.items():
                try:
                    # 获取今天的聊天记录
                    messages = await self._get_messages_for_chat(
                        chat_id, start_time, end_time
                    )

                    # 检查消息数量是否达到最小要求
                    if len(messages) < min_messages:
                        continue

                    # 生成总结
                    summary = await self._generate_summary_for_chat(messages)

                    if summary:
                        # 生成并发送图片
                        try:
                            # 统计参与用户
                            participants = set()
                            for msg in messages:
                                nickname = msg.get("user_nickname", "")
                                if nickname:
                                    participants.add(nickname)

                            # 分析用户统计
                            user_stats = ChatAnalysisUtils.analyze_user_stats(messages)
                            user_titles = []
                            golden_quotes = []

                            # 计算24小时发言分布
                            from collections import Counter
                            hourly_distribution = Counter()
                            for msg in messages:
                                timestamp = msg.get("time", 0)
                                hour = datetime.fromtimestamp(timestamp).hour
                                hourly_distribution[hour] += 1
                            # 转换为普通字典
                            hourly_distribution = dict(hourly_distribution)

                            # 分析群友称号（如果启用）
                            if self.get_config("summary.enable_user_titles", True):
                                user_titles = await ChatAnalysisUtils.analyze_user_titles(messages, user_stats) or []

                            # 分析金句（如果启用）
                            if self.get_config("summary.enable_golden_quotes", True):
                                golden_quotes = await ChatAnalysisUtils.analyze_golden_quotes(messages) or []

                            # 分析炫压抑指数（如果启用）
                            depression_index = []
                            if self.get_config("summary.enable_depression_index", True):
                                depression_index = await ChatAnalysisUtils.analyze_depression_index(messages, user_stats) or []

                            # 生成图片并获取临时文件路径
                            img_path = await SummaryImageGenerator.generate_summary_image(
                                title="📊 今日群聊总结",
                                summary_text=summary,
                                time_info=datetime.now().strftime("%Y-%m-%d"),
                                message_count=len(messages),
                                participant_count=len(participants),
                                user_titles=user_titles,
                                golden_quotes=golden_quotes,
                                depression_index=depression_index,
                                hourly_distribution=hourly_distribution
                            )

                            # 发送图片
                            try:
                                if not os.path.exists(img_path):
                                    raise FileNotFoundError(f"图片文件不存在: {img_path}")

                                with open(img_path, 'rb') as f:
                                    img_data = f.read()

                                import base64
                                img_base64 = base64.b64encode(img_data).decode('utf-8')
                                await send_api.image_to_stream(img_base64, chat_id, storage_message=False)
                                await asyncio.sleep(2)
                            finally:
                                try:
                                    if os.path.exists(img_path):
                                        os.remove(img_path)
                                except Exception as e:
                                    logger.warning(f"清理临时图片失败: {e}")

                        except Exception as e:
                            logger.error(f"生成图片失败，使用文本输出: {e}", exc_info=True)
                            # 降级到文本输出
                            prefix = "📊 今日群聊总结\n\n"
                            await send_api.text_to_stream(prefix + summary, chat_id, storage_message=False)
                    else:
                        logger.warning(f"群聊 {group_id} 总结生成失败")

                except Exception as e:
                    logger.error(f"为群聊 {group_id} 生成总结失败: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"生成每日总结失败: {e}", exc_info=True)

    async def _get_messages_for_chat(
        self, chat_id: str, start_time: float, end_time: float
    ) -> List[dict]:
        """获取指定群聊的聊天记录"""
        try:
            # 查询消息
            all_messages = await database_api.db_query(
                Messages,
                query_type="get",
                filters={"chat_id": chat_id},
                order_by=["-time"],
            )

            if not all_messages:
                return []

            # 过滤时间范围和消息类型
            filtered_messages = []
            for msg in all_messages:
                msg_time = msg.get("time", 0)
                if not (start_time <= msg_time < end_time):
                    continue

                # 排除命令和通知
                if msg.get("is_command") or msg.get("is_notify"):
                    continue

                filtered_messages.append(msg)

            # 按时间正序排序
            filtered_messages.sort(key=lambda x: x.get("time", 0))
            return filtered_messages

        except Exception as e:
            logger.error(f"获取群聊 {chat_id} 的聊天记录出错: {e}", exc_info=True)
            return []

    async def _generate_summary_for_chat(self, messages: List[dict]) -> Optional[str]:
        """为指定聊天记录生成总结"""
        try:
            # 构建聊天记录文本
            chat_text = ChatAnalysisUtils.format_messages(messages)

            # 获取人设和回复风格
            from src.config.config import global_config
            bot_name = global_config.bot.nickname
            personality = global_config.personality.personality
            reply_style = global_config.personality.reply_style

            # 获取字数限制
            max_words = self.get_config("summary.group_summary_max_words", 400)

            # 统计参与用户
            participants = set()
            for msg in messages:
                nickname = msg.get("user_nickname", "")
                if nickname:
                    participants.add(nickname)

            # 构建提示词
            prompt = f"""你是{bot_name}。{personality}
{reply_style}

以下是群聊记录（{len(messages)}条消息，{len(participants)}人参与）：
{chat_text}

请像给朋友讲故事一样复述群里发生了什么。

【重要约束】字数必须严格控制在{max_words}字以内！这是硬性要求！

要求：
1. 按时间顺序讲，保持连贯性
2. 精彩内容详细说，平淡内容略过
3. 对话要说清谁说了什么、谁怎么回的
4. 必须有具体人名和具体内容，不要抽象描述
5. 口语化，不要用"首先""其次""然后""总之"这类词
6. 总字数不得超过{max_words}字

直接开始，不要标题。记住：必须在{max_words}字以内完成！"""

            # 使用LLM生成总结
            model_task_config = model_config.model_task_config.replyer

            success, summary, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_task_config,
                request_type="plugin.chat_summary.auto",
            )

            if not success:
                logger.error(f"LLM生成自动总结失败: {summary}")
                return None

            return summary.strip()

        except Exception as e:
            logger.error(f"生成聊天总结出错: {e}", exc_info=True)
            return None


@register_plugin
class ChatSummaryPlugin(BasePlugin):
    """聊天记录总结插件"""

    plugin_name: str = "chat_summary_plugin"
    enable_plugin: bool = False
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本信息",
        "summary": "总结功能配置",
        "auto_summary": "自动总结配置",
    }

    # 配置Schema定义
    config_schema: dict = {
        "plugin": {
            "config_version": ConfigField(type=str, default="1.0.0", description="配置文件版本"),
            "enabled": ConfigField(type=bool, default=False, description="是否启用插件"),
        },
        "summary": {
            "group_summary_max_words": ConfigField(
                type=int, default=400, description="群聊总结的字数限制"
            ),
            "user_summary_max_words": ConfigField(
                type=int, default=300, description="单个用户总结的字数限制"
            ),
            "enable_user_summary": ConfigField(type=bool, default=True, description="是否启用单个用户的聊天总结"),
            "enable_user_titles": ConfigField(type=bool, default=True, description="是否启用群友称号分析"),
            "enable_golden_quotes": ConfigField(type=bool, default=True, description="是否启用金句提取"),
            "enable_depression_index": ConfigField(type=bool, default=True, description="是否启用炫压抑指数分析"),
        },
        "auto_summary": {
            "enabled": ConfigField(type=bool, default=False, description="是否启用每日自动总结"),
            "time": ConfigField(type=str, default="23:00", description="每日自动总结的时间（HH:MM格式）"),
            "timezone": ConfigField(type=str, default="Asia/Shanghai", description="时区设置（需安装pytz模块）"),
            "min_messages": ConfigField(type=int, default=10, description="生成总结所需的最少消息数量"),
            "target_chats": ConfigField(type=list, default=[], description="目标群聊QQ号列表（为空则对所有群聊生效）"),
        },
    }

    def get_plugin_components(self) -> List[Tuple]:
        return [
            (ChatSummaryCommand.get_command_info(), ChatSummaryCommand),
            (DailySummaryEventHandler.get_handler_info(), DailySummaryEventHandler),
        ]
