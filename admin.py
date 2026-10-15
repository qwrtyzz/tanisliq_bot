"""TindraVen admin commands for python-telegram-bot v22+.

Integration in bot.py:
    from admin import register_admin, notify_new_profile
    register_admin(app, DB)

After a user confirms their profile:
    await notify_new_profile(context, q.from_user.id, DB)

Set ADMIN_ID in Railway Variables. This module never registers public bot commands.
"""

import logging
import os
import sqlite3
from html import escape
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

log = logging.getLogger(__name__)


def _admin_id():
    try:
        return int(os.environ.get('ADMIN_ID', '0'))
    except ValueError:
        return 0


def _authorized(update: Update) -> bool:
    return bool(update.effective_user and _admin_id() and update.effective_user.id == _admin_id()
                and update.effective_chat and update.effective_chat.type == 'private')


def _connect(db_path):
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _has_table(conn, table):
    return conn.execute('SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?', ('table', table)).fetchone() is not None


def _columns(conn, table):
    return {row['name'] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def _count(conn, table, condition=None):
    if not _has_table(conn, table):
        return None
    sql = f'SELECT COUNT(*) FROM "{table}"'
    if condition:
        sql += ' WHERE ' + condition
    return conn.execute(sql).fetchone()[0]


def register_admin(app: Application, db_path):
    """Register protected admin handlers. Call after existing conversation handlers."""
    db_path = Path(db_path)

    async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _authorized(update):
            return
        await update.message.reply_text('🛡 TindraVen Admin\n\n/admin — Panel\n/stats — Statistika\n/users — Son profillər\n/reports — Şikayətlər')

    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _authorized(update):
            return
        try:
            with _connect(db_path) as conn:
                if not _has_table(conn, 'profiles'):
                    await update.message.reply_text('profiles cədvəli tapılmadı.')
                    return
                cols = _columns(conn, 'profiles')
                total = _count(conn, 'profiles', 'confirmed = 1') if 'confirmed' in cols else _count(conn, 'profiles')
                active = _count(conn, 'profiles', 'confirmed = 1 AND active = 1') if {'confirmed', 'active'} <= cols else None
                matches = _count(conn, 'matches')
                reports = _count(conn, 'reports')
            lines = ['📊 TindraVen statistikası', f'👤 Təsdiqlənmiş profillər: {total}']
            if active is not None:
                lines.append(f'🟢 Aktiv profillər: {active}')
            if matches is not None:
                lines.append(f'❤️ Match qeydləri: {matches}')
            if reports is not None:
                lines.append(f'🚩 Şikayət qeydləri: {reports}')
            await update.message.reply_text('\n'.join(lines))
        except sqlite3.Error:
            log.exception('Admin stats failed')
            await update.message.reply_text('Database oxunarkən xəta baş verdi. Railway Logs bölməsini yoxla.')

    async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _authorized(update):
            return
        try:
            with _connect(db_path) as conn:
                if not _has_table(conn, 'profiles'):
                    await update.message.reply_text('profiles cədvəli tapılmadı.')
                    return
                cols = _columns(conn, 'profiles')
                wanted = [x for x in ('user_id', 'name', 'age', 'city', 'language') if x in cols]
                if not wanted:
                    await update.message.reply_text('Profil sütunları uyğun deyil.')
                    return
                select = ', '.join('"' + x + '"' for x in wanted)
                order = 'user_id' if 'user_id' in cols else wanted[0]
                where = ' WHERE confirmed = 1' if 'confirmed' in cols else ''
                rows = conn.execute(f'SELECT {select} FROM profiles{where} ORDER BY "{order}" DESC LIMIT 10').fetchall()
            if not rows:
                await update.message.reply_text('Hələ təsdiqlənmiş profil yoxdur.')
                return
            parts = ['👥 Son 10 profil (ID sırası ilə):']
            for p in rows:
                parts.append(' | '.join(f'{k}: {str(p[k])[:50]}' for k in wanted))
            await update.message.reply_text('\n'.join(parts)[:3900])
        except sqlite3.Error:
            log.exception('Admin users failed')
            await update.message.reply_text('Database oxunarkən xəta baş verdi.')

    async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _authorized(update):
            return
        try:
            with _connect(db_path) as conn:
                if not _has_table(conn, 'reports'):
                    await update.message.reply_text('Şikayət cədvəli yoxdur.')
                    return
                cols = _columns(conn, 'reports')
                wanted = [x for x in ('reporter_id', 'reported_id', 'target_id', 'reason', 'created_at') if x in cols]
                if not wanted:
                    await update.message.reply_text(f'Şikayət sayı: {_count(conn, "reports")}')
                    return
                select = ', '.join('"' + x + '"' for x in wanted)
                rows = conn.execute(f'SELECT {select} FROM reports ORDER BY rowid DESC LIMIT 10').fetchall()
            parts = ['🚩 Son 10 şikayət:']
            for p in rows:
                parts.append(' | '.join(f'{k}: {str(p[k])[:90]}' for k in wanted))
            if not rows:
                parts.append('Şikayət yoxdur.')
            await update.message.reply_text('\n'.join(parts)[:3900])
        except sqlite3.Error:
            log.exception('Admin reports failed')
            await update.message.reply_text('Database oxunarkən xəta baş verdi.')

    app.add_handler(CommandHandler('admin', admin))
    app.add_handler(CommandHandler('stats', stats))
    app.add_handler(CommandHandler('users', users))
    app.add_handler(CommandHandler('reports', reports))
    log.info('Admin handlers registered (configured: %s)', bool(_admin_id()))


async def notify_new_profile(context: ContextTypes.DEFAULT_TYPE, user_id: int, db_path):
    """Call ONLY after a newly confirmed registration, not on every /start."""
    if not _admin_id():
        return
    try:
        with _connect(db_path) as conn:
            if not _has_table(conn, 'profiles'):
                return
            row = conn.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,)).fetchone()
        if row is None:
            return
        data = dict(row)
        summary = ['🆕 Yeni profil təsdiqləndi!', f'Telegram ID: {user_id}']
        for key in ('name', 'age', 'city', 'language'):
            if key in data and data[key] is not None:
                summary.append(f'{key}: {str(data[key])[:100]}')
        await context.bot.send_message(chat_id=_admin_id(), text='\n'.join(summary))
    except Exception:
        log.exception('Admin notification failed (ensure admin has started the bot)')
