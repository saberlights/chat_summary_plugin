"""
创建装饰元素的脚本
"""
from PIL import Image, ImageDraw
import os

def create_star_decoration():
    """创建星星装饰"""
    size = 100
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 五角星
    center = size // 2
    outer_r = 40
    inner_r = 16

    import math
    points = []
    for i in range(10):
        angle = math.pi / 2 + (2 * math.pi * i / 10)
        r = outer_r if i % 2 == 0 else inner_r
        x = center + r * math.cos(angle)
        y = center - r * math.sin(angle)
        points.append((x, y))

    # 渐变色星星
    draw.polygon(points, fill=(255, 215, 0, 255))  # 金色

    # 添加高光
    smaller_points = []
    for i in range(10):
        angle = math.pi / 2 + (2 * math.pi * i / 10)
        r = (outer_r * 0.6) if i % 2 == 0 else (inner_r * 0.6)
        x = center + r * math.cos(angle)
        y = center - 5 - r * math.sin(angle)
        smaller_points.append((x, y))
    draw.polygon(smaller_points, fill=(255, 255, 200, 200))

    return img

def create_sparkle_decoration():
    """创建闪光装饰"""
    size = 80
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size // 2

    # 四芒星形状的闪光
    # 横线
    draw.line([(10, center), (size-10, center)], fill=(255, 255, 255, 220), width=4)
    # 竖线
    draw.line([(center, 10), (center, size-10)], fill=(255, 255, 255, 220), width=4)

    # 中心圆点
    draw.ellipse([center-8, center-8, center+8, center+8], fill=(255, 255, 255, 255))

    return img

def create_bubble_decoration():
    """创建气泡装饰"""
    size = 120
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 三个不同大小的圆形气泡
    bubbles = [
        (30, 40, 50, (200, 230, 255, 180)),
        (70, 25, 35, (220, 240, 255, 160)),
        (55, 70, 25, (210, 235, 255, 150))
    ]

    for x, y, r, color in bubbles:
        # 气泡外圈
        draw.ellipse([x-r, y-r, x+r, y+r], fill=color)
        # 高光
        draw.ellipse([x-r//3, y-r//3, x+r//4, y+r//4], fill=(255, 255, 255, 200))

    return img

def create_corner_decoration():
    """创建卡片角落装饰"""
    size = 80
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 弧形线条装饰
    color = (102, 126, 234, 150)  # 淡蓝紫色

    # 三条弧线
    for i in range(3):
        offset = i * 8
        draw.arc([offset, offset, size-offset, size-offset],
                 start=180, end=270, fill=color, width=3)

    return img

def create_quote_decoration():
    """创建引号装饰"""
    size = 100
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 左引号
    color = (147, 112, 219, 200)  # 紫色

    # 第一个引号
    points1 = [(20, 30), (35, 30), (35, 50), (20, 60)]
    draw.polygon(points1, fill=color)

    # 第二个引号
    points2 = [(45, 30), (60, 30), (60, 50), (45, 60)]
    draw.polygon(points2, fill=color)

    return img

def create_heart_decoration():
    """创建爱心装饰"""
    size = 100
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 粉色爱心
    color = (255, 105, 180, 200)

    center_x, center_y = size // 2, size // 2

    # 上半部分两个圆
    draw.ellipse([center_x-25, center_y-20, center_x, center_y+5], fill=color)
    draw.ellipse([center_x, center_y-20, center_x+25, center_y+5], fill=color)

    # 下半部分三角形
    points = [(center_x-25, center_y-5), (center_x+25, center_y-5), (center_x, center_y+25)]
    draw.polygon(points, fill=color)

    # 高光
    draw.ellipse([center_x-15, center_y-12, center_x-8, center_y-5],
                 fill=(255, 255, 255, 150))

    return img

def main():
    """生成所有装饰图片"""
    output_dir = "/root/maimai/MaiBot/plugins/chat_summary_plugin"

    decorations = {
        "decoration_star.png": create_star_decoration(),
        "decoration_sparkle.png": create_sparkle_decoration(),
        "decoration_bubble.png": create_bubble_decoration(),
        "decoration_corner.png": create_corner_decoration(),
        "decoration_quote.png": create_quote_decoration(),
        "decoration_heart.png": create_heart_decoration(),
    }

    for filename, img in decorations.items():
        filepath = os.path.join(output_dir, filename)
        img.save(filepath, "PNG")
        print(f"✓ 已创建: {filename}")

    print(f"\n共创建 {len(decorations)} 个装饰元素")

if __name__ == "__main__":
    main()
