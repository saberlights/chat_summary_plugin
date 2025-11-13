"""
聊天总结图片生成器 - 梦幻渐变风格
明亮温暖的视觉设计，充分利用所有装饰元素
"""

import os
import io
import base64
import tempfile
from typing import Tuple, List, Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# 导入logger
try:
    from src.common.logger import get_logger
    logger = get_logger("summary_image_generator")
except ImportError:
    import logging
    logger = logging.getLogger("summary_image_generator")


class SummaryImageGenerator:
    """生成聊天总结图片 - 梦幻渐变风格"""

    # 明亮渐变背景 - 温暖梦幻风格
    BG_START = (240, 230, 255)        # 淡紫色
    BG_MID = (255, 240, 245)          # 粉白色
    BG_END = (245, 250, 255)          # 淡蓝白

    # 卡片配色 - 白色半透明
    CARD_BG = (255, 255, 255, 250)    # 白色半透明卡片背景
    CARD_BG_LIGHT = (250, 250, 255, 245) # 稍紫的卡片背景

    # 彩色边框和装饰
    BORDER_CYAN = (100, 200, 255)     # 柔和青色
    BORDER_MAGENTA = (255, 100, 200)  # 柔和品红
    BORDER_YELLOW = (255, 200, 80)    # 柔和金色
    BORDER_GREEN = (120, 220, 150)    # 柔和绿色
    BORDER_PINK = (255, 150, 180)     # 柔和粉色
    BORDER_ORANGE = (255, 160, 100)   # 柔和橙色
    BORDER_PURPLE = (180, 120, 255)   # 柔和紫色
    BORDER_BLUE = (120, 180, 255)     # 柔和蓝色

    # 文字颜色
    TITLE_COLOR = (80, 60, 120)       # 深紫色标题
    TEXT_COLOR = (60, 60, 80)         # 深灰蓝文字
    SUBTITLE_COLOR = (100, 100, 130)  # 中灰文字
    LIGHT_TEXT_COLOR = (130, 130, 150) # 浅灰文字
    HIGHLIGHT_COLOR = (255, 100, 150)  # 高亮粉色

    # 渐变强调色 - 柔和版本
    GRADIENT_1_START = (100, 200, 255)         # 柔和青色
    GRADIENT_1_END = (150, 100, 255)           # 柔和蓝紫色

    GRADIENT_2_START = (255, 120, 200)         # 柔和品红
    GRADIENT_2_END = (255, 150, 180)           # 柔和粉色

    GRADIENT_3_START = (255, 200, 80)          # 柔和金色
    GRADIENT_3_END = (255, 160, 100)           # 柔和橙色

    # 尺寸配置
    WIDTH = 1200
    PADDING = 70
    CARD_PADDING = 45
    CARD_SPACING = 35

    # 字体大小
    TITLE_SIZE = 64
    SECTION_TITLE_SIZE = 46
    SUBTITLE_SIZE = 32
    TEXT_SIZE = 28
    SMALL_SIZE = 24

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
        """文本自动换行"""
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
                ratio = (x - x1) / max(1, (x2 - x1))
                r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
                draw.line([(x, y1), (x, y2)], fill=(r, g, b))
        else:
            # 垂直渐变
            for y in range(y1, y2):
                ratio = (y - y1) / max(1, (y2 - y1))
                r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
                draw.line([(x1, y), (x2, y)], fill=(r, g, b))

    @staticmethod
    def _draw_colorful_card(
        img: Image.Image,
        coords: tuple,
        border_color: tuple,
        radius: int = 20,
        shadow_strength: int = 15
    ) -> Image.Image:
        """绘制彩色卡片（适合明亮背景）

        Args:
            img: 目标图片
            coords: 卡片坐标 (x1, y1, x2, y2)
            border_color: 边框颜色
            radius: 圆角半径
            shadow_strength: 阴影强度
        """
        x1, y1, x2, y2 = coords

        # 创建RGBA图层
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # 绘制柔和阴影效果（从外到内）
        for i in range(shadow_strength, 0, -1):
            alpha = int(30 * (shadow_strength - i) / shadow_strength)
            shadow_color = (100, 100, 120, alpha)
            offset = i

            SummaryImageGenerator._draw_rounded_rectangle(
                overlay_draw,
                (x1 - offset + 2, y1 - offset + 2, x2 + offset + 2, y2 + offset + 2),
                radius + offset,
                fill=(0, 0, 0, 0),
                outline=shadow_color,
                width=2
            )

        # 应用模糊
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=shadow_strength // 2))

        # 合并到主图
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)

        # 绘制卡片背景
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        SummaryImageGenerator._draw_rounded_rectangle(
            overlay_draw,
            coords,
            radius,
            fill=SummaryImageGenerator.CARD_BG
        )
        img = Image.alpha_composite(img, overlay)

        # 绘制彩色边框
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        border_rgba = border_color + (255,)
        SummaryImageGenerator._draw_rounded_rectangle(
            overlay_draw,
            coords,
            radius,
            fill=(0, 0, 0, 0),
            outline=border_rgba,
            width=4
        )
        img = Image.alpha_composite(img, overlay)

        return img

    @staticmethod
    def _draw_text_with_shadow(
        draw: ImageDraw.ImageDraw,
        position: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        text_color: tuple,
        shadow_offset: int = 2,
        shadow_color: tuple = (200, 200, 220, 120)
    ):
        """绘制带阴影的文字（柔和版本）"""
        x, y = position

        # 绘制阴影
        draw.text((x + shadow_offset, y + shadow_offset), text, fill=shadow_color, font=font)

        # 绘制主文字
        draw.text((x, y), text, fill=text_color, font=font)

    @staticmethod
    def _draw_colorful_text(
        img: Image.Image,
        position: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        text_color: tuple,
        outline_color: tuple = None,
        shadow_radius: int = 6
    ) -> Image.Image:
        """绘制彩色描边文字（明亮风格）"""
        # 创建临时图层
        shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)

        # 如果有描边颜色，绘制柔和描边
        if outline_color:
            for offset in range(shadow_radius, 0, -1):
                alpha = int(80 * (shadow_radius - offset) / shadow_radius)
                outline_col = outline_color[:3] + (alpha,)
                for dx in range(-offset, offset + 1):
                    for dy in range(-offset, offset + 1):
                        if dx*dx + dy*dy <= offset*offset:
                            shadow_draw.text(
                                (position[0] + dx, position[1] + dy),
                                text,
                                fill=outline_col,
                                font=font
                            )

            # 应用轻微模糊
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_radius // 3))

            # 合并阴影
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, shadow_layer)

        # 绘制主文字
        text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_draw.text(position, text, fill=text_color, font=font)
        img = Image.alpha_composite(img, text_layer)

        return img

    @staticmethod
    def _add_decoration_with_glow(
        img: Image.Image,
        deco_path: str,
        position: tuple,
        max_size: tuple,
        glow_color: tuple = None
    ) -> Image.Image:
        """添加带发光效果的装饰图片

        Args:
            img: 目标图片
            deco_path: 装饰图片路径
            position: 位置 (x, y)
            max_size: 最大尺寸 (width, height)
            glow_color: 发光颜色（可选）
        """
        if not os.path.exists(deco_path):
            return img

        try:
            deco_img = Image.open(deco_path).convert("RGBA")
            w, h = deco_img.size

            # 缩放
            scale = min(max_size[0] / w, max_size[1] / h, 1.0)
            new_w, new_h = int(w * scale), int(h * scale)
            if scale < 1.0:
                deco_img = deco_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 如果有光晕颜色，添加柔和光晕效果
            if glow_color:
                glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))

                # 创建柔和光晕
                for offset in range(15, 0, -2):
                    alpha = int(40 * (15 - offset) / 15)  # 降低透明度
                    glow_temp = Image.new('RGBA', (new_w + offset * 2, new_h + offset * 2), (0, 0, 0, 0))
                    glow_temp.paste(deco_img, (offset, offset), deco_img)

                    # 添加颜色叠加
                    color_layer = Image.new('RGBA', glow_temp.size, glow_color + (alpha,))
                    glow_temp = Image.alpha_composite(glow_temp, color_layer)

                    glow_layer.paste(glow_temp, (position[0] - offset, position[1] - offset), glow_temp)

                # 应用模糊
                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
                img = Image.alpha_composite(img, glow_layer)

            # 粘贴装饰图片
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay.paste(deco_img, position, deco_img)
            img = Image.alpha_composite(img, overlay)

            return img

        except Exception as e:
            logger.error(f"添加装饰失败 {deco_path}: {e}")
            return img

    @staticmethod
    def _draw_gradient_badge(
        img: Image.Image,
        position: tuple,
        size: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        gradient_start: tuple,
        gradient_end: tuple
    ) -> Image.Image:
        """绘制渐变徽章"""
        x, y = position
        w, h = size

        # 创建临时图层
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # 绘制渐变背景
        SummaryImageGenerator._draw_gradient_rect(
            overlay_draw,
            (x, y, x + w, y + h),
            gradient_start,
            gradient_end,
            horizontal=True
        )

        # 圆角蒙版
        mask = Image.new('L', img.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        SummaryImageGenerator._draw_rounded_rectangle(
            mask_draw,
            (x, y, x + w, y + h),
            h // 2,
            fill=255
        )
        overlay.putalpha(mask)

        # 合并
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)

        # 绘制文字
        text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_bbox = font.getbbox(text)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_x = x + (w - text_w) // 2
        text_y = y + (h - text_h) // 2 - 2

        # 文字阴影
        text_draw.text((text_x + 2, text_y + 2), text, fill=(0, 0, 0, 200), font=font)
        text_draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

        img = Image.alpha_composite(img, text_layer)

        return img

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
    ) -> str:
        """生成聊天总结图片 - 霓虹赛博朋克风格

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

        Returns:
            str: 临时图片文件的绝对路径
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

        plugin_dir = os.path.dirname(__file__)

        # ===== 计算所需高度 =====
        header_height = 300
        summary_card_height = 0
        titles_section_height = 0
        quotes_section_height = 0

        # 计算总结卡片高度
        max_text_width = width - SummaryImageGenerator.PADDING * 2 - SummaryImageGenerator.CARD_PADDING * 2
        wrapped_lines = SummaryImageGenerator._wrap_text(summary_text, max_text_width, font_text)
        line_height = font_text.getbbox('测试')[3] - font_text.getbbox('测试')[1]
        summary_card_height = SummaryImageGenerator.CARD_PADDING * 2 + len(wrapped_lines) * (line_height + 15) + 80

        # 计算称号区域高度
        if user_titles:
            titles_section_height = 150  # 标题高度
            max_reason_width = width - SummaryImageGenerator.PADDING * 2 - SummaryImageGenerator.CARD_PADDING * 2 - 200 - 50
            for title_item in user_titles[:4]:  # 显示4个
                reason = title_item.get("reason", "")
                reason_lines = SummaryImageGenerator._wrap_text(reason, max_reason_width, font_small)
                card_height = 60 + 50 + len(reason_lines) * (28 + 8) + 30
                titles_section_height += card_height + SummaryImageGenerator.CARD_SPACING

        # 计算金句区域高度
        if golden_quotes:
            quotes_section_height = 150  # 标题高度
            max_quote_width = width - SummaryImageGenerator.PADDING * 2 - SummaryImageGenerator.CARD_PADDING * 2
            for quote_item in golden_quotes[:4]:  # 显示4个
                content = quote_item.get("content", "")
                reason = quote_item.get("reason", "")
                quote_text = f'"{content}"'
                quote_lines = SummaryImageGenerator._wrap_text(quote_text, max_quote_width, font_text)
                reason_lines = SummaryImageGenerator._wrap_text(reason, max_quote_width, font_small)
                card_height = 50 + len(quote_lines) * (line_height + 12) + 50 + len(reason_lines) * 32 + 40
                quotes_section_height += card_height + SummaryImageGenerator.CARD_SPACING

        # 总高度（增加底部空间以显示decoration2）
        footer_height = 280
        total_height = header_height + summary_card_height + titles_section_height + quotes_section_height + footer_height

        # ===== 创建图片 =====
        img = Image.new('RGB', (width, total_height), SummaryImageGenerator.BG_START)
        draw = ImageDraw.Draw(img)

        # 绘制渐变背景
        for y in range(total_height):
            if y < total_height // 2:
                ratio = y / (total_height // 2)
                r = int(SummaryImageGenerator.BG_START[0] + (SummaryImageGenerator.BG_MID[0] - SummaryImageGenerator.BG_START[0]) * ratio)
                g = int(SummaryImageGenerator.BG_START[1] + (SummaryImageGenerator.BG_MID[1] - SummaryImageGenerator.BG_START[1]) * ratio)
                b = int(SummaryImageGenerator.BG_START[2] + (SummaryImageGenerator.BG_MID[2] - SummaryImageGenerator.BG_START[2]) * ratio)
            else:
                ratio = (y - total_height // 2) / (total_height // 2)
                r = int(SummaryImageGenerator.BG_MID[0] + (SummaryImageGenerator.BG_END[0] - SummaryImageGenerator.BG_MID[0]) * ratio)
                g = int(SummaryImageGenerator.BG_MID[1] + (SummaryImageGenerator.BG_END[1] - SummaryImageGenerator.BG_MID[1]) * ratio)
                b = int(SummaryImageGenerator.BG_MID[2] + (SummaryImageGenerator.BG_END[2] - SummaryImageGenerator.BG_MID[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 转换为RGBA
        img = img.convert('RGBA')

        # 添加背景装饰 - 波点图案
        import random
        random.seed(42)  # 固定种子保证每次生成相同图案
        bg_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_overlay)

        # 绘制柔和波点
        for _ in range(80):
            x = random.randint(0, width)
            y = random.randint(0, total_height)
            size = random.randint(30, 80)
            colors = [
                (255, 200, 220, 25),  # 粉色
                (200, 220, 255, 25),  # 蓝色
                (220, 200, 255, 25),  # 紫色
                (255, 240, 200, 25),  # 金色
            ]
            color = random.choice(colors)
            bg_draw.ellipse([x, y, x + size, y + size], fill=color)

        img = Image.alpha_composite(img, bg_overlay)

        y = 0

        # ===== 标题区域 =====
        title_clean = title.replace('📊', '').strip()

        title_bbox = font_title.getbbox(title_clean)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = 80

        # 绘制彩色描边标题
        img = SummaryImageGenerator._draw_colorful_text(
            img,
            (title_x, title_y),
            title_clean,
            font_title,
            SummaryImageGenerator.TITLE_COLOR,
            outline_color=SummaryImageGenerator.BORDER_PURPLE,
            shadow_radius=8
        )

        # 添加decoration1装饰（标题左侧）
        deco1_path = os.path.join(plugin_dir, "decorations", "decoration1.png")
        img = SummaryImageGenerator._add_decoration_with_glow(
            img,
            deco1_path,
            (title_x - 200, title_y - 30),
            (150, 150),
            SummaryImageGenerator.BORDER_CYAN
        )

        # 右侧镜像
        if os.path.exists(deco1_path):
            try:
                deco1_img = Image.open(deco1_path).convert("RGBA")
                w, h = deco1_img.size
                scale = min(150 / w, 150 / h, 1.0)
                new_w, new_h = int(w * scale), int(h * scale)
                if scale < 1.0:
                    deco1_img = deco1_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # 镜像翻转
                deco1_flipped = deco1_img.transpose(Image.FLIP_LEFT_RIGHT)

                # 手动添加光晕和图片（使用镜像后的图片）
                paste_x = title_x + title_width + 50
                paste_y = title_y - 30

                # 添加柔和光晕
                glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                for offset in range(15, 0, -2):
                    alpha = int(40 * (15 - offset) / 15)
                    glow_temp = Image.new('RGBA', (new_w + offset * 2, new_h + offset * 2), (0, 0, 0, 0))
                    glow_temp.paste(deco1_flipped, (offset, offset), deco1_flipped)
                    color_layer = Image.new('RGBA', glow_temp.size, SummaryImageGenerator.BORDER_CYAN + (alpha,))
                    glow_temp = Image.alpha_composite(glow_temp, color_layer)
                    glow_layer.paste(glow_temp, (paste_x - offset, paste_y - offset), glow_temp)

                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
                img = Image.alpha_composite(img, glow_layer)

                # 粘贴镜像图片
                overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                overlay.paste(deco1_flipped, (paste_x, paste_y), deco1_flipped)
                img = Image.alpha_composite(img, overlay)
            except Exception as e:
                logger.error(f"添加镜像decoration1失败: {e}")

        # 添加星星装饰
        star_path = os.path.join(plugin_dir, "decorations", "decoration_star.png")
        positions = [
            (title_x - 280, 60),
            (title_x + title_width + 250, 70),
            (title_x - 320, 140),
            (title_x + title_width + 290, 150),
        ]
        for pos in positions:
            img = SummaryImageGenerator._add_decoration_with_glow(
                img,
                star_path,
                pos,
                (40, 40),
                SummaryImageGenerator.BORDER_YELLOW
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

            text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_layer)
            SummaryImageGenerator._draw_text_with_shadow(
                text_draw,
                (info_x, 180),
                info_text,
                font_small,
                SummaryImageGenerator.HIGHLIGHT_COLOR,
                shadow_offset=2
            )
            img = Image.alpha_composite(img, text_layer)

        y = header_height

        # ===== 总结卡片（霓虹卡片） =====
        card_x = SummaryImageGenerator.PADDING
        card_width = width - SummaryImageGenerator.PADDING * 2

        img = SummaryImageGenerator._draw_colorful_card(
            img,
            (card_x, y, card_x + card_width, y + summary_card_height),
            SummaryImageGenerator.BORDER_CYAN,
            radius=25,
            shadow_strength=15
        )

        # 绘制总结文本
        text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_y = y + SummaryImageGenerator.CARD_PADDING + 20
        text_x = card_x + SummaryImageGenerator.CARD_PADDING

        for line in wrapped_lines:
            if line:
                SummaryImageGenerator._draw_text_with_shadow(
                    text_draw,
                    (text_x, text_y),
                    line,
                    font_text,
                    SummaryImageGenerator.TEXT_COLOR,
                    shadow_offset=2
                )
            text_y += line_height + 15

        img = Image.alpha_composite(img, text_layer)

        # 在总结卡片角落添加闪光装饰
        sparkle_path = os.path.join(plugin_dir, "decorations", "decoration_sparkle.png")
        sparkle_positions = [
            (card_x + 15, y + 15),
            (card_x + card_width - 55, y + 15),
            (card_x + 15, y + summary_card_height - 55),
            (card_x + card_width - 55, y + summary_card_height - 55),
        ]
        for pos in sparkle_positions:
            img = SummaryImageGenerator._add_decoration_with_glow(
                img,
                sparkle_path,
                pos,
                (40, 40),
                SummaryImageGenerator.BORDER_CYAN
            )

        y += summary_card_height + 50

        # ===== 群友称号区域 =====
        if user_titles:
            # 标题
            section_title = "群友称号"
            title_bbox = font_section_title.getbbox(section_title)
            section_title_width = title_bbox[2] - title_bbox[0]
            section_title_x = (width - section_title_width) // 2

            # 彩色描边标题
            img = SummaryImageGenerator._draw_colorful_text(
                img,
                (section_title_x, y + 30),
                section_title,
                font_section_title,
                SummaryImageGenerator.TITLE_COLOR,
                outline_color=SummaryImageGenerator.BORDER_MAGENTA,
                shadow_radius=8
            )

            # 添加decoration3装饰（群友称号区域）
            deco3_path = os.path.join(plugin_dir, "decorations", "decoration3.png")
            img = SummaryImageGenerator._add_decoration_with_glow(
                img,
                deco3_path,
                (section_title_x - 150, y + 10),
                (120, 120),
                SummaryImageGenerator.BORDER_MAGENTA
            )

            # 右侧镜像
            if os.path.exists(deco3_path):
                try:
                    deco3_img = Image.open(deco3_path).convert("RGBA")
                    w, h = deco3_img.size
                    scale = min(120 / w, 120 / h, 1.0)
                    new_w, new_h = int(w * scale), int(h * scale)
                    if scale < 1.0:
                        deco3_img = deco3_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    deco3_flipped = deco3_img.transpose(Image.FLIP_LEFT_RIGHT)
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    paste_x = section_title_x + section_title_width + 30
                    paste_y = y + 10

                    # 添加柔和光晕
                    glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    for offset in range(15, 0, -2):
                        alpha = int(40 * (15 - offset) / 15)
                        glow_temp = Image.new('RGBA', (new_w + offset * 2, new_h + offset * 2), (0, 0, 0, 0))
                        glow_temp.paste(deco3_flipped, (offset, offset), deco3_flipped)
                        color_layer = Image.new('RGBA', glow_temp.size, SummaryImageGenerator.BORDER_MAGENTA + (alpha,))
                        glow_temp = Image.alpha_composite(glow_temp, color_layer)
                        glow_layer.paste(glow_temp, (paste_x - offset, paste_y - offset), glow_temp)

                    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
                    img = Image.alpha_composite(img, glow_layer)

                    overlay.paste(deco3_flipped, (paste_x, paste_y), deco3_flipped)
                    img = Image.alpha_composite(img, overlay)
                except Exception as e:
                    logger.error(f"添加镜像decoration3失败: {e}")

            y += 150

            # 称号卡片
            badge_colors = [
                (SummaryImageGenerator.GRADIENT_3_START, SummaryImageGenerator.GRADIENT_3_END, SummaryImageGenerator.BORDER_YELLOW),   # 金色
                (SummaryImageGenerator.GRADIENT_1_START, SummaryImageGenerator.GRADIENT_1_END, SummaryImageGenerator.BORDER_CYAN),     # 青色
                (SummaryImageGenerator.GRADIENT_2_START, SummaryImageGenerator.GRADIENT_2_END, SummaryImageGenerator.BORDER_MAGENTA),  # 品红
                (SummaryImageGenerator.GRADIENT_1_START, SummaryImageGenerator.GRADIENT_1_END, SummaryImageGenerator.BORDER_PURPLE),   # 紫色（第4个）
            ]

            for idx, title_item in enumerate(user_titles[:4]):
                name = title_item.get("name", "")
                title_text = title_item.get("title", "")
                reason = title_item.get("reason", "")

                # 计算理由高度
                max_reason_width = card_width - SummaryImageGenerator.CARD_PADDING * 2
                reason_lines = SummaryImageGenerator._wrap_text(reason, max_reason_width, font_small)
                reason_line_height = font_small.getbbox('测试')[3] - font_small.getbbox('测试')[1]
                title_line_height = font_subtitle.getbbox('测试')[3] - font_subtitle.getbbox('测试')[1]

                card_height = 50 + title_line_height + 25 + len(reason_lines) * (reason_line_height + 8) + 30
                card_height = max(card_height, 120)

                # 彩色卡片
                grad_start, grad_end, border_color = badge_colors[idx]
                img = SummaryImageGenerator._draw_colorful_card(
                    img,
                    (card_x, y, card_x + card_width, y + card_height),
                    border_color,
                    radius=20,
                    shadow_strength=15
                )

                # 第一行：装饰图标 + 群称号徽章 + 群友名称
                content_x = card_x + SummaryImageGenerator.CARD_PADDING
                content_y = y + 35

                # 1. 添加装饰图标（根据排名选择）
                deco_icons = [
                    os.path.join(plugin_dir, "decorations", "decoration_star.png"),     # 第1名：星星
                    os.path.join(plugin_dir, "decorations", "decoration_sparkle.png"),  # 第2名：闪光
                    os.path.join(plugin_dir, "decorations", "decoration_heart.png"),    # 第3名：爱心
                    os.path.join(plugin_dir, "decorations", "decoration_bubble.png"),   # 第4名：气泡
                ]

                icon_path = deco_icons[idx] if idx < len(deco_icons) else deco_icons[0]
                icon_x = content_x
                icon_y = content_y - 5

                if os.path.exists(icon_path):
                    try:
                        icon_img = Image.open(icon_path).convert("RGBA")
                        icon_w, icon_h = icon_img.size
                        icon_scale = min(35 / icon_w, 35 / icon_h, 1.0)
                        icon_new_w, icon_new_h = int(icon_w * icon_scale), int(icon_h * icon_scale)
                        if icon_scale < 1.0:
                            icon_img = icon_img.resize((icon_new_w, icon_new_h), Image.Resampling.LANCZOS)

                        # 添加柔和光晕
                        glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                        for offset in range(10, 0, -2):
                            alpha = int(30 * (10 - offset) / 10)
                            glow_temp = Image.new('RGBA', (icon_new_w + offset * 2, icon_new_h + offset * 2), (0, 0, 0, 0))
                            glow_temp.paste(icon_img, (offset, offset), icon_img)
                            color_layer = Image.new('RGBA', glow_temp.size, border_color + (alpha,))
                            glow_temp = Image.alpha_composite(glow_temp, color_layer)
                            glow_layer.paste(glow_temp, (icon_x - offset, icon_y - offset), glow_temp)

                        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=5))
                        img = Image.alpha_composite(img, glow_layer)

                        # 粘贴图标
                        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                        overlay.paste(icon_img, (icon_x, icon_y), icon_img)
                        img = Image.alpha_composite(img, overlay)

                        content_x += icon_new_w + 15  # 图标后留空隙
                    except Exception as e:
                        logger.error(f"添加装饰图标失败: {e}")

                # 2. 绘制群称号徽章
                title_bbox = font_subtitle.getbbox(title_text)
                title_w = title_bbox[2] - title_bbox[0]
                badge_w = title_w + 30
                badge_h = title_line_height + 16
                badge_x = content_x
                badge_y = content_y - 3

                img = SummaryImageGenerator._draw_gradient_badge(
                    img,
                    (badge_x, badge_y),
                    (badge_w, badge_h),
                    title_text,
                    font_subtitle,
                    grad_start,
                    grad_end
                )

                # 3. 绘制群友名称
                text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)

                name_x = badge_x + badge_w + 20
                name_y = content_y

                # 群友名称（加粗效果）
                for offset_x in [0, 1]:
                    for offset_y in [0, 1]:
                        text_draw.text(
                            (name_x + offset_x, name_y + offset_y),
                            name,
                            fill=SummaryImageGenerator.TITLE_COLOR,
                            font=font_subtitle
                        )

                # 4. 第二行：理由
                reason_y = content_y + title_line_height + 25
                reason_x = card_x + SummaryImageGenerator.CARD_PADDING
                for line in reason_lines:
                    SummaryImageGenerator._draw_text_with_shadow(
                        text_draw,
                        (reason_x, reason_y),
                        line,
                        font_small,
                        SummaryImageGenerator.LIGHT_TEXT_COLOR,
                        shadow_offset=1
                    )
                    reason_y += reason_line_height + 8

                img = Image.alpha_composite(img, text_layer)

                y += card_height + SummaryImageGenerator.CARD_SPACING

            y += 30

        # ===== 金句区域 =====
        if golden_quotes:
            # 标题
            section_title = "群圣经"
            title_bbox = font_section_title.getbbox(section_title)
            section_title_width = title_bbox[2] - title_bbox[0]
            section_title_x = (width - section_title_width) // 2

            # 彩色描边标题
            img = SummaryImageGenerator._draw_colorful_text(
                img,
                (section_title_x, y + 30),
                section_title,
                font_section_title,
                SummaryImageGenerator.TITLE_COLOR,
                outline_color=SummaryImageGenerator.BORDER_ORANGE,
                shadow_radius=8
            )

            # 添加decoration4装饰（金句区域）
            deco4_path = os.path.join(plugin_dir, "decorations", "decoration4.png")
            img = SummaryImageGenerator._add_decoration_with_glow(
                img,
                deco4_path,
                (section_title_x - 150, y + 10),
                (120, 120),
                SummaryImageGenerator.BORDER_ORANGE
            )

            # 右侧镜像
            if os.path.exists(deco4_path):
                try:
                    deco4_img = Image.open(deco4_path).convert("RGBA")
                    w, h = deco4_img.size
                    scale = min(120 / w, 120 / h, 1.0)
                    new_w, new_h = int(w * scale), int(h * scale)
                    if scale < 1.0:
                        deco4_img = deco4_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    deco4_flipped = deco4_img.transpose(Image.FLIP_LEFT_RIGHT)
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    paste_x = section_title_x + section_title_width + 30
                    paste_y = y + 10

                    # 添加柔和光晕
                    glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    for offset in range(15, 0, -2):
                        alpha = int(40 * (15 - offset) / 15)
                        glow_temp = Image.new('RGBA', (new_w + offset * 2, new_h + offset * 2), (0, 0, 0, 0))
                        glow_temp.paste(deco4_flipped, (offset, offset), deco4_flipped)
                        color_layer = Image.new('RGBA', glow_temp.size, SummaryImageGenerator.BORDER_ORANGE + (alpha,))
                        glow_temp = Image.alpha_composite(glow_temp, color_layer)
                        glow_layer.paste(glow_temp, (paste_x - offset, paste_y - offset), glow_temp)

                    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=8))
                    img = Image.alpha_composite(img, glow_layer)

                    overlay.paste(deco4_flipped, (paste_x, paste_y), deco4_flipped)
                    img = Image.alpha_composite(img, overlay)
                except Exception as e:
                    logger.error(f"添加镜像decoration4失败: {e}")

            # 添加引号装饰
            quote_deco_path = os.path.join(plugin_dir, "decorations", "decoration_quote.png")
            img = SummaryImageGenerator._add_decoration_with_glow(
                img,
                quote_deco_path,
                (section_title_x - 80, y + 35),
                (50, 50),
                SummaryImageGenerator.BORDER_ORANGE
            )

            y += 150

            # 金句卡片
            for idx, quote_item in enumerate(golden_quotes[:4]):
                content = quote_item.get("content", "")
                sender = quote_item.get("sender", "")
                reason = quote_item.get("reason", "")

                # 计算高度
                content_x = card_x + SummaryImageGenerator.CARD_PADDING
                max_quote_width = card_width - SummaryImageGenerator.CARD_PADDING * 2
                quote_text = f'"{content}"'
                quote_lines = SummaryImageGenerator._wrap_text(quote_text, max_quote_width, font_text)
                reason_lines = SummaryImageGenerator._wrap_text(reason, max_quote_width, font_small)

                quote_line_height = font_text.getbbox('测试')[3] - font_text.getbbox('测试')[1]
                reason_line_height = font_small.getbbox('测试')[3] - font_small.getbbox('测试')[1]

                card_height = 50 + len(quote_lines) * (quote_line_height + 12) + 50 + len(reason_lines) * (reason_line_height + 8) + 40
                card_height = max(card_height, 200)

                # 彩色卡片
                img = SummaryImageGenerator._draw_colorful_card(
                    img,
                    (card_x, y, card_x + card_width, y + card_height),
                    SummaryImageGenerator.BORDER_PINK,
                    radius=25,
                    shadow_strength=15
                )

                # 添加心形装饰
                heart_path = os.path.join(plugin_dir, "decorations", "decoration_heart.png")
                img = SummaryImageGenerator._add_decoration_with_glow(
                    img,
                    heart_path,
                    (card_x + card_width - 70, y + 20),
                    (45, 45),
                    SummaryImageGenerator.BORDER_PINK
                )

                # 金句内容
                text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)

                content_y = y + 35
                for line in quote_lines:
                    SummaryImageGenerator._draw_text_with_shadow(
                        text_draw,
                        (content_x, content_y),
                        line,
                        font_text,
                        SummaryImageGenerator.TEXT_COLOR,
                        shadow_offset=2
                    )
                    content_y += quote_line_height + 12

                # 发言人
                sender_y = content_y + 20
                sender_text = f"—— {sender}"
                SummaryImageGenerator._draw_text_with_shadow(
                    text_draw,
                    (content_x, sender_y),
                    sender_text,
                    font_small,
                    SummaryImageGenerator.HIGHLIGHT_COLOR,
                    shadow_offset=2
                )

                # 理由
                reason_y = sender_y + 40
                for line in reason_lines:
                    SummaryImageGenerator._draw_text_with_shadow(
                        text_draw,
                        (content_x, reason_y),
                        line,
                        font_small,
                        SummaryImageGenerator.LIGHT_TEXT_COLOR,
                        shadow_offset=1
                    )
                    reason_y += reason_line_height + 8

                img = Image.alpha_composite(img, text_layer)

                y += card_height + SummaryImageGenerator.CARD_SPACING

        # ===== 底部装饰 =====
        y += 50

        # 添加decoration2作为底部大型装饰
        deco2_path = os.path.join(plugin_dir, "decorations", "decoration2.png")
        if os.path.exists(deco2_path):
            try:
                deco2_img = Image.open(deco2_path).convert("RGBA")
                w, h = deco2_img.size
                # 确保完整显示，调整最大尺寸
                scale = min(300 / w, 180 / h, 1.0)
                new_w, new_h = int(w * scale), int(h * scale)
                if scale < 1.0:
                    deco2_img = deco2_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                paste_x = (width - new_w) // 2
                paste_y = y + 20

                img = SummaryImageGenerator._add_decoration_with_glow(
                    img,
                    deco2_path,
                    (paste_x, paste_y),
                    (new_w, new_h),
                    SummaryImageGenerator.BORDER_PURPLE
                )
            except Exception as e:
                logger.error(f"添加decoration2失败: {e}")

        # 添加气泡装饰
        bubble_path = os.path.join(plugin_dir, "decorations", "decoration_bubble.png")
        bubble_positions = [
            (120, y + 20),
            (width - 170, y + 30),
            (180, y + 100),
            (width - 230, y + 110),
        ]
        for pos in bubble_positions:
            img = SummaryImageGenerator._add_decoration_with_glow(
                img,
                bubble_path,
                pos,
                (60, 60),
                SummaryImageGenerator.BORDER_BLUE
            )

        # 转换为RGB并保存到项目 images 目录
        img = img.convert('RGB')

        # 创建临时文件，保存到项目的 data/images 目录
        try:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 向上三级到达 MaiBot 目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            images_dir = os.path.join(project_root, "data", "images")

            # 确保目录存在
            os.makedirs(images_dir, exist_ok=True)

            # 生成唯一文件名
            import uuid
            filename = f"summary_{uuid.uuid4().hex[:8]}.png"
            img_path = os.path.join(images_dir, filename)

            # 保存图片
            img.save(img_path, format='PNG', quality=95)
            return img_path
        except Exception as e:
            logger.error(f"保存图片失败: {e}", exc_info=True)
            raise
