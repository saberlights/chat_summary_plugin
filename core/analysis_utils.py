"""
聊天分析工具类

提取公共的聊天记录分析方法，避免代码重复
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any
from collections import Counter

from src.config.config import model_config
from src.plugin_system import llm_api, get_logger
from .constants import AnalysisConfig

logger = get_logger("chat_analysis_utils")


class ChatAnalysisUtils:
    """聊天记录分析工具类"""

    # Emoji 正则表达式（完整Unicode范围）
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "]+",
        flags=re.UNICODE
    )

    @staticmethod
    def format_messages(messages: List[dict]) -> str:
        """格式化聊天记录为文本

        Args:
            messages: 聊天记录列表

        Returns:
            格式化的聊天记录文本
        """
        formatted = []
        for msg in messages:
            timestamp = msg.get("time", 0)
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            nickname = msg.get("user_nickname", "未知用户")
            cardname = msg.get("user_cardname", "")
            display_name = cardname if cardname else nickname
            text = msg.get("processed_plain_text", "")

            if text:
                formatted.append(f"[{time_str}] {display_name}: {text}")

        return "\n".join(formatted)

    @staticmethod
    def count_emojis(text: str) -> int:
        """统计文本中的 emoji 数量（使用正则表达式）

        Args:
            text: 待统计的文本

        Returns:
            emoji 数量
        """
        matches = ChatAnalysisUtils.EMOJI_PATTERN.findall(text)
        return len(matches)

    @staticmethod
    def analyze_user_stats(messages: List[dict]) -> Dict[str, Dict]:
        """分析用户统计数据

        Args:
            messages: 聊天记录列表

        Returns:
            用户统计字典，格式: {user_id: {nickname, message_count, char_count, emoji_count, hours}}
        """
        user_stats = {}

        for msg in messages:
            user_id = str(msg.get("user_id", ""))
            if not user_id:
                continue

            nickname = msg.get("user_nickname", "未知用户")
            text = msg.get("processed_plain_text", "")

            if user_id not in user_stats:
                user_stats[user_id] = {
                    "nickname": nickname,
                    "message_count": 0,
                    "char_count": 0,
                    "emoji_count": 0,
                    "hours": Counter(),  # 各小时发言次数
                }

            stats = user_stats[user_id]
            stats["message_count"] += 1
            stats["char_count"] += len(text)

            # 使用改进的 emoji 统计
            stats["emoji_count"] += ChatAnalysisUtils.count_emojis(text)

            # 统计发言时间
            timestamp = msg.get("time", 0)
            hour = datetime.fromtimestamp(timestamp).hour
            stats["hours"][hour] += 1

        return user_stats

    @staticmethod
    async def analyze_user_titles(
        messages: List[dict],
        user_stats: Dict,
        get_config: Callable = None
    ) -> Optional[List[Dict]]:
        """使用 LLM 分析群友称号

        Args:
            messages: 聊天记录列表（用于上下文）
            user_stats: 用户统计数据
            get_config: 配置获取函数（可选）

        Returns:
            称号列表，格式: [{name, title, reason}, ...]
        """
        try:
            # 只分析发言 >= 配置的最小发言数的用户
            active_users = {
                uid: stats for uid, stats in user_stats.items()
                if stats["message_count"] >= AnalysisConfig.MIN_MESSAGES_FOR_TITLE
            }

            if not active_users:
                return []

            # 构建用户数据文本
            users_text = []
            for user_id, stats in sorted(
                active_users.items(),
                key=lambda x: x[1]["message_count"],
                reverse=True
            )[:AnalysisConfig.MAX_USERS_FOR_TITLE]:  # 使用配置的最大用户数
                night_messages = sum(stats["hours"][h] for h in range(0, 6))
                avg_chars = stats["char_count"] / stats["message_count"] if stats["message_count"] > 0 else 0
                emoji_ratio = stats["emoji_count"] / stats["message_count"] if stats["message_count"] > 0 else 0
                night_ratio = night_messages / stats["message_count"] if stats["message_count"] > 0 else 0

                users_text.append(
                    f"- {stats['nickname']}: "
                    f"发言{stats['message_count']}条, 平均{avg_chars:.1f}字, "
                    f"表情比例{emoji_ratio:.2f}, 夜间发言比例{night_ratio:.2f}"
                )

            users_info = "\n".join(users_text)

            # 构建 prompt
            prompt = f"""根据群友数据创造有趣的称号。

