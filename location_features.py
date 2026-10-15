"""Opt-in distance search. Coordinates are never shown to other users."""
import math
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

DEFAULT_RADIUS_KM = 50
TRANSLATIONS = {
 'az': ('📍 Yaxınlıqdakı profilləri tapmaq üçün aşağıdakı düymə ilə məkanınızı könüllü paylaşın. Dəqiq məkanınız digər istifadəçilərə göstərilmir.', '📍 Məkanımı paylaş', 'Məkanınız saxlanıldı. Axtarış məsafəsi: 50 km. /search', 'Məkan məlumatınız silindi. Adi axtarış aktivdir.', 'Etibarlı Telegram məkan məlumatı göndərin.', '📍 Məkanınız hələ paylaşılmayıb. /location', '📍 Məkanınız aktivdir. Radius: 50 km. Silmək üçün /locationoff'),
 'en': ('📍 Share your location optionally using the button below to find people nearby. Your exact location is not shown to others.', '📍 Share my location', 'Location saved. Search radius: 50 km. /search', 'Location deleted. Regular search is active.', 'Please send a valid Telegram location.', '📍 No location saved. /location', '📍 Location active. Radius: 50 km. Delete with /locationoff'),
 'tr': ('📍 Yakındaki kişileri bulmak için konumunuzu isteğe bağlı paylaşın. Kesin konumunuz başkalarına gösterilmez.', '📍 Konumumu paylaş', 'Konum kaydedildi. Arama yarıçapı: 50 km. /search', 'Konum silindi. Normal arama etkin.', 'Geçerli bir Telegram konumu gönderin.', '📍 Henüz konum paylaşılmadı. /location', '📍 Konum etkin. Yarıçap: 50 km. Silmek için /locationoff'),
 'ru': ('📍 Чтобы искать людей рядом, по желанию отправьте геопозицию кнопкой ниже. Точные координаты не показываются другим.', '📍 Поделиться геопозицией', 'Геопозиция сохранена. Радиус: 50 км. /search', 'Геопозиция удалена. Обычный поиск активен.', 'Отправьте корректную геопозицию Telegram.', '📍 Геопозиция не сохранена. /location', '📍 Геопозиция включена. Радиус: 50 км. Удалить: /locationoff'),
 'id': ('📍 Bagikan lokasi secara sukarela untuk menemukan orang terdekat. Lokasi persis Anda tidak ditampilkan kepada pengguna lain.', '📍 Bagikan lokasi saya', 'Lokasi disimpan. Radius pencarian: 50 km. /search', 'Lokasi dihapus. Pencarian biasa aktif.', 'Kirim lokasi Telegram yang valid.', '📍 Belum ada lokasi. /location', '📍 Lokasi aktif. Radius: 50 km. Hapus dengan /locationoff')
}

def words(language):
 return TRANSLATIONS.get(language, TRANSLATIONS['en'])

def init_location(conn):
 with conn() as c:
  c.execute('CREATE TABLE IF NOT EXISTS user_locations (user_id INTEGER PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')

def get_location(conn, uid):
 with conn() as c:
  row=c.execute('SELECT lat,lon FROM user_locations WHERE user_id=?',(uid,)).fetchone()
 return (row['lat'],row['lon']) if row else None

def save_location(conn, uid, lat, lon):
 if not (-90<=lat<=90 and -180<=lon<=180) or not all(map(math.isfinite,(lat,lon))):
  raise ValueError('Invalid coordinates')
 with conn() as c:
  c.execute('INSERT INTO user_locations(user_id,lat,lon) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET lat=excluded.lat,lon=excluded.lon,updated_at=CURRENT_TIMESTAMP',(uid,lat,lon))

def delete_location(conn, uid):
 with conn() as c:
  c.execute('DELETE FROM user_locations WHERE user_id=?',(uid,))

def distance_km(a,b):
 lat1,lon1=map(math.radians,a);lat2,lon2=map(math.radians,b)
 x=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
 return 6371.0088*2*math.asin(min(1,math.sqrt(x)))

def distance_label(km,language):
 # 5 km wide bins; never disclose exact coordinates or precise distance.
 lo=int(km//5)*5;hi=lo+5
 return (f'📍 Təxminən {lo}–{hi} km uzaqlıqda' if language=='az' else
         f'📍 Yaklaşık {lo}–{hi} km uzakta' if language=='tr' else
         f'📍 Примерно {lo}–{hi} км от вас' if language=='ru' else
         f'📍 Sekitar {lo}–{hi} km jauhnya' if language=='id' else
         f'📍 About {lo}–{hi} km away')

async def location_command(update,context,conn,language):
 uid=update.effective_user.id
 await update.effective_message.reply_text(choice_words(language(context,uid))[0], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(choice_words(language(context,uid))[1],callback_data='locchoice:yes')],[InlineKeyboardButton(choice_words(language(context,uid))[2],callback_data='locchoice:no')]]))

