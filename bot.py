import os
import sqlite3
import logging
from pathlib import Path
from storage import prepare_database
from location_features import init_location, get_location, delete_location, distance_km, distance_label, location_command, location_off, location_message, DEFAULT_RADIUS_KM, choice_words, init_location_choice, get_mode, set_mode, delete_choice, share_keyboard
from html import escape
from telegram import Update, InlineKeyboardButton as B, InlineKeyboardMarkup as K
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from menu import setup_menu
from admin import register_admin, notify_new_profile
from search_filters import init_filters, get_age_range, delete_filters, filters_command, filters_callback

TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB = Path(os.getenv("DB_PATH", "/data/tindraven.sqlite3" if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID") else str(Path(__file__).with_name("tindraven.sqlite3"))))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
T = {'az': {'welcome': 'TindraVen-ə xoş gəlmisiniz! ❤️ Dilinizi seçin:',
        'name': 'Adınızı yazın:',
        'age': 'Yaşınızı yazın (yalnız 18+):',
        'under': 'TindraVen yalnız 18 yaş və yuxarı şəxslər üçündür.',
        'city': 'Şəhərinizi və ya ərazinizi yazın. Dəqiq ev ünvanınızı yazmayın:',
        'bioq': 'Özünüz haqqında əlavə məlumat vermək istəyirsiniz?',
        'bio': 'Özünüz haqqında qısa məlumat yazın (maksimum 500 simvol):',
        'photo': 'Profil şəklinizi göndərin:',
        'confirm': 'Bu profillə davam edək?',
        'yes': 'Bəli',
        'no': 'Xeyr',
        'edit': 'Redaktə et',
        'delete': 'Profili sil',
        'saved': 'Profiliniz təsdiqləndi! ❤️',
        'editq': 'Nəyi dəyişmək istəyirsiniz?',
        'namekey': 'Ad',
        'agekey': 'Yaş',
        'citykey': 'Şəhər',
        'biokey': 'Haqqımda',
        'photokey': 'Şəkil',
        'askname': 'Yeni adınızı yazın:',
        'askage': 'Yeni yaşınızı yazın (18+):',
        'askcity': 'Yeni şəhərinizi yazın:',
        'askbio': 'Yeni məlumatınızı yazın:',
        'askphoto': 'Yeni şəklinizi göndərin:',
        'badage': 'Yaşı rəqəmlə yazın. Yalnız 18+ qəbul edilir.',
        'bad': 'Zəhmət olmasa, düzgün məlumat göndərin.',
        'profile': 'Profiliniz',
        'about': 'Haqqımda',
        'none': 'Əlavə məlumat yoxdur',
        'deleted': 'Profil silindi. /start yazın.',
        'need': 'Profiliniz yoxdur. /start yazın.',
        'help': 'Komandalar: /start, /profile, /delete, /help, /cancel',
        'deleteq': 'Profilinizi silmək istəyirsiniz?',
        'cancel': 'Əməliyyat dayandırıldı.',
        'languages': ['Azərbaycan', 'English', 'Turkish', 'Russian', 'Indonesian'],
        'gender': 'Cinsinizi seçin:',
        'man': 'Kişi',
        'woman': 'Qadın',
        'other': 'Digər',
        'preference': 'Kimi görmək istəyirsiniz?',
        'everyone': 'Hamısı',
        'search': '🔎 Axtarış',
        'like': '❤️ Bəyən',
        'skip': '➡️ Keç',
        'block': '🚫 Blokla',
        'report': '🚩 Şikayət et',
        'nonefound': 'Uyğun profil tapılmadı. Sonra yenidən yoxlayın.',
        'matched': '❤️ Qarşılıqlı bəyənmə!',
        'liked_notice': 'Sizi bəyənən şəxs var! Axtarışa davam edin.',
        'ready': 'Profiliniz tamamlandı. /search yazın.',
        'reportq': 'Şikayət səbəbini seçin:',
        'spam': 'Spam',
        'fake': 'Saxta profil',
        'inappropriate': 'Uyğunsuz məzmun',
        'other_reason': 'Digər səbəb',
        'reported': 'Şikayət qəbul edildi.',
        'blocked': 'İstifadəçi bloklandı.',
        'need_confirm': 'Axtarış üçün əvvəlcə profili təsdiqləyin: /start',
        'no_username': 'Şəxsi Telegram keçidiniz yoxdur. Settings > Privacy > Username bölməsindən '
                       'istifadəçi adı yaradın.',
        'contact': 'Əlaqə keçidi',
        'notfound': 'İstifadəçi tapılmadı.',
        'lang_updated': 'Dil dəyişdirildi.',
        'stale': 'Əməliyyat artıq etibarlı deyil.',
        'need_preferences': 'Axtarış üçün profilinizdə cins və seçim məlumatını tamamlayın: /start',
        'safety': 'Təhlükəsizlik üçün dəqiq ünvan, telefon və şəxsi məlumat paylaşmayın.',
        'pause_help': 'Profili göstərməmək üçün /pause, yenidən göstərmək üçün /resume yazın.',
        'paused': 'Profiliniz gizlədildi.',
        'resumed': 'Profiliniz yenidən aktivdir.'},
 'en': {'welcome': 'Welcome to TindraVen! ❤️ Please choose your language:',
        'name': 'Enter your name:',
        'age': 'Enter your age (18+ only):',
        'under': 'TindraVen is only for people aged 18 and over.',
        'city': 'Enter your city or area. Do not share your exact home address:',
        'bioq': 'Would you like to add information about yourself?',
        'bio': 'Write a short description (maximum 500 characters):',
        'photo': 'Send your profile photo:',
        'confirm': 'Would you like to continue with this profile?',
        'yes': 'Yes',
        'no': 'No',
        'edit': 'Edit profile',
        'delete': 'Delete profile',
        'saved': 'Your profile is confirmed! ❤️',
        'editq': 'What would you like to change?',
        'namekey': 'Name',
        'agekey': 'Age',
        'citykey': 'City',
        'biokey': 'About me',
        'photokey': 'Photo',
        'askname': 'Enter your new name:',
        'askage': 'Enter your new age (18+):',
        'askcity': 'Enter your new city:',
        'askbio': 'Enter your new description:',
        'askphoto': 'Send your new photo:',
        'badage': 'Enter a numeric age. Only people aged 18+ are accepted.',
        'bad': 'Please send valid information.',
        'profile': 'Your profile',
        'about': 'About me',
        'none': 'No extra information',
        'deleted': 'Profile deleted. Send /start.',
        'need': 'You do not have a profile. Send /start.',
        'help': 'Commands: /start, /profile, /delete, /help, /cancel',
        'deleteq': 'Do you want to delete your profile?',
        'cancel': 'Operation cancelled.',
        'languages': ['Azərbaycan', 'English', 'Turkish', 'Russian', 'Indonesian'],
        'gender': 'Choose your gender:',
        'man': 'Man',
        'woman': 'Woman',
        'other': 'Other',
        'preference': 'Who would you like to see?',
        'everyone': 'Everyone',
        'search': '🔎 Search',
        'like': '❤️ Like',
        'skip': '➡️ Skip',
        'block': '🚫 Block',
        'report': '🚩 Report',
        'nonefound': 'No matching profiles found. Try again later.',
        'matched': '❤️ It’s a match!',
        'liked_notice': 'Someone liked you! Keep searching.',
        'ready': 'Profile complete. Use /search.',
        'reportq': 'Choose a report reason:',
        'spam': 'Spam',
        'fake': 'Fake profile',
        'inappropriate': 'Inappropriate content',
        'other_reason': 'Other reason',
        'reported': 'Report received.',
        'blocked': 'User blocked.',
        'need_confirm': 'Confirm your profile first: /start',
        'no_username': 'You do not have a public Telegram username. Set one in Telegram Settings > Username.',
        'contact': 'Contact link',
        'notfound': 'User not found.',
        'lang_updated': 'Language updated.',
        'stale': 'This action is no longer valid.',
        'need_preferences': 'Complete your gender and preference in /start before searching.',
        'safety': 'For safety, never share your exact address, phone number, or private information.',
        'pause_help': 'Use /pause to hide your profile and /resume to show it again.',
        'paused': 'Your profile is hidden.',
        'resumed': 'Your profile is visible again.'},
 'tr': {'welcome': "TindraVen'e hoş geldiniz! ❤️ Dilinizi seçin:",
        'name': 'Adınızı yazın:',
        'age': 'Yaşınızı yazın (yalnızca 18+):',
        'under': 'TindraVen yalnızca 18 yaş ve üzeri kişiler içindir.',
        'city': 'Şehrinizi veya bölgenizi yazın. Açık ev adresinizi paylaşmayın:',
        'bioq': 'Kendiniz hakkında ek bilgi vermek ister misiniz?',
        'bio': 'Kendiniz hakkında kısa bir açıklama yazın (maks. 500 karakter):',
        'photo': 'Profil fotoğrafınızı gönderin:',
        'confirm': 'Bu profille devam edelim mi?',
        'yes': 'Evet',
        'no': 'Hayır',
        'edit': 'Profili düzenle',
        'delete': 'Profili sil',
        'saved': 'Profiliniz onaylandı! ❤️',
        'editq': 'Neyi değiştirmek istersiniz?',
        'namekey': 'Ad',
        'agekey': 'Yaş',
        'citykey': 'Şehir',
        'biokey': 'Hakkımda',
        'photokey': 'Fotoğraf',
        'askname': 'Yeni adınızı yazın:',
        'askage': 'Yeni yaşınızı yazın (18+):',
        'askcity': 'Yeni şehrinizi yazın:',
        'askbio': 'Yeni açıklamanızı yazın:',
        'askphoto': 'Yeni fotoğrafınızı gönderin:',
        'badage': 'Yaşı rakamla yazın. Yalnızca 18+.',
        'bad': 'Lütfen geçerli bilgi gönderin.',
        'profile': 'Profiliniz',
        'about': 'Hakkımda',
        'none': 'Ek bilgi yok',
        'deleted': 'Profil silindi. /start yazın.',
        'need': 'Profiliniz yok. /start yazın.',
        'help': 'Komutlar: /start, /profile, /delete, /help, /cancel',
        'deleteq': 'Profilinizi silmek istiyor musunuz?',
        'cancel': 'İşlem iptal edildi.',
        'languages': ['Azərbaycan', 'English', 'Turkish', 'Russian', 'Indonesian'],
        'gender': 'Cinsiyetinizi seçin:',
        'man': 'Erkek',
        'woman': 'Kadın',
        'other': 'Diğer',
        'preference': 'Kimi görmek istersiniz?',
        'everyone': 'Herkes',
        'search': '🔎 Ara',
        'like': '❤️ Beğen',
        'skip': '➡️ Geç',
        'block': '🚫 Engelle',
        'report': '🚩 Şikayet et',
        'nonefound': 'Uygun profil bulunamadı. Daha sonra tekrar deneyin.',
        'matched': '❤️ Eşleştiniz!',
        'liked_notice': 'Biri sizi beğendi! Aramaya devam edin.',
        'ready': 'Profil tamamlandı. /search yazın.',
        'reportq': 'Şikayet nedeni seçin:',
        'spam': 'Spam',
        'fake': 'Sahte profil',
        'inappropriate': 'Uygunsuz içerik',
        'other_reason': 'Diğer',
        'reported': 'Şikayet alındı.',
        'blocked': 'Kullanıcı engellendi.',
        'need_confirm': 'Önce profilinizi onaylayın: /start',
        'no_username': 'Telegram kullanıcı adınız yok. Ayarlardan bir kullanıcı adı belirleyin.',
        'contact': 'İletişim bağlantısı',
        'notfound': 'Kullanıcı bulunamadı.',
        'lang_updated': 'Dil güncellendi.',
        'stale': 'Bu işlem artık geçerli değil.',
        'need_preferences': 'Aramadan önce /start ile cinsiyet ve tercihleri tamamlayın.',
        'safety': 'Güvenliğiniz için açık adres, telefon ve özel bilgi paylaşmayın.',
        'pause_help': 'Profilinizi gizlemek için /pause, açmak için /resume yazın.',
        'paused': 'Profiliniz gizlendi.',
        'resumed': 'Profiliniz tekrar görünür.'},
 'ru': {'welcome': 'Добро пожаловать в TindraVen! ❤️ Выберите язык:',
        'name': 'Введите имя:',
        'age': 'Введите возраст (только 18+):',
        'under': 'TindraVen предназначен только для пользователей от 18 лет.',
        'city': 'Укажите город или район. Не указывайте точный домашний адрес:',
        'bioq': 'Хотите добавить информацию о себе?',
        'bio': 'Кратко расскажите о себе (до 500 символов):',
        'photo': 'Отправьте фото профиля:',
        'confirm': 'Продолжить с этим профилем?',
        'yes': 'Да',
        'no': 'Нет',
        'edit': 'Изменить профиль',
        'delete': 'Удалить профиль',
        'saved': 'Профиль подтверждён! ❤️',
        'editq': 'Что хотите изменить?',
        'namekey': 'Имя',
        'agekey': 'Возраст',
        'citykey': 'Город',
        'biokey': 'О себе',
        'photokey': 'Фото',
        'askname': 'Введите новое имя:',
        'askage': 'Введите новый возраст (18+):',
        'askcity': 'Введите новый город:',
        'askbio': 'Введите новое описание:',
        'askphoto': 'Отправьте новое фото:',
        'badage': 'Введите возраст цифрами. Только 18+.',
        'bad': 'Пожалуйста, отправьте корректные данные.',
        'profile': 'Ваш профиль',
        'about': 'О себе',
        'none': 'Нет дополнительной информации',
        'deleted': 'Профиль удалён. Отправьте /start.',
        'need': 'Профиля нет. Отправьте /start.',
        'help': 'Команды: /start, /profile, /delete, /help, /cancel',
        'deleteq': 'Удалить профиль?',
        'cancel': 'Операция отменена.',
        'languages': ['Azərbaycan', 'English', 'Turkish', 'Russian', 'Indonesian'],
        'gender': 'Выберите пол:',
        'man': 'Мужчина',
        'woman': 'Женщина',
        'other': 'Другое',
        'preference': 'Кого хотите видеть?',
        'everyone': 'Всех',
        'search': '🔎 Поиск',
        'like': '❤️ Нравится',
        'skip': '➡️ Далее',
        'block': '🚫 Блок',
        'report': '🚩 Жалоба',
        'nonefound': 'Подходящих анкет нет. Попробуйте позже.',
        'matched': '❤️ Qarşılıqlı bəyənmə!',
 'liked_notice': 'Kimsə profilinizi bəyəndi! Axtarışa davam edin.',
 'ready': 'Profil hazırdır. /search yazın.',
 'reportq': 'Şikayət səbəbini seçin:',
 'spam': 'Spam',
 'fake': 'Saxta profil',
 'inappropriate': 'Uyğunsuz məzmun',
 'other_reason': 'Digər',
 'reported': 'Şikayət qeydə alındı.',
 'blocked': 'İstifadəçi bloklandı.',
 'need_confirm': 'Əvvəlcə profilinizi təsdiqləyin: /start',
 'no_username': 'Telegram istifadəçi adınız yoxdur. Parametrlərdən əlavə edin.',
 'contact': 'Əlaqə keçidi',
 'notfound': 'İstifadəçi tapılmadı.',
 'lang_updated': 'Dil dəyişdirildi.',
 'stale': 'Bu düymə artıq etibarlı deyil.',
 'need_preferences': 'Axtarış üçün cins və seçim məlumatlarını /start ilə tamamlayın.',
 'safety': 'Dəqiq ünvanınızı, telefonunuzu və şəxsi məlumatlarınızı paylaşmayın.',
 'pause_help': 'Profili gizlətmək üçün /pause, yenidən göstərmək üçün /resume yazın.',
 'paused': 'Profiliniz gizlədildi.',
 'resumed': 'Profiliniz yenidən aktivdir.'},
 'id': {'welcome': 'Selamat datang di TindraVen! ❤️ Pilih bahasa Anda:',
        'name': 'Masukkan nama Anda:',
        'age': 'Masukkan usia Anda (hanya 18+):',
        'under': 'TindraVen hanya untuk pengguna berusia 18 tahun ke atas.',
        'city': 'Masukkan kota atau area. Jangan bagikan alamat rumah lengkap:',
        'bioq': 'Ingin menambahkan informasi tentang diri Anda?',
        'bio': 'Tulis deskripsi singkat (maksimal 500 karakter):',
        'photo': 'Kirim foto profil Anda:',
        'confirm': 'Lanjutkan dengan profil ini?',
        'yes': 'Ya',
        'no': 'Tidak',
        'edit': 'Edit profil',
        'delete': 'Hapus profil',
        'saved': 'Profil Anda dikonfirmasi! ❤️',
        'editq': 'Apa yang ingin Anda ubah?',
        'namekey': 'Nama',
        'agekey': 'Usia',
        'citykey': 'Kota',
        'biokey': 'Tentang saya',
        'photokey': 'Foto',
        'askname': 'Masukkan nama baru:',
        'askage': 'Masukkan usia baru (18+):',
        'askcity': 'Masukkan kota baru:',
        'askbio': 'Masukkan deskripsi baru:',
        'askphoto': 'Kirim foto baru:',
        'badage': 'Masukkan usia dengan angka. Hanya 18+.',
        'bad': 'Silakan kirim informasi yang valid.',
        'profile': 'Profil Anda',
        'about': 'Tentang saya',
        'none': 'Tidak ada info tambahan',
        'deleted': 'Profil dihapus. Kirim /start.',
        'need': 'Anda belum memiliki profil. Kirim /start.',
        'help': 'Perintah: /start, /profile, /delete, /help, /cancel',
        'deleteq': 'Hapus profil Anda?',
        'cancel': 'Operasi dibatalkan.',
        'languages': ['Azərbaycan', 'English', 'Turkish', 'Russian', 'Indonesian'],
        'gender': 'Pilih gender Anda:',
        'man': 'Pria',
        'woman': 'Wanita',
        'other': 'Lainnya',
        'preference': 'Siapa yang ingin Anda lihat?',
        'everyone': 'Semua',
        'search': '🔎 Cari',
        'like': '❤️ Suka',
        'skip': '➡️ Lewati',
        'block': '🚫 Blokir',
        'report': '🚩 Laporkan',
        'nonefound': 'Tidak ada profil cocok. Coba lagi nanti.',
        'matched': '❤️ Kalian cocok!',
        'liked_notice': 'Seseorang menyukai Anda! Lanjutkan pencarian.',
        'ready': 'Profil selesai. Gunakan /search.',
        'reportq': 'Pilih alasan laporan:',
        'spam': 'Spam',
        'fake': 'Profil palsu',
        'inappropriate': 'Konten tidak pantas',
        'other_reason': 'Lainnya',
        'reported': 'Laporan diterima.',
        'blocked': 'Pengguna diblokir.',
        'need_confirm': 'Konfirmasi profil terlebih dahulu: /start',
        'no_username': 'Anda belum punya username Telegram publik. Atur di Settings.',
        'contact': 'Tautan kontak',
        'notfound': 'Pengguna tidak ditemukan.',
        'lang_updated': 'Bahasa diperbarui.',
        'stale': 'Tindakan ini sudah tidak berlaku.',
        'need_preferences': 'Lengkapi gender dan preferensi melalui /start sebelum mencari.',
        'safety': 'Jangan bagikan alamat lengkap, nomor telepon, atau informasi pribadi.',
        'pause_help': 'Gunakan /pause untuk menyembunyikan profil dan /resume untuk menampilkan lagi.',
        'paused': 'Profil disembunyikan.',
        'resumed': 'Profil terlihat lagi.'}}

LANGS = {'az':'🇦🇿 Azərbaycan','en':'🇬🇧 English','tr':'🇹🇷 Türkçe','ru':'🇷🇺 Русский','id':'🇮🇩 Indonesia'}

def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB, timeout=20)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA busy_timeout=20000')
    return c

def init_db():
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'en', name TEXT, age INTEGER, city TEXT, bio TEXT DEFAULT '', photo TEXT, confirmed INTEGER DEFAULT 0)''')
        cols={r['name'] for r in c.execute('PRAGMA table_info(profiles)')}
        for col,typ in [('gender','TEXT'),('preference','TEXT'),('active','INTEGER NOT NULL DEFAULT 1'),('username','TEXT')]:
            if col not in cols:c.execute(f'ALTER TABLE profiles ADD COLUMN {col} {typ}')
        c.execute('CREATE TABLE IF NOT EXISTS likes (from_id INTEGER NOT NULL,to_id INTEGER NOT NULL,PRIMARY KEY(from_id,to_id))')
        c.execute('CREATE TABLE IF NOT EXISTS skips (from_id INTEGER NOT NULL,to_id INTEGER NOT NULL,PRIMARY KEY(from_id,to_id))')
        c.execute('CREATE TABLE IF NOT EXISTS blocks (from_id INTEGER NOT NULL,to_id INTEGER NOT NULL,PRIMARY KEY(from_id,to_id))')
        c.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT,from_id INTEGER NOT NULL,to_id INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        c.execute('CREATE TABLE IF NOT EXISTS matches (a INTEGER NOT NULL,b INTEGER NOT NULL,PRIMARY KEY(a,b))')
        c.execute('CREATE TABLE IF NOT EXISTS official_profile_views (viewer_id INTEGER PRIMARY KEY, shown_at TEXT DEFAULT CURRENT_TIMESTAMP)')

def get(uid):
    with conn() as c:return c.execute('SELECT * FROM profiles WHERE user_id=?',(uid,)).fetchone()

def put(uid,**fields):
    allowed={'language','name','age','city','bio','photo','confirmed','gender','preference','active','username'}
    if not fields or not set(fields)<=allowed:raise ValueError('Invalid fields')
    with conn() as c:
        c.execute('INSERT OR IGNORE INTO profiles(user_id) VALUES (?)',(uid,))
        c.execute('UPDATE profiles SET '+', '.join(f'{k}=?' for k in fields)+' WHERE user_id=?',(*fields.values(),uid))

def remove(uid):
    with conn() as c:
        for table in ('likes','skips','blocks'):
            c.execute(f'DELETE FROM {table} WHERE from_id=? OR to_id=?',(uid,uid))
        c.execute('DELETE FROM matches WHERE a=? OR b=?',(uid,uid))
        c.execute('DELETE FROM reports WHERE from_id=? OR to_id=?',(uid,uid))
        c.execute('DELETE FROM profiles WHERE user_id=?',(uid,))
        c.execute('DELETE FROM official_profile_views WHERE viewer_id=?',(uid,))
    delete_filters(conn, uid)
    delete_location(conn, uid)
    delete_choice(conn, uid)

def lang(context,uid=None):
    if uid is not None:
        p=get(uid)
        if p and p['language'] in T:return p['language']
    return context.user_data.get('language','en')

def t(context,key,uid=None):return T[lang(context,uid)].get(key,T['en'].get(key,key))

def kb(rows):return K([[B(label,callback_data=data) for label,data in row] for row in rows])

def is_official_admin(user_id):
    # Admin status is based exclusively on the server-side ADMIN_ID.
    admin_id = os.getenv('ADMIN_ID', '').strip()
    return bool(admin_id and admin_id.isdecimal() and int(admin_id) == int(user_id))

def profile_caption(p,context):
    x=T[p['language']] if p['language'] in T else T['en']
    name=escape(str(p['name'] or ''))
    age=escape(str(p['age'] or ''))
    city=escape(str(p['city'] or ''))
    if is_official_admin(p['user_id']):
        return ("<b>TINDRAVEN / OFFICIAL ACCOUNT</b>  🔵✓\n\n"
                + "<b>" + name + "</b> · " + age + "\n"
                + "<b>Founder &amp; Platform Administrator</b>\n"
                + "Identity verified by TindraVen\n\n"
                + "<b>Location:</b> " + city)
    return ('<b>'+name+'</b>, '+age+'\n'+city+'\n'+escape(str(p['bio'] or x['none'])))

def founder_intro_caption(p):
    """Distinct official introduction card, sent with the existing admin logo."""
    return ("<b>TINDRAVEN</b>  /  <b>001 — FOUNDER</b>\n\n"
            "<b>" + escape(str(p['name'] or 'Founder')) + "</b>\n"
            "<b>The person behind TindraVen.</b>\n\n"
            "<i>This is not an ordinary dating profile.</i>\n\n"
            "FOUNDER ACCESS  /  001")


def founder_intro_keyboard(admin_id, viewer_id, context):
    return kb([
        [('Discover the Founder', 'founder:discover:' + str(admin_id))],
        [(t(context,'skip',viewer_id), 'founder:continue:' + str(admin_id))],
        [(t(context,'block',viewer_id), 'act:block:' + str(admin_id)),
         (t(context,'report',viewer_id), 'act:report:' + str(admin_id))],
    ])


def founder_details(p):
    name=escape(str(p['name'] or 'Founder'))
    city=escape(str(p['city'] or ''))
    return ("<b>FOUNDER FILE  /  001</b>\n\n"
            "<b>" + name + "</b>\n"
            "Founder &amp; Platform Administrator\n\n"
            "<b>ABOUT THE FOUNDER</b>\n"
            "TindraVen was created to help people make meaningful connections "
            "across the world.\n\n"
            "<b>LOCATION</b>\n" + city + "\n\n"
            "<i>TINDRAVEN  /  OFFICIAL ACCOUNT</i>")

async def show_preview(update,context):
    uid=update.effective_user.id;p=get(uid)
    context.user_data['step']='confirm'
    await context.bot.send_photo(update.effective_chat.id,p['photo'],caption=profile_caption(p,context),parse_mode=ParseMode.HTML,
        reply_markup=kb([[(t(context,'yes'),'confirm:yes'),(t(context,'no'),'confirm:no')]]))

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    """One Telegram account has at most one profile; /start never overwrites it."""
    uid = update.effective_user.id
    p = get(uid)
    context.user_data.clear()
    if p and p['confirmed'] and p['name'] and p['age'] and p['city'] and p['photo']:
        # Older profiles may not yet have gender/preference; do not restart registration.
        if not p['gender'] or not p['preference']:
            context.user_data['step'] = 'editmenu'
            msg = {
                'az': '❤️ Profiliniz artıq mövcuddur. Axtarış üçün cins və seçim məlumatlarını /edit vasitəsilə tamamlayın.',
                'en': '❤️ Your profile already exists. Complete gender and preference using /edit to start searching.',
                'tr': '❤️ Profiliniz zaten var. Arama için cinsiyet ve tercihlerinizi /edit ile tamamlayın.',
                'ru': '❤️ Ваш профиль уже существует. Укажите пол и предпочтения через /edit для поиска.',
                'id': '❤️ Profil Anda sudah ada. Lengkapi gender dan preferensi melalui /edit untuk mencari.'
            }
            await update.effective_message.reply_text(msg.get(lang(context,uid), msg['en']), reply_markup=edit_keyboard(context,uid))
            return
        await update.effective_message.reply_text(
            t(context,'ready',uid) + '\n' + t(context,'pause_help',uid),
            reply_markup=kb([[(t(context,'search',uid),'home:search')],
                             [(t(context,'edit',uid),'home:edit')]]))
        return
    if p and p['name'] and p['age'] and p['city'] and p['photo']:
        # Profile exists but was not confirmed; resume at confirmation, don't duplicate.
        if get_mode(conn,uid)=='nearby' and get_location(conn,uid):
            await show_preview(update,context)
        else:
            await ask_location_choice(update,context)
        return
    if p:
        # Incomplete profile: retain saved language and continue from first missing field.
        fields = [('name','name'),('age','age'),('city','city'),
                  ('gender','gender'),('preference','preference'),('photo','photo')]
        missing = next((field for field, _ in fields if not p[field]), None)
        if missing in ('name','age','city'):
            context.user_data['step'] = missing
            await update.effective_message.reply_text(t(context,missing,uid))
            return
        if missing == 'gender':
            context.user_data['step']='gender'
            await update.effective_message.reply_text(t(context,'gender',uid),reply_markup=kb([[(t(context,'man',uid),'gender:man'),(t(context,'woman',uid),'gender:woman'),(t(context,'other',uid),'gender:other')]]))
            return
        if missing == 'preference':
            context.user_data['step']='preference'
            await update.effective_message.reply_text(t(context,'preference',uid),reply_markup=kb([[(t(context,'man',uid),'pref:man'),(t(context,'woman',uid),'pref:woman'),(t(context,'everyone',uid),'pref:everyone')]]))
            return
        if missing == 'photo':
            context.user_data['step']='photo'
            await update.effective_message.reply_text(t(context,'photo',uid))
            return
    context.user_data['step']='lang'
    await update.effective_message.reply_text(T['en']['welcome'],reply_markup=kb([[(v,'lang:'+k)] for k,v in LANGS.items()]))

async def ask_location_choice(update,context):
    uid=update.effective_user.id
    code=lang(context,uid)
    w=choice_words(code)
    context.user_data['step']='location_choice'
    await context.bot.send_message(update.effective_chat.id,w[0],reply_markup=kb([[(w[1],'locchoice:yes')],[(w[2],'locchoice:no')]]))

async def request_location(update,context):
    uid=update.effective_user.id
    code=lang(context,uid)
    context.user_data['step']='await_location'
    await context.bot.send_message(update.effective_chat.id,choice_words(code)[3],reply_markup=share_keyboard(code))

async def handle_location(update,context):
    uid=update.effective_user.id
    p=get(uid)
    if not p or context.user_data.get('step')!='await_location':
        await update.effective_message.reply_text('Use /location to choose your location preference first.')
        return
    loc=update.effective_message.location
    if not loc or loc.live_period is not None:
        await update.effective_message.reply_text('Please send a one-time location.');return
    from location_features import save_location
    try:
        save_location(conn,uid,loc.latitude,loc.longitude)
    except ValueError:
        await update.effective_message.reply_text('Invalid location.');return
    set_mode(conn,uid,'nearby')
    from telegram import ReplyKeyboardRemove
    await update.effective_message.reply_text(choice_words(lang(context,uid))[5],reply_markup=ReplyKeyboardRemove())
    if not p['confirmed']:
        await show_preview(update,context)
    else:
        context.user_data.pop('step',None)

async def next_gender(q,context):
    context.user_data['step']='gender'
    await q.message.reply_text(t(context,'gender'),reply_markup=kb([[(t(context,'man'),'gender:man'),(t(context,'woman'),'gender:woman'),(t(context,'other'),'gender:other')]]))

async def next_preference(q,context):
    context.user_data['step']='preference'
    await q.message.reply_text(t(context,'preference'),reply_markup=kb([[(t(context,'man'),'pref:man'),(t(context,'woman'),'pref:woman'),(t(context,'everyone'),'pref:everyone')]]))

async def callbacks(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;uid=q.from_user.id;data=q.data or ''
    await q.answer()
    step=context.user_data.get('step')
    if data.startswith('locchoice:'):
        if data not in ('locchoice:yes','locchoice:no'):return
        p=get(uid)
        if not p:return
        # A stale registration button must not reset an existing confirmed profile.
        if p['confirmed'] and step not in ('location_choice','await_location'):
            await q.message.reply_text(t(context,'stale',uid));return
        await q.edit_message_reply_markup(reply_markup=None)
        if data=='locchoice:yes':
            await request_location(update,context)
        else:
            delete_location(conn,uid)
            set_mode(conn,uid,'worldwide')
            from telegram import ReplyKeyboardRemove
            await q.message.reply_text(choice_words(lang(context,uid))[4],reply_markup=ReplyKeyboardRemove())
            if not p['confirmed']:
                await show_preview(update,context)
            else:
                context.user_data.pop('step',None)
        return
    if data.startswith('agefilter:'):
        await filters_callback(update,context,conn,lang)
        return
    if data.startswith('home:'):
        if data=='home:search':
            await search_next(update,context)
        elif data=='home:edit':
            p=get(uid)
            if p:
                context.user_data['step']='editmenu'
                context.user_data['editing_profile']=True
                await q.message.reply_text(t(context,'editq',uid),reply_markup=edit_keyboard(context,uid))
        return
    if data.startswith('delete:'):
        if data=='delete:yes':
            code=lang(context,uid);remove(uid);context.user_data.clear();await q.edit_message_text(T[code]['deleted'])
        else:await q.edit_message_text(t(context,'cancel',uid))
        return
    if data.startswith('settings:'):
        action=data.split(':',1)[1]
        p=get(uid)
        if not p or not p['confirmed']:
            await q.edit_message_text(t(context,'need',uid));return
        if action=='pause':
            put(uid,active=0)
            await q.edit_message_text(t(context,'paused',uid));return
        if action=='resume':
            put(uid,active=1)
            await q.edit_message_text(t(context,'resumed',uid));return
        if action=='delete':
            await q.edit_message_text(t(context,'deleteq',uid),reply_markup=kb([[(t(context,'yes',uid),'delete:yes'),(t(context,'no',uid),'delete:no')]]));return
        return
    if data.startswith('lang:') and step=='lang':
        code=data[5:]
        if code not in LANGS:return
        existing=get(uid)
        if existing and existing['confirmed']:
            await q.edit_message_text(t(context,'ready',uid));return
        put(uid,language=code,username=q.from_user.username)
        context.user_data['language']=code;context.user_data['step']='name'
        await q.edit_message_text(t(context,'name'))
        return
    if data.startswith('gender:') and step=='gender':
        value=data[7:]
        if value not in ('man','woman','other'):return
        put(uid,gender=value);await q.edit_message_reply_markup(reply_markup=None)
        if context.user_data.pop('edit_gender',False):
            put(uid,confirmed=0);await show_preview(update,context);return
        await next_preference(q,context);return
    if data.startswith('pref:') and step=='preference':
        value=data[5:]
        if value not in ('man','woman','everyone'):return
        put(uid,preference=value)
        if context.user_data.pop('edit_preference',False):
            put(uid,confirmed=0);await q.edit_message_reply_markup(reply_markup=None);await show_preview(update,context);return
        context.user_data['step']='biochoice'
        await q.edit_message_text(t(context,'bioq'),reply_markup=kb([[(t(context,'yes'),'bio:yes'),(t(context,'no'),'bio:no')]]));return
    if data.startswith('bio:') and step=='biochoice':
        if data=='bio:yes':context.user_data['step']='bio';await q.edit_message_text(t(context,'bio'))
        else:put(uid,bio='');context.user_data['step']='photo';await q.edit_message_text(t(context,'photo'))
        return
    if data.startswith('confirm:') and step=='confirm':
        await q.edit_message_reply_markup(reply_markup=None)
        if data=='confirm:yes':
            was_confirmed = bool(get(uid) and get(uid)['confirmed'])
            put(uid,confirmed=1,active=1,username=q.from_user.username)
            if not was_confirmed and not context.user_data.get('editing_profile'):
                await notify_new_profile(context, uid, DB)
            context.user_data.clear();await q.message.reply_text(t(context,'ready',uid)+'\n'+t(context,'safety',uid))
        else:
            context.user_data['step']='editmenu';await q.message.reply_text(t(context,'editq',uid),reply_markup=edit_keyboard(context,uid))
        return
    if data.startswith('edit:') and step=='editmenu':
        field=data[5:]
        if field=='delete':
            await q.edit_message_text(t(context,'deleteq',uid),reply_markup=kb([[(t(context,'yes',uid),'delete:yes'),(t(context,'no',uid),'delete:no')]]));return
        if field not in ('name','age','city','bio','photo','gender','preference'):return
        context.user_data['editing_profile']=True
        context.user_data['edit_field']=field
        if field=='gender':await q.edit_message_reply_markup(reply_markup=None);await next_gender(q,context);context.user_data['edit_gender']=True;return
        if field=='preference':await q.edit_message_reply_markup(reply_markup=None);await next_preference(q,context);context.user_data['edit_preference']=True;return
        context.user_data['step']='editvalue'
        await q.edit_message_text(t(context,{'name':'askname','age':'askage','city':'askcity','bio':'askbio','photo':'askphoto'}[field],uid));return
    if data.startswith('founder:'):
        parts=data.split(':')
        if len(parts)!=3 or not parts[2].isdecimal():return
        _,action,sid=parts
        target=int(sid)
        if not is_official_admin(target) or context.user_data.get('current_target')!=target:
            await q.message.reply_text(t(context,'stale',uid));return
        founder=get(target)
        if not founder or not founder['confirmed'] or not founder['active']:
            await q.message.reply_text(t(context,'stale',uid));return
        if action=='discover':
            rows=[[B(t(context,'like',uid),callback_data=f'act:like:{target}'),
                   B(t(context,'skip',uid),callback_data=f'act:skip:{target}')]]
            # A Telegram username is required for a reliable public contact link.
            username=(founder['username'] or '').strip().lstrip('@')
            if username and all(ch.isalnum() or ch=='_' for ch in username):
                rows.append([B('Message the Founder',url='https://t.me/'+username)])
            rows.append([B('Continue Searching',callback_data=f'founder:continue:{target}')])
            rows.append([B(t(context,'block',uid),callback_data=f'act:block:{target}'),
                         B(t(context,'report',uid),callback_data=f'act:report:{target}')])
            await q.edit_message_reply_markup(reply_markup=None)
            await q.message.reply_text(founder_details(founder),parse_mode=ParseMode.HTML,
                                       reply_markup=K(rows))
            return
        if action=='continue':
            await q.edit_message_reply_markup(reply_markup=None)
            context.user_data.pop('current_target',None)
            await search_next(update,context)
            return
        return
    if data.startswith('act:'):
        parts=data.split(':')
        if len(parts)!=3:return
        _,action,sid=parts
        if not sid.isdecimal():return
        target=int(sid)
        if target==uid:return
        if context.user_data.get('current_target')!=target:
            await q.message.reply_text(t(context,'stale',uid));return
        own=get(uid);other=get(target)
        if not own or not own['confirmed'] or not other or not other['confirmed']:
            await q.message.reply_text(t(context,'stale',uid));return
        if action=='report':
            context.user_data['step']='report';await q.edit_message_reply_markup(reply_markup=None)
            await q.message.reply_text(t(context,'reportq',uid),reply_markup=kb([[(t(context,k,uid),f'reason:{k}:{target}')] for k in ('spam','fake','inappropriate','other_reason')]));return
        if action not in ('like','skip','block'):return
        with conn() as c:
            if action=='like':c.execute('INSERT OR IGNORE INTO likes VALUES (?,?)',(uid,target))
            if action=='skip':c.execute('INSERT OR IGNORE INTO skips VALUES (?,?)',(uid,target))
            if action=='block':c.execute('INSERT OR IGNORE INTO blocks VALUES (?,?)',(uid,target))
            reciprocal=c.execute('SELECT 1 FROM likes WHERE from_id=? AND to_id=?',(target,uid)).fetchone() if action=='like' else None
            blocked=c.execute('SELECT 1 FROM blocks WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)',(uid,target,target,uid)).fetchone()
            new_match=False
            if reciprocal and not blocked:
                a,b=sorted((uid,target));cur=c.execute('INSERT OR IGNORE INTO matches VALUES (?,?)',(a,b));new_match=cur.rowcount>0
        await q.edit_message_reply_markup(reply_markup=None)
        context.user_data.pop('current_target',None)
        if action=='block':await q.message.reply_text(t(context,'blocked',uid))
        if new_match:
            await send_match(context,uid,target)
        elif action=='like':
            try:await context.bot.send_message(target,t(context,'liked_notice',target))
            except Exception:logging.info('Unable to notify %s',target)
        await search_next(update,context);return
    if data.startswith('reason:') and step=='report':
        parts=data.split(':')
        if len(parts)!=3 or parts[1] not in ('spam','fake','inappropriate','other_reason') or not parts[2].isdecimal():return
        target=int(parts[2])
        if target!=context.user_data.get('current_target'):return
        with conn() as c:
            c.execute('INSERT INTO reports(from_id,to_id,reason) VALUES (?,?,?)',(uid,target,parts[1]))
            c.execute('INSERT OR IGNORE INTO blocks VALUES (?,?)',(uid,target))
        context.user_data.pop('current_target',None);context.user_data.pop('step',None)
        await q.edit_message_text(t(context,'reported',uid));await search_next(update,context);return
    await q.message.reply_text(t(context,'stale',uid))

def edit_keyboard(context,uid):
    fields=['name','age','city','bio','photo','gender','preference','delete']
    labels=['namekey','agekey','citykey','biokey','photokey','gender','preference','delete']
    return kb([[(t(context,label,uid),'edit:'+field)] for field,label in zip(fields,labels)])

async def messages(update:Update,context:ContextTypes.DEFAULT_TYPE):
    msg=update.message;uid=update.effective_user.id;step=context.user_data.get('step')
    if step not in ('name','age','city','bio','photo','editvalue'):
        await msg.reply_text(t(context,'help',uid));return
    field=context.user_data.get('edit_field') if step=='editvalue' else step
    value=(msg.text or '').strip()
    if field=='photo':
        if not msg.photo:await msg.reply_text(t(context,'photo',uid));return
        value=msg.photo[-1].file_id
    elif field=='age':
        try:age=int(value)
        except ValueError:age=0
        if 0 < age < 18:
            if step!='editvalue':
                code=lang(context,uid);remove(uid);context.user_data.clear();await msg.reply_text(T[code]['under']);return
            await msg.reply_text(t(context,'badage',uid));return
        if age<18 or age>120:await msg.reply_text(t(context,'badage',uid));return
        value=age
    elif (not value and field!='bio') or len(value)>{'name':50,'city':100,'bio':500}.get(field,500):
        await msg.reply_text(t(context,'bad',uid));return
    put(uid,**{field:value})
    if step=='editvalue':
        context.user_data.pop('edit_field',None)
        put(uid,confirmed=0)
        await show_preview(update,context);return
    next_step={'name':'age','age':'city','city':'gender','bio':'photo'}
    if field=='photo':await ask_location_choice(update,context)
    elif field=='city':await msg.reply_text(t(context,'gender',uid),reply_markup=kb([[(t(context,'man',uid),'gender:man'),(t(context,'woman',uid),'gender:woman'),(t(context,'other',uid),'gender:other')]]));context.user_data['step']='gender'
    else:
        context.user_data['step']=next_step[field]
        await msg.reply_text(t(context,next_step[field],uid))

async def send_match(context,uid,target):
    for receiver,partner in ((uid,target),(target,uid)):
        p=get(partner)
        if not p:continue
        url=f'tg://user?id={partner}'
        if p['username']:url='https://t.me/'+p['username'].lstrip('@')
        caption=t(context,'matched',receiver)+'\n'+escape(str(p['name']))+'\n'+t(context,'contact',receiver)+': '+escape(url)
        try:await context.bot.send_message(receiver,caption,parse_mode=ParseMode.HTML,disable_web_page_preview=True)
        except Exception:logging.exception('Match notification failed')

async def search_next(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['confirmed'] or not p['active']:
        await context.bot.send_message(update.effective_chat.id,t(context,'need_confirm',uid));return
    if not p['gender'] or not p['preference']:
        await context.bot.send_message(update.effective_chat.id,t(context,'need_preferences',uid));return
    # Present the verified official profile once to each eligible viewer.
    # Gender, age, preference and proximity do not restrict this introduction.
    admin_raw=os.getenv('ADMIN_ID','').strip()
    admin_uid=int(admin_raw) if admin_raw.isdecimal() else None
    if admin_uid is not None and admin_uid!=uid:
        with conn() as c:
            already_shown=c.execute('SELECT 1 FROM official_profile_views WHERE viewer_id=?',(uid,)).fetchone()
            blocked=c.execute('''SELECT 1 FROM blocks WHERE
                (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)''',
                (uid,admin_uid,admin_uid,uid)).fetchone()
            admin_profile=c.execute('''SELECT * FROM profiles WHERE user_id=? AND confirmed=1
                AND active=1 AND photo IS NOT NULL''',(admin_uid,)).fetchone()
        if not already_shown and not blocked and admin_profile:
            await context.bot.send_photo(
                update.effective_chat.id,admin_profile['photo'],
                caption=founder_intro_caption(admin_profile),parse_mode=ParseMode.HTML,
                reply_markup=founder_intro_keyboard(admin_uid,uid,context))
            context.user_data['current_target']=admin_uid
            with conn() as c:
                c.execute('INSERT OR IGNORE INTO official_profile_views(viewer_id) VALUES (?)',(uid,))
            return
    min_age,max_age=get_age_range(conn,uid)
    own_location=get_location(conn,uid) if get_mode(conn,uid)=='nearby' else None
    with conn() as c:
        candidates=c.execute('''SELECT p.* FROM profiles p WHERE p.user_id!=? AND p.confirmed=1 AND p.active=1
            AND p.photo IS NOT NULL AND p.age BETWEEN ? AND ? AND p.gender IS NOT NULL AND p.preference IS NOT NULL
            AND (?='everyone' OR p.gender=?)
            AND (p.preference='everyone' OR p.preference=?)
            AND NOT (p.user_id=? AND EXISTS (SELECT 1 FROM official_profile_views v WHERE v.viewer_id=?))
            AND NOT EXISTS (SELECT 1 FROM likes l WHERE l.from_id=? AND l.to_id=p.user_id)
            AND NOT EXISTS (SELECT 1 FROM skips s WHERE s.from_id=? AND s.to_id=p.user_id)
            AND NOT EXISTS (SELECT 1 FROM blocks b WHERE (b.from_id=? AND b.to_id=p.user_id) OR (b.from_id=p.user_id AND b.to_id=?))
            ORDER BY RANDOM()''',(uid,min_age,max_age,p['preference'],p['preference'],p['gender'],admin_uid or -1,uid,uid,uid,uid,uid)).fetchall()
    target=None
    shown_distance=None
    if own_location is None:
        target=candidates[0] if candidates else None
    else:
        for candidate in candidates:
            candidate_location=get_location(conn,candidate['user_id'])
            if candidate_location is None:
                continue
            km=distance_km(own_location,candidate_location)
            if km<=DEFAULT_RADIUS_KM:
                target=candidate
                shown_distance=km
                break
    if not target:
        context.user_data.pop('current_target',None)
        await context.bot.send_message(update.effective_chat.id,t(context,'nonefound',uid));return
    target_id=target['user_id'];context.user_data['current_target']=target_id
    await context.bot.send_photo(update.effective_chat.id,target['photo'],caption=profile_caption(target,context)+('\n'+distance_label(shown_distance,lang(context,uid)) if shown_distance is not None else ''),parse_mode=ParseMode.HTML,
        reply_markup=kb([[(t(context,'like',uid),f'act:like:{target_id}'),(t(context,'skip',uid),f'act:skip:{target_id}')],[(t(context,'block',uid),f'act:block:{target_id}'),(t(context,'report',uid),f'act:report:{target_id}')]]))

async def search(update,context):
    context.user_data.pop('step',None)
    await search_next(update,context)

async def age_filters_command(update,context):
    await filters_command(update,context,conn,lang)

async def profile(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['photo']:
        await update.message.reply_text(t(context,'need',uid));return
    await update.message.reply_photo(p['photo'],caption=profile_caption(p,context),parse_mode=ParseMode.HTML)

async def edit(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['photo']:
        await update.message.reply_text(t(context,'need',uid));return
    context.user_data['step']='editmenu'
    context.user_data['editing_profile']=True
    await update.message.reply_text(t(context,'editq',uid),reply_markup=edit_keyboard(context,uid))

async def delete(update,context):
    uid=update.effective_user.id
    await update.message.reply_text(t(context,'deleteq',uid),reply_markup=kb([[(t(context,'yes',uid),'delete:yes'),(t(context,'no',uid),'delete:no')]]))

async def settings_cmd(update,context):
    uid=update.effective_user.id
    p=get(uid)
    if not p or not p['confirmed']:
        await update.effective_message.reply_text(t(context,'need',uid));return
    code=lang(context,uid)
    headings={'az':'⚙️ Profil ayarları','en':'⚙️ Profile settings','tr':'⚙️ Profil ayarları','ru':'⚙️ Настройки профиля','id':'⚙️ Pengaturan profil'}
    await update.effective_message.reply_text(
        headings.get(code,headings['en']),
        reply_markup=kb([[(t(context,'paused',uid) if False else {'az':'⏸ Profili gizlət','en':'⏸ Hide profile','tr':'⏸ Profili gizle','ru':'⏸ Скрыть профиль','id':'⏸ Sembunyikan profil'}[code],'settings:pause')],
                         [({'az':'▶️ Profili aktivləşdir','en':'▶️ Show profile','tr':'▶️ Profili etkinleştir','ru':'▶️ Показать профиль','id':'▶️ Aktifkan profil'}[code],'settings:resume')],
                         [(t(context,'delete',uid),'settings:delete')]]))

async def safety_cmd(update,context):
    uid=update.effective_user.id
    code=lang(context,uid)
    notes={
      'az':'🛡️ Təhlükəsizlik: Dəqiq ünvan, şifrə və pul məlumatlarını paylaşmayın. /search zamanı Block və Report düymələrindən istifadə edin. Yalnız 18+.',
      'en':'🛡️ Safety: Never share your exact address, passwords or financial details. Use Block or Report while browsing /search. Adults 18+ only.',
      'tr':'🛡️ Güvenlik: Açık adresinizi, şifrenizi veya finansal bilgilerinizi paylaşmayın. /search içinde Engelle ve Şikayet et kullanın. Yalnızca 18+.',
      'ru':'🛡️ Безопасность: Не сообщайте точный адрес, пароли и финансовые данные. В /search доступны блокировка и жалоба. Только 18+.',
      'id':'🛡️ Keamanan: Jangan bagikan alamat lengkap, kata sandi, atau data keuangan. Gunakan Blokir dan Laporkan di /search. Khusus 18+.'}
    await update.effective_message.reply_text(notes.get(code,notes['en']))

async def help_cmd(update,context):
    uid=update.effective_user.id
    await update.message.reply_text('/start /search /filters /location /locationoff /myprofile /edit /settings /safety /help\n/delete /pause /resume /cancel\n'+t(context,'pause_help',uid))

async def cancel(update,context):
    uid=update.effective_user.id;context.user_data.clear()
    await update.message.reply_text(t(context,'cancel',uid))

async def pause(update,context):
    uid=update.effective_user.id
    if not get(uid):await update.message.reply_text(t(context,'need',uid));return
    put(uid,active=0);await update.message.reply_text(t(context,'paused',uid))

async def resume(update,context):
    uid=update.effective_user.id;p=get(uid)
    if not p or not p['confirmed']:await update.message.reply_text(t(context,'need_confirm',uid));return
    put(uid,active=1);await update.message.reply_text(t(context,'resumed',uid))

async def error_handler(update,context):
    logging.error('Telegram bot error: %s',context.error,exc_info=context.error)

def main():
    if not TOKEN:raise SystemExit('BOT_TOKEN missing. Windows CMD: set "BOT_TOKEN=your_token"')
    prepare_database(DB)
    init_db()
    init_filters(conn)
    init_location(conn)
    init_location_choice(conn)
    app=Application.builder().token(TOKEN).post_init(setup_menu).build()
    for name,func in [('start',start),('search',search),('filters',age_filters_command),('location',lambda u,c: location_command(u,c,conn,lang)),('locationoff',lambda u,c: location_off(u,c,conn,lang)),('profile',profile),('myprofile',profile),('edit',edit),('delete',delete),('help',help_cmd),('settings',settings_cmd),('safety',safety_cmd),('cancel',cancel),('pause',pause),('resume',resume)]:
        app.add_handler(CommandHandler(name,func,filters=filters.ChatType.PRIVATE))
    register_admin(app, DB)
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.LOCATION & filters.ChatType.PRIVATE,handle_location))
    app.add_handler(MessageHandler(filters.ALL & ~filters.LOCATION & ~filters.COMMAND & filters.ChatType.PRIVATE,messages))
    app.add_error_handler(error_handler)
    logging.info('TindraVen running')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=='__main__':main()
