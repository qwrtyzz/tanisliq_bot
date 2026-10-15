"""Opt-in distance search. Coordinates are never shown to other users."""
import math
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

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
 if get_location(conn,uid):
  await update.effective_message.reply_text(words(language(context,uid))[6]);return
 msg,button,*_=words(language(context,uid))
 await update.effective_message.reply_text(msg,reply_markup=ReplyKeyboardMarkup([[KeyboardButton(button,request_location=True)]],resize_keyboard=True,one_time_keyboard=True))

async def location_off(update,context,conn,language):
 uid=update.effective_user.id;delete_location(conn,uid)
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
 await update.effective_message.reply_text(words(language(context,uid))[2],reply_markup=ReplyKeyboardRemove())
