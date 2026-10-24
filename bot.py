import time
from typing import Dict, Optional
import aiohttp
import discord
from discord.ext import commands, tasks

import config
from database import Database, calculate_level_info
from id_card import generate_id_card

# تفعيل الـ Intents الضرورية لحساب الرسائل، الفويس، الأعضاء، والدعوات
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, help_command=None)
db = Database()

# كاش للكول داون بين الرسائل: {(guild_id, user_id): last_message_timestamp}
chat_cooldowns: Dict[tuple, float] = {}

# كاش الدعوات لمعرفة مين دعا كل عضو جديد: {guild_id: {invite_code: (inviter_id, uses)}}
invites_cache: Dict[int, Dict[str, tuple]] = {}


# =====================================================================
# دوال مساعدة للرتب التلقائية والدعوات
# =====================================================================
async def sync_guild_invites(guild: discord.Guild) -> None:
    """مزامنة دعوات السيرفر وحفظ مجموع دعوات كل عضو في قاعدة البيانات."""
    try:
        invites = await guild.invites()
    except discord.Forbidden:
        return
    except Exception:
        return

    guild_map = {}
    user_totals: Dict[int, int] = {}
    for inv in invites:
        if inv.inviter and not inv.inviter.bot:
            guild_map[inv.code] = (inv.inviter.id, inv.uses or 0)
            user_totals[inv.inviter.id] = user_totals.get(inv.inviter.id, 0) + (inv.uses or 0)

    invites_cache[guild.id] = guild_map
    for inviter_id, total_uses in user_totals.items():
        db.set_invites(guild.id, inviter_id, total_uses)


async def check_and_assign_level_roles(
    member: discord.Member, new_level: int, role_map: Dict[int, object], category_label: str
) -> Optional[discord.Role]:
    """يعطي العضو الرتبة التلقائية إذا وصل للفل المطلوب."""
    guild = member.guild
    granted_role = None

    for req_lvl, role_identifier in sorted(role_map.items()):
        if new_level >= req_lvl:
            role = None
            if isinstance(role_identifier, int):
                role = guild.get_role(role_identifier)
            elif isinstance(role_identifier, str):
                role = discord.utils.get(guild.roles, name=role_identifier)
                if role is None:
                    # إنشاء الرتبة تلقائياً إذا لم تكن موجودة وكان البوت يملك صلاحية Manage Roles
                    try:
                        role = await guild.create_role(
                            name=role_identifier,
                            color=discord.Color.from_rgb(114, 137, 218),
                            reason=f"رتبة تلقائية لنظام الـ XP ({category_label})",
                        )
                    except Exception:
                        role = None

            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"وصل إلى لفل {new_level} في {category_label}")
                    granted_role = role
                except Exception:
                    pass

    return granted_role


async def notify_level_up(
    member: discord.Member,
    new_level: int,
    category_ar: str,
    fallback_channel: Optional[discord.abc.Messageable] = None,
    granted_role: Optional[discord.Role] = None,
) -> None:
    """إرسال إشعار لطيف عند ارتفاع لفل العضو."""
    if not config.SEND_LEVEL_UP_MESSAGE:
        return

    target_channel = None
    if config.LEVEL_UP_CHANNEL_ID:
        target_channel = member.guild.get_channel(config.LEVEL_UP_CHANNEL_ID)
    if target_channel is None:
        target_channel = fallback_channel

    if target_channel is None:
        return

    role_text = f" وحصلت على رتبة {granted_role.mention} 🏅" if granted_role else ""
    try:
        await target_channel.send(
            f"🎉 كفو {member.mention}! ارتفع مستواك في **{category_ar}** إلى **Level {new_level}**{role_text}!"
        )
    except Exception:
        pass


# =====================================================================
# الأحداث (Events)
# =====================================================================
@bot.event
async def on_ready():
    print(f"✅ تم تسجيل دخول البوت بنجاح: {bot.user} (ID: {bot.user.id})")
    for guild in bot.guilds:
        await sync_guild_invites(guild)
    if not voice_xp_loop.is_running():
        voice_xp_loop.start()


@bot.event
async def on_invite_create(invite: discord.Invite):
    if invite.guild:
        await sync_guild_invites(invite.guild)


@bot.event
async def on_invite_delete(invite: discord.Invite):
    if invite.guild:
        await sync_guild_invites(invite.guild)


