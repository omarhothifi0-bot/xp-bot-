import sqlite3
import math
from datetime import datetime
from typing import Dict, Any, List, Tuple

DB_PATH = "xp_database.db"


def get_current_month_key() -> str:
    """يرجع مفتاح الشهر الحالي بصيغة YYYY-MM لتصفير توب الشهر تلقائياً كل شهر جديد."""
    now = datetime.utcnow()
    return f"{now.year:04d}-{now.month:02d}"


def calculate_level_info(xp: int) -> Tuple[int, int, int, float]:
    """
    حساب اللفل ونسبة التقدم للفل القادم بناءً على مجموع الـ XP.
    المعادلة متدرجة:
    Level 1 -> يحتاج 100 XP
    Level 2 -> يحتاج 350 XP
    Level 7 -> حوالي 10,000 - 13,000 XP (مطابق للصورة المرفقة)
    يرجع: (level, current_level_xp, next_level_xp, progress_ratio_0_to_1)
    """
    if xp <= 0:
        return 0, 0, 100, 0.0

    def total_xp_for_level(lvl: int) -> int:
        if lvl <= 0:
            return 0
        # معادلة متدرجة دقيقة مطابقة لنظام الـ ID المرفق
        return int(82 * (lvl ** 2.42))

    lvl = 0
    while total_xp_for_level(lvl + 1) <= xp:
        lvl += 1

    start_xp = total_xp_for_level(lvl)
    next_xp = total_xp_for_level(lvl + 1)
    needed = max(1, next_xp - start_xp)
    current_in_lvl = max(0, xp - start_xp)
    progress = min(1.0, max(0.08, current_in_lvl / needed))
    return lvl, current_in_lvl, needed, progress


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    chat_xp INTEGER DEFAULT 0,
                    monthly_chat_xp INTEGER DEFAULT 0,
                    inpublic_count INTEGER DEFAULT 0,
                    voice_deafen_xp INTEGER DEFAULT 0,
                    voice_undeafen_xp INTEGER DEFAULT 0,
                    monthly_voice_xp INTEGER DEFAULT 0,
                    invites_count INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
        self.check_monthly_reset()

    def check_monthly_reset(self) -> None:
        """يتحقق إذا دخلنا بشهر جديد، وإذا نعم يصفر نقاط الشهر فقط ويحافظ على النقاط الكاملة."""
        current_month = get_current_month_key()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM metadata WHERE key = 'active_month'"
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO metadata (key, value) VALUES ('active_month', ?)",
                    (current_month,),
                )
                conn.commit()
            elif row["value"] != current_month:
                conn.execute(
                    "UPDATE users SET monthly_chat_xp = 0, monthly_voice_xp = 0"
                )
                conn.execute(
                    "UPDATE metadata SET value = ? WHERE key = 'active_month'",
                    (current_month,),
                )
                conn.commit()

    def _ensure_user(self, conn: sqlite3.Connection, guild_id: int, user_id: int) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (guild_id, user_id)
            VALUES (?, ?)
            """,
            (guild_id, user_id),
        )

    def add_chat_message(
        self, guild_id: int, user_id: int, xp_gain: int, is_public: bool = True
    ) -> Tuple[int, int]:
        """
        يضيف رسالة ونقاط شات للعضو.
        يرجع (old_level, new_level) لمعرفة إذا ارتفع لفل العضو.
        """
        self.check_monthly_reset()
        with self._get_conn() as conn:
            self._ensure_user(conn, guild_id, user_id)
            row = conn.execute(
                "SELECT chat_xp FROM users WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ).fetchone()
            old_xp = row["chat_xp"] if row else 0
            old_lvl = calculate_level_info(old_xp)[0]

            inpublic_inc = 1 if is_public else 0
            conn.execute(
                """
                UPDATE users
                SET chat_xp = chat_xp + ?,
                    monthly_chat_xp = monthly_chat_xp + ?,
                    inpublic_count = inpublic_count + ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (xp_gain, xp_gain, inpublic_inc, guild_id, user_id),
            )
            conn.commit()

            new_xp = old_xp + xp_gain
            new_lvl = calculate_level_info(new_xp)[0]
            return old_lvl, new_lvl

    def add_voice_xp(
        self, guild_id: int, user_id: int, xp_gain: int, is_deafened: bool
    ) -> Tuple[int, int]:
        """
        يضيف نقاط الفويس (إما في خانة deafen أو undeafen حسب حالة العضو).
        يرجع (old_level, new_level).
        """
        if xp_gain <= 0:
            return 0, 0
        self.check_monthly_reset()
        with self._get_conn() as conn:
            self._ensure_user(conn, guild_id, user_id)
            row = conn.execute(
                """
                SELECT voice_deafen_xp, voice_undeafen_xp
                FROM users WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id),
            ).fetchone()
            old_total = (
                (row["voice_deafen_xp"] + row["voice_undeafen_xp"]) if row else 0
            )
            old_lvl = calculate_level_info(old_total)[0]

            if is_deafened:
                conn.execute(
                    """
                    UPDATE users
                    SET voice_deafen_xp = voice_deafen_xp + ?,
                        monthly_voice_xp = monthly_voice_xp + ?
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (xp_gain, xp_gain, guild_id, user_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE users
                    SET voice_undeafen_xp = voice_undeafen_xp + ?,
                        monthly_voice_xp = monthly_voice_xp + ?
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (xp_gain, xp_gain, guild_id, user_id),
                )
            conn.commit()

            new_total = old_total + xp_gain
            new_lvl = calculate_level_info(new_total)[0]
            return old_lvl, new_lvl

    def set_invites(self, guild_id: int, user_id: int, invites_count: int) -> None:
        with self._get_conn() as conn:
            self._ensure_user(conn, guild_id, user_id)
            conn.execute(
                """
                UPDATE users SET invites_count = ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (max(0, invites_count), guild_id, user_id),
            )
            conn.commit()

    def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        self.check_monthly_reset()
        with self._get_conn() as conn:
            self._ensure_user(conn, guild_id, user_id)
            row = conn.execute(
                "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            ).fetchone()

        chat_xp = row["chat_xp"] if row else 0
        deafen_xp = row["voice_deafen_xp"] if row else 0
        undeafen_xp = row["voice_undeafen_xp"] if row else 0
        voice_xp = deafen_xp + undeafen_xp

        chat_lvl, _, _, chat_prog = calculate_level_info(chat_xp)
        voice_lvl, _, _, voice_prog = calculate_level_info(voice_xp)

        return {
            "user_id": user_id,
            "invites": row["invites_count"] if row else 0,
            "inpublic": row["inpublic_count"] if row else 0,
            "deafen": deafen_xp,
            "undeafen": undeafen_xp,
            "voice_xp": voice_xp,
            "voice_lvl": voice_lvl,
            "voice_progress": voice_prog,
            "chat_xp": chat_xp,
            "chat_lvl": chat_lvl,
            "chat_progress": chat_prog,
            "monthly_chat_xp": row["monthly_chat_xp"] if row else 0,
            "monthly_voice_xp": row["monthly_voice_xp"] if row else 0,
        }

    def get_leaderboard(
        self, guild_id: int, category: str = "chat", monthly: bool = False, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        category: 'chat' أو 'voice'
        monthly: True لتوب الشهر، False للتوب الكامل
        """
        self.check_monthly_reset()
        if category == "chat":
            order_col = "monthly_chat_xp" if monthly else "chat_xp"
            expr = order_col
        else:
            order_col = (
                "monthly_voice_xp"
                if monthly
                else "(voice_deafen_xp + voice_undeafen_xp)"
            )
            expr = order_col

        query = f"""
            SELECT user_id,
                   chat_xp,
                   monthly_chat_xp,
                   inpublic_count,
                   voice_deafen_xp,
                   voice_undeafen_xp,
                   (voice_deafen_xp + voice_undeafen_xp) AS total_voice_xp,
                   monthly_voice_xp,
                   {expr} AS score
            FROM users
            WHERE guild_id = ? AND {expr} > 0
            ORDER BY score DESC
            LIMIT ?
        """
        with self._get_conn() as conn:
            rows = conn.execute(query, (guild_id, limit)).fetchall()
        return [dict(r) for r in rows]
