"""Persistent, per-user age filters. Does not modify profiles or matches."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

RANGES = {"all": (18, 120), "18_24": (18, 24), "25_34": (25, 34), "35_44": (35, 44), "45_plus": (45, 120)}
LABELS = {"all": "18+", "18_24": "18–24", "25_34": "25–34", "35_44": "35–44", "45_plus": "45+"}
MESSAGES = {
 "az": ("🔎 Axtarış üçün yaş aralığını seçin:", "Yaş filtri yadda saxlandı: "),
 "en": ("🔎 Choose an age range for search:", "Age filter saved: "),
 "tr": ("🔎 Arama için yaş aralığı seçin:", "Yaş filtresi kaydedildi: "),
 "ru": ("🔎 Выберите возрастной диапазон:", "Возрастной фильтр сохранён: "),
 "id": ("🔎 Pilih rentang usia pencarian:", "Filter usia tersimpan: "),
}

def init_filters(conn_factory):
    with conn_factory() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS search_filters (
          user_id INTEGER PRIMARY KEY,
          age_range TEXT NOT NULL DEFAULT 'all')""")

def get_age_range(conn_factory, uid):
    with conn_factory() as c:
        row=c.execute('SELECT age_range FROM search_filters WHERE user_id=?',(uid,)).fetchone()
    return RANGES.get(row['age_range'] if row else 'all', RANGES['all'])

def delete_filters(conn_factory, uid):
    with conn_factory() as c:
        c.execute('DELETE FROM search_filters WHERE user_id=?',(uid,))

async def filters_command(update, context, conn_factory, language):
    uid=update.effective_user.id
    code=language(context,uid)
    buttons=[[InlineKeyboardButton(LABELS[k], callback_data='agefilter:'+k)] for k in RANGES]
    await update.effective_message.reply_text(MESSAGES.get(code,MESSAGES['en'])[0],reply_markup=InlineKeyboardMarkup(buttons))

async def filters_callback(update, context, conn_factory, language):
    q=update.callback_query
    key=(q.data or '').split(':',1)[-1]
    if key not in RANGES:
        await q.answer('Invalid option',show_alert=True)
        return
    uid=q.from_user.id
    with conn_factory() as c:
        c.execute('INSERT INTO search_filters(user_id,age_range) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET age_range=excluded.age_range',(uid,key))
    await q.answer()
    code=language(context,uid)
    await q.edit_message_text(MESSAGES.get(code,MESSAGES['en'])[1]+LABELS[key]+'\n/search')