@bot.event
async def on_member_join(member: discord.Member):
    await sync_guild_invites(member.guild)


@bot.event
async def on_message(message: discord.Message):
    # تجاهل البوتات والرسائل الخاصة
    if message.author.bot or not message.guild:
        return

    # تنفيذ الأوامر أولاً إذا كانت الرسالة تبدأ بالـ Prefix
    if message.content.strip().startswith(config.PREFIX):
        await bot.process_commands(message)
        return

    guild_id = message.guild.id
    user_id = message.author.id
    now = time.time()

    # فحص ما إذا كان الروم ضمن الشات العام
    is_public = (
        True
        if not config.PUBLIC_CHANNEL_IDS
        else (message.channel.id in config.PUBLIC_CHANNEL_IDS)
    )

    # فحص الكول داون لمنع السبام
    key = (guild_id, user_id)
    last_time = chat_cooldowns.get(key, 0.0)
    if now - last_time >= config.CHAT_COOLDOWN_SECONDS:
        chat_cooldowns[key] = now
        old_lvl, new_lvl = db.add_chat_message(
            guild_id=guild_id,
            user_id=user_id,
            xp_gain=config.CHAT_XP_PER_MESSAGE,
            is_public=is_public,
        )
        if new_lvl > old_lvl and isinstance(message.author, discord.Member):
            role = await check_and_assign_level_roles(
                message.author, new_lvl, config.CHAT_LEVEL_ROLES, "الشات"
            )
            await notify_level_up(
                message.author, new_lvl, "الشات 💬", message.channel, role
            )
    else:
        # حتى لو كان داخل الكول داون، لو حبيت تحسب الرسالة كعدد فقط بدون XP يمكنك تفعيل السطر التالي:
        pass

    await bot.process_commands(message)


# =====================================================================
# مهمة حساب نقاط الفويس كل دقيقة (Voice XP Loop)
# =====================================================================
@tasks.loop(seconds=60)
async def voice_xp_loop():
    for guild in bot.guilds:
        afk_channel_id = guild.afk_channel.id if guild.afk_channel else None

        for vc in guild.voice_channels:
            if config.IGNORE_AFK_CHANNEL and afk_channel_id and vc.id == afk_channel_id:
                continue

            for member in vc.members:
                if member.bot or member.voice is None:
                    continue

                # فحص هل العضو عامل Deafen (لحاله self_deaf أو من السيرفر deaf)
                is_deaf = bool(member.voice.self_deaf or member.voice.deaf)
                xp_gain = (
                    config.VOICE_XP_PER_MINUTE_DEAFEN
                    if is_deaf
                    else config.VOICE_XP_PER_MINUTE_UNDEAFEN
                )

                old_lvl, new_lvl = db.add_voice_xp(
                    guild_id=guild.id,
                    user_id=member.id,
                    xp_gain=xp_gain,
                    is_deafened=is_deaf,
                )

                if new_lvl > old_lvl:
                    role = await check_and_assign_level_roles(
                        member, new_lvl, config.VOICE_LEVEL_ROLES, "الفويس"
                    )
                    await notify_level_up(member, new_lvl, "الفويس 🎙️", None, role)


# =====================================================================
# بناء الـ Embed والأزرار التفاعلية لأوامر التوب (-توب)
# =====================================================================
def build_top_embed(guild: discord.Guild, mode: str = "top5") -> discord.Embed:
    """
    mode:
      - 'top5'    -> -توب (توب 5 شات + توب 5 فويس)
      - 'month'   -> -توب شهر (توب الشهر للشات والفويس)
      - 'full'    -> -توب كامل (التوب الكامل لأعلى 10 بالشات والفويس)
    """
    if mode == "month":
        title = f"📅 متصدرين الشهر — {guild.name}"
        limit = 10
        monthly = True
    elif mode == "full":
        title = f"🏆 التوب الكامل (All-Time) — {guild.name}"
        limit = 10
        monthly = False
    else:
        title = f"✨ التوب 5 (الشات العام & الفويس) — {guild.name}"
        limit = 5
        monthly = False

    embed = discord.Embed(
        title=title,
        color=discord.Color.from_rgb(76, 84, 114),
    )

    chat_rows = db.get_leaderboard(guild.id, category="chat", monthly=monthly, limit=limit)
    voice_rows = db.get_leaderboard(guild.id, category="voice", monthly=monthly, limit=limit)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    # تنسيق قسم الشات
    if not chat_rows:
        chat_text = "لا يوجد بيانات شات بعد."
    else:
        lines = []
        for idx, r in enumerate(chat_rows, start=1):
            badge = medals.get(idx, f"`#{idx}`")
            lvl = calculate_level_info(r["chat_xp"])[0]
            xp_val = r["monthly_chat_xp"] if monthly else r["chat_xp"]
            lines.append(f"{badge} <@{r['user_id']}> — **Lvl {lvl}** (`{xp_val}` XP)")
        chat_text = "