async def location_off(update,context,conn,language):
 uid=update.effective_user.id;delete_location(conn,uid);set_mode(conn,uid,'worldwide')
 await update.effective_message.reply_text(words(language(context,uid))[3],reply_markup=ReplyKeyboardRemove())

async def location_message(update,context,conn,language):
 uid=update.effective_user.id;loc=update.effective_message.location
 if not loc:return
 # Reject live-location updates; only use one-time static coordinates.
 if loc.live_period is not None:
  await update.effective_message.reply_text(words(language(context,uid))[4]);return
 try:save_location(conn,uid,loc.latitude,loc.longitude)
 except ValueError:
  await update.effective_message.reply_text(words(language(context,uid))[4]);return
 set_mode(conn,uid,'nearby')
 await update.effective_message.reply_text(words(language(context,uid))[2],reply_markup=ReplyKeyboardRemove())


# Persist the user's explicit search choice separately from exact coordinates.
# Existing accounts default to worldwide; no migration deletes existing profiles.
CHOICE_TEXT = {
 'az': ('📍 Yaxınlığınızdakı insanları görmək istəyirsiniz? Məkanınızı könüllü paylaşsanız, 50 km ətrafınızdakı insanları görə bilərsiniz. Dəqiq yeriniz göstərilməyəcək.', '✅ Bəli — 50 km', '🌍 Xeyr — bütün dünya', '📍 Məkanınızı aşağıdakı düymə ilə paylaşın. İstəmirsinizsə, /locationoff yazın.', '🌍 Ümumi axtarış aktivdir. Məsafə göstərilməyəcək.', '📍 Yaxınlıq axtarışı aktivdir: 50 km.'),
 'en': ('📍 Want to meet people nearby? Optionally share your location to see people within 50 km. Your exact position is not shown.', '✅ Yes — 50 km', '🌍 No — worldwide', '📍 Use the button below to share your location, or /locationoff to cancel.', '🌍 Worldwide search enabled. No distances shown.', '📍 Nearby search enabled: 50 km.'),
 'tr': ('📍 Yakınınızdaki kişileri görmek ister misiniz? Konumunuzu isteğe bağlı paylaşarak 50 km içindekileri görebilirsiniz. Kesin konumunuz gösterilmez.', '✅ Evet — 50 km', '🌍 Hayır — herkes', '📍 Aşağıdaki düğmeyle konum paylaşın veya /locationoff ile vazgeçin.', '🌍 Genel arama açık. Mesafe gösterilmez.', '📍 Yakın arama açık: 50 km.'),
 'ru': ('📍 Хотите видеть людей поблизости? По желанию отправьте геопозицию для поиска в радиусе 50 км. Точные координаты не показываются.', '✅ Да — 50 км', '🌍 Нет — все', '📍 Отправьте геопозицию кнопкой ниже или отмените через /locationoff.', '🌍 Поиск по всем профилям. Расстояние не показывается.', '📍 Поиск рядом включён: 50 км.'),
 'id': ('📍 Ingin melihat orang di dekat Anda? Bagikan lokasi secara opsional untuk mencari dalam 50 km. Koordinat tepat tidak ditampilkan.', '✅ Ya — 50 km', '🌍 Tidak — semua orang', '📍 Bagikan lokasi dengan tombol di bawah, atau batalkan dengan /locationoff.', '🌍 Pencarian global aktif. Jarak tidak ditampilkan.', '📍 Pencarian terdekat aktif: 50 km.')
}

def choice_words(code):
 return CHOICE_TEXT.get(code, CHOICE_TEXT['en'])

def init_location_choice(conn):
 with conn() as c:
  c.execute("CREATE TABLE IF NOT EXISTS location_choices (user_id INTEGER PRIMARY KEY, mode TEXT NOT NULL CHECK(mode IN ('worldwide','nearby'))) ")

def get_mode(conn, uid):
 with conn() as c:
  row=c.execute('SELECT mode FROM location_choices WHERE user_id=?',(uid,)).fetchone()
 return row['mode'] if row else 'worldwide'

def set_mode(conn, uid, mode):
 if mode not in ('worldwide','nearby'): raise ValueError('Invalid location mode')
 with conn() as c:
  c.execute('INSERT INTO location_choices(user_id,mode) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET mode=excluded.mode',(uid,mode))

def delete_choice(conn, uid):
 with conn() as c:
  c.execute('DELETE FROM location_choices WHERE user_id=?',(uid,))

def share_keyboard(code):
 return ReplyKeyboardMarkup([[KeyboardButton(words(code)[1],request_location=True)]],resize_keyboard=True,one_time_keyboard=True)