用户数据：
{users_info}

要求：
1. 称号2-4个汉字
2. 基于真实数据，不要编造
3. 避免重复类型（不要多个"龙王""话痨"）
4. 有创意，避免陈词滥调
5. 理由60-80字，引用数据说明为什么

参考分类：活跃度（龙王、潜水员）、时间特征（夜猫子）、内容风格（段子手）、表情/情绪（表情帝）、互动特征（接梗高手）

返回JSON（不要markdown代码块，不要emoji）：
[
  {{
    "name": "用户名",
    "title": "称号（2-4字）",
    "reason": "获得理由，引用数据（60-80字）"
  }}
]"""

            # 使用 LLM 生成
            model_task_config = model_config.model_task_config.replyer
            success, result, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_task_config,
                request_type="plugin.chat_summary.titles",
            )

            if not success:
                logger.error(f"LLM生成称号失败: {result}")
                return []

            # 解析并验证 JSON
            data = ChatAnalysisUtils._parse_llm_json(result)
            return ChatAnalysisUtils._validate_titles(data)

        except Exception as e:
            logger.error(f"分析群友称号失败: {e}", exc_info=True)
            return []

    @staticmethod
    async def analyze_golden_quotes(
        messages: List[dict],
        get_config: Callable = None
    ) -> Optional[List[Dict]]:
        """使用 LLM 提取群聊金句（群圣经）

        Args:
            messages: 聊天记录列表
            get_config: 配置获取函数（可选）

        Returns:
            金句列表，格式: [{content, sender, reason}, ...]
        """
        try:
            # 提取适合的消息（使用配置的长度范围）
            interesting_messages = []
            for msg in messages:
                nickname = msg.get("user_nickname", "未知用户")
                cardname = msg.get("user_cardname", "")
                display_name = cardname if cardname else nickname
                text = msg.get("processed_plain_text", "")
                timestamp = msg.get("time", 0)
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M")

                # 清理 @ 提及格式（如 @理理<123456> → 去掉整个提及部分）
                # 使用正则移除 @用户名<数字> 格式
                text = re.sub(r'@[^<\s]+<\d+>\s*', '', text)
                text = text.strip()

                if (AnalysisConfig.MIN_QUOTE_LENGTH <= len(text) <= AnalysisConfig.MAX_QUOTE_LENGTH
                    and not text.startswith(("http", "www", "/"))):
                    interesting_messages.append({
                        "sender": display_name,
                        "time": time_str,
                        "content": text
                    })

            if not interesting_messages:
                return []

            # 构建消息文本
            messages_text = "\n".join([
                f"[{msg['time']}] {msg['sender']}: {msg['content']}"
                for msg in interesting_messages
            ])

            # 构建 prompt
            prompt = f"""从群聊记录中挑选3-5句最有趣的金句。

优先级（从高到低）：
1. 神回复、接梗高手（优先选择回复的那句，不是发起的）
2. 有上下文才有笑点的梗
3. 精彩吐槽或离谱观点
4. 高/低情商发言

要求：
- 每个金句来自不同发言人
- 避免平淡陈述句、问候语
- 内容水可以只返回2-3个
- 理由60-80字，说明为什么有趣、回应了什么

群聊记录：
{messages_text}