".join(lines)

    # تنسيق قسم الفويس
    if not voice_rows:
        voice_text = "لا يوجد بيانات فويس بعد."
    else:
        lines = []
        for idx, r in enumerate(voice_rows, start=1):
            badge = medals.get(idx, f"`#{idx}`")
            lvl = calculate_level_info(r["total_voice_xp"])[0]
            xp_val = r["monthly_voice_xp"] if monthly else r["total_voice_xp"]
            lines.append(
                f"{badge} <@{r['user_id']}> — **Lvl {lvl}** (`{xp_val}` XP)"
            )
        voice_text = "
".join(lines)

    embed.add_field(name="💬 توب الشات العام", value=chat_text, inline=True)
    embed.add_field(name="🎙️ توب الفويس", value=voice_text, inline=True)
    embed.set_footer(text="استخدم الأزرار بالأسفل للتبديل بين التوب 5، توب الشهر، والتوب الكامل")
    return embed


class TopLeaderboardView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.guild = guild

    @discord.ui.button(label="التوب 5", emoji="✨", style=discord.ButtonStyle.primary)
    async def btn_top5(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_top_embed(self.guild, mode="top5")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="توب الشهر", emoji="📅", style=discord.ButtonStyle.secondary)
    async def btn_month(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_top_embed(self.guild, mode="month")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="التوب الكامل", emoji="🏆", style=discord.ButtonStyle.success)
    async def btn_full(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_top_embed(self.guild, mode="full")
        await interaction.response.edit_message(embed=embed, view=self)


# =====================================================================
# الأوامر (-id و -توب)
# =====================================================================
@bot.command(name="id", aliases=["ايدي", "ID", "هوية"])
async def cmd_id(ctx: commands.Context, member: Optional[discord.Member] = None):
    """
    أمر -id أو -id @mention
    يعرض بطاقة العضو المصممة بنفس شكل الصورة المرفقة تماماً.
    """
    target = member or ctx.author
    await sync_guild_invites(ctx.guild)
    stats = db.get_user_stats(ctx.guild.id, target.id)

    avatar_bytes = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(target.display_avatar.with_size(256).url) as resp:
                if resp.status == 200:
                    avatar_bytes = await resp.read()
    except Exception:
        avatar_bytes = None

    card_buffer = generate_id_card(
        username=target.name,
        stats=stats,
        avatar_bytes=avatar_bytes,
    )
    file = discord.File(fp=card_buffer, filename="id_card.png")
    await ctx.reply(file=file, mention_author=False)


@bot.command(name="توب", aliases=["top", "TOP"])
async def cmd_top(ctx: commands.Context, *, arg: str = ""):
    """
    يدعم:
    -توب        -> يعرض التوب 5 للشات العام والفويس
    -توب شهر    -> يعرض توب الشهر الحالي
    -توب كامل   -> يعرض التوب الكامل
    """
    clean_arg = arg.strip()
    if clean_arg in ("شهر", "الشهر", "month", "monthly"):
        mode = "month"
    elif clean_arg in ("كامل", "الكامل", "all", "full"):
        mode = "full"
    else:
        mode = "top5"

    embed = build_top_embed(ctx.guild, mode=mode)
    view = TopLeaderboardView(ctx.guild)
    await ctx.reply(embed=embed, view=view, mention_author=False)


if __name__ == "__main__":
    if config.BOT_TOKEN == "PUT_YOUR_TOKEN_HERE" or not config.BOT_TOKEN:
        print("⚠️ تنبيه: يرجى وضع توكن البوت في ملف .env أو داخل config.py قبل التشغيل!")
    else:
        bot.run(config.BOT_TOKEN)
