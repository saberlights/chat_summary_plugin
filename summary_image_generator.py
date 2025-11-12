"""
聊天总结图片生成器 - 参考astrbot设计的清爽风格
"""

import os
import io
import base64
from typing import Tuple, List, Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 导入logger
try:
    from src.common.logger import get_logger
    logger = get_logger("summary_image_generator")
except ImportError:
    import logging
    logger = logging.getLogger("summary_image_generator")


class SummaryImageGenerator:
    """生成聊天总结图片 - astrbot风格"""

    # 配色方案 - 参考astrbot
    BG_COLOR = (248, 250, 252)  # 浅灰背景 #f8fafc

    # 标题区域渐变色
    HEADER_START = (66, 153, 225)  # #4299e1
    HEADER_END = (102, 126, 234)   # #667eea

    # 文字颜色
    TITLE_COLOR = (255, 255, 255)     # 白色标题
    SUBTITLE_COLOR = (74, 85, 104)    # #4a5568 副标题
    TEXT_COLOR = (45, 55, 72)         # #2d3748 正文
    LIGHT_TEXT_COLOR = (102, 102, 102)  # #666666 浅色文字

    # 卡片颜色
    CARD_BG = (255, 255, 255)         # 白色卡片
    CARD_BORDER = (226, 232, 240)     # #e2e8f0 边框

    # 徽章渐变色
    BADGE_START = (66, 153, 225)      # #4299e1
    BADGE_END = (49, 130, 206)        # #3182ce

    # 金句卡片背景
    QUOTE_BG = (250, 245, 255)        # #faf5ff 淡紫色
    QUOTE_TEXT = (100, 50, 150)       # 紫色文字

    # 尺寸配置
    WIDTH = 1200
    PADDING = 50
    CARD_PADDING = 30

    # 字体大小
    TITLE_SIZE = 48
    SECTION_TITLE_SIZE = 36  # 群友称号、群圣经标题字体
    SUBTITLE_SIZE = 28
    TEXT_SIZE = 24
    SMALL_SIZE = 20

    @staticmethod
    def _get_font(size: int) -> ImageFont.FreeTypeFont:
        """获取字体"""
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue

        raise RuntimeError("未找到可用的中文字体")

    @staticmethod
    def _draw_rounded_rectangle(
        draw: ImageDraw.ImageDraw,
        coords: tuple,
        radius: int,
        fill: tuple,
        outline: tuple = None,
        width: int = 1
    ):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = coords

        # 绘制主体矩形
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

        # 四个圆角
        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
        draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

        # 绘制边框
        if outline:
            draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
            draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)
            draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
            draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
            draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
            draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)

    @staticmethod
    def _wrap_text(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> List[str]:
        """文本自动换行 - 改进版，正确处理中英文"""
        lines = []

        for paragraph in text.split('\n'):
            if not paragraph.strip():
                lines.append('')
                continue

            current_line = ''
            for char in paragraph:
                test_line = current_line + char
                bbox = font.getbbox(test_line)
                w = bbox[2] - bbox[0]

                if w <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char

            if current_line:
                lines.append(current_line)

        return lines

    @staticmethod
    def _draw_gradient_rect(
        draw: ImageDraw.ImageDraw,
        coords: tuple,
        start_color: tuple,
        end_color: tuple,
        horizontal: bool = True
    ):
        """绘制渐变矩形"""
        x1, y1, x2, y2 = coords

        if horizontal:
            # 水平渐变
            for x in range(x1, x2):
                ratio = (x - x1) / (x2 - x1)
                r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
                draw.line([(x, y1), (x, y2)], fill=(r, g, b))
        else:
            # 垂直渐变
            for y in range(y1, y2):
                ratio = (y - y1) / (y2 - y1)
                r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
                draw.line([(x1, y), (x2, y)], fill=(r, g, b))

    @staticmethod
    def _load_and_paste_decoration(
        img: Image.Image,
        decoration_paths: list,
        center_x: int,
        y: int,
        max_width: int = 800,
        max_height: int = 150
    ) -> int:
        """加载并粘贴装饰图片（支持多张横向排列）

        Args:
            img: 目标图片
            decoration_paths: 装饰图片路径列表
            center_x: 中心X坐标
            y: Y坐标
            max_width: 单张图片最大宽度
            max_height: 单张图片最大高度

        Returns:
            装饰图片的实际高度
        """
        if not decoration_paths:
            return 0

        loaded_images = []
        total_width = 0
        max_img_height = 0
        spacing = 20  # 图片之间的间距

        # 加载所有装饰图片
        for deco_path in decoration_paths:
            if not os.path.exists(deco_path):
                logger.warning(f"装饰图片不存在: {deco_path}")
                continue

            try:
                deco_img = Image.open(deco_path).convert("RGBA")

                # 调整大小保持比例
                w, h = deco_img.size
                scale = min(max_width / w, max_height / h, 1.0)
                new_w = int(w * scale)
                new_h = int(h * scale)

                if scale < 1.0:
                    deco_img = deco_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                loaded_images.append(deco_img)
                total_width += new_w
                max_img_height = max(max_img_height, new_h)

            except Exception as e:
                logger.error(f"加载装饰图片失败 {deco_path}: {e}")
                continue

        if not loaded_images:
            return 0

        # 计算总宽度（包含间距）
        total_width += spacing * (len(loaded_images) - 1)

        # 计算起始X坐标（居中）
        current_x = center_x - total_width // 2

        # 粘贴所有图片
        for deco_img in loaded_images:
            # 创建一个临时图层用于混合
            temp = Image.new('RGBA', img.size, (0, 0, 0, 0))

            # 居中对齐
            paste_y = y + (max_img_height - deco_img.size[1]) // 2
            temp.paste(deco_img, (current_x, paste_y), deco_img)

            # 将临时图层合并到主图
            img_with_alpha = img.convert('RGBA')
            img_with_alpha = Image.alpha_composite(img_with_alpha, temp)
            img.paste(img_with_alpha.convert('RGB'))

            current_x += deco_img.size[0] + spacing

        return max_img_height

    @staticmethod
    def generate_summary_image(
        title: str,
        summary_text: str,
        time_info: str = "",
        message_count: int = 0,
        participant_count: int = 0,
        width: int = None,
        decoration_image_path: str = None,
        user_titles: list = None,
        golden_quotes: list = None
    ) -> Tuple[bytes, str]:
        """生成聊天总结图片

        Args:
            title: 标题
            summary_text: 总结文本
            time_info: 时间信息
            message_count: 消息数量
            participant_count: 参与人数
            width: 图片宽度
            decoration_image_path: 装饰图片路径（暂不使用）
            user_titles: 群友称号列表
            golden_quotes: 金句列表
        """
        if width is None:
            width = SummaryImageGenerator.WIDTH

        # 初始化
        if user_titles is None:
            user_titles = []
        if golden_quotes is None:
            golden_quotes = []

        # 加载字体
        font_title = SummaryImageGenerator._get_font(SummaryImageGenerator.TITLE_SIZE)
        font_section_title = SummaryImageGenerator._get_font(SummaryImageGenerator.SECTION_TITLE_SIZE)
        font_subtitle = SummaryImageGenerator._get_font(SummaryImageGenerator.SUBTITLE_SIZE)
        font_text = SummaryImageGenerator._get_font(SummaryImageGenerator.TEXT_SIZE)
        font_small = SummaryImageGenerator._get_font(SummaryImageGenerator.SMALL_SIZE)

        # 计算所需高度
        header_height = 200
        summary_card_height = 0
        titles_section_height = 0
        quotes_section_height = 0
        decoration_height = 150  # 装饰图片预留高度

        # 计算总结卡片高度
        max_text_width = width - SummaryImageGenerator.PADDING * 2 - SummaryImageGenerator.CARD_PADDING * 2
        wrapped_lines = SummaryImageGenerator._wrap_text(summary_text, max_text_width, font_text)
        line_height = font_text.getbbox('测试')[3] - font_text.getbbox('测试')[1]
        summary_card_height = SummaryImageGenerator.CARD_PADDING * 2 + len(wrapped_lines) * (line_height + 8) + 50

        # 计算称号区域高度
        if user_titles:
            titles_section_height = 80 + len(user_titles) * 95  # 标题 + 卡片*数量

        # 计算金句区域高度
        if golden_quotes:
            quotes_section_height = 80 + len(golden_quotes) * 180  # 标题 + 卡片*数量

        # 总高度
        total_height = header_height + summary_card_height + titles_section_height + quotes_section_height + 100

        # 创建图片
        img = Image.new('RGB', (width, total_height), SummaryImageGenerator.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # 当前Y坐标
        y = 0

        # ===== 标题区域 =====
        SummaryImageGenerator._draw_gradient_rect(
            draw,
            (0, 0, width, header_height),
            SummaryImageGenerator.HEADER_START,
            SummaryImageGenerator.HEADER_END,
            horizontal=True
        )

        # 绘制标题（移除emoji）
        title_clean = title.replace('📊', '').strip()
        title_bbox = font_title.getbbox(title_clean)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, 50), title_clean, fill=SummaryImageGenerator.TITLE_COLOR, font=font_title)

        # 在标题左右两侧添加装饰图片
        plugin_dir = os.path.dirname(__file__)
        deco1_path = os.path.join(plugin_dir, "decoration1.png")
        deco4_path = os.path.join(plugin_dir, "decoration4.png")

        # 左侧decoration1
        SummaryImageGenerator._load_and_paste_decoration(
            img, [deco1_path], title_x - 150, 35, max_width=120, max_height=80
        )
        # 右侧decoration4
        SummaryImageGenerator._load_and_paste_decoration(
            img, [deco4_path], title_x + title_width + 150, 35, max_width=120, max_height=80
        )

        # 绘制时间和统计信息
        if time_info or message_count > 0:
            info_parts = []
            if time_info:
                info_parts.append(time_info)
            if message_count > 0:
                msg_text = f"{message_count}条消息"
                if participant_count > 0:
                    msg_text += f" · {participant_count}人参与"
                info_parts.append(msg_text)

            info_text = " | ".join(info_parts)
            info_bbox = font_small.getbbox(info_text)
            info_width = info_bbox[2] - info_bbox[0]
            info_x = (width - info_width) // 2
            draw.text((info_x, 120), info_text, fill=(255, 255, 255, 230), font=font_small)

        y = header_height + 30

        # ===== 总结卡片 =====
        card_x = SummaryImageGenerator.PADDING
        card_width = width - SummaryImageGenerator.PADDING * 2

        SummaryImageGenerator._draw_rounded_rectangle(
            draw,
            (card_x, y, card_x + card_width, y + summary_card_height),
            15,
            fill=SummaryImageGenerator.CARD_BG,
            outline=SummaryImageGenerator.CARD_BORDER,
            width=1
        )

        # 绘制总结文本
        text_y = y + SummaryImageGenerator.CARD_PADDING
        text_x = card_x + SummaryImageGenerator.CARD_PADDING

        for line in wrapped_lines:
            if line:
                draw.text((text_x, text_y), line, fill=SummaryImageGenerator.TEXT_COLOR, font=font_text)
            text_y += line_height + 8

        y += summary_card_height + 40

        # ===== 群友称号区域 =====
        if user_titles:
            # 获取插件目录
            plugin_dir = os.path.dirname(__file__)

            # 标题区域（带蓝色渐变背景框和装饰图）
            section_title = "群友称号"
            title_height = 80

            # 绘制蓝色渐变背景框
            SummaryImageGenerator._draw_gradient_rect(
                draw,
                (SummaryImageGenerator.PADDING, y, width - SummaryImageGenerator.PADDING, y + title_height),
                SummaryImageGenerator.HEADER_START,
                SummaryImageGenerator.HEADER_END,
                horizontal=True
            )

            # 在标题左侧添加decoration2
            deco2_path = os.path.join(plugin_dir, "decoration2.png")
            # 计算装饰图片位置：标题中心左侧，距离标题一半宽度再偏移100像素
            title_center_x = width // 2
            deco_x = title_center_x - title_width // 2 - 70
            SummaryImageGenerator._load_and_paste_decoration(
                img, [deco2_path], deco_x, y + 10, max_width=60, max_height=60
            )

            # 绘制标题文字（白色，居中）
            title_bbox = font_section_title.getbbox(section_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(
                ((width - title_width) // 2, y + 25),
                section_title,
                fill=SummaryImageGenerator.TITLE_COLOR,
                font=font_section_title
            )
            y += title_height + 20

            # 绘制称号卡片
            for idx, title_item in enumerate(user_titles):
                name = title_item.get("name", "")
                title_text = title_item.get("title", "")
                reason = title_item.get("reason", "")

                # 卡片背景
                card_height = 80
                SummaryImageGenerator._draw_rounded_rectangle(
                    draw,
                    (card_x, y, card_x + card_width, y + card_height),
                    12,
                    fill=SummaryImageGenerator.CARD_BG,
                    outline=SummaryImageGenerator.CARD_BORDER,
                    width=1
                )

                # 左边徽章
                badge_x = card_x + 20
                badge_y = y + 20
                badge_width = 140
                badge_height = 40

                # 绘制徽章渐变背景
                SummaryImageGenerator._draw_gradient_rect(
                    draw,
                    (badge_x, badge_y, badge_x + badge_width, badge_y + badge_height),
                    SummaryImageGenerator.BADGE_START,
                    SummaryImageGenerator.BADGE_END,
                    horizontal=True
                )

                # 徽章文字
                badge_text_bbox = font_text.getbbox(title_text)
                badge_text_width = badge_text_bbox[2] - badge_text_bbox[0]
                badge_text_x = badge_x + (badge_width - badge_text_width) // 2
                badge_text_y = badge_y + (badge_height - (badge_text_bbox[3] - badge_text_bbox[1])) // 2
                draw.text((badge_text_x, badge_text_y), title_text, fill=(255, 255, 255), font=font_text)

                # 用户名
                name_x = badge_x + badge_width + 25
                name_y = y + 15
                draw.text((name_x, name_y), name, fill=SummaryImageGenerator.TEXT_COLOR, font=font_subtitle)

                # 理由（自动换行）
                reason_y = y + 50
                max_reason_width = card_width - (badge_width + 60)
                reason_lines = SummaryImageGenerator._wrap_text(reason, max_reason_width, font_small)
                reason_text = reason_lines[0] if reason_lines else reason  # 只显示第一行
                if len(reason) > 25:
                    reason_text = reason_text[:23] + "..."
                draw.text((name_x, reason_y), reason_text, fill=SummaryImageGenerator.LIGHT_TEXT_COLOR, font=font_small)

                y += card_height + 15

            y += 25

        # ===== 金句区域 =====
        if golden_quotes:
            # 获取插件目录
            plugin_dir = os.path.dirname(__file__)

            # 标题区域（带蓝色渐变背景框和装饰图）
            section_title = "群圣经"
            title_height = 80

            # 绘制蓝色渐变背景框
            SummaryImageGenerator._draw_gradient_rect(
                draw,
                (SummaryImageGenerator.PADDING, y, width - SummaryImageGenerator.PADDING, y + title_height),
                SummaryImageGenerator.HEADER_START,
                SummaryImageGenerator.HEADER_END,
                horizontal=True
            )

            # 在标题左侧添加decoration3
            deco3_path = os.path.join(plugin_dir, "decoration3.png")
            # 计算装饰图片位置：标题中心左侧，距离标题一半宽度再偏移100像素
            title_center_x = width // 2
            deco_x = title_center_x - title_width // 2 - 70
            SummaryImageGenerator._load_and_paste_decoration(
                img, [deco3_path], deco_x, y + 10, max_width=60, max_height=60
            )

            # 绘制标题文字（白色，居中）
            title_bbox = font_section_title.getbbox(section_title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(
                ((width - title_width) // 2, y + 25),
                section_title,
                fill=SummaryImageGenerator.TITLE_COLOR,
                font=font_section_title
            )
            y += title_height + 20

            # 绘制金句卡片
            for idx, quote_item in enumerate(golden_quotes):
                content = quote_item.get("content", "")
                sender = quote_item.get("sender", "")
                reason = quote_item.get("reason", "")

                # 限制长度
                if len(content) > 40:
                    content = content[:38] + "..."
                if len(reason) > 25:
                    reason = reason[:23] + "..."

                # 卡片背景
                card_height = 160
                SummaryImageGenerator._draw_rounded_rectangle(
                    draw,
                    (card_x, y, card_x + card_width, y + card_height),
                    12,
                    fill=SummaryImageGenerator.QUOTE_BG,
                    outline=SummaryImageGenerator.CARD_BORDER,
                    width=1
                )

                # 金句内容（带引号）
                content_x = card_x + 25
                content_y = y + 25
                quote_text = f'"{content}"'

                # 自动换行金句内容
                max_quote_width = card_width - 50
                quote_lines = SummaryImageGenerator._wrap_text(quote_text, max_quote_width, font_text)

                for line in quote_lines[:2]:  # 最多显示2行
                    draw.text((content_x, content_y), line, fill=SummaryImageGenerator.QUOTE_TEXT, font=font_text)
                    content_y += line_height + 5

                # 发言人
                sender_y = y + 75
                sender_text = f"—— {sender}"
                draw.text((content_x, sender_y), sender_text, fill=SummaryImageGenerator.SUBTITLE_COLOR, font=font_small)

                # 理由
                reason_y = y + 100
                draw.text((content_x, reason_y), reason, fill=SummaryImageGenerator.LIGHT_TEXT_COLOR, font=font_small)

                y += card_height + 15

            y += 10

        # 转换为字节和base64
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        return img_bytes, img_base64
