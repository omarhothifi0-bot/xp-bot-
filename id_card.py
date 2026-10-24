import io
import math
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """تحميل خط واضح ومرتب مع بدائل تلقائية لأي نظام تشغيل."""
    candidates = (
        [
            "/usr/share/fonts/truetype/inter/Inter-SemiBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "segoeui.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
            "segoeui.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_background(width: int, height: int) -> Image.Image:
    """
    يرسم خلفية البطاقة بنفس أسلوب الصورة المرفقة:
    - تدرج كحلي/رمادي مزرق هادئ
    - أشكال هندسية وجبال وقمر وخطوط موجية ناعمة بالخلفية
    - زاوية مقصوصة انسيابية في أعلى اليمين وإطار خارجي ناعم
    """
    bg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    art = Image.new("RGBA", (width, height), (72, 79, 106, 255))
    draw = ImageDraw.Draw(art)

    # تدرج لوني خفيف للخلفية
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(76 * (1 - t) + 58 * t)
        g = int(83 * (1 - t) + 65 * t)
        b = int(112 * (1 - t) + 88 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # دوائر/كواكب خفيفة بالخلفية
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # دائرة القمر في الأعلى يسار المنتصف
    odraw.ellipse((395, 22, 470, 97), fill=(95, 102, 130, 95))
    # قوس كبير أعلى اليمين
    odraw.ellipse((680, -140, 1020, 170), fill=(88, 95, 124, 70))

    # مثلثات هندسية ناعمة باليمين
    odraw.polygon([(665, 110), (770, 50), (735, 185)], fill=(52, 58, 78, 95))
    odraw.polygon([(805, 130), (925, 165), (845, 260)], fill=(96, 105, 135, 80))

    # جبال في الأسفل
    odraw.polygon(
        [(130, height), (245, 235), (365, height)], fill=(50, 56, 75, 150)
    )
    odraw.polygon(
        [(380, height), (510, 215), (650, height)], fill=(54, 61, 82, 145)
    )
    odraw.polygon(
        [(460, height), (545, 255), (630, height)], fill=(86, 95, 120, 110)
    )

    # خطوط موجية رفيعة مثل التصميم الأصلي
    for offset in range(0, 70, 8):
        pts = []
        for x in range(180, 680, 10):
            y = int(185 + offset * 0.7 + 28 * math.sin((x - 180) / 75.0))
            pts.append((x, y))
        odraw.line(pts, fill=(108, 116, 146, 48), width=2)

    # شكل هندسي مضلع أعلى اليمين عند الحافة المقصوصة
    odraw.polygon(
        [(990, 92), (1094, 92), (1094, 154), (1025, 154)],
        fill=(145, 156, 196, 140),
        outline=(185, 196, 230, 180),
    )

    art = Image.alpha_composite(art, overlay)

    # قناع الحواف الدائرية مع القص الانسيابي أعلى اليمين (نفس شكل الصورة بالضبط)
    mask = Image.new("L", (width, height), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle((4, 4, width - 4, height - 4), radius=36, fill=255)

    # قص الزاوية العلوية اليمنى بشكل منحني أنيق
    mdraw.pieslice((width - 210, -110, width + 110, 115), 0, 360, fill=0)
    mdraw.rectangle((width - 105, 0, width, 60), fill=0)

    # تطبيق القناع
    card = Image.new("RGBA", (width, height), (47, 49, 54, 255))
    card.paste(art, (0, 0), mask)

    # رسم إطار خارجي ناعم يتبع حدود البطاقة
    edge = mask.filter(ImageFilter.FIND_EDGES)
    edge_rgba = Image.new("RGBA", (width, height), (125, 134, 166, 180))
    card.paste(edge_rgba, (0, 0), edge)

    return card


def _draw_mic_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color=(20, 24, 33, 255)):
    """يرسم أيقونة المايكروفون بنفس ستايل الصورة."""
    # جسم المايك الكبسولي
    draw.rounded_rectangle((x + 14, y + 4, x + 38, y + 44), radius=12, fill=color)
    # خطوط المايك الجانبية لتفاصيل أجمل
    for ly in (y + 15, y + 23, y + 31):
        draw.line([(x + 14, ly), (x + 22, ly)], fill=(95, 103, 128, 255), width=3)
        draw.line([(x + 30, ly), (x + 38, ly)], fill=(95, 103, 128, 255), width=3)
    # القوس الحامل حول المايك
    draw.arc((x + 6, y + 18, x + 46, y + 54), start=0, end=180, fill=color, width=5)
    # العمود والقاعدة
    draw.line([(x + 26, y + 54), (x + 26, y + 66)], fill=color, width=5)
    draw.line([(x + 12, y + 66), (x + 40, y + 66)], fill=color, width=5)


def _draw_chat_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color=(20, 24, 33, 255)):
    """يرسم أيقونة الشات (فقاعة الرسائل) بنفس ستايل الصورة."""
    draw.rounded_rectangle((x + 4, y + 10, x + 48, y + 46), radius=8, fill=color)
    # ذيل فقاعة الرسالة
    draw.polygon([(x + 12, y + 45), (x + 10, y + 58), (x + 25, y + 45)], fill=color)
    # سطور داخل الفقاعة
    draw.line([(x + 13, y + 23), (x + 39, y + 23)], fill=(95, 103, 128, 255), width=4)
    draw.line([(x + 13, y + 33), (x + 31, y + 33)], fill=(95, 103, 128, 255), width=4)


def generate_id_card(
    username: str,
    stats: Dict[str, Any],
    avatar_bytes: Optional[bytes] = None,
) -> io.BytesIO:
    """
    ينشئ صورة بطاقة الـ -id بدقة عالية (1094x404) مطابقة للصورة المرفقة.
    """
    W, H = 1094, 404
    card = _draw_background(W, H)
    draw = ImageDraw.Draw(card)

    font_label = _load_font(22, bold=False)
    font_box_val = _load_font(31, bold=False)
    font_user = _load_font(29, bold=False)
    font_lvl = _load_font(34, bold=False)
    font_ex = _load_font(23, bold=False)

    # ==========================================================
    # 1. المربعات الأربعة على اليسار (invites, inpublic, deafen, undeafen)
    # ==========================================================
    left_items = [
        ("invites", str(stats.get("invites", 0))),
        ("inpublic", str(stats.get("inpublic", 0))),
        ("deafen", str(stats.get("deafen", 0))),
        ("undeafen", str(stats.get("undeafen", 0))),
    ]

    box_x1, box_x2 = 22, 168
    box_w = box_x2 - box_x1
    box_h = 56
    start_y = 32
    gap_y = 92

    for idx, (label, val) in enumerate(left_items):
        by1 = start_y + idx * gap_y
        by2 = by1 + box_h

        # النص فوق المربع
        l_bbox = draw.textbbox((0, 0), label, font=font_label)
        lw = l_bbox[2] - l_bbox[0]
        draw.text(
            (box_x1 + (box_w - lw) / 2, by1 - 26),
            label,
            font=font_label,
            fill=(212, 216, 228, 255),
        )

        # المربع الغامق مع الإطار الخفيف
        draw.rectangle(
            (box_x1, by1, box_x2, by2),
            fill=(38, 42, 60, 235),
            outline=(118, 124, 148, 210),
            width=2,
        )

        # الرقم داخل المربع
        v_bbox = draw.textbbox((0, 0), val, font=font_box_val)
        vw = v_bbox[2] - v_bbox[0]
        vh = v_bbox[3] - v_bbox[1]
        draw.text(
            (box_x1 + (box_w - vw) / 2, by1 + (box_h - vh) / 2 - 4),
            val,
            font=font_box_val,
            fill=(242, 244, 250, 255),
        )

    # ==========================================================
    # 2. صورة العضو الدائرية (Avatar) والكبسولة تحتها بالمنتصف
    # ==========================================================
    av_size = 204
    av_x, av_y = 258, 92

    if avatar_bytes:
        try:
            av_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            av_img = av_img.resize((av_size, av_size), Image.Resampling.LANCZOS)
        except Exception:
            av_img = _create_default_avatar(av_size)
    else:
        av_img = _create_default_avatar(av_size)

    # قناع دائري للصورة الشخصية
    av_mask = Image.new("L", (av_size, av_size), 0)
    ImageDraw.Draw(av_mask).ellipse((0, 0, av_size - 1, av_size - 1), fill=255)
    card.paste(av_img, (av_x, av_y), av_mask)

    # إطار دائري أبيض/فضي رفيع حول الصورة الشخصية
    draw.ellipse(
        (av_x - 2, av_y - 2, av_x + av_size + 1, av_y + av_size + 1),
        outline=(215, 220, 232, 230),
        width=3,
    )

    # كبسولة اسم المستخدم تحت الصورة
    pill_w, pill_h = 186, 40
    pill_x = av_x + (av_size - pill_w) // 2
    pill_y = av_y + av_size + 16
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=16,
        fill=(32, 37, 48, 240),
    )

    display_name = username if len(username) <= 14 else username[:12] + ".."
    u_bbox = draw.textbbox((0, 0), display_name, font=font_user)
    uw = u_bbox[2] - u_bbox[0]
    uh = u_bbox[3] - u_bbox[1]
    draw.text(
        (pill_x + (pill_w - uw) / 2, pill_y + (pill_h - uh) / 2 - 4),
        display_name,
        font=font_user,
        fill=(242, 245, 250, 255),
    )

    # ==========================================================
    # 3. أشرطة لفل الفويس ولفل الشات على اليمين
    # ==========================================================
    bar_x1, bar_x2 = 755, 1066
    bar_w = bar_x2 - bar_x1
    bar_h = 46

    # --- أولاً: قسم الفويس ---
    v_bar_y = 212
    _draw_mic_icon(draw, x=696, y=v_bar_y - 18)

    voice_lvl_str = f"{stats.get('voice_lvl', 0)} lvl"
    voice_ex_str = f"ex: {stats.get('voice_xp', 0)}"
    draw.text(
        (bar_x1 + 10, v_bar_y - 42),
        voice_lvl_str,
        font=font_lvl,
        fill=(235, 238, 245, 255),
    )
    vex_bbox = draw.textbbox((0, 0), voice_ex_str, font=font_ex)
    vex_w = vex_bbox[2] - vex_bbox[0]
    draw.text(
        (bar_x2 - vex_w - 6, v_bar_y - 32),
        voice_ex_str,
        font=font_ex,
        fill=(220, 225, 236, 255),
    )

    # الخلفية الغامقة لشريط الفويس
    draw.rounded_rectangle(
        (bar_x1, v_bar_y, bar_x2, v_bar_y + bar_h),
        radius=16,
        fill=(30, 35, 45, 245),
    )
    # التعبئة الفاتحة لشريط الفويس
    v_prog = float(stats.get("voice_progress", 0.0))
    if stats.get("voice_xp", 0) > 0:
        fill_w = max(48, int(bar_w * min(1.0, max(0.15, v_prog))))
        rad = min(18, fill_w // 3)
        draw.rounded_rectangle(
            (bar_x1, v_bar_y, bar_x1 + fill_w, v_bar_y + bar_h),
            radius=rad,
            fill=(124, 132, 152, 255),
        )

    # --- ثانياً: قسم الشات ---
    c_bar_y = 314
    _draw_chat_icon(draw, x=694, y=c_bar_y - 8)

    chat_lvl_str = f"{stats.get('chat_lvl', 0)} lvl"
    chat_ex_str = f"ex: {stats.get('chat_xp', 0)}"
    draw.text(
        (bar_x1 + 10, c_bar_y - 42),
        chat_lvl_str,
        font=font_lvl,
        fill=(235, 238, 245, 255),
    )
    cex_bbox = draw.textbbox((0, 0), chat_ex_str, font=font_ex)
    cex_w = cex_bbox[2] - cex_bbox[0]
    draw.text(
        (bar_x2 - cex_w - 6, c_bar_y - 32),
        chat_ex_str,
        font=font_ex,
        fill=(220, 225, 236, 255),
    )

    # الخلفية الغامقة لشريط الشات
    draw.rounded_rectangle(
        (bar_x1, c_bar_y, bar_x2, c_bar_y + bar_h),
        radius=16,
        fill=(30, 35, 45, 245),
    )
    # التعبئة الفاتحة لشريط الشات
    c_prog = float(stats.get("chat_progress", 0.0))
    if stats.get("chat_xp", 0) > 0:
        fill_w = max(48, int(bar_w * min(1.0, max(0.15, c_prog))))
        rad = min(18, fill_w // 3)
        draw.rounded_rectangle(
            (bar_x1, c_bar_y, bar_x1 + fill_w, c_bar_y + bar_h),
            radius=rad,
            fill=(124, 132, 152, 255),
        )

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    return output


def _create_default_avatar(size: int) -> Image.Image:
    """ينشئ صورة افتراضية أنيقة في حال عدم توفر صورة للعضو."""
    img = Image.new("RGBA", (size, size), (28, 30, 36, 255))
    d = ImageDraw.Draw(img)
    # رسم silhouette بسيط وراقي
    d.ellipse((size * 0.28, size * 0.16, size * 0.72, size * 0.60), fill=(160, 165, 178, 255))
    d.pieslice((size * 0.12, size * 0.58, size * 0.88, size * 1.25), 180, 360, fill=(160, 165, 178, 255))
    return img