返回JSON（不要markdown代码块，不要emoji）：
[
  {{
    "content": "金句原文",
    "sender": "发言人",
    "reason": "选择理由（60-80字）"
  }}
]"""

            # 使用 LLM 生成
            model_task_config = model_config.model_task_config.replyer
            success, result, reasoning, model_name = await llm_api.generate_with_model(
                prompt=prompt,
                model_config=model_task_config,
                request_type="plugin.chat_summary.quotes",
            )

            if not success:
                logger.error(f"LLM生成金句失败: {result}")
                return []

            # 解析并验证 JSON
            data = ChatAnalysisUtils._parse_llm_json(result)
            return ChatAnalysisUtils._validate_quotes(data)

        except Exception as e:
            logger.error(f"分析金句失败: {e}", exc_info=True)
            return []

    @staticmethod
    def _validate_titles(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证并清理群友称号数据

        Args:
            data: 原始数据列表

        Returns:
            验证后的数据列表
        """
        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue

            # 必需字段
            if not all(key in item for key in ["name", "title", "reason"]):
                logger.warning(f"群友称号数据缺少必需字段: {item}")
                continue

            # 验证数据类型和长度
            name = str(item["name"])[:50]  # 限制长度
            title = str(item["title"])[:AnalysisConfig.MAX_TITLE_LENGTH]
            reason = str(item["reason"])[:AnalysisConfig.MAX_REASON_LENGTH]

            if not name or not title or not reason:
                continue

            validated.append({
                "name": name,
                "title": title,
                "reason": reason
            })

        return validated

    @staticmethod
    def _validate_quotes(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证并清理金句数据

        Args:
            data: 原始数据列表

        Returns:
            验证后的数据列表
        """
        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue

            # 必需字段
            if not all(key in item for key in ["content", "sender", "reason"]):
                logger.warning(f"金句数据缺少必需字段: {item}")
                continue

            # 验证数据类型和长度
            content = str(item["content"])[:200]  # 限制长度
            sender = str(item["sender"])[:50]
            reason = str(item["reason"])[:AnalysisConfig.MAX_REASON_LENGTH]

            if not content or not sender or not reason:
                continue

            validated.append({
                "content": content,
                "sender": sender,
                "reason": reason
            })

        return validated

    @staticmethod
    def _parse_llm_json(result: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的 JSON（带 emoji 清理 fallback）

        Args:
            result: LLM 返回的原始结果

        Returns:
            解析后的列表，失败返回空列表
        """
        try:
            # 去除可能的 markdown 代码块标记
            result = result.strip()
            if result.startswith("```"):
                parts = result.split("```")
                if len(parts) >= 2:
                    result = parts[1]
                    if result.startswith("json"):
                        result = result[4:]
            result = result.strip()

            # 尝试提取JSON数组部分（从第一个 [ 到最后一个 ]）
            # 这可以处理LLM在JSON后添加额外说明文本的情况
            start_idx = result.find('[')
            end_idx = result.rfind(']')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                result = result[start_idx:end_idx + 1]

            # 尝试直接解析
            data = json.loads(result)

            # 验证返回的是列表
            if not isinstance(data, list):
                logger.warning(f"LLM返回非列表数据: {type(data)}")
                return []

            # 验证列表元素是字典
            if data and not all(isinstance(item, dict) for item in data):
                logger.warning("LLM返回的列表包含非字典元素")
                return []

            return data

        except json.JSONDecodeError as e:
            logger.warning(f"解析 JSON 失败: {e}, 尝试清理emoji和修复格式后重试")
            # 只有解析失败时才尝试清理和修复
            try:
                # 1. 移除emoji
                result_cleaned = ChatAnalysisUtils.EMOJI_PATTERN.sub('', result)

                # 2. 再次提取JSON数组部分
                start_idx = result_cleaned.find('[')
                end_idx = result_cleaned.rfind(']')

                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    result_cleaned = result_cleaned[start_idx:end_idx + 1]

                # 3. 尝试修复中文字符间的异常空格（可能是emoji清理或LLM输出导致）
                # 保留JSON结构中的必要空格，只清理中文字符、数字、标点间的多余空格
                result_cleaned = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', result_cleaned)
                result_cleaned = re.sub(r'([\u4e00-\u9fff])\s+([\d])', r'\1\2', result_cleaned)
                result_cleaned = re.sub(r'([\d])\s+([\u4e00-\u9fff])', r'\1\2', result_cleaned)

                data = json.loads(result_cleaned)

                if not isinstance(data, list):
                    return []
                if data and not all(isinstance(item, dict) for item in data):
                    return []

                return data
            except Exception as e2:
                logger.error(f"清理emoji和修复格式后仍然失败: {e2}")
                logger.debug(f"清理后的内容（前500字符）: {result_cleaned[:500] if 'result_cleaned' in locals() else 'N/A'}")
                return []
        except Exception as e:
            logger.error(f"解析JSON时发生未预期错误: {e}")
            return []
