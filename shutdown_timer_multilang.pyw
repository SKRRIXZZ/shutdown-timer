import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import time
import os
import sys
import json
import tempfile
import math
import struct
import wave
import ctypes
import collections
from datetime import datetime, timedelta

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    import winsound
    WINSOUND_OK = True
except ImportError:
    WINSOUND_OK = False

try:
    import winreg
    WINREG_OK = True
except ImportError:
    WINREG_OK = False

try:
    import keyboard
    KEYBOARD_OK = True
except ImportError:
    KEYBOARD_OK = False


def _set_app_id(app_id):
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

_set_app_id("ShutdownTimer.Custom.App.2")


SIGNAL_FILE = os.path.join(tempfile.gettempdir(), "shutdown_timer_singleton.signal")
_mutex_handle = None
ERROR_ALREADY_EXISTS = 183

AUTORUN_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTORUN_NAME = "ShutdownTimer"
REG_PATH     = r"Software\ShutdownTimer"

SAMPLE_RATE = 44100

GWL_EXSTYLE       = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED     = 0x00080000
GA_ROOT           = 2


def acquire_single_instance():
    global _mutex_handle
    try:
        kernel32 = ctypes.windll.kernel32
        _mutex_handle = kernel32.CreateMutexW(None, False, "ShutdownTimer_SingleInstance_Mutex")
        return kernel32.GetLastError() != ERROR_ALREADY_EXISTS
    except Exception:
        return True


def signal_existing_instance():
    try:
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            f.write("1")
    except Exception:
        pass


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


APP_DIR = _app_dir()


def _reg_read(name):
    if not WINREG_OK:
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, name)
            return val
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _reg_write(name, value):
    if not WINREG_OK:
        return False
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        try:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def load_settings():
    raw = _reg_read("settings")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def save_settings(data):
    try:
        _reg_write("settings", json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


_LOG_BUFFER = collections.deque(maxlen=500)


def log_event(text):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        _LOG_BUFFER.append(f"[{ts}] {text}")
    except Exception:
        pass


def get_log_text():
    if not _LOG_BUFFER:
        return "(log is empty)"
    return "\n".join(_LOG_BUFFER)


def clear_log_memory():
    _LOG_BUFFER.clear()


THEMES = {
    "dark": {
        # --- база ---
        "bg": "#1c1f26",           # основной фон окна
        "bg_dark": "#13161b",       # «утопленные» элементы (спиннеры, поля)
        "fg": "#e8eaf0",            # основной текст
        "fg_dim": "#8b8f9c",        # приглушённый текст
        "white": "#ffffff",
        "selected_fg": "#ffffff",   # текст на активной кнопке-переключателе

        # --- статусы / акценты ---
        "green": "#4ade80",         # «запущено», иконка, прогресс
        "green_b": "#86efac",       # яркая фаза пульсации
        "orange": "#fbbf24",        # «пауза», предупреждения
        "orange_b": "#fde047",
        "orange_hi": "#fde047",     # hover кнопки «Понятно»
        "red": "#f87171",           # «отмена», трей неактивен
        "red_b": "#fca5a5",

        # --- стрелки спиннера ---
        "up_clr": "#6b6f7c",

        # --- стандартные пресеты ---
        "preset_bg": "#262a33",
        "preset_hover": "#31363f",
        "preset_active": "#16a34a",

        # --- свои пресеты ---
        "custom_bg": "#1e392e",
        "custom_hover": "#294a3c",

        # --- переключатели действия / режима ---
        "action_bg": "#262a33",
        "action_hover": "#31363f",
        "action_active": "#16a34a",

        # --- большие кнопки ---
        "btn_start": "#16a34a",
        "btn_start_hov": "#22c55e",
        "btn_pause": "#475569",
        "btn_pause_hov": "#5a6879",
        "btn_cancel": "#7f1d1d",
        "btn_cancel_hov": "#991b1b",

        # --- поля ввода ---
        "entry_bg": "#13161b",
        "entry_border": "#31363f",
    },
    "light": {
        # --- база ---
        "bg": "#f6f8fb",            # мягкий холодный белый
        "bg_dark": "#ffffff",        # «приподнятые» элементы
        "fg": "#1a1f29",
        "fg_dim": "#6b7280",
        "white": "#ffffff",
        "selected_fg": "#ffffff",

        # --- статусы / акценты ---
        "green": "#10b981",
        "green_b": "#059669",       # в светлой теме пульс делаем темнее
        "orange": "#f59e0b",
        "orange_b": "#d97706",
        "orange_hi": "#fbbf24",
        "red": "#ef4444",
        "red_b": "#dc2626",

        # --- стрелки спиннера ---
        "up_clr": "#9aa1ad",

        # --- стандартные пресеты ---
        "preset_bg": "#e8ecf3",
        "preset_hover": "#d8dee8",
        "preset_active": "#059669",

        # --- свои пресеты ---
        "custom_bg": "#d1f0e0",
        "custom_hover": "#b8e5cc",

        # --- переключатели действия / режима ---
        "action_bg": "#e8ecf3",
        "action_hover": "#d8dee8",
        "action_active": "#059669",

        # --- большие кнопки ---
        "btn_start": "#059669",
        "btn_start_hov": "#047857",
        "btn_pause": "#64748b",
        "btn_pause_hov": "#556070",
        "btn_cancel": "#dc2626",
        "btn_cancel_hov": "#b91c1c",

        # --- поля ввода ---
        "entry_bg": "#ffffff",
        "entry_border": "#cbd5e1",
    },
}


ACTIONS = {
    "shutdown":  {"label_key": '⏻  Выключение',  "switch": "/s"},
    "restart":   {"label_key": '⟲  Перезагрузка', "switch": "/r"},
    "sleep":     {"label_key": '☾  Сон',         "switch": None},
    "hibernate": {"label_key": '❄  Гибернация',  "switch": None},
}

ACTION_TOOLTIP_KEYS = {
    "shutdown": ['⏻  Выключение', 'Полностью выключить компьютер по завершении таймера.'],
    "restart":  ['⟲  Перезагрузка', 'Перезагрузить компьютер по завершении таймера.'],
    "sleep":    ['☾  Сон',
                 'Перевести ПК в сон. Быстрое пробуждение, низкое энергопотребление. Не сохраняет состояние на диск.',
                 'Включён всегда, никаких настроек не требует.'],
    "hibernate":['❄  Гибернация',
                 'Сохраняет всю сессию на диск и полностью выключает ПК. Пробуждение — как из обычного выключения, но всё открыто.',
                 '⚠ Требует, чтобы гибернация была включена в параметрах Windows.'],
}


UI_LANGS = {
    'en': 'English', 'ru': 'Русский', 'de': 'Deutsch', 'fr': 'Français',
    'es': 'Español', 'it': 'Italiano', 'pt': 'Português', 'nl': 'Nederlands',
    'pl': 'Polski', 'tr': 'Türkçe', 'cs': 'Čeština', 'hu': 'Magyar',
    'ro': 'Română', 'uk': 'Українська', 'sv': 'Svenska', 'fi': 'Suomi',
    'ja': '日本語', 'ko': '한국어', 'zh': '中文', 'ar': 'العربية'
}


def _mk(ru, en, **kw):
    d = {'ru': ru, 'en': en}
    d.update(kw)
    return d


UI_TR = {
    'Таймер выключения': _mk(
        'Таймер выключения', 'Shutdown Timer',
        de='Abschalttimer', fr="Minuteur d'arrêt", es='Temporizador de apagado',
        it='Timer di spegnimento', pt='Temporizador de desligamento',
        nl='Uitschakeltimer', pl='Timer wyłączania', tr='Kapatma zamanlayıcısı',
        cs='Časovač vypnutí', hu='Leállítási időzítő', ro='Temporizator oprire',
        uk='Таймер вимкнення', sv='Avstängningstimer', fi='Sammutusajastin',
        ja='シャットダウンタイマー', ko='종료 타이머', zh='关机定时器', ar='مؤقت الإيقاف'),
    'Таймер выключения ПК': _mk(
        'Таймер выключения ПК', 'PC Shutdown Timer',
        de='PC-Abschalttimer', fr="Minuteur d'arrêt du PC",
        es='Temporizador de apagado del PC', it='Timer spegnimento PC',
        pt='Temporizador de desligamento do PC', nl='PC-uitschakeltimer',
        pl='Timer wyłączania PC', tr='PC kapatma zamanlayıcısı',
        cs='Časovač vypnutí PC', hu='PC-leállítási időzítő',
        ro='Temporizator oprire PC', uk='Таймер вимкнення ПК',
        sv='PC-avstängningstimer', fi='Tietokoneen sammutusajastin',
        ja='PCシャットダウンタイマー', ko='PC 종료 타이머',
        zh='电脑关机定时器', ar='مؤقت إيقاف تشغيل الكمبيوتر'),
    'Действие по завершении': _mk(
        'Действие по завершении', 'Action on completion',
        de='Aktion nach Ablauf', fr='Action à la fin',
        es='Acción al finalizar', it='Azione al termine',
        pt='Ação ao terminar', nl='Actie na afloop',
        pl='Działanie po zakończeniu', tr='Bitişte eylem',
        cs='Akce po dokončení', hu='Művelet befejezéskor',
        ro='Acțiune la final', uk='Дія після завершення',
        sv='Åtgärd vid slut', fi='Toiminto lopussa',
        ja='終了時の操作', ko='완료 시 동작', zh='完成后的操作', ar='الإجراء عند الانتهاء'),
    '⏻  Выключение': _mk(
        '⏻  Выключение', '⏻  Shutdown',
        de='⏻  Herunterfahren', fr='⏻  Arrêter', es='⏻  Apagar',
        it='⏻  Spegni', pt='⏻  Desligar', nl='⏻  Afsluiten',
        pl='⏻  Wyłącz', tr='⏻  Kapat', cs='⏻  Vypnout',
        hu='⏻  Leállítás', ro='⏻  Oprește', uk='⏻  Вимкнути',
        sv='⏻  Stäng av', fi='⏻  Sammuta',
        ja='⏻  シャットダウン', ko='⏻  종료', zh='⏻  关机', ar='⏻  إيقاف التشغيل'),
    '⟲  Перезагрузка': _mk(
        '⟲  Перезагрузка', '⟲  Restart',
        de='⟲  Neu starten', fr='⟲  Redémarrer', es='⟲  Reiniciar',
        it='⟲  Riavvia', pt='⟲  Reiniciar', nl='⟲  Herstarten',
        pl='⟲  Uruchom ponownie', tr='⟲  Yeniden başlat',
        cs='⟲  Restartovat', hu='⟲  Újraindítás', ro='⟲  Repornește',
        uk='⟲  Перезавантажити', sv='⟲  Starta om', fi='⟲  Käynnistä uudelleen',
        ja='⟲  再起動', ko='⟲  재시작', zh='⟲  重启', ar='⟲  إعادة التشغيل'),
    '☾  Сон': _mk(
        '☾  Сон', '☾  Sleep',
        de='☾  Ruhezustand', fr='☾  Veille', es='☾  Suspender',
        it='☾  Sospendi', pt='☾  Suspender', nl='☾  Slaapstand',
        pl='☾  Uśpij', tr='☾  Uyku', cs='☾  Spánek',
        hu='☾  Alvás', ro='☾  Repaus', uk='☾  Сон',
        sv='☾  Viloläge', fi='☾  Lepotila',
        ja='☾  スリープ', ko='☾  절전', zh='☾  睡眠', ar='☾  السكون'),
    '❄  Гибернация': _mk(
        '❄  Гибернация', '❄  Hibernate',
        de='❄  Energiesparmodus', fr='❄  Hibernation', es='❄  Hibernar',
        it='❄  Ibernazione', pt='❄  Hibernar', nl='❄  Slaapstand naar schijf',
        pl='❄  Hibernacja', tr='❄  Hazırda beklet', cs='❄  Hibernace',
        hu='❄  Hibernálás', ro='❄  Hibernare', uk='❄  Гібернація',
        sv='❄  Viloläge på disk', fi='❄  Lepotila levylle',
        ja='❄  休止状態', ko='❄  최대 절전', zh='❄  休眠', ar='❄  الإسبات'),
    'Когда выключить': _mk(
        'Когда выключить', 'When to shut down',
        de='Wann herunterfahren', fr="Quand arrêter",
        es='Cuándo apagar', it='Quando spegnere',
        pt='Quando desligar', nl='Wanneer afsluiten',
        pl='Kiedy wyłączyć', tr='Ne zaman kapatılsın',
        cs='Kdy vypnout', hu='Mikor álljon le',
        ro='Când să oprească', uk='Коли вимкнути',
        sv='När ska stängas av', fi='Milloin sammutetaan',
        ja='いつシャットダウン', ko='종료 시간', zh='何时关机', ar='متى يتم الإيقاف'),
    '⏱  Через время': _mk(
        '⏱  Через время', '⏱  After a duration',
        de='⏱  Nach einer Dauer', fr='⏱  Après un délai',
        es='⏱  Tras un tiempo', it='⏱  Dopo un tempo',
        pt='⏱  Após um tempo', nl='⏱  Na een duur',
        pl='⏱  Po czasie', tr='⏱  Belirli süre sonra',
        cs='⏱  Po čase', hu='⏱  Idő után', ro='⏱  După un timp',
        uk='⏱  Через час', sv='⏱  Efter en tid', fi='⏱  Ajan kuluttua',
        ja='⏱  時間後', ko='⏱  시간 후', zh='⏱  时长后', ar='⏱  بعد مدة'),
    '🕐  В конкретное время': _mk(
        '🕐  В конкретное время', '🕐  At a specific time',
        de='🕐  Zu bestimmter Zeit', fr='🕐  À une heure précise',
        es='🕐  A una hora concreta', it='🕐  A un orario specifico',
        pt='🕐  A uma hora específica', nl='🕐  Op een specifiek tijdstip',
        pl='🕐  O określonej godzinie', tr='🕐  Belirli bir saatte',
        cs='🕐  V určený čas', hu='🕐  Adott időpontban',
        ro='🕐  La o oră anume', uk='🕐  У конкретний час',
        sv='🕐  Vid en specifik tid', fi='🕐  Tiettyyn aikaan',
        ja='🕐  指定時刻', ko='🕐  특정 시간에', zh='🕐  指定时间', ar='🕐  في وقت محدد'),
    'Дни': _mk('Дни', 'Days', de='Tage', fr='Jours', es='Días', it='Giorni',
               pt='Dias', nl='Dagen', pl='Dni', tr='Gün', cs='Dny', hu='Nap',
               ro='Zile', uk='Дні', sv='Dagar', fi='Päivät',
               ja='日', ko='일', zh='天', ar='أيام'),
    'Часы': _mk('Часы', 'Hours', de='Stunden', fr='Heures', es='Horas',
                it='Ore', pt='Horas', nl='Uren', pl='Godziny', tr='Saat',
                cs='Hodiny', hu='Óra', ro='Ore', uk='Години', sv='Timmar',
                fi='Tunnit', ja='時間', ko='시간', zh='小时', ar='ساعات'),
    'Минуты': _mk('Минуты', 'Minutes', de='Minuten', fr='Minutes',
                  es='Minutos', it='Minuti', pt='Minutos', nl='Minuten',
                  pl='Minuty', tr='Dakika', cs='Minuty', hu='Perc',
                  ro='Minute', uk='Хвилини', sv='Minuter', fi='Minuutit',
                  ja='分', ko='분', zh='分钟', ar='دقائق'),
    'Секунды': _mk('Секунды', 'Seconds', de='Sekunden', fr='Secondes',
                   es='Segundos', it='Secondi', pt='Segundos', nl='Seconden',
                   pl='Sekundy', tr='Saniye', cs='Sekundy', hu='Másodperc',
                   ro='Secunde', uk='Секунди', sv='Sekunder', fi='Sekunnit',
                   ja='秒', ko='초', zh='秒', ar='ثواني'),
    'Быстрые пресеты': _mk(
        'Быстрые пресеты', 'Quick presets',
        de='Schnellvoreinstellungen', fr='Préréglages rapides',
        es='Preajustes rápidos', it='Preset rapidi',
        pt='Predefinições rápidas', nl='Snelle presets',
        pl='Szybkie presety', tr='Hızlı hazır ayarlar',
        cs='Rychlé předvolby', hu='Gyors beállítások',
        ro='Presetări rapide', uk='Швидкі пресети',
        sv='Snabbval', fi='Pikavalinnat',
        ja='クイックプリセット', ko='빠른 프리셋', zh='快速预设', ar='إعدادات سريعة'),
    'Свои пресеты': _mk(
        'Свои пресеты', 'Custom presets',
        de='Eigene Voreinstellungen', fr='Préréglages personnalisés',
        es='Preajustes personalizados', it='Preset personalizzati',
        pt='Predefinições personalizadas', nl='Aangepaste presets',
        pl='Własne presety', tr='Özel hazır ayarlar',
        cs='Vlastní předvolby', hu='Egyéni beállítások',
        ro='Presetări personalizate', uk='Власні пресети',
        sv='Egna snabbval', fi='Omat pikavalinnat',
        ja='カスタムプリセット', ko='사용자 프리셋', zh='自定义预设', ar='إعدادات مخصصة'),
    '▶  Запустить': _mk(
        '▶  Запустить', '▶  Start',
        de='▶  Starten', fr='▶  Démarrer', es='▶  Iniciar',
        it='▶  Avvia', pt='▶  Iniciar', nl='▶  Starten',
        pl='▶  Uruchom', tr='▶  Başlat', cs='▶  Spustit',
        hu='▶  Indítás', ro='▶  Pornește', uk='▶  Запустити',
        sv='▶  Starta', fi='▶  Käynnistä',
        ja='▶  開始', ko='▶  시작', zh='▶  开始', ar='▶  بدء'),
    '⏸  Пауза': _mk(
        '⏸  Пауза', '⏸  Pause',
        de='⏸  Pause', fr='⏸  Pause', es='⏸  Pausa',
        it='⏸  Pausa', pt='⏸  Pausa', nl='⏸  Pauze',
        pl='⏸  Pauza', tr='⏸  Duraklat', cs='⏸  Pozastavit',
        hu='⏸  Szünet', ro='⏸  Pauză', uk='⏸  Пауза',
        sv='⏸  Paus', fi='⏸  Tauko',
        ja='⏸  一時停止', ko='⏸  일시정지', zh='⏸  暂停', ar='⏸  إيقاف مؤقت'),
    '▶  Продолжить': _mk(
        '▶  Продолжить', '▶  Resume',
        de='▶  Fortsetzen', fr='▶  Reprendre', es='▶  Continuar',
        it='▶  Riprendi', pt='▶  Retomar', nl='▶  Hervatten',
        pl='▶  Wznów', tr='▶  Devam et', cs='▶  Pokračovat',
        hu='▶  Folytatás', ro='▶  Continuă', uk='▶  Продовжити',
        sv='▶  Fortsätt', fi='▶  Jatka',
        ja='▶  再開', ko='▶  재개', zh='▶  继续', ar='▶  استئناف'),
    '✕  Отменить': _mk(
        '✕  Отменить', '✕  Cancel',
        de='✕  Abbrechen', fr='✕  Annuler', es='✕  Cancelar',
        it='✕  Annulla', pt='✕  Cancelar', nl='✕  Annuleren',
        pl='✕  Anuluj', tr='✕  İptal', cs='✕  Zrušit',
        hu='✕  Mégse', ro='✕  Anulează', uk='✕  Скасувати',
        sv='✕  Avbryt', fi='✕  Peruuta',
        ja='✕  キャンセル', ko='✕  취소', zh='✕  取消', ar='✕  إلغاء'),
    'Таймер не запущен': _mk(
        'Таймер не запущен', 'Timer not running',
        de='Timer nicht gestartet', fr='Minuteur non lancé',
        es='Temporizador no iniciado', it='Timer non avviato',
        pt='Temporizador não iniciado', nl='Timer niet gestart',
        pl='Timer nie uruchomiony', tr='Zamanlayıcı çalışmıyor',
        cs='Časovač není spuštěn', hu='Az időzítő nem fut',
        ro='Temporizatorul nu rulează', uk='Таймер не запущено',
        sv='Timern körs inte', fi='Ajastin ei ole käynnissä',
        ja='タイマー未起動', ko='타이머가 실행되지 않음',
        zh='定时器未运行', ar='المؤقت غير مشغّل'),
    'Запущено': _mk(
        'Запущено', 'Running',
        de='Läuft', fr='En cours', es='En ejecución',
        it='In esecuzione', pt='A correr', nl='Actief',
        pl='Uruchomiony', tr='Çalışıyor', cs='Spuštěno',
        hu='Fut', ro='Rulează', uk='Запущено',
        sv='Igång', fi='Käynnissä',
        ja='実行中', ko='실행 중', zh='运行中', ar='قيد التشغيل'),
    'Пауза': _mk(
        'Пауза', 'Paused',
        de='Pausiert', fr='En pause', es='En pausa',
        it='In pausa', pt='Em pausa', nl='Gepauzeerd',
        pl='Wstrzymany', tr='Duraklatıldı', cs='Pozastaveno',
        hu='Szüneteltetve', ro='În pauză', uk='Пауза',
        sv='Pausad', fi='Tauko',
        ja='一時停止', ko='일시정지', zh='已暂停', ar='متوقف مؤقتًا'),
    'Таймер отменён': _mk(
        'Таймер отменён', 'Timer cancelled',
        de='Timer abgebrochen', fr='Minuteur annulé',
        es='Temporizador cancelado', it='Timer annullato',
        pt='Temporizador cancelado', nl='Timer geannuleerd',
        pl='Timer anulowany', tr='Zamanlayıcı iptal edildi',
        cs='Časovač zrušen', hu='Időzítő megszakítva',
        ro='Temporizator anulat', uk='Таймер скасовано',
        sv='Timern avbruten', fi='Ajastin peruttu',
        ja='タイマー中止', ko='타이머 취소됨',
        zh='定时器已取消', ar='تم إلغاء المؤقت'),
    'Свернуть': _mk(
        'Свернуть', 'Minimize',
        de='Minimieren', fr='Réduire', es='Minimizar',
        it='Riduci', pt='Minimizar', nl='Minimaliseren',
        pl='Zwiń', tr='Küçült', cs='Minimalizovat',
        hu='Kicsinyítés', ro='Minimizează', uk='Згорнути',
        sv='Minimera', fi='Pienennä',
        ja='最小化', ko='최소화', zh='最小化', ar='تصغير'),
    'Журнал': _mk(
        'Журнал', 'Log',
        de='Protokoll', fr='Journal', es='Registro',
        it='Registro', pt='Registo', nl='Logboek',
        pl='Dziennik', tr='Günlük', cs='Protokol',
        hu='Napló', ro='Jurnal', uk='Журнал',
        sv='Logg', fi='Loki',
        ja='ログ', ko='로그', zh='日志', ar='السجل'),
    '💾 Экспорт': _mk(
        '💾 Экспорт', '💾 Export',
        de='💾 Export', fr='💾 Exporter', es='💾 Exportar',
        it='💾 Esporta', pt='💾 Exportar', nl='💾 Exporteren',
        pl='💾 Eksportuj', tr='💾 Dışa aktar', cs='💾 Export',
        hu='💾 Exportálás', ro='💾 Exportă', uk='💾 Експорт',
        sv='💾 Exportera', fi='💾 Vie',
        ja='💾 エクスポート', ko='💾 내보내기', zh='💾 导出', ar='💾 تصدير'),
    '📥 Импорт': _mk(
        '📥 Импорт', '📥 Import',
        de='📥 Import', fr='📥 Importer', es='📥 Importar',
        it='📥 Importa', pt='📥 Importar', nl='📥 Importeren',
        pl='📥 Importuj', tr='📥 İçe aktar', cs='📥 Import',
        hu='📥 Importálás', ro='📥 Importă', uk='📥 Імпорт',
        sv='📥 Importera', fi='📥 Tuo',
        ja='📥 インポート', ko='📥 가져오기', zh='📥 导入', ar='📥 استيراد'),
    'Закрыть': _mk(
        'Закрыть', 'Close',
        de='Schließen', fr='Fermer', es='Cerrar',
        it='Chiudi', pt='Fechar', nl='Sluiten',
        pl='Zamknij', tr='Kapat', cs='Zavřít',
        hu='Bezárás', ro='Închide', uk='Закрити',
        sv='Stäng', fi='Sulje',
        ja='閉じる', ko='닫기', zh='关闭', ar='إغلاق'),
    'Осталось:': _mk(
        'Осталось:', 'Remaining:',
        de='Verbleibend:', fr='Restant :', es='Restante:',
        it='Rimanente:', pt='Restante:', nl='Resterend:',
        pl='Pozostało:', tr='Kalan:', cs='Zbývá:',
        hu='Hátralévő:', ro='Rămas:', uk='Залишилось:',
        sv='Återstår:', fi='Jäljellä:',
        ja='残り：', ko='남음:', zh='剩余：', ar='المتبقي:'),
    'Осталось': _mk(
        'Осталось', 'Remaining',
        de='Verbleibend', fr='Restant', es='Restante',
        it='Rimanente', pt='Restante', nl='Resterend',
        pl='Pozostało', tr='Kalan', cs='Zbývá',
        hu='Hátralévő', ro='Rămas', uk='Залишилось',
        sv='Återstår', fi='Jäljellä',
        ja='残り', ko='남음', zh='剩余', ar='المتبقي'),
    'Действие:': _mk(
        'Действие:', 'Action:',
        de='Aktion:', fr='Action :', es='Acción:',
        it='Azione:', pt='Ação:', nl='Actie:',
        pl='Działanie:', tr='Eylem:', cs='Akce:',
        hu='Művelet:', ro='Acțiune:', uk='Дія:',
        sv='Åtgärd:', fi='Toiminto:',
        ja='操作：', ko='동작:', zh='操作：', ar='الإجراء:'),
    'через': _mk(
        'через', 'in',
        de='in', fr='dans', es='en', it='tra', pt='em',
        nl='over', pl='za', tr='sonra', cs='za',
        hu='ennyi múlva:', ro='peste', uk='через',
        sv='om', fi='kuluttua',
        ja='あと', ko='후', zh='后', ar='خلال'),
    'сегодня': _mk(
        'сегодня', 'today',
        de='heute', fr="aujourd'hui", es='hoy',
        it='oggi', pt='hoje', nl='vandaag',
        pl='dziś', tr='bugün', cs='dnes',
        hu='ma', ro='astăzi', uk='сьогодні',
        sv='idag', fi='tänään',
        ja='今日', ko='오늘', zh='今天', ar='اليوم'),
    'завтра': _mk(
        'завтра', 'tomorrow',
        de='morgen', fr='demain', es='mañana',
        it='domani', pt='amanhã', nl='morgen',
        pl='jutro', tr='yarın', cs='zítra',
        hu='holnap', ro='mâine', uk='завтра',
        sv='imorgon', fi='huomenna',
        ja='明日', ko='내일', zh='明天', ar='غدًا'),
    'в': _mk('в', 'at', de='um', fr='à', es='a las', it='alle', pt='às',
             nl='om', pl='o', tr='saat', cs='v', hu='-kor', ro='la',
             uk='о', sv='kl', fi='klo', ja='に', ko='에', zh='在', ar='في'),
    'д': _mk('д', 'd', de='T', fr='j', es='d', it='g', pt='d', nl='d',
             pl='d', tr='g', cs='d', hu='n', ro='z', uk='д', sv='d', fi='p',
             ja='日', ko='일', zh='天', ar='ي'),
    'ч': _mk('ч', 'h', de='Std', fr='h', es='h', it='h', pt='h', nl='u',
             pl='g', tr='s', cs='h', hu='ó', ro='h', uk='год', sv='t', fi='t',
             ja='時', ko='시', zh='时', ar='س'),
    'мин': _mk('мин', 'min', de='Min', fr='min', es='min', it='min',
               pt='min', nl='min', pl='min', tr='dk', cs='min', hu='p',
               ro='min', uk='хв', sv='min', fi='min', ja='分', ko='분',
               zh='分', ar='د'),
    'Понятно': _mk(
        'Понятно', 'OK',
        de='Verstanden', fr='OK', es='Entendido',
        it='OK', pt='OK', nl='Begrepen',
        pl='OK', tr='Tamam', cs='OK',
        hu='Rendben', ro='OK', uk='Зрозуміло',
        sv='OK', fi='OK',
        ja='了解', ko='확인', zh='好的', ar='حسنًا'),
    'Обновить': _mk(
        'Обновить', 'Refresh',
        de='Aktualisieren', fr='Actualiser', es='Actualizar',
        it='Aggiorna', pt='Atualizar', nl='Vernieuwen',
        pl='Odśwież', tr='Yenile', cs='Obnovit',
        hu='Frissítés', ro='Reîmprospătează', uk='Оновити',
        sv='Uppdatera', fi='Päivitä',
        ja='更新', ko='새로고침', zh='刷新', ar='تحديث'),
    'Очистить': _mk(
        'Очистить', 'Clear',
        de='Leeren', fr='Effacer', es='Borrar',
        it='Cancella', pt='Limpar', nl='Wissen',
        pl='Wyczyść', tr='Temizle', cs='Vymazat',
        hu='Törlés', ro='Golește', uk='Очистити',
        sv='Rensa', fi='Tyhjennä',
        ja='クリア', ko='지우기', zh='清除', ar='مسح'),
    'Отмена': _mk(
        'Отмена', 'Cancel',
        de='Abbrechen', fr='Annuler', es='Cancelar',
        it='Annulla', pt='Cancelar', nl='Annuleren',
        pl='Anuluj', tr='İptal', cs='Zrušit',
        hu='Mégse', ro='Anulare', uk='Скасувати',
        sv='Avbryt', fi='Peruuta',
        ja='キャンセル', ko='취소', zh='取消', ar='إلغاء'),
    'Создать': _mk(
        'Создать', 'Create',
        de='Erstellen', fr='Créer', es='Crear',
        it='Crea', pt='Criar', nl='Aanmaken',
        pl='Utwórz', tr='Oluştur', cs='Vytvořit',
        hu='Létrehozás', ro='Creează', uk='Створити',
        sv='Skapa', fi='Luo',
        ja='作成', ko='만들기', zh='创建', ar='إنشاء'),
    'Название': _mk(
        'Название', 'Name',
        de='Name', fr='Nom', es='Nombre',
        it='Nome', pt='Nome', nl='Naam',
        pl='Nazwa', tr='Ad', cs='Název',
        hu='Név', ro='Nume', uk='Назва',
        sv='Namn', fi='Nimi',
        ja='名前', ko='이름', zh='名称', ar='الاسم'),
    'Новый пресет': _mk(
        'Новый пресет', 'New preset',
        de='Neue Voreinstellung', fr='Nouveau préréglage',
        es='Nuevo preajuste', it='Nuovo preset',
        pt='Nova predefinição', nl='Nieuwe preset',
        pl='Nowy preset', tr='Yeni hazır ayar', cs='Nová předvolba',
        hu='Új beállítás', ro='Presetă nouă', uk='Новий пресет',
        sv='Ny förinställning', fi='Uusi esiasetus',
        ja='新しいプリセット', ko='새 프리셋', zh='新预设', ar='إعداد مسبق جديد'),
    'Мой пресет': _mk(
        'Мой пресет', 'My preset',
        de='Meine Voreinstellung', fr='Mon préréglage',
        es='Mi preajuste', it='Il mio preset',
        pt='Minha predefinição', nl='Mijn preset',
        pl='Mój preset', tr='Hazır ayarım', cs='Moje předvolba',
        hu='Saját beállításom', ro='Presetul meu', uk='Мій пресет',
        sv='Min förinställning', fi='Oma esiasetus',
        ja='自分のプリセット', ko='내 프리셋', zh='我的预设', ar='إعدادي'),
    'Без названия': _mk(
        'Без названия', 'Untitled',
        de='Unbenannt', fr='Sans titre', es='Sin título',
        it='Senza titolo', pt='Sem título', nl='Naamloos',
        pl='Bez nazwy', tr='Başlıksız', cs='Bez názvu',
        hu='Névtelen', ro='Fără titlu', uk='Без назви',
        sv='Namnlös', fi='Nimetön',
        ja='無題', ko='제목 없음', zh='未命名', ar='بدون عنوان'),
    'Журнал событий': _mk(
        'Журнал событий', 'Event log',
        de='Ereignisprotokoll', fr='Journal des événements',
        es='Registro de eventos', it='Registro eventi',
        pt='Registo de eventos', nl='Gebeurtenislogboek',
        pl='Dziennik zdarzeń', tr='Olay günlüğü',
        cs='Protokol událostí', hu='Eseménynapló',
        ro='Jurnal de evenimente', uk='Журнал подій',
        sv='Händelselogg', fi='Tapahtumaloki',
        ja='イベントログ', ko='이벤트 로그', zh='事件日志', ar='سجل الأحداث'),
    'Журнал в памяти': _mk(
        'Журнал в памяти', 'Log in memory',
        de='Protokoll im Speicher', fr='Journal en mémoire',
        es='Registro en memoria', it='Registro in memoria',
        pt='Registo em memória', nl='Logboek in geheugen',
        pl='Dziennik w pamięci', tr='Bellekteki günlük',
        cs='Protokol v paměti', hu='Napló a memóriában',
        ro='Jurnal în memorie', uk='Журнал у пам’яті',
        sv='Logg i minnet', fi='Loki muistissa',
        ja='メモリ内のログ', ko='메모리 내 로그',
        zh='内存中的日志', ar='السجل في الذاكرة'),
    'записей': _mk(
        'записей', 'records',
        de='Einträge', fr='entrées', es='entradas',
        it='voci', pt='registos', nl='vermeldingen',
        pl='wpisów', tr='kayıt', cs='záznamů',
        hu='bejegyzés', ro='înregistrări', uk='записів',
        sv='poster', fi='merkintää',
        ja='件', ko='개', zh='条', ar='سجل'),
    'макс.': _mk(
        'макс.', 'max.',
        de='max.', fr='max.', es='máx.',
        it='max.', pt='máx.', nl='max.',
        pl='maks.', tr='maks.', cs='max.',
        hu='max.', ro='max.', uk='макс.',
        sv='max.', fi='max.',
        ja='最大', ko='최대', zh='最大', ar='الحد الأقصى'),
    'Открыть окно': _mk(
        'Открыть окно', 'Open window',
        de='Fenster öffnen', fr='Ouvrir la fenêtre',
        es='Abrir ventana', it='Apri finestra',
        pt='Abrir janela', nl='Venster openen',
        pl='Otwórz okno', tr='Pencereyi aç', cs='Otevřít okno',
        hu='Ablak megnyitása', ro='Deschide fereastra', uk='Відкрити вікно',
        sv='Öppna fönster', fi='Avaa ikkuna',
        ja='ウィンドウを開く', ko='창 열기', zh='打开窗口', ar='فتح النافذة'),
    'Показать виджет': _mk(
        'Показать виджет', 'Show widget',
        de='Widget anzeigen', fr='Afficher le widget',
        es='Mostrar widget', it='Mostra widget',
        pt='Mostrar widget', nl='Widget tonen',
        pl='Pokaż widget', tr="Widget'ı göster", cs='Zobrazit widget',
        hu='Widget megjelenítése', ro='Arată widgetul', uk='Показати віджет',
        sv='Visa widget', fi='Näytä widget',
        ja='ウィジェットを表示', ko='위젯 표시', zh='显示小部件', ar='إظهار الودجت'),
    '🎮 Игровой режим': _mk(
        '🎮 Игровой режим', '🎮 Game mode',
        de='🎮 Spielmodus', fr='🎮 Mode jeu', es='🎮 Modo juego',
        it='🎮 Modalità gioco', pt='🎮 Modo de jogo', nl='🎮 Spelmodus',
        pl='🎮 Tryb gry', tr='🎮 Oyun modu', cs='🎮 Herní režim',
        hu='🎮 Játékmód', ro='🎮 Mod joc', uk='🎮 Ігровий режим',
        sv='🎮 Spelläge', fi='🎮 Pelitila',
        ja='🎮 ゲームモード', ko='🎮 게임 모드', zh='🎮 游戏模式', ar='🎮 وضع اللعب'),
    'Автозапуск с Windows': _mk(
        'Автозапуск с Windows', 'Autorun with Windows',
        de='Autostart mit Windows', fr='Démarrage avec Windows',
        es='Inicio con Windows', it='Avvio con Windows',
        pt='Arranque com Windows', nl='Opstarten met Windows',
        pl='Autostart z Windows', tr='Windows ile başlat',
        cs='Autostart s Windows', hu='Indítás a Windows-szal',
        ro='Pornire cu Windows', uk='Автозапуск з Windows',
        sv='Autostart med Windows', fi='Käynnistys Windowsin kanssa',
        ja='Windows起動時に実行', ko='Windows 시작 시 실행',
        zh='随 Windows 启动', ar='التشغيل مع ويندوز'),
    'Выход': _mk(
        'Выход', 'Exit',
        de='Beenden', fr='Quitter', es='Salir',
        it='Esci', pt='Sair', nl='Afsluiten',
        pl='Wyjście', tr='Çıkış', cs='Konec',
        hu='Kilépés', ro='Ieșire', uk='Вихід',
        sv='Avsluta', fi='Poistu',
        ja='終了', ko='종료', zh='退出', ar='خروج'),
    'Через реестр': _mk(
        'Через реестр', 'Via registry',
        de='Über Registry', fr='Via le registre', es='Vía registro',
        it='Tramite registro', pt='Via registo', nl='Via register',
        pl='Przez rejestr', tr='Kayıt defteri ile', cs='Přes registr',
        hu='Rendszerleíró adatbázison át', ro='Prin registru', uk='Через реєстр',
        sv='Via registret', fi='Rekisterin kautta',
        ja='レジストリ経由', ko='레지스트리를 통해', zh='通过注册表', ar='عبر السجل'),
    'Через папку Startup': _mk(
        'Через папку Startup', 'Via Startup folder',
        de='Über Startup-Ordner', fr='Via dossier Démarrage',
        es='Vía carpeta Inicio', it='Tramite cartella Esecuzione automatica',
        pt='Via pasta Inicializar', nl='Via opstartmap',
        pl='Przez folder Startup', tr='Başlangıç klasörü ile',
        cs='Přes složku Po spuštění', hu='Indító mappán keresztül',
        ro='Prin folderul Startup', uk='Через папку Startup',
        sv='Via Startup-mappen', fi='Kautta Startup-kansion',
        ja='Startupフォルダ経由', ko='시작프로그램 폴더를 통해',
        zh='通过 Startup 文件夹', ar='عبر مجلد بدء التشغيل'),
    'Отключить автозагрузку': _mk(
        'Отключить автозагрузку', 'Disable autorun',
        de='Autostart deaktivieren', fr='Désactiver le démarrage auto',
        es='Desactivar inicio automático', it='Disabilita avvio automatico',
        pt='Desativar arranque automático', nl='Autostart uitschakelen',
        pl='Wyłącz autostart', tr='Otomatik başlatmayı devre dışı bırak',
        cs='Zakázat autostart', hu='Autostart kikapcsolása',
        ro='Dezactivează pornirea automată', uk='Вимкнути автозапуск',
        sv='Inaktivera autostart', fi='Poista automaattikäynnistys',
        ja='自動起動を無効化', ko='자동 실행 비활성화',
        zh='禁用自启动', ar='تعطيل التشغيل التلقائي'),
    'Запускать свёрнутым в трей': _mk(
        'Запускать свёрнутым в трей', 'Start minimized to tray',
        de='Minimiert im Infobereich starten', fr='Démarrer réduit dans la barre',
        es='Iniciar minimizado en la bandeja', it='Avvia ridotto nella barra',
        pt='Iniciar minimizado na bandeja', nl='Geminimaliseerd starten',
        pl='Uruchamiaj zminimalizowany w zasobniku', tr='Tepsiye küçültülmüş başlat',
        cs='Spouštět minimalizovaně v oznamovací oblasti',
        hu='Indítás a tálcára kicsinyítve', ro='Pornește minimizat în tavă',
        uk='Запускати згорнутим у трей', sv='Starta minimerad i aktivitetsfältet',
        fi='Käynnistä pienennettynä ilmaisinalueelle',
        ja='トレイに最小化して起動', ko='트레이로 최소화하여 시작',
        zh='最小化到托盘启动', ar='بدء التشغيل مصغرًا في شريط النظام'),
    'Приложение свёрнуто в трей.': _mk(
        'Приложение свёрнуто в трей.', 'Application minimized to tray.',
        de='Anwendung im Infobereich minimiert.', fr="Application réduite dans la barre.",
        es='Aplicación minimizada en la bandeja.', it='Applicazione ridotta nella barra.',
        pt='Aplicação minimizada para a bandeja.', nl='Applicatie geminimaliseerd naar systeemvak.',
        pl='Aplikacja zminimalizowana do zasobnika.', tr='Uygulama tepsiye küçültüldü.',
        cs='Aplikace minimalizována do oznamovací oblasti.',
        hu='Az alkalmazás a tálcára kicsinyítve.', ro='Aplicație minimizată în tavă.',
        uk='Застосунок згорнуто в трей.', sv='Programmet minimeras till aktivitetsfältet.',
        fi='Sovellus pienennetty ilmaisinalueelle.',
        ja='アプリをトレイに最小化しました。', ko='앱이 트레이로 최소화되었습니다.',
        zh='应用已最小化到托盘。', ar='تم تصغير التطبيق إلى شريط النظام.'),
    'Приложение запущено и свёрнуто в трей.': _mk(
        'Приложение запущено и свёрнуто в трей.', 'Application started and minimized to tray.',
        de='Anwendung gestartet und im Infobereich minimiert.',
        fr="Application démarrée et réduite dans la barre.",
        es='Aplicación iniciada y minimizada en la bandeja.',
        it='Applicazione avviata e ridotta nella barra.',
        pt='Aplicação iniciada e minimizada para a bandeja.',
        nl='Applicatie gestart en geminimaliseerd naar systeemvak.',
        pl='Aplikacja uruchomiona i zminimalizowana do zasobnika.',
        tr='Uygulama başlatıldı ve tepsiye küçültüldü.',
        cs='Aplikace spuštěna a minimalizována do oznamovací oblasti.',
        hu='Az alkalmazás elindult és a tálcára kicsinyítve.',
        ro='Aplicație pornită și minimizată în tavă.',
        uk='Застосунок запущено та згорнуто в трей.',
        sv='Programmet startades och minimeras till aktivitetsfältet.',
        fi='Sovellus käynnistyi ja pienennettiin ilmaisinalueelle.',
        ja='アプリを起動し、トレイに最小化しました。',
        ko='앱이 시작되어 트레이로 최소화되었습니다.',
        zh='应用已启动并最小化到托盘。', ar='تم بدء التطبيق وتصغيره إلى شريط النظام.'),
    'Таймер выключения ПК — не запущен': _mk(
        'Таймер выключения ПК — не запущен', 'PC Shutdown Timer — not running',
        de='PC-Abschalttimer — nicht gestartet', fr="Minuteur d'arrêt du PC — non lancé",
        es='Temporizador de apagado — no iniciado', it='Timer spegnimento PC — non avviato',
        pt='Temporizador de desligamento — não iniciado', nl='PC-uitschakeltimer — niet gestart',
        pl='Timer wyłączania PC — nie uruchomiony', tr='PC kapatma zamanlayıcısı — çalışmıyor',
        cs='Časovač vypnutí PC — není spuštěn', hu='PC-leállítási időzítő — nem fut',
        ro='Temporizator oprire PC — nu rulează', uk='Таймер вимкнення ПК — не запущено',
        sv='PC-avstängningstimer — körs inte', fi='Tietokoneen sammutusajastin — ei käynnissä',
        ja='PCシャットダウンタイマー — 未起動', ko='PC 종료 타이머 — 실행되지 않음',
        zh='电脑关机定时器 — 未运行', ar='مؤقت إيقاف تشغيل الكمبيوتر — غير مشغّل'),
    'Отсчёт от текущего момента': _mk(
        'Отсчёт от текущего момента', 'Countdown from now',
        de='Countdown ab jetzt', fr="Compte à rebours à partir de maintenant",
        es='Cuenta atrás desde ahora', it='Conto alla rovescia da adesso',
        pt='Contagem decrescente a partir de agora', nl='Aftellen vanaf nu',
        pl='Odliczanie od teraz', tr='Şu andan itibaren geri sayım',
        cs='Odpočet od teď', hu='Visszaszámlálás mostantól',
        ro='Numărătoare inversă de acum', uk='Відлік від поточного моменту',
        sv='Nedräkning från nu', fi='Lähtölaskenta tästä hetkestä',
        ja='現在からのカウントダウン', ko='지금부터 카운트다운',
        zh='从现在起倒计时', ar='العد التنازلي من الآن'),
    'Выключить в конкретное время': _mk(
        'Выключить в конкретное время', 'Shut down at a specific time',
        de='Zu bestimmter Zeit herunterfahren', fr='Arrêter à une heure précise',
        es='Apagar a una hora concreta', it='Spegni a un orario specifico',
        pt='Desligar a uma hora específica', nl='Afsluiten op een specifiek tijdstip',
        pl='Wyłącz o określonej godzinie', tr='Belirli bir saatte kapat',
        cs='Vypnout v určený čas', hu='Leállítás adott időpontban',
        ro='Oprește la o oră anume', uk='Вимкнути в конкретний час',
        sv='Stäng av vid en specifik tid', fi='Sammuta tiettyyn aikaan',
        ja='指定時刻にシャットダウン', ko='특정 시간에 종료',
        zh='在指定时间关机', ar='إيقاف التشغيل في وقت محدد'),
    'Переключить на светлую тему': _mk(
        'Переключить на светлую тему', 'Switch to light theme',
        de='Zum hellen Design wechseln', fr='Passer au thème clair',
        es='Cambiar al tema claro', it='Passa al tema chiaro',
        pt='Mudar para tema claro', nl='Naar licht thema schakelen',
        pl='Przełącz na jasny motyw', tr='Açık temaya geç',
        cs='Přepnout na světlé téma', hu='Váltás világos témára',
        ro='Comută pe tema deschisă', uk='Перемкнути на світлу тему',
        sv='Byt till ljust tema', fi='Vaihda vaaleaan teemaan',
        ja='ライトテーマに切り替え', ko='라이트 테마로 전환',
        zh='切换到浅色主题', ar='التبديل إلى السمة الفاتحة'),
    'Переключить на тёмную тему': _mk(
        'Переключить на тёмную тему', 'Switch to dark theme',
        de='Zum dunklen Design wechseln', fr='Passer au thème sombre',
        es='Cambiar al tema oscuro', it='Passa al tema scuro',
        pt='Mudar para tema escuro', nl='Naar donker thema schakelen',
        pl='Przełącz na ciemny motyw', tr='Koyu temaya geç',
        cs='Přepnout na tmavé téma', hu='Váltás sötét témára',
        ro='Comută pe tema închisă', uk='Перемкнути на темну тему',
        sv='Byt till mörkt tema', fi='Vaihda tummaan teemaan',
        ja='ダークテーマに切り替え', ko='다크 테마로 전환',
        zh='切换到深色主题', ar='التبديل إلى السمة الداكنة'),
    'Сменить язык интерфейса': _mk(
        'Сменить язык интерфейса', 'Change interface language',
        de='Sprache der Oberfläche ändern', fr="Changer la langue de l'interface",
        es='Cambiar el idioma de la interfaz', it="Cambia la lingua dell'interfaccia",
        pt='Alterar o idioma da interface', nl='Interfacetaal wijzigen',
        pl='Zmień język interfejsu', tr='Arayüz dilini değiştir',
        cs='Změnit jazyk rozhraní', hu='Felület nyelvének módosítása',
        ro='Schimbă limba interfeței', uk='Змінити мову інтерфейсу',
        sv='Byt gränssnittsspråk', fi='Vaihda käyttöliittymän kieli',
        ja='インターフェース言語を変更', ko='인터페이스 언어 변경',
        zh='更改界面语言', ar='تغيير لغة الواجهة'),
    'Добавить свой пресет': _mk(
        'Добавить свой пресет', 'Add custom preset',
        de='Eigene Voreinstellung hinzufügen', fr='Ajouter un préréglage personnalisé',
        es='Añadir preajuste personalizado', it='Aggiungi preset personalizzato',
        pt='Adicionar predefinição personalizada', nl='Aangepaste preset toevoegen',
        pl='Dodaj własny preset', tr='Özel hazır ayar ekle',
        cs='Přidat vlastní předvolbu', hu='Egyéni beállítás hozzáadása',
        ro='Adaugă presetare personalizată', uk='Додати власний пресет',
        sv='Lägg till egen förinställning', fi='Lisää oma esiasetus',
        ja='カスタムプリセットを追加', ko='사용자 프리셋 추가',
        zh='添加自定义预设', ar='إضافة إعداد مخصص'),
    'Экспорт настроек в файл': _mk(
        'Экспорт настроек в файл', 'Export settings to file',
        de='Einstellungen in Datei exportieren', fr='Exporter les paramètres dans un fichier',
        es='Exportar configuración a archivo', it='Esporta impostazioni su file',
        pt='Exportar definições para ficheiro', nl='Instellingen naar bestand exporteren',
        pl='Eksportuj ustawienia do pliku', tr='Ayarları dosyaya aktar',
        cs='Exportovat nastavení do souboru', hu='Beállítások exportálása fájlba',
        ro='Exportă setările într-un fișier', uk='Експорт налаштувань у файл',
        sv='Exportera inställningar till fil', fi='Vie asetukset tiedostoon',
        ja='設定をファイルにエクスポート', ko='설정을 파일로 내보내기',
        zh='导出设置到文件', ar='تصدير الإعدادات إلى ملف'),
    'Импорт настроек из файла': _mk(
        'Импорт настроек из файла', 'Import settings from file',
        de='Einstellungen aus Datei importieren', fr='Importer les paramètres depuis un fichier',
        es='Importar configuración desde archivo', it='Importa impostazioni da file',
        pt='Importar definições de ficheiro', nl='Instellingen uit bestand importeren',
        pl='Importuj ustawienia z pliku', tr='Ayarları dosyadan içe aktar',
        cs='Importovat nastavení ze souboru', hu='Beállítások importálása fájlból',
        ro='Importă setările dintr-un fișier', uk='Імпорт налаштувань із файлу',
        sv='Importera inställningar från fil', fi='Tuo asetukset tiedostosta',
        ja='設定をファイルからインポート', ko='파일에서 설정 가져오기',
        zh='从文件导入设置', ar='استيراد الإعدادات من ملف'),
    'Удалить': _mk(
        'Удалить', 'Delete',
        de='Löschen', fr='Supprimer', es='Eliminar',
        it='Elimina', pt='Eliminar', nl='Verwijderen',
        pl='Usuń', tr='Sil', cs='Smazat',
        hu='Törlés', ro='Șterge', uk='Видалити',
        sv='Ta bort', fi='Poista',
        ja='削除', ko='삭제', zh='删除', ar='حذف'),
    'Удалить этот пресет': _mk(
        'Удалить этот пресет', 'Delete this preset',
        de='Diese Voreinstellung löschen', fr='Supprimer ce préréglage',
        es='Eliminar este preajuste', it='Elimina questo preset',
        pt='Eliminar esta predefinição', nl='Deze preset verwijderen',
        pl='Usuń ten preset', tr='Bu hazır ayarı sil',
        cs='Smazat tuto předvolbu', hu='Ennek a beállításnak a törlése',
        ro='Șterge această presetare', uk='Видалити цей пресет',
        sv='Ta bort denna förinställning', fi='Poista tämä esiasetus',
        ja='このプリセットを削除', ko='이 프리셋 삭제',
        zh='删除此预设', ar='حذف هذا الإعداد'),
    'Правый клик — меню.': _mk(
        'Правый клик — меню.', 'Right-click for menu.',
        de='Rechtsklick für Menü.', fr='Clic droit pour menu.',
        es='Clic derecho para menú.', it='Clic destro per menu.',
        pt='Clique direito para menu.', nl='Rechtermuisknop voor menu.',
        pl='Kliknij prawym — menu.', tr='Menü için sağ tıklayın.',
        cs='Pravým tlačítkem — menu.', hu='Jobb kattintás — menü.',
        ro='Click dreapta — meniu.', uk='Правий клік — меню.',
        sv='Högerklicka för meny.', fi='Hiiren oikealla — valikko.',
        ja='右クリックでメニュー。', ko='마우스 오른쪽 클릭 — 메뉴.',
        zh='右键打开菜单。', ar='انقر بزر الماوس الأيمن للقائمة.'),
    'Полностью выключить компьютер по завершении таймера.': _mk(
        'Полностью выключить компьютер по завершении таймера.',
        'Fully shut down the computer when the timer finishes.',
        de='Computer nach Ablauf des Timers vollständig herunterfahren.',
        fr="Éteindre complètement l'ordinateur à la fin du minuteur.",
        es='Apagar completamente el equipo al terminar el temporizador.',
        it='Spegni completamente il computer al termine del timer.',
        pt='Desligar completamente o computador quando o temporizador terminar.',
        nl='Computer volledig afsluiten wanneer de timer afloopt.',
        pl='Całkowicie wyłącz komputer po zakończeniu timera.',
        tr='Zamanlayıcı bittiğinde bilgisayarı tamamen kapat.',
        cs='Po dokončení časovače zcela vypnout počítač.',
        hu='A számítógép teljes leállítása az időzítő lejártakor.',
        ro='Oprește complet computerul la finalul temporizatorului.',
        uk='Повністю вимкнути комп’ютер після завершення таймера.',
        sv='Stäng av datorn helt när timern är klar.',
        fi='Sammuta tietokone kokonaan, kun ajastin päättyy.',
        ja='タイマー終了時にPCを完全にシャットダウンします。',
        ko='타이머 종료 시 컴퓨터를 완전히 종료합니다.',
        zh='计时器结束时完全关闭计算机。',
        ar='إيقاف تشغيل الكمبيوتر بالكامل عند انتهاء المؤقت.'),
    'Перезагрузить компьютер по завершении таймера.': _mk(
        'Перезагрузить компьютер по завершении таймера.',
        'Restart the computer when the timer finishes.',
        de='Computer nach Ablauf des Timers neu starten.',
        fr="Redémarrer l'ordinateur à la fin du minuteur.",
        es='Reiniciar el equipo al terminar el temporizador.',
        it='Riavvia il computer al termine del timer.',
        pt='Reiniciar o computador quando o temporizador terminar.',
        nl='Computer opnieuw opstarten wanneer de timer afloopt.',
        pl='Uruchom ponownie komputer po zakończeniu timera.',
        tr='Zamanlayıcı bittiğinde bilgisayarı yeniden başlat.',
        cs='Po dokončení časovače restartovat počítač.',
        hu='A számítógép újraindítása az időzítő lejártakor.',
        ro='Repornește computerul la finalul temporizatorului.',
        uk='Перезавантажити комп’ютер після завершення таймера.',
        sv='Starta om datorn när timern är klar.',
        fi='Käynnistä tietokone uudelleen, kun ajastin päättyy.',
        ja='タイマー終了時にPCを再起動します。',
        ko='타이머 종료 시 컴퓨터를 재시작합니다.',
        zh='计时器结束时重启计算机。',
        ar='إعادة تشغيل الكمبيوتر عند انتهاء المؤقت.'),
    'Перевести ПК в сон. Быстрое пробуждение, низкое энергопотребление. Не сохраняет состояние на диск.': _mk(
        'Перевести ПК в сон. Быстрое пробуждение, низкое энергопотребление. Не сохраняет состояние на диск.',
        'Put the PC to sleep. Fast wake-up, low power consumption. Does not save state to disk.',
        de='PC in den Ruhezustand versetzen. Schnelles Aufwachen, geringer Stromverbrauch. Zustand wird nicht auf Festplatte gespeichert.',
        fr="Mettre le PC en veille. Réveil rapide, faible consommation. Ne sauvegarde pas l'état sur le disque.",
        es='Suspender el PC. Reanudación rápida, bajo consumo. No guarda el estado en disco.',
        it='Sospendi il PC. Ripristino rapido, basso consumo. Non salva lo stato su disco.',
        pt='Suspender o PC. Retoma rápida, baixo consumo. Não guarda o estado em disco.',
        nl='PC in slaapstand. Snel ontwaken, laag verbruik. Slaat status niet op schijf op.',
        pl='Uśpij komputer. Szybkie wybudzanie, niski pobór energii. Nie zapisuje stanu na dysku.',
        tr='Bilgisayarı uyku moduna al. Hızlı uyanma, düşük güç tüketimi. Durumu diske kaydetmez.',
        cs='Uspat PC. Rychlé probuzení, nízká spotřeba. Neukládá stav na disk.',
        hu='A PC alvó módba helyezése. Gyors ébredés, alacsony fogyasztás. Nem menti az állapotot lemezre.',
        ro='Trece PC-ul în repaus. Trezire rapidă, consum redus. Nu salvează starea pe disc.',
        uk='Перевести ПК у сон. Швидке пробудження, низьке енергоспоживання. Не зберігає стан на диск.',
        sv='Försätt datorn i viloläge. Snabb uppvakning, låg energiförbrukning. Sparar inte tillstånd på disk.',
        fi='Aseta tietokone lepotilaan. Nopea herätys, alhainen virrankulutus. Ei tallenna tilaa levylle.',
        ja='PCをスリープ状態にします。素早い復帰、低消費電力。状態をディスクに保存しません。',
        ko='PC를 절전 모드로 전환합니다. 빠른 깨어남, 낮은 전력 소비. 상태를 디스크에 저장하지 않습니다.',
        zh='将 PC 置于睡眠状态。唤醒快速、功耗低。不将状态保存到磁盘。',
        ar='وضع الكمبيوتر في وضع السكون. استيقاظ سريع واستهلاك منخفض للطاقة. لا يحفظ الحالة على القرص.'),
    'Включён всегда, никаких настроек не требует.': _mk(
        'Включён всегда, никаких настроек не требует.',
        'Always enabled, requires no configuration.',
        de='Immer aktiviert, keine Konfiguration erforderlich.',
        fr='Toujours activé, ne nécessite aucune configuration.',
        es='Siempre activado, no requiere configuración.',
        it='Sempre attivo, non richiede configurazione.',
        pt='Sempre ativado, não requer configuração.',
        nl='Altijd ingeschakeld, vereist geen configuratie.',
        pl='Zawsze włączone, nie wymaga konfiguracji.',
        tr='Her zaman etkin, yapılandırma gerektirmez.',
        cs='Vždy povoleno, nevyžaduje konfiguraci.',
        hu='Mindig engedélyezve, nincs szükség beállításra.',
        ro='Întotdeauna activat, nu necesită configurare.',
        uk='Завжди увімкнено, не потребує налаштувань.',
        sv='Alltid aktiverat, kräver ingen konfiguration.',
        fi='Aina käytössä, ei vaadi asetuksia.',
        ja='常に有効で、設定は不要です。',
        ko='항상 활성화되어 있으며 설정이 필요하지 않습니다.',
        zh='始终启用，无需配置。',
        ar='مُمكَّن دائمًا، لا يتطلب أي إعداد.'),
    'Сохраняет всю сессию на диск и полностью выключает ПК. Пробуждение — как из обычного выключения, но всё открыто.': _mk(
        'Сохраняет всю сессию на диск и полностью выключает ПК. Пробуждение — как из обычного выключения, но всё открыто.',
        'Saves the entire session to disk and fully shuts down the PC. Wake-up is like a normal boot, but everything is still open.',
        de='Speichert die gesamte Sitzung auf der Festplatte und schaltet den PC vollständig aus. Aufwachen wie beim normalen Start, aber alles bleibt geöffnet.',
        fr="Enregistre toute la session sur le disque et éteint complètement le PC. Le réveil est comme un démarrage normal, mais tout reste ouvert.",
        es='Guarda toda la sesión en disco y apaga completamente el PC. El arranque es como un inicio normal, pero todo sigue abierto.',
        it='Salva tutta la sessione su disco e spegne completamente il PC. Il risveglio è come un avvio normale, ma tutto resta aperto.',
        pt='Guarda toda a sessão em disco e desliga completamente o PC. O arranque é como um arranque normal, mas tudo continua aberto.',
        nl='Slaat de hele sessie op schijf op en sluit de pc volledig af. Ontwaken is als een normale start, maar alles blijft open.',
        pl='Zapisuje całą sesję na dysku i całkowicie wyłącza komputer. Wybudzenie jak przy normalnym starcie, ale wszystko pozostaje otwarte.',
        tr='Tüm oturumu diske kaydeder ve bilgisayarı tamamen kapatır. Uyanma normal başlatma gibidir, ancak her şey açık kalır.',
        cs='Uloží celou relaci na disk a zcela vypne PC. Probuzení je jako normální start, ale vše zůstane otevřené.',
        hu='A teljes munkamenetet lemezre menti, és teljesen leállítja a PC-t. Az ébredés olyan, mint egy normál indítás, de minden nyitva marad.',
        ro='Salvează întreaga sesiune pe disc și oprește complet PC-ul. Trezirea este ca o pornire normală, dar totul rămâne deschis.',
        uk='Зберігає всю сесію на диск і повністю вимикає ПК. Пробудження — як звичайний запуск, але все залишається відкритим.',
        sv='Sparar hela sessionen på disk och stänger av datorn helt. Uppvaknandet är som en vanlig start, men allt är fortfarande öppet.',
        fi='Tallentaa koko istunnon levylle ja sammuttaa tietokoneen kokonaan. Herätys on kuin normaali käynnistys, mutta kaikki on edelleen auki.',
        ja='セッション全体をディスクに保存し、PCを完全にシャットダウンします。復帰は通常の起動と同じですが、すべてが開いたままです。',
        ko='전체 세션을 디스크에 저장하고 PC를 완전히 종료합니다. 깨어나기는 일반 부팅과 같지만 모든 것이 열려 있습니다.',
        zh='将整个会话保存到磁盘并完全关闭 PC。唤醒就像正常启动一样，但所有内容仍然打开。',
        ar='يحفظ الجلسة بأكملها على القرص ويوقف الكمبيوتر تمامًا. الاستيقاظ مثل الإقلاع العادي، لكن كل شيء لا يزال مفتوحًا.'),
    '⚠ Требует, чтобы гибернация была включена в параметрах Windows.': _mk(
        '⚠ Требует, чтобы гибернация была включена в параметрах Windows.',
        '⚠ Requires hibernation to be enabled in Windows settings.',
        de='⚠ Erfordert, dass der Ruhezustand in den Windows-Einstellungen aktiviert ist.',
        fr="⚠ Nécessite que l'hibernation soit activée dans les paramètres Windows.",
        es='⚠ Requiere que la hibernación esté activada en la configuración de Windows.',
        it="⚠ Richiede che l'ibernazione sia abilitata nelle impostazioni di Windows.",
        pt='⚠ Requer que a hibernação esteja ativada nas configurações do Windows.',
        nl='⚠ Vereist dat slaapstand is ingeschakeld in Windows-instellingen.',
        pl='⚠ Wymaga włączenia hibernacji w ustawieniach Windows.',
        tr='⚠ Windows ayarlarında hazırda bekletmenin etkin olmasını gerektirir.',
        cs='⚠ Vyžaduje povolení hibernace v nastavení Windows.',
        hu='⚠ A hibernálást engedélyezni kell a Windows beállításaiban.',
        ro='⚠ Necesită activarea hibernării în setările Windows.',
        uk='⚠ Потребує, щоб гібернація була увімкнена в параметрах Windows.',
        sv='⚠ Kräver att viloläge är aktiverat i Windows-inställningarna.',
        fi='⚠ Vaatii, että lepotila on otettu käyttöön Windows-asetuksissa.',
        ja='⚠ Windowsの設定で休止状態を有効にする必要があります。',
        ko='⚠ Windows 설정에서 최대 절전 모드를 활성화해야 합니다.',
        zh='⚠ 需要在 Windows 设置中启用休眠。',
        ar='⚠ يتطلب تمكين الإسبات في إعدادات Windows.'),
    'Таймер': _mk(
        'Таймер', 'Timer',
        de='Timer', fr='Minuteur', es='Temporizador',
        it='Timer', pt='Temporizador', nl='Timer',
        pl='Timer', tr='Zamanlayıcı', cs='Časovač',
        hu='Időzítő', ro='Temporizator', uk='Таймер',
        sv='Timer', fi='Ajastin',
        ja='タイマー', ko='타이머', zh='定时器', ar='المؤقت'),
    'Установите время больше нуля.': _mk(
        'Установите время больше нуля.', 'Set a time greater than zero.',
        de='Legen Sie eine Zeit größer als null fest.', fr='Définissez une durée supérieure à zéro.',
        es='Establezca un tiempo mayor que cero.', it='Imposta un tempo maggiore di zero.',
        pt='Defina um tempo maior que zero.', nl='Stel een tijd groter dan nul in.',
        pl='Ustaw czas większy od zera.', tr='Sıfırdan büyük bir süre belirleyin.',
        cs='Nastavte čas větší než nula.', hu='Adjon meg nullánál nagyobb időt.',
        ro='Setați un timp mai mare decât zero.', uk='Встановіть час більше нуля.',
        sv='Ange en tid större än noll.', fi='Aseta aika, joka on suurempi kuin nolla.',
        ja='0より大きい時間を設定してください。', ko='0보다 큰 시간을 설정하세요.',
        zh='请设置大于零的时间。', ar='اضبط وقتًا أكبر من الصفر.'),
    'Ошибка': _mk(
        'Ошибка', 'Error',
        de='Fehler', fr='Erreur', es='Error',
        it='Errore', pt='Erro', nl='Fout',
        pl='Błąd', tr='Hata', cs='Chyba',
        hu='Hiba', ro='Eroare', uk='Помилка',
        sv='Fel', fi='Virhe',
        ja='エラー', ko='오류', zh='错误', ar='خطأ'),
    'Не удалось запустить:': _mk(
        'Не удалось запустить:', 'Failed to start:',
        de='Konnte nicht gestartet werden:', fr='Échec du démarrage :',
        es='No se pudo iniciar:', it='Avvio non riuscito:',
        pt='Falha ao iniciar:', nl='Kan niet starten:',
        pl='Nie udało się uruchomić:', tr='Başlatılamadı:',
        cs='Nepodařilo se spustit:', hu='Nem sikerült elindítani:',
        ro='Pornirea a eșuat:', uk='Не вдалося запустити:',
        sv='Kunde inte starta:', fi='Käynnistys epäonnistui:',
        ja='起動に失敗しました：', ko='시작하지 못했습니다:',
        zh='启动失败：', ar='فشل البدء:'),
    'Таймер запущен': _mk(
        'Таймер запущен', 'Timer is running',
        de='Timer läuft', fr='Minuteur en cours', es='Temporizador en marcha',
        it='Timer in esecuzione', pt='Temporizador em execução', nl='Timer actief',
        pl='Timer uruchomiony', tr='Zamanlayıcı çalışıyor', cs='Časovač běží',
        hu='Az időzítő fut', ro='Temporizatorul rulează', uk='Таймер запущено',
        sv='Timern körs', fi='Ajastin käynnissä',
        ja='タイマー実行中', ko='타이머 실행 중', zh='定时器运行中', ar='المؤقت قيد التشغيل'),
    'Нельзя закрыть приложение, пока идёт отсчёт.': _mk(
        'Нельзя закрыть приложение, пока идёт отсчёт.',
        'Cannot close the app while the countdown is running.',
        de='Die Anwendung kann nicht geschlossen werden, solange der Countdown läuft.',
        fr="Impossible de fermer l'application pendant le compte à rebours.",
        es='No se puede cerrar la aplicación mientras la cuenta atrás está activa.',
        it="Impossibile chiudere l'app durante il conto alla rovescia.",
        pt='Não é possível fechar a aplicação enquanto a contagem decrescente está em curso.',
        nl='Kan de app niet sluiten terwijl het aftellen loopt.',
        pl='Nie można zamknąć aplikacji, gdy trwa odliczanie.',
        tr='Geri sayım devam ederken uygulama kapatılamaz.',
        cs='Aplikaci nelze zavřít, dokud běží odpočítávání.',
        hu='Az alkalmazás nem zárható be, amíg a visszaszámlálás fut.',
        ro='Aplicația nu poate fi închisă cât timp numărătoarea inversă rulează.',
        uk='Не можна закрити застосунок, поки триває відлік.',
        sv='Appen kan inte stängas medan nedräkningen pågår.',
        fi='Sovellusta ei voi sulkea, kun lähtölaskenta on käynnissä.',
        ja='カウントダウン中はアプリを閉じられません。',
        ko='카운트다운 중에는 앱을 닫을 수 없습니다.',
        zh='倒计时进行中无法关闭应用。',
        ar='لا يمكن إغلاق التطبيق أثناء تشغيل العد التنازلي.'),
    'Сначала отмените таймер.': _mk(
        'Сначала отмените таймер.', 'Cancel the timer first.',
        de='Brechen Sie zuerst den Timer ab.', fr="Annulez d'abord le minuteur.",
        es='Cancele primero el temporizador.', it='Annulla prima il timer.',
        pt='Cancele primeiro o temporizador.', nl='Annuleer eerst de timer.',
        pl='Najpierw anuluj timer.', tr='Önce zamanlayıcıyı iptal edin.',
        cs='Nejprve zrušte časovač.', hu='Először szakítsa meg az időzítőt.',
        ro='Anulați mai întâi temporizatorul.', uk='Спочатку скасуйте таймер.',
        sv='Avbryt timern först.', fi='Peruuta ajastin ensin.',
        ja='先にタイマーをキャンセルしてください。', ko='먼저 타이머를 취소하세요.',
        zh='请先取消定时器。', ar='ألغِ المؤقت أولاً.'),
    'Гибернация выключена': _mk(
        'Гибернация выключена', 'Hibernation is disabled',
        de='Ruhezustand ist deaktiviert', fr='Hibernation désactivée',
        es='Hibernación desactivada', it='Ibernazione disabilitata',
        pt='Hibernação desativada', nl='Slaapstand uitgeschakeld',
        pl='Hibernacja wyłączona', tr='Hazırda beklet devre dışı',
        cs='Hibernace zakázána', hu='A hibernálás le van tiltva',
        ro='Hibernarea este dezactivată', uk='Гібернацію вимкнено',
        sv='Viloläge är inaktiverat', fi='Lepotila on poistettu käytöstä',
        ja='休止状態が無効です', ko='최대 절전 모드가 비활성화되어 있습니다',
        zh='休眠已禁用', ar='الإسبات معطّل'),
    'На этом компьютере гибернация отключена.': _mk(
        'На этом компьютере гибернация отключена.',
        'Hibernation is disabled on this computer.',
        de='Auf diesem Computer ist der Ruhezustand deaktiviert.',
        fr="L'hibernation est désactivée sur cet ordinateur.",
        es='La hibernación está desactivada en este equipo.',
        it="L'ibernazione è disabilitata su questo computer.",
        pt='A hibernação está desativada neste computador.',
        nl='Slaapstand is uitgeschakeld op deze computer.',
        pl='Hibernacja jest wyłączona na tym komputerze.',
        tr='Bu bilgisayarda hazırda beklet devre dışı.',
        cs='Na tomto počítači je hibernace zakázána.',
        hu='Ezen a számítógépen a hibernálás le van tiltva.',
        ro='Hibernarea este dezactivată pe acest computer.',
        uk='На цьому комп’ютері гібернацію вимкнено.',
        sv='Viloläge är inaktiverat på den här datorn.',
        fi='Lepotila on poistettu käytöstä tällä tietokoneella.',
        ja='このコンピューターでは休止状態が無効です。',
        ko='이 컴퓨터에서는 최대 절전 모드가 비활성화되어 있습니다.',
        zh='此计算机已禁用休眠。',
        ar='الإسبات معطّل على هذا الكمبيوتر.'),
    'Включите её в параметрах электропитания Windows или выберите «Сон».': _mk(
        'Включите её в параметрах электропитания Windows или выберите «Сон».',
        'Enable it in Windows power options or select "Sleep".',
        de='Aktivieren Sie ihn in den Windows-Energieoptionen oder wählen Sie „Ruhezustand".',
        fr="Activez-la dans les options d'alimentation Windows ou choisissez « Veille ».",
        es='Actívela en las opciones de energía de Windows o seleccione «Suspender».',
        it='Abilitala nelle opzioni di risparmio energetico di Windows o seleziona «Sospendi».',
        pt='Ative-a nas opções de energia do Windows ou selecione «Suspender».',
        nl='Schakel het in bij Windows-energiebeheer of kies "Slaapstand".',
        pl='Włącz ją w opcjach zasilania Windows lub wybierz „Uśpij".',
        tr='Windows güç seçeneklerinden etkinleştirin veya "Uyku"yu seçin.',
        cs='Povolte ji v možnostech napájení Windows nebo zvolte „Spánek".',
        hu='Engedélyezze a Windows energiaellátási beállításaiban, vagy válassza az „Alvás" opciót.',
        ro='Activați-o în opțiunile de energie Windows sau selectați „Repaus".',
        uk='Увімкніть її в параметрах електроживлення Windows або виберіть «Сон».',
        sv='Aktivera det i Windows energialternativ eller välj "Viloläge".',
        fi='Ota se käyttöön Windowsin virta-asetuksissa tai valitse "Lepotila".',
        ja='Windowsの電源オプションで有効にするか、「スリープ」を選択してください。',
        ko='Windows 전원 옵션에서 활성화하거나 "절전"을 선택하세요.',
        zh='在 Windows 电源选项中启用它，或选择“睡眠”。',
        ar='قم بتمكينه من خيارات الطاقة في Windows أو اختر "السكون".'),
    'Обнаружено запланированное выключение': _mk(
        'Обнаружено запланированное выключение', 'Scheduled shutdown detected',
        de='Geplantes Herunterfahren erkannt', fr='Arrêt planifié détecté',
        es='Apagado programado detectado', it='Spegnimento pianificato rilevato',
        pt='Desligamento agendado detetado', nl='Geplande afsluiting gedetecteerd',
        pl='Wykryto zaplanowane wyłączenie', tr='Planlanmış kapatma algılandı',
        cs='Zjištěno plánované vypnutí', hu='Ütemezett leállítás észlelve',
        ro='Oprire programată detectată', uk='Виявлено заплановане вимкнення',
        sv='Schemalagd avstängning upptäckt', fi='Ajastettu sammutus havaittu',
        ja='スケジュールされたシャットダウンを検出', ko='예약된 종료 감지됨',
        zh='检测到已计划的关机', ar='تم اكتشاف إيقاف تشغيل مجدول'),
    'В системе было активно запланированное выключение Windows.': _mk(
        'В системе было активно запланированное выключение Windows.',
        'A scheduled Windows shutdown was active.',
        de='Ein geplantes Windows-Herunterfahren war aktiv.',
        fr='Un arrêt Windows planifié était actif.',
        es='Había un apagado programado de Windows activo.',
        it='Era attivo uno spegnimento pianificato di Windows.',
        pt='Estava ativo um desligamento agendado do Windows.',
        nl='Er was een geplande Windows-afsluiting actief.',
        pl='Zaplanowane wyłączenie Windows było aktywne.',
        tr='Planlanmış bir Windows kapatması etkindi.',
        cs='Bylo aktivní plánované vypnutí Windows.',
        hu='Egy ütemezett Windows-leállítás volt aktív.',
        ro='Era activă o oprire programată Windows.',
        uk='Було активним заплановане вимкнення Windows.',
        sv='En schemalagd Windows-avstängning var aktiv.',
        fi='Ajastettu Windows-sammutus oli aktiivinen.',
        ja='スケジュールされた Windows のシャットダウンが実行中でした。',
        ko='예약된 Windows 종료가 활성 상태였습니다.',
        zh='有一个计划的 Windows 关机处于活动状态。',
        ar='كان هناك إيقاف تشغيل مجدول لويندوز نشطًا.'),
    'Приложение его отменило, чтобы не конфликтовало.': _mk(
        'Приложение его отменило, чтобы не конфликтовало.',
        'The application cancelled it to avoid conflicts.',
        de='Die Anwendung hat es abgebrochen, um Konflikte zu vermeiden.',
        fr="L'application l'a annulé pour éviter les conflits.",
        es='La aplicación lo canceló para evitar conflictos.',
        it="L'applicazione l'ha annullato per evitare conflitti.",
        pt='A aplicação cancelou-o para evitar conflitos.',
        nl='De applicatie heeft het geannuleerd om conflicten te voorkomen.',
        pl='Aplikacja anulowała je, aby uniknąć konfliktów.',
        tr='Uygulama çakışmaları önlemek için iptal etti.',
        cs='Aplikace jej zrušila, aby se předešlo konfliktům.',
        hu='Az alkalmazás megszakította az ütközések elkerülése érdekében.',
        ro='Aplicația l-a anulat pentru a evita conflictele.',
        uk='Застосунок скасував його, щоб уникнути конфліктів.',
        sv='Programmet avbröt det för att undvika konflikter.',
        fi='Sovellus peruutti sen välttääkseen ristiriidat.',
        ja='競合を避けるため、アプリがこれをキャンセルしました。',
        ko='충돌을 피하기 위해 앱이 이를 취소했습니다.',
        zh='应用已取消它以避免冲突。',
        ar='قام التطبيق بإلغائه لتجنب التعارض.'),
    'Куда сохранить настройки?': _mk(
        'Куда сохранить настройки?', 'Where to save the settings?',
        de='Wohin sollen die Einstellungen gespeichert werden?',
        fr='Où enregistrer les paramètres ?',
        es='¿Dónde guardar la configuración?',
        it='Dove salvare le impostazioni?',
        pt='Onde guardar as definições?',
        nl='Waar moeten de instellingen worden opgeslagen?',
        pl='Gdzie zapisać ustawienia?',
        tr='Ayarlar nereye kaydedilsin?',
        cs='Kam uložit nastavení?',
        hu='Hová mentse a beállításokat?',
        ro='Unde să salvez setările?',
        uk='Куди зберегти налаштування?',
        sv='Var ska inställningarna sparas?',
        fi='Minne asetukset tallennetaan?',
        ja='設定を保存する場所は？', ko='설정을 어디에 저장할까요?',
        zh='保存设置到哪里？', ar='أين يتم حفظ الإعدادات؟'),
    'Выберите файл с настройками': _mk(
        'Выберите файл с настройками', 'Select the settings file',
        de='Wählen Sie die Einstellungsdatei', fr='Sélectionnez le fichier de paramètres',
        es='Seleccione el archivo de configuración', it='Seleziona il file delle impostazioni',
        pt='Selecione o ficheiro de definições', nl='Selecteer het instellingenbestand',
        pl='Wybierz plik ustawień', tr='Ayar dosyasını seçin',
        cs='Vyberte soubor nastavení', hu='Válassza ki a beállításfájlt',
        ro='Selectați fișierul de setări', uk='Виберіть файл із налаштуваннями',
        sv='Välj inställningsfilen', fi='Valitse asetustiedosto',
        ja='設定ファイルを選択', ko='설정 파일 선택',
        zh='选择设置文件', ar='حدد ملف الإعدادات'),
    'Экспорт завершён': _mk(
        'Экспорт завершён', 'Export completed',
        de='Export abgeschlossen', fr='Exportation terminée',
        es='Exportación completada', it='Esportazione completata',
        pt='Exportação concluída', nl='Export voltooid',
        pl='Eksport zakończony', tr='Dışa aktarma tamamlandı',
        cs='Export dokončen', hu='Exportálás befejezve',
        ro='Export finalizat', uk='Експорт завершено',
        sv='Export klar', fi='Vienti valmis',
        ja='エクスポート完了', ko='내보내기 완료',
        zh='导出完成', ar='اكتمل التصدير'),
    'Настройки сохранены в файл:': _mk(
        'Настройки сохранены в файл:', 'Settings saved to file:',
        de='Einstellungen gespeichert in Datei:', fr='Paramètres enregistrés dans le fichier :',
        es='Configuración guardada en el archivo:', it='Impostazioni salvate nel file:',
        pt='Definições guardadas no ficheiro:', nl='Instellingen opgeslagen in bestand:',
        pl='Ustawienia zapisane w pliku:', tr='Ayarlar dosyaya kaydedildi:',
        cs='Nastavení uloženo do souboru:', hu='Beállítások mentve a fájlba:',
        ro='Setările au fost salvate în fișierul:', uk='Налаштування збережено у файл:',
        sv='Inställningar sparade i fil:', fi='Asetukset tallennettu tiedostoon:',
        ja='設定をファイルに保存しました：', ko='설정이 파일에 저장되었습니다:',
        zh='设置已保存到文件：', ar='تم حفظ الإعدادات في الملف:'),
    'Импорт завершён': _mk(
        'Импорт завершён', 'Import completed',
        de='Import abgeschlossen', fr='Importation terminée',
        es='Importación completada', it='Importazione completata',
        pt='Importação concluída', nl='Import voltooid',
        pl='Import zakończony', tr='İçe aktarma tamamlandı',
        cs='Import dokončen', hu='Importálás befejezve',
        ro='Import finalizat', uk='Імпорт завершено',
        sv='Import klar', fi='Tuonti valmis',
        ja='インポート完了', ko='가져오기 완료',
        zh='导入完成', ar='اكتمل الاستيراد'),
    'Настройки успешно загружены и применены.': _mk(
        'Настройки успешно загружены и применены.',
        'Settings loaded and applied successfully.',
        de='Einstellungen erfolgreich geladen und angewendet.',
        fr='Paramètres chargés et appliqués avec succès.',
        es='Configuración cargada y aplicada correctamente.',
        it='Impostazioni caricate e applicate correttamente.',
        pt='Definições carregadas e aplicadas com sucesso.',
        nl='Instellingen met succes geladen en toegepast.',
        pl='Ustawienia zostały pomyślnie wczytane i zastosowane.',
        tr='Ayarlar başarıyla yüklendi ve uygulandı.',
        cs='Nastavení bylo úspěšně načteno a použito.',
        hu='A beállítások sikeresen betöltve és alkalmazva.',
        ro='Setările au fost încărcate și aplicate cu succes.',
        uk='Налаштування успішно завантажено та застосовано.',
        sv='Inställningarna lästes in och tillämpades.',
        fi='Asetukset ladattiin ja otettiin käyttöön.',
        ja='設定を正常に読み込み、適用しました。',
        ko='설정을 성공적으로 불러와 적용했습니다.',
        zh='设置已成功加载并应用。',
        ar='تم تحميل الإعدادات وتطبيقها بنجاح.'),
    'Ошибка экспорта': _mk(
        'Ошибка экспорта', 'Export error',
        de='Exportfehler', fr="Erreur d'exportation",
        es='Error de exportación', it='Errore di esportazione',
        pt='Erro de exportação', nl='Exportfout',
        pl='Błąd eksportu', tr='Dışa aktarma hatası',
        cs='Chyba exportu', hu='Exportálási hiba',
        ro='Eroare de export', uk='Помилка експорту',
        sv='Exportfel', fi='Vientivirhe',
        ja='エクスポートエラー', ko='내보내기 오류',
        zh='导出错误', ar='خطأ في التصدير'),
    'Не удалось сохранить:': _mk(
        'Не удалось сохранить:', 'Failed to save:',
        de='Speichern fehlgeschlagen:', fr="Échec de l'enregistrement :",
        es='No se pudo guardar:', it='Salvataggio non riuscito:',
        pt='Falha ao guardar:', nl='Opslaan mislukt:',
        pl='Nie udało się zapisać:', tr='Kaydedilemedi:',
        cs='Nepodařilo se uložit:', hu='Nem sikerült menteni:',
        ro='Salvarea a eșuat:', uk='Не вдалося зберегти:',
        sv='Kunde inte spara:', fi='Tallennus epäonnistui:',
        ja='保存に失敗しました：', ko='저장하지 못했습니다:',
        zh='保存失败：', ar='فشل الحفظ:'),
    'Ошибка импорта': _mk(
        'Ошибка импорта', 'Import error',
        de='Importfehler', fr="Erreur d'importation",
        es='Error de importación', it='Errore di importazione',
        pt='Erro de importação', nl='Importfout',
        pl='Błąd importu', tr='İçe aktarma hatası',
        cs='Chyba importu', hu='Importálási hiba',
        ro='Eroare de import', uk='Помилка імпорту',
        sv='Importfel', fi='Tuontivirhe',
        ja='インポートエラー', ko='가져오기 오류',
        zh='导入错误', ar='خطأ في الاستيراد'),
    'Не удалось загрузить:': _mk(
        'Не удалось загрузить:', 'Failed to load:',
        de='Laden fehlgeschlagen:', fr='Échec du chargement :',
        es='No se pudo cargar:', it='Caricamento non riuscito:',
        pt='Falha ao carregar:', nl='Laden mislukt:',
        pl='Nie udało się wczytać:', tr='Yüklenemedi:',
        cs='Nepodařilo se načíst:', hu='Nem sikerült betölteni:',
        ro='Încărcarea a eșuat:', uk='Не вдалося завантажити:',
        sv='Kunde inte läsa in:', fi='Lataus epäonnistui:',
        ja='読み込みに失敗しました：', ko='불러오지 못했습니다:',
        zh='加载失败：', ar='فشل التحميل:'),
    'Ошибка чтения': _mk(
        'Ошибка чтения', 'Read error',
        de='Lesefehler', fr='Erreur de lecture',
        es='Error de lectura', it='Errore di lettura',
        pt='Erro de leitura', nl='Leesfout',
        pl='Błąd odczytu', tr='Okuma hatası',
        cs='Chyba čtení', hu='Olvasási hiba',
        ro='Eroare de citire', uk='Помилка читання',
        sv='Läsfel', fi='Lukuvirhe',
        ja='読み取りエラー', ko='읽기 오류',
        zh='读取错误', ar='خطأ في القراءة'),
    'Файл повреждён или не JSON:': _mk(
        'Файл повреждён или не JSON:', 'The file is corrupted or not JSON:',
        de='Die Datei ist beschädigt oder kein JSON:',
        fr="Le fichier est corrompu ou n'est pas du JSON :",
        es='El archivo está dañado o no es JSON:',
        it='Il file è danneggiato o non è JSON:',
        pt='O ficheiro está corrompido ou não é JSON:',
        nl='Het bestand is beschadigd of geen JSON:',
        pl='Plik jest uszkodzony lub nie jest JSON:',
        tr='Dosya bozuk veya JSON değil:',
        cs='Soubor je poškozený nebo není JSON:',
        hu='A fájl sérült vagy nem JSON:',
        ro='Fișierul este corupt sau nu este JSON:',
        uk='Файл пошкоджено або це не JSON:',
        sv='Filen är skadad eller inte JSON:',
        fi='Tiedosto on vioittunut tai ei ole JSON:',
        ja='ファイルが破損しているか JSON ではありません：',
        ko='파일이 손상되었거나 JSON이 아닙니다:',
        zh='文件已损坏或不是 JSON：', ar='الملف تالف أو ليس JSON:'),
    '✅ Настройки экспортированы': _mk(
        '✅ Настройки экспортированы', '✅ Settings exported',
        de='✅ Einstellungen exportiert', fr='✅ Paramètres exportés',
        es='✅ Configuración exportada', it='✅ Impostazioni esportate',
        pt='✅ Definições exportadas', nl='✅ Instellingen geëxporteerd',
        pl='✅ Ustawienia wyeksportowane', tr='✅ Ayarlar dışa aktarıldı',
        cs='✅ Nastavení exportováno', hu='✅ Beállítások exportálva',
        ro='✅ Setări exportate', uk='✅ Налаштування експортовано',
        sv='✅ Inställningar exporterade', fi='✅ Asetukset viety',
        ja='✅ 設定をエクスポートしました', ko='✅ 설정을 내보냈습니다',
        zh='✅ 设置已导出', ar='✅ تم تصدير الإعدادات'),
    '✅ Настройки импортированы': _mk(
        '✅ Настройки импортированы', '✅ Settings imported',
        de='✅ Einstellungen importiert', fr='✅ Paramètres importés',
        es='✅ Configuración importada', it='✅ Impostazioni importate',
        pt='✅ Definições importadas', nl='✅ Instellingen geïmporteerd',
        pl='✅ Ustawienia zaimportowane', tr='✅ Ayarlar içe aktarıldı',
        cs='✅ Nastavení importováno', hu='✅ Beállítások importálva',
        ro='✅ Setări importate', uk='✅ Налаштування імпортовано',
        sv='✅ Inställningar importerade', fi='✅ Asetukset tuotu',
        ja='✅ 設定をインポートしました', ko='✅ 설정을 가져왔습니다',
        zh='✅ 设置已导入', ar='✅ تم استيراد الإعدادات'),
    'Это не файл настроек ShutdownTimer.': _mk(
        'Это не файл настроек ShutdownTimer.', 'This is not a ShutdownTimer settings file.',
        de='Dies ist keine ShutdownTimer-Einstellungsdatei.',
        fr="Ce n'est pas un fichier de paramètres ShutdownTimer.",
        es='Este no es un archivo de configuración de ShutdownTimer.',
        it='Questo non è un file di impostazioni di ShutdownTimer.',
        pt='Este não é um ficheiro de definições do ShutdownTimer.',
        nl='Dit is geen ShutdownTimer-instellingenbestand.',
        pl='To nie jest plik ustawień ShutdownTimer.',
        tr='Bu bir ShutdownTimer ayar dosyası değil.',
        cs='Toto není soubor nastavení ShutdownTimer.',
        hu='Ez nem egy ShutdownTimer beállításfájl.',
        ro='Acesta nu este un fișier de setări ShutdownTimer.',
        uk='Це не файл налаштувань ShutdownTimer.',
        sv='Detta är inte en ShutdownTimer-inställningsfil.',
        fi='Tämä ei ole ShutdownTimer-asetustiedosto.',
        ja='これは ShutdownTimer の設定ファイルではありません。',
        ko='ShutdownTimer 설정 파일이 아닙니다.',
        zh='这不是 ShutdownTimer 设置文件。',
        ar='هذا ليس ملف إعدادات ShutdownTimer.'),
    'Файл не содержит корректных настроек': _mk(
        'Файл не содержит корректных настроек', 'The file does not contain valid settings',
        de='Die Datei enthält keine gültigen Einstellungen',
        fr='Le fichier ne contient pas de paramètres valides',
        es='El archivo no contiene configuración válida',
        it='Il file non contiene impostazioni valide',
        pt='O ficheiro não contém definições válidas',
        nl='Het bestand bevat geen geldige instellingen',
        pl='Plik nie zawiera prawidłowych ustawień',
        tr='Dosya geçerli ayarlar içermiyor',
        cs='Soubor neobsahuje platná nastavení',
        hu='A fájl nem tartalmaz érvényes beállításokat',
        ro='Fișierul nu conține setări valide',
        uk='Файл не містить коректних налаштувань',
        sv='Filen innehåller inga giltiga inställningar',
        fi='Tiedosto ei sisällä kelvollisia asetuksia',
        ja='ファイルに有効な設定が含まれていません',
        ko='파일에 유효한 설정이 없습니다',
        zh='文件不包含有效的设置', ar='الملف لا يحتوي على إعدادات صالحة'),
    'Пустой пресет': _mk(
        'Пустой пресет', 'Empty preset',
        de='Leere Voreinstellung', fr='Préréglage vide',
        es='Preajuste vacío', it='Preset vuoto',
        pt='Predefinição vazia', nl='Leeg preset',
        pl='Pusty preset', tr='Boş hazır ayar',
        cs='Prázdná předvolba', hu='Üres beállítás',
        ro='Presetare goală', uk='Порожній пресет',
        sv='Tom förinställning', fi='Tyhjä esiasetus',
        ja='空のプリセット', ko='빈 프리셋',
        zh='空预设', ar='إعداد فارغ'),
    'Нельзя сохранить пресет, где всё время по нулям.': _mk(
        'Нельзя сохранить пресет, где всё время по нулям.',
        'Cannot save a preset where all time values are zero.',
        de='Eine Voreinstellung, bei der alle Zeitwerte null sind, kann nicht gespeichert werden.',
        fr="Impossible d'enregistrer un préréglage où toutes les valeurs de temps sont à zéro.",
        es='No se puede guardar un preajuste con todos los valores a cero.',
        it='Impossibile salvare un preset con tutti i tempi a zero.',
        pt='Não é possível guardar uma predefinição com todos os valores a zero.',
        nl='Kan geen preset opslaan waarbij alle tijdwaarden nul zijn.',
        pl='Nie można zapisać presetu, w którym wszystkie wartości czasu są zerowe.',
        tr='Tüm süre değerleri sıfır olan bir hazır ayar kaydedilemez.',
        cs='Nelze uložit předvolbu, kde jsou všechny časy nulové.',
        hu='Nem menthető olyan beállítás, ahol minden idő nulla.',
        ro='Nu se poate salva o presetare cu toate valorile de timp zero.',
        uk='Не можна зберегти пресет, де всі значення часу нульові.',
        sv='Kan inte spara en förinställning där alla tidsvärden är noll.',
        fi='Esiasetusta, jossa kaikki aika-arvot ovat nollia, ei voi tallentaa.',
        ja='すべての時間がゼロのプリセットは保存できません。',
        ko='모든 시간이 0인 프리셋은 저장할 수 없습니다.',
        zh='无法保存所有时间均为零的预设。',
        ar='لا يمكن حفظ إعداد تكون فيه جميع القيم الزمنية صفرًا.'),
}


def _tr(key, lang, **fmt):
    entry = UI_TR.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get('en') or entry.get('ru') or key
    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


def _make_preset_label(value, unit, lang):
    if unit == 'min':
        unit_key = 'мин'
    elif unit == 'h':
        unit_key = 'ч'
    else:
        unit_key = 'д'
    return f"{value} {_tr(unit_key, lang)}"


class Tooltip:
    def __init__(self, widget, key_or_list, app=None, delay=450):
        self.widget = widget
        self.app = app
        self.key = key_or_list
        self.delay = delay
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def set_key(self, key):
        self.key = key

    def _get_text(self):
        if self.app is None or self.key is None:
            return ""
        if isinstance(self.key, (list, tuple)):
            parts = [self.app._t(k) for k in self.key]
            return "\n\n".join(p for p in parts if p)
        return self.app._t(self.key)

    def _on_enter(self, event=None):
        self._cancel()
        try:
            self.after_id = self.widget.after(self.delay, self._show)
        except Exception:
            pass

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show(self):
        if self.tip:
            return
        text = self._get_text()
        if not text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except Exception:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_attributes("-topmost", True)
        self.tip.configure(bg="#e0a030")
        inner = tk.Frame(self.tip, bg="#1a1a1a")
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=text, bg="#1a1a1a", fg="#ffffff",
                 font=("Segoe UI", 9), justify="left",
                 padx=12, pady=8, wraplength=420).pack()
        self.tip.update_idletasks()
        tw = self.tip.winfo_width()
        th = self.tip.winfo_height()
        sw = self.tip.winfo_screenwidth()
        sh = self.tip.winfo_screenheight()
        if x + tw > sw - 6:
            x = sw - tw - 6
        if x < 6:
            x = 6
        if y + th > sh - 6:
            y = self.widget.winfo_rooty() - th - 6
        self.tip.wm_geometry(f"+{x}+{y}")

    def _hide(self):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


class Spinner(tk.Frame):
    def __init__(self, parent, label_key, max_value, width=3, on_change=None, T=None,
                 on_wrap_up=None, on_wrap_down=None, app=None):
        self.T = T
        self.app = app
        self.label_key = label_key
        super().__init__(parent, bg=T["bg"])
        self.max_value = max_value
        self.value = 0
        self.on_change = on_change
        self.on_wrap_up = on_wrap_up
        self.on_wrap_down = on_wrap_down

        text = _tr(label_key, app._ui_lang) if app else label_key
        self._name_lbl = tk.Label(self, text=text, bg=T["bg"], fg=T["fg_dim"],
                                  font=("Segoe UI", 10))
        self._name_lbl.pack(pady=(0, 4))

        self._up_lbl = tk.Label(self, text="▲", bg=T["bg"], fg=T["up_clr"],
                                font=("Segoe UI", 12), cursor="hand2")
        self._up_lbl.pack()

        self.lbl = tk.Label(self, text="00", bg=T["bg_dark"], fg=T["fg"],
                            font=("Consolas", 30, "bold"),
                            width=width, relief="flat")
        self.lbl.pack(pady=4, ipady=8, ipadx=4)

        self._down_lbl = tk.Label(self, text="▼", bg=T["bg"], fg=T["up_clr"],
                                  font=("Segoe UI", 12), cursor="hand2")
        self._down_lbl.pack()

        self._up_lbl.bind("<Button-1>", lambda e: self.change(1))
        self._down_lbl.bind("<Button-1>", lambda e: self.change(-1))
        self._up_lbl.bind("<Enter>", lambda e: self._up_lbl.config(fg=self.T["fg"]))
        self._up_lbl.bind("<Leave>", lambda e: self._up_lbl.config(fg=self.T["up_clr"]))
        self._down_lbl.bind("<Enter>", lambda e: self._down_lbl.config(fg=self.T["fg"]))
        self._down_lbl.bind("<Leave>", lambda e: self._down_lbl.config(fg=self.T["up_clr"]))

    def set_lang(self, lang):
        try:
            self._name_lbl.config(text=_tr(self.label_key, lang))
        except Exception:
            pass

    def change(self, delta):
        v = self.value + delta
        wrapped_up = False
        wrapped_down = False
        if v < 0:
            v = self.max_value
            wrapped_down = True
        elif v > self.max_value:
            v = 0
            wrapped_up = True
        self.value = v
        self.lbl.config(text=f"{v:02d}")
        if wrapped_up and self.on_wrap_up:
            self.on_wrap_up()
        if wrapped_down and self.on_wrap_down:
            self.on_wrap_down()
        if self.on_change:
            self.on_change()

    def set_value(self, v):
        v = max(0, min(self.max_value, v))
        self.value = v
        self.lbl.config(text=f"{v:02d}")

    def get(self):
        return self.value

    def repaint(self):
        T = self.T
        self.config(bg=T["bg"])
        self._name_lbl.config(bg=T["bg"], fg=T["fg_dim"])
        self._up_lbl.config(bg=T["bg"], fg=T["up_clr"])
        self.lbl.config(bg=T["bg_dark"], fg=T["fg"])
        self._down_lbl.config(bg=T["bg"], fg=T["up_clr"])


class App:
    def __init__(self):
        self.settings = load_settings()
        self._autorun_launch = "--minimized" in sys.argv

        self.theme_name = self.settings.get("theme", "dark")
        if self.theme_name not in THEMES:
            self.theme_name = "dark"
        self.T = {}
        self.T.update(THEMES[self.theme_name])

        self._ui_lang = self.settings.get("ui_lang", "en")
        if self._ui_lang not in UI_LANGS:
            self._ui_lang = "en"

        self.root = tk.Tk()
        self.root.title(self._t('Таймер выключения ПК'))
        self.root.configure(bg=self.T["bg"])
        self.root.resizable(False, False)
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass

        w, h = 720, 880
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        if self._autorun_launch and TRAY_AVAILABLE:
            try:
                self.root.withdraw()
            except Exception:
                pass

        self.shutdown_active = False
        self.paused = False
        self.paused_remaining = 0
        self.stop_flag = False
        self.end_time = 0
        self.tray_icon = None
        self.preset_buttons = []          # (btn, d, h, m, s, kind, val, unit)
        self._custom_preset_frames = []   # фреймы кастомных пресетов
        self._mini_positioned = False
        self._warning_dlg = None
        self._preset_dlg = None
        self._log_dlg = None
        self._last_tray_text = None
        self._icon_photo = None
        self._beeped = set()
        self._total_duration = 0
        self._sound_files = {}
        self._game_mode = bool(self.settings.get("game_mode", False))
        self._tooltips = []
        self._hibernation_warned = False
        self._styled = []
        self._theme_btn = None
        self._theme_tooltip = None
        self._lang_btn = None
        self._lang_tooltip = None
        self._lang_click_x = 0
        self._lang_click_y = 0
        self._i18n_widgets = []
        self._action_buttons_text_keys = {}
        self._status_key = 'Таймер не запущен'
        self._hint_key = None

        self._init_sounds()

        # ---- Header ----
        header = tk.Frame(self.root, bg=self.T["bg"])
        header.pack(pady=(14, 0), fill="x", padx=18)
        self._reg(header, "frame")

        lbl_icon = tk.Label(header, text="⏻", bg=self.T["bg"], fg=self.T["green"],
                            font=("Segoe UI", 26))
        lbl_icon.pack(side="left", padx=(0, 10))
        self._reg(lbl_icon, "icon_green")

        lbl_title = tk.Label(header, text=self._t('Таймер выключения'),
                             bg=self.T["bg"], fg=self.T["fg"],
                             font=("Segoe UI", 18, "bold"))
        lbl_title.pack(side="left")
        self._reg(lbl_title, "label")
        self._i18n_widgets.append((lbl_title, 'Таймер выключения'))

        self._theme_btn = tk.Label(header, text="", bg=self.T["bg"],
                                   fg=self.T["fg_dim"],
                                   font=("Segoe UI", 16), cursor="hand2")
        self._theme_btn.pack(side="right", padx=(6, 0))
        self._reg(self._theme_btn, "theme_btn")
        self._theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())
        self._theme_btn.bind("<Enter>",
                             lambda e: self._theme_btn.config(fg=self.T["green"]))
        self._theme_btn.bind("<Leave>",
                             lambda e: self._theme_btn.config(fg=self.T["fg_dim"]))
        self._update_theme_button()
        self._theme_tooltip = Tooltip(self._theme_btn, self._theme_tooltip_key(), app=self)
        self._tooltips.append(self._theme_tooltip)

        self._lang_btn = tk.Label(
            header,
            text=f"🌐 {self._ui_lang.upper()}",
            bg=self.T["bg"], fg=self.T["fg_dim"],
            font=("Segoe UI", 10, "bold"),
            cursor="hand2", padx=8, pady=2)
        self._lang_btn.pack(side="right", padx=(6, 0))
        self._lang_btn._ui_skip = True
        self._reg(self._lang_btn, "lang_btn")

        self._lang_btn.bind("<ButtonPress-1>", self._lang_press, add="+")
        self._lang_btn.bind("<ButtonRelease-1>", self._lang_release, add="+")
        self._lang_btn.bind("<Enter>",
                            lambda e: self._lang_btn.config(fg=self.T["green"]), add="+")
        self._lang_btn.bind("<Leave>",
                            lambda e: self._lang_btn.config(fg=self.T["fg_dim"]), add="+")
        self._lang_tooltip = Tooltip(self._lang_btn, 'Сменить язык интерфейса', app=self)
        self._tooltips.append(self._lang_tooltip)

        self._enable_drag(header)

        # ---- Action selector ----
        self.action_var = tk.StringVar(value=self.settings.get("action", "shutdown"))
        actions_frame = tk.Frame(self.root, bg=self.T["bg"])
        actions_frame.pack(pady=(12, 4))
        self._reg(actions_frame, "frame")

        al = tk.Label(actions_frame, text=self._t('Действие по завершении'),
                      bg=self.T["bg"], fg=self.T["fg_dim"],
                      font=("Segoe UI", 9))
        al.pack(anchor="w", padx=4, pady=(0, 5))
        self._reg(al, "label_dim")
        self._i18n_widgets.append((al, 'Действие по завершении'))

        action_row = tk.Frame(actions_frame, bg=self.T["bg"])
        action_row.pack()
        self._reg(action_row, "frame")

        self.action_buttons = {}
        for key, meta in ACTIONS.items():
            text_key = meta["label_key"]
            rb = tk.Radiobutton(
                action_row, text=self._t(text_key),
                variable=self.action_var, value=key,
                indicatoron=0, bd=0, relief="flat",
                bg=self.T["action_bg"], fg=self.T["fg"],
                activebackground=self.T["action_hover"],
                activeforeground=self.T["fg"],
                selectcolor=self.T["action_active"],
                font=("Segoe UI", 9, "bold"),
                padx=14, pady=8, cursor="hand2",
                command=self._on_action_changed)
            rb.pack(side="left", padx=3)
            self.action_buttons[key] = rb
            self._reg(rb, "action_btn")
            self._i18n_widgets.append((rb, text_key))
            self._action_buttons_text_keys[key] = text_key
            self._tooltips.append(Tooltip(rb, ACTION_TOOLTIP_KEYS[key], app=self))

        # ---- Time mode ----
        self.time_mode = tk.StringVar(value=self.settings.get("time_mode", "duration"))
        mode_frame = tk.Frame(self.root, bg=self.T["bg"])
        mode_frame.pack(pady=(10, 4))
        self._reg(mode_frame, "frame")

        ml = tk.Label(mode_frame, text=self._t('Когда выключить'), bg=self.T["bg"],
                      fg=self.T["fg_dim"], font=("Segoe UI", 9))
        ml.pack(anchor="w", padx=4, pady=(0, 5))
        self._reg(ml, "label_dim")
        self._i18n_widgets.append((ml, 'Когда выключить'))

        mode_row = tk.Frame(mode_frame, bg=self.T["bg"])
        mode_row.pack()
        self._reg(mode_row, "frame")

        self.mode_duration_btn = tk.Radiobutton(
            mode_row, text=self._t('⏱  Через время'),
            variable=self.time_mode, value="duration",
            indicatoron=0, bd=0, relief="flat",
            bg=self.T["action_bg"], fg=self.T["fg"],
            activebackground=self.T["action_hover"],
            activeforeground=self.T["fg"],
            selectcolor=self.T["action_active"],
            font=("Segoe UI", 9, "bold"),
            padx=14, pady=7, cursor="hand2",
            command=self._on_time_mode_changed)
        self.mode_duration_btn.pack(side="left", padx=3)
        self._reg(self.mode_duration_btn, "action_btn")
        self._i18n_widgets.append((self.mode_duration_btn, '⏱  Через время'))
        self._tooltips.append(Tooltip(
            self.mode_duration_btn, 'Отсчёт от текущего момента', app=self))

        self.mode_attime_btn = tk.Radiobutton(
            mode_row, text=self._t('🕐  В конкретное время'),
            variable=self.time_mode, value="attime",
            indicatoron=0, bd=0, relief="flat",
            bg=self.T["action_bg"], fg=self.T["fg"],
            activebackground=self.T["action_hover"],
            activeforeground=self.T["fg"],
            selectcolor=self.T["action_active"],
            font=("Segoe UI", 9, "bold"),
            padx=14, pady=7, cursor="hand2",
            command=self._on_time_mode_changed)
        self.mode_attime_btn.pack(side="left", padx=3)
        self._reg(self.mode_attime_btn, "action_btn")
        self._i18n_widgets.append((self.mode_attime_btn, '🕐  В конкретное время'))
        self._tooltips.append(Tooltip(
            self.mode_attime_btn, 'Выключить в конкретное время', app=self))

        # ---- Duration frame ----
        self.duration_frame = tk.Frame(self.root, bg=self.T["bg"])
        self.duration_frame.pack(pady=(10, 10))
        self._reg(self.duration_frame, "frame")

        row = self.duration_frame
        self.days    = Spinner(row, 'Дни',    30, on_change=self._on_spinner_change, T=self.T, app=self)
        self.hours   = Spinner(row, 'Часы',   23, on_change=self._on_spinner_change, T=self.T, app=self)
        self.minutes = Spinner(row, 'Минуты', 59, on_change=self._on_spinner_change, T=self.T, app=self)
        self.seconds = Spinner(row, 'Секунды', 59, on_change=self._on_spinner_change, T=self.T, app=self)

        self.days.pack(side="left", padx=10)
        s1 = tk.Label(row, text=":", bg=self.T["bg"], fg=self.T["fg_dim"],
                      font=("Consolas", 30, "bold"))
        s1.pack(side="left", pady=(28, 0))
        self._reg(s1, "label_dim")
        self.hours.pack(side="left", padx=10)
        s2 = tk.Label(row, text=":", bg=self.T["bg"], fg=self.T["fg_dim"],
                      font=("Consolas", 30, "bold"))
        s2.pack(side="left", pady=(28, 0))
        self._reg(s2, "label_dim")
        self.minutes.pack(side="left", padx=10)
        s3 = tk.Label(row, text=":", bg=self.T["bg"], fg=self.T["fg_dim"],
                      font=("Consolas", 30, "bold"))
        s3.pack(side="left", pady=(28, 0))
        self._reg(s3, "label_dim")
        self.seconds.pack(side="left", padx=10)

        self.days.set_value(int(self.settings.get("days", 0)))
        self.hours.set_value(int(self.settings.get("hours", 0)))
        self.minutes.set_value(int(self.settings.get("minutes", 0)))
        self.seconds.set_value(int(self.settings.get("seconds", 0)))

        # ---- At-time frame ----
        self.attime_frame = tk.Frame(self.root, bg=self.T["bg"])
        self._reg(self.attime_frame, "frame")

        at_row = self.attime_frame
        self.at_hour = Spinner(at_row, 'Часы', 23,
                               on_change=self._on_at_time_change, T=self.T, app=self)
        self.at_minute = Spinner(
            at_row, 'Минуты', 59,
            on_change=self._on_at_time_change, T=self.T, app=self,
            on_wrap_up=lambda: self.at_hour.change(1),
            on_wrap_down=lambda: self.at_hour.change(-1))

        self.at_hour.pack(side="left", padx=10)
        at_sep = tk.Label(at_row, text=":", bg=self.T["bg"], fg=self.T["fg_dim"],
                          font=("Consolas", 30, "bold"))
        at_sep.pack(side="left", pady=(28, 0))
        self._reg(at_sep, "label_dim")
        self.at_minute.pack(side="left", padx=10)

        self.at_hour.set_value(int(self.settings.get("at_hour", 23)))
        self.at_minute.set_value(int(self.settings.get("at_minute", 0)))

        self.at_info = tk.Label(self.attime_frame, text="", bg=self.T["bg"],
                                fg=self.T["fg_dim"], font=("Segoe UI", 9))
        self._reg(self.at_info, "label_dim")

        # ---- Presets ----
        self.preset_frame = tk.Frame(self.root, bg=self.T["bg"])
        self.preset_frame.pack(pady=(4, 10))
        self._reg(self.preset_frame, "frame")

        preset_header = tk.Frame(self.preset_frame, bg=self.T["bg"])
        preset_header.pack(fill="x", padx=4, pady=(0, 5))
        self._reg(preset_header, "frame")

        ph_lbl = tk.Label(preset_header, text=self._t('Быстрые пресеты'),
                          bg=self.T["bg"], fg=self.T["fg_dim"],
                          font=("Segoe UI", 9))
        ph_lbl.pack(side="left")
        self._reg(ph_lbl, "label_dim")
        self._i18n_widgets.append((ph_lbl, 'Быстрые пресеты'))

        add_btn = tk.Label(preset_header, text="＋", bg=self.T["bg"],
                           fg=self.T["fg_dim"], font=("Segoe UI", 14, "bold"),
                           cursor="hand2")
        add_btn.pack(side="right")
        self._reg(add_btn, "theme_btn")
        add_btn.bind("<Button-1>", lambda e: self._open_add_preset_dialog())
        add_btn.bind("<Enter>", lambda e: add_btn.config(fg=self.T["green"]))
        add_btn.bind("<Leave>", lambda e: add_btn.config(fg=self.T["fg_dim"]))
        self._tooltips.append(Tooltip(add_btn, 'Добавить свой пресет', app=self))

        prow1 = tk.Frame(self.preset_frame, bg=self.T["bg"]); prow1.pack()
        self._reg(prow1, "frame")
        prow2 = tk.Frame(self.preset_frame, bg=self.T["bg"]); prow2.pack(pady=(6, 0))
        self._reg(prow2, "frame")

        presets_defs = [
            (10, 'min', 0, 0, 10, 0), (20, 'min', 0, 0, 20, 0),
            (30, 'min', 0, 0, 30, 0), (1, 'h', 0, 1, 0, 0),
            (2, 'h', 0, 2, 0, 0),     (3, 'h', 0, 3, 0, 0),
            (6, 'h', 0, 6, 0, 0),     (12, 'h', 0, 12, 0, 0),
            (1, 'd', 1, 0, 0, 0),     (2, 'd', 2, 0, 0, 0),
            (3, 'd', 3, 0, 0, 0),     (7, 'd', 7, 0, 0, 0),
            (14, 'd', 14, 0, 0, 0),   (30, 'd', 30, 0, 0, 0),
        ]

        for i, (val, unit, d, h, m, s) in enumerate(presets_defs):
            parent = prow1 if i < 7 else prow2
            b = tk.Button(
                parent, text=_make_preset_label(val, unit, self._ui_lang),
                bg=self.T["preset_bg"], fg=self.T["fg"],
                activebackground=self.T["preset_hover"],
                activeforeground=self.T["fg"],
                font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                padx=12, pady=7, cursor="hand2",
                command=lambda d=d, h=h, m=m, s=s:
                    self.apply_preset((None, d, h, m, s)))
            b.pack(side="left", padx=3)
            self.preset_buttons.append((b, d, h, m, s, "std", val, unit))
            self._reg(b, "preset_std")

        # Секция своих пресетов
        self.custom_preset_section = tk.Frame(self.preset_frame, bg=self.T["bg"])
        self.custom_preset_section.pack(fill="x", pady=(10, 0))
        self._reg(self.custom_preset_section, "frame")

        cps_lbl = tk.Label(self.custom_preset_section, text=self._t('Свои пресеты'),
                           bg=self.T["bg"], fg=self.T["fg_dim"],
                           font=("Segoe UI", 9))
        cps_lbl.pack(anchor="w", padx=4, pady=(0, 5))
        self._reg(cps_lbl, "label_dim")
        self._i18n_widgets.append((cps_lbl, 'Свои пресеты'))

        self.custom_preset_row = tk.Frame(self.custom_preset_section, bg=self.T["bg"])
        self.custom_preset_row.pack()
        self._reg(self.custom_preset_row, "frame")

        # ---- Buttons ----
        btns = tk.Frame(self.root, bg=self.T["bg"])
        btns.pack(pady=(4, 10))
        self._reg(btns, "frame")

        self.start_btn = tk.Button(
            btns, text=self._t('▶  Запустить'),
            bg=self.T["btn_start"], fg=self.T["white"],
            activebackground=self.T["btn_start_hov"],
            activeforeground=self.T["white"],
            font=("Segoe UI", 12, "bold"), relief="flat",
            padx=20, pady=10, cursor="hand2", bd=0,
            command=self.start_timer)
        self.start_btn.pack(side="left", padx=6)
        self._reg(self.start_btn, "btn_start")
        self._i18n_widgets.append((self.start_btn, '▶  Запустить'))

        self.pause_btn = tk.Button(
            btns, text=self._t('⏸  Пауза'),
            bg=self.T["btn_pause"], fg=self.T["white"],
            activebackground=self.T["btn_pause_hov"],
            activeforeground=self.T["white"],
            font=("Segoe UI", 12, "bold"), relief="flat",
            padx=20, pady=10, cursor="hand2", bd=0,
            state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=6)
        self._reg(self.pause_btn, "btn_pause")

        self.cancel_btn = tk.Button(
            btns, text=self._t('✕  Отменить'),
            bg=self.T["btn_cancel"], fg=self.T["white"],
            activebackground=self.T["btn_cancel_hov"],
            activeforeground=self.T["white"],
            font=("Segoe UI", 12, "bold"), relief="flat",
            padx=20, pady=10, cursor="hand2", bd=0,
            state="disabled", command=self.cancel_timer)
        self.cancel_btn.pack(side="left", padx=6)
        self._reg(self.cancel_btn, "btn_cancel")
        self._i18n_widgets.append((self.cancel_btn, '✕  Отменить'))

        # ---- Status ----
        self.status = tk.Label(self.root, text=self._t(self._status_key),
                               bg=self.T["bg"], fg=self.T["fg_dim"],
                               font=("Segoe UI", 14, "bold"))
        self.status.pack(pady=4)
        self._reg(self.status, "label_dim")

        self.hint = tk.Label(self.root, text="",
                             bg=self.T["bg"], fg=self.T["fg_dim"],
                             font=("Segoe UI", 9))
        self.hint.pack()
        self._reg(self.hint, "label_dim")

        # ---- Bottom bar ----
        bottom_bar = tk.Frame(self.root, bg=self.T["bg"])
        bottom_bar.pack(pady=(14, 12))
        self._reg(bottom_bar, "frame")

        def _separator():
            """Точка-разделитель между ссылками. Участвует в перекраске тем."""
            sep = tk.Label(bottom_bar, text="  •  ", bg=self.T["bg"],
                           fg=self.T["fg_dim"], font=("Segoe UI", 9))
            sep.pack(side="left")
            self._reg(sep, "label_dim")
            return sep

        self.minimize_link = tk.Label(
            bottom_bar, text=self._t('Свернуть'), bg=self.T["bg"], fg=self.T["fg_dim"],
            font=("Segoe UI", 9, "underline"), cursor="hand2")
        self.minimize_link.pack(side="left")
        self._reg(self.minimize_link, "label_dim")
        self._i18n_widgets.append((self.minimize_link, 'Свернуть'))
        self.minimize_link.bind("<Button-1>", lambda e: self.hide_to_tray())
        self.minimize_link.bind("<Enter>",
                                lambda e: self.minimize_link.config(fg=self.T["green"]))
        self.minimize_link.bind("<Leave>",
                                lambda e: self.minimize_link.config(fg=self.T["fg_dim"]))

        _separator()

        log_lbl = tk.Label(bottom_bar, text=self._t('Журнал'), bg=self.T["bg"],
                           fg=self.T["fg_dim"], font=("Segoe UI", 9, "underline"),
                           cursor="hand2")
        log_lbl.pack(side="left")
        self._reg(log_lbl, "label_dim")
        self._i18n_widgets.append((log_lbl, 'Журнал'))
        log_lbl.bind("<Button-1>", lambda e: self._open_log_window())
        log_lbl.bind("<Enter>", lambda e: log_lbl.config(fg=self.T["green"]))
        log_lbl.bind("<Leave>", lambda e: log_lbl.config(fg=self.T["fg_dim"]))

        _separator()

        exp_lbl = tk.Label(bottom_bar, text=self._t('💾 Экспорт'),
                           bg=self.T["bg"], fg=self.T["fg_dim"],
                           font=("Segoe UI", 9, "underline"), cursor="hand2")
        exp_lbl.pack(side="left")
        self._reg(exp_lbl, "label_dim")
        self._i18n_widgets.append((exp_lbl, '💾 Экспорт'))
        exp_lbl.bind("<Button-1>", lambda e: self._export_settings())
        exp_lbl.bind("<Enter>", lambda e: exp_lbl.config(fg=self.T["orange"]))
        exp_lbl.bind("<Leave>", lambda e: exp_lbl.config(fg=self.T["fg_dim"]))
        self._tooltips.append(Tooltip(exp_lbl, 'Экспорт настроек в файл', app=self))

        _separator()

        imp_lbl = tk.Label(bottom_bar, text=self._t('📥 Импорт'),
                           bg=self.T["bg"], fg=self.T["fg_dim"],
                           font=("Segoe UI", 9, "underline"), cursor="hand2")
        imp_lbl.pack(side="left")
        self._reg(imp_lbl, "label_dim")
        self._i18n_widgets.append((imp_lbl, '📥 Импорт'))
        imp_lbl.bind("<Button-1>", lambda e: self._import_settings())
        imp_lbl.bind("<Enter>", lambda e: imp_lbl.config(fg=self.T["orange"]))
        imp_lbl.bind("<Leave>", lambda e: imp_lbl.config(fg=self.T["fg_dim"]))
        self._tooltips.append(Tooltip(imp_lbl, 'Импорт настроек из файла', app=self))

        _separator()

        self.close_btn = tk.Label(
            bottom_bar, text=self._t('Закрыть'), bg=self.T["bg"], fg=self.T["fg_dim"],
            font=("Segoe UI", 9, "underline"), cursor="hand2")
        self.close_btn.pack(side="left")
        self._reg(self.close_btn, "label_dim")
        self._i18n_widgets.append((self.close_btn, 'Закрыть'))
        self.close_btn.bind("<Button-1>", lambda e: self.close_app())
        self.close_btn.bind("<Enter>",
                            lambda e: self.close_btn.config(fg=self.T["red"]))
        self.close_btn.bind("<Leave>",
                            lambda e: self.close_btn.config(fg=self.T["fg_dim"]))

        self.root.bind_all("<MouseWheel>", self._global_wheel)
        self.root.bind("<Return>", lambda e: self.start_timer())

        self._create_mini_window()
        self._setup_tray()
        self._render_custom_presets()

        self._apply_time_mode()
        self._refresh_preset_highlight()
        self._refresh_radio_fg()

        self.root.after(200, self._apply_icon)
        self.root.after(600, self._check_existing_shutdown)
        self.root.after(500, self._poll_signal)
        self.root.after(1000, self._setup_hotkeys)

        log_event("=== " + self._t('Таймер выключения') + " ===")

        if self._autorun_launch and TRAY_AVAILABLE:
            self.root.after(800, self._notify_started_in_tray)

    # ============ i18n ============
    def _t(self, key, **fmt):
        return _tr(key, self._ui_lang, **fmt)

    def _rebuild_all_texts(self):
        for w, key in self._i18n_widgets:
            try:
                if w.winfo_exists():
                    w.config(text=self._t(key))
            except Exception:
                pass
        for entry in self.preset_buttons:
            if len(entry) >= 8 and entry[5] == "std":
                b, d, h, m, s, kind, val, unit = entry[:8]
                try:
                    b.config(text=_make_preset_label(val, unit, self._ui_lang))
                except Exception:
                    pass
        for sp in (self.days, self.hours, self.minutes, self.seconds,
                   self.at_hour, self.at_minute):
            try:
                sp.set_lang(self._ui_lang)
            except Exception:
                pass
        try:
            self.pause_btn.config(text=self._t(self._current_pause_key()))
        except Exception:
            pass
        try:
            self.status.config(text=self._t(self._status_key))
        except Exception:
            pass
        try:
            if self._hint_key:
                action_text = self._t(self._action_buttons_text_keys[self._current_action()])
                action_clean = action_text.split("  ", 1)[-1].strip()
                self.hint.config(text=self._t('Действие:') + " " + action_clean)
            else:
                self.hint.config(text="")
        except Exception:
            pass
        try:
            self._update_at_info()
        except Exception:
            pass
        try:
            if TRAY_AVAILABLE and self.tray_icon is not None:
                self._rebuild_tray_menu()
        except Exception:
            pass
        try:
            self.root.title(self._t('Таймер выключения ПК'))
        except Exception:
            pass
        self._refresh_radio_fg()

    def _current_pause_key(self):
        return '▶  Продолжить' if self.paused else '⏸  Пауза'

    def _theme_tooltip_key(self):
        if self.theme_name == "dark":
            return 'Переключить на светлую тему'
        return 'Переключить на тёмную тему'

    def _lang_press(self, e):
        self._lang_click_x = e.x_root
        self._lang_click_y = e.y_root

    def _lang_release(self, e):
        try:
            if (abs(e.x_root - self._lang_click_x) < 5 and
                    abs(e.y_root - self._lang_click_y) < 5):
                self._show_lang_menu()
        except Exception:
            pass

    def _show_lang_menu(self):
        T = self.T
        m = tk.Menu(self.root, tearoff=0,
                    bg=T["bg_dark"], fg=T["fg"],
                    activebackground=T["preset_active"],
                    activeforeground=T["selected_fg"],
                    bd=0, relief="flat",
                    font=("Segoe UI", 10))
        for code, name in UI_LANGS.items():
            prefix = "✓  " if code == self._ui_lang else "     "
            m.add_command(label=prefix + name,
                          command=lambda c=code: self._set_ui_lang(c))
        try:
            x = self._lang_btn.winfo_rootx()
            y = self._lang_btn.winfo_rooty() + self._lang_btn.winfo_height() + 2
            m.tk_popup(x, y)
        finally:
            try:
                m.grab_release()
            except Exception:
                pass

    def _set_ui_lang(self, code):
        if code not in UI_LANGS:
            return
        self._ui_lang = code
        self.settings["ui_lang"] = code
        save_settings(self.settings)
        if self._lang_btn is not None:
            self._lang_btn.config(text=f"🌐 {code.upper()}")
        try:
            self._theme_tooltip.set_key(self._theme_tooltip_key())
        except Exception:
            pass
        self._rebuild_all_texts()

    def _refresh_radio_fg(self):
        T = self.T
        try:
            for key, btn in self.action_buttons.items():
                selected = (self.action_var.get() == key)
                btn.config(
                    fg=T["selected_fg"] if selected else T["fg"],
                    activeforeground=T["selected_fg"] if selected else T["fg"])
        except Exception:
            pass
        try:
            for btn, val in ((self.mode_duration_btn, "duration"),
                             (self.mode_attime_btn, "attime")):
                selected = (self.time_mode.get() == val)
                btn.config(
                    fg=T["selected_fg"] if selected else T["fg"],
                    activeforeground=T["selected_fg"] if selected else T["fg"])
        except Exception:
            pass

    # ============ ЭКСПОРТ / ИМПОРТ ============
    def _collect_all_settings(self):
        data = dict(self.settings)
        data["theme"] = self.theme_name
        data["days"] = self.days.get()
        data["hours"] = self.hours.get()
        data["minutes"] = self.minutes.get()
        data["seconds"] = self.seconds.get()
        data["at_hour"] = self.at_hour.get()
        data["at_minute"] = self.at_minute.get()
        data["time_mode"] = self.time_mode.get()
        data["action"] = self.action_var.get()
        data["game_mode"] = self._game_mode
        data["ui_lang"] = self._ui_lang
        data.pop("autorun_method", None)
        return data

    def _export_settings(self):
        try:
            data = self._collect_all_settings()
            default_name = "ShutdownTimer_settings.json"
            path = filedialog.asksaveasfilename(
                title=self._t('Куда сохранить настройки?'),
                defaultextension=".json",
                initialdir=os.path.expanduser("~"),
                initialfile=default_name,
                filetypes=[("JSON", "*.json"), ("*.*", "*.*")])
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log_event(f"Export: {path}")
            self.status.config(text=self._t('✅ Настройки экспортированы'),
                               fg=self.T["green"])
            self._show_warning_dialog(
                self._t('Экспорт завершён'),
                self._t('Настройки сохранены в файл:') + f"\n\n{path}")
        except Exception as e:
            log_event(f"Export error: {e}")
            self._show_warning_dialog(self._t('Ошибка экспорта'),
                                       self._t('Не удалось сохранить:') + f"\n{e}")

    def _import_settings(self):
        try:
            path = filedialog.askopenfilename(
                title=self._t('Выберите файл с настройками'),
                initialdir=os.path.expanduser("~"),
                filetypes=[("JSON", "*.json"), ("*.*", "*.*")])
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(self._t('Файл не содержит корректных настроек'))
            if not any(k in data for k in
                       ("theme", "action", "time_mode",
                        "days", "hours", "minutes", "seconds")):
                raise ValueError(self._t('Это не файл настроек ShutdownTimer.'))
            self._apply_imported_settings(data)
            log_event(f"Import: {path}")
            self.status.config(text=self._t('✅ Настройки импортированы'),
                               fg=self.T["green"])
            self._show_warning_dialog(
                self._t('Импорт завершён'),
                self._t('Настройки успешно загружены и применены.'))
        except json.JSONDecodeError as e:
            self._show_warning_dialog(self._t('Ошибка чтения'),
                                       self._t('Файл повреждён или не JSON:') + f"\n{e}")
        except Exception as e:
            log_event(f"Import error: {e}")
            self._show_warning_dialog(self._t('Ошибка импорта'),
                                       self._t('Не удалось загрузить:') + f"\n{e}")

    def _apply_imported_settings(self, data):
        self.settings.update(data)
        new_theme = data.get("theme", self.theme_name)
        if new_theme not in THEMES:
            new_theme = "dark"
        if new_theme != self.theme_name:
            self.theme_name = new_theme
            self.T.clear()
            self.T.update(THEMES[new_theme])
            self._repaint_all()
            self._update_theme_button()
        new_lang = data.get("ui_lang", self._ui_lang)
        if new_lang in UI_LANGS:
            self._ui_lang = new_lang
        try:
            self.days.set_value(int(data.get("days", self.days.get())))
            self.hours.set_value(int(data.get("hours", self.hours.get())))
            self.minutes.set_value(int(data.get("minutes", self.minutes.get())))
            self.seconds.set_value(int(data.get("seconds", self.seconds.get())))
            self.at_hour.set_value(int(data.get("at_hour", self.at_hour.get())))
            self.at_minute.set_value(int(data.get("at_minute", self.at_minute.get())))
        except Exception:
            pass
        tm = data.get("time_mode", self.time_mode.get())
        if tm in ("duration", "attime"):
            self.time_mode.set(tm)
            self._apply_time_mode()
        act = data.get("action", self.action_var.get())
        if act in ACTIONS:
            self.action_var.set(act)
        gm = bool(data.get("game_mode", self._game_mode))
        if gm != self._game_mode:
            self._game_mode = gm
            self.root.after(50, self._apply_game_mode)
        self._render_custom_presets()
        self._refresh_radio_fg()
        if self._lang_btn is not None:
            self._lang_btn.config(text=f"🌐 {self._ui_lang.upper()}")
        self._rebuild_all_texts()
        self._persist_settings()

    # ============ ХОТКЕИ ============
    def _setup_hotkeys(self):
        if not KEYBOARD_OK:
            return
        try:
            keyboard.add_hotkey("ctrl+alt+s", lambda: self.root.after(0, self._hotkey_toggle))
            keyboard.add_hotkey("ctrl+alt+p", lambda: self.root.after(0, self._hotkey_pause))
            keyboard.add_hotkey("ctrl+alt+x", lambda: self.root.after(0, self._hotkey_cancel))
        except Exception:
            pass

    def _hotkey_toggle(self):
        try:
            if self.root.state() == "withdrawn":
                if self.shutdown_active:
                    self._show_mini()
                else:
                    self._restore_main()
            else:
                self.hide_to_tray()
        except Exception:
            pass

    def _hotkey_pause(self):
        if self.shutdown_active:
            self.toggle_pause()

    def _hotkey_cancel(self):
        if self.shutdown_active:
            self.cancel_timer()

    # ============ Time mode ============
    def _on_time_mode_changed(self):
        self.settings["time_mode"] = self.time_mode.get()
        save_settings(self.settings)
        self._refresh_radio_fg()
        self._apply_time_mode()

    def _apply_time_mode(self):
        if self.time_mode.get() == "duration":
            self.attime_frame.pack_forget()
            self.duration_frame.pack(pady=(10, 10), before=self.preset_frame)
        else:
            self.duration_frame.pack_forget()
            self.attime_frame.pack(pady=(10, 10), before=self.preset_frame)
            self.at_info.pack(pady=(8, 0))
            self._update_at_info()
        self._refresh_preset_highlight()

    def _update_at_info(self):
        h = self.at_hour.get()
        m = self.at_minute.get()
        now = datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
            suffix = self._t('завтра')
        else:
            suffix = self._t('сегодня')
        diff = int((target - now).total_seconds())
        hh = diff // 3600
        mm = (diff % 3600) // 60
        self.at_info.config(
            text=f"⏳ {suffix} {self._t('в')} {h:02d}:{m:02d}  •  "
                 f"{self._t('через')} {hh}{self._t('ч')} {mm:02d}{self._t('мин')}")

    def _on_at_time_change(self):
        self._update_at_info()
        self._persist_settings()

    def _compute_total_seconds(self):
        if self.time_mode.get() == "duration":
            return (self.days.get() * 86400 + self.hours.get() * 3600
                    + self.minutes.get() * 60 + self.seconds.get())
        else:
            now = datetime.now()
            target = now.replace(hour=self.at_hour.get(),
                                 minute=self.at_minute.get(),
                                 second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return max(1, int((target - now).total_seconds()))

    # ============ Single instance ============
    def _poll_signal(self):
        try:
            if os.path.exists(SIGNAL_FILE):
                try:
                    os.remove(SIGNAL_FILE)
                except Exception:
                    pass
                self._restore_main()
        except Exception:
            pass
        try:
            self.root.after(500, self._poll_signal)
        except Exception:
            pass

    # ============ Theme ============
    def _reg(self, widget, role):
        self._styled.append((widget, role))

    def _update_theme_button(self):
        if self._theme_btn is None:
            return
        self._theme_btn.config(text="☾" if self.theme_name == "dark" else "☀")

    def _toggle_theme(self):
        new_name = "light" if self.theme_name == "dark" else "dark"
        self.theme_name = new_name
        self.settings["theme"] = new_name
        save_settings(self.settings)
        self.T.clear()
        self.T.update(THEMES[new_name])
        self._repaint_all()
        self._update_theme_button()
        if self._theme_tooltip is not None:
            self._theme_tooltip.set_key(self._theme_tooltip_key())

    def _apply_style(self, widget, role):
        T = self.T
        try:
            if role == "frame":
                widget.config(bg=T["bg"])
            elif role == "label":
                widget.config(bg=T["bg"], fg=T["fg"])
            elif role == "label_dim":
                widget.config(bg=T["bg"], fg=T["fg_dim"])
            elif role == "icon_green":
                widget.config(bg=T["bg"], fg=T["green"])
            elif role == "theme_btn":
                widget.config(bg=T["bg"], fg=T["fg_dim"])
            elif role == "lang_btn":
                widget.config(bg=T["bg"], fg=T["fg_dim"])
            elif role == "preset_std":
                widget.config(bg=T["preset_bg"], fg=T["fg"],
                              activebackground=T["preset_hover"],
                              activeforeground=T["fg"])
            elif role == "preset_custom":
                widget.config(bg=T["custom_bg"], fg=T["fg"],
                              activebackground=T["custom_hover"],
                              activeforeground=T["fg"])
            elif role == "custom_del":
                widget.config(bg=T["custom_bg"], fg=T["fg_dim"],
                              activebackground=T["red"],
                              activeforeground=T["white"])
            elif role == "action_btn":
                widget.config(bg=T["action_bg"], fg=T["fg"],
                              activebackground=T["action_hover"],
                              activeforeground=T["fg"],
                              selectcolor=T["action_active"])
            elif role == "btn_start":
                widget.config(bg=T["btn_start"], fg=T["white"],
                              activebackground=T["btn_start_hov"],
                              activeforeground=T["white"])
            elif role == "btn_pause":
                widget.config(bg=T["btn_pause"], fg=T["white"],
                              activebackground=T["btn_pause_hov"],
                              activeforeground=T["white"])
            elif role == "btn_cancel":
                widget.config(bg=T["btn_cancel"], fg=T["white"],
                              activebackground=T["btn_cancel_hov"],
                              activeforeground=T["white"])
        except Exception:
            pass

    def _repaint_all(self):
        try:
            self.root.configure(bg=self.T["bg"])
        except Exception:
            pass
        for widget, role in self._styled:
            try:
                if widget.winfo_exists():
                    self._apply_style(widget, role)
            except Exception:
                pass
        for sp in (self.days, self.hours, self.minutes, self.seconds,
                   self.at_hour, self.at_minute):
            try:
                sp.repaint()
            except Exception:
                pass
        self._repaint_mini()
        self._refresh_preset_highlight()
        self._refresh_radio_fg()

    def _repaint_mini(self):
        T = self.T
        try:
            self.mini.configure(bg=T["green"])
            self._mini_inner.configure(bg=T["bg_dark"])
            self._mini_row.configure(bg=T["bg_dark"])
            self.mini_icon.configure(bg=T["bg_dark"], fg=T["green"])
            self.mini_time.configure(bg=T["bg_dark"], fg=T["green"])
            self.mini_pause.configure(bg=T["bg_dark"], fg=T["fg_dim"])
            self.mini_expand.configure(bg=T["bg_dark"], fg=T["fg_dim"])
            self.mini_close.configure(bg=T["bg_dark"], fg=T["fg_dim"])
            self.mini_progress.configure(bg=T["bg_dark"])
            self.mini_progress.itemconfig(self._progress_rect, fill=T["green"])
        except Exception:
            pass

    # ============ Drag ============
    def _enable_drag(self, widget):
        widget.bind("<Button-1>", self._drag_window_start, add="+")
        widget.bind("<B1-Motion>", self._drag_window_move, add="+")
        for child in widget.winfo_children():
            self._enable_drag(child)

    def _drag_window_start(self, e):
        self._drag_offset_x = e.x_root - self.root.winfo_x()
        self._drag_offset_y = e.y_root - self.root.winfo_y()

    def _drag_window_move(self, e):
        x = e.x_root - self._drag_offset_x
        y = e.y_root - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    # ============ Settings ============
    def _collect_settings(self):
        return {
            "days": self.days.get(),
            "hours": self.hours.get(),
            "minutes": self.minutes.get(),
            "seconds": self.seconds.get(),
            "at_hour": self.at_hour.get(),
            "at_minute": self.at_minute.get(),
            "time_mode": self.time_mode.get(),
            "action": self.action_var.get(),
            "game_mode": self._game_mode,
            "autorun_method": self.settings.get("autorun_method", "none"),
            "start_minimized": self.settings.get("start_minimized", False),
            "custom_presets": self.settings.get("custom_presets", []),
            "theme": self.theme_name,
            "ui_lang": self._ui_lang,
        }

    def _persist_settings(self):
        self.settings = self._collect_settings()
        save_settings(self.settings)

    def _on_action_changed(self):
        self._persist_settings()
        self._refresh_radio_fg()
        if self.action_var.get() == "hibernate" and not self._hibernation_warned:
            threading.Thread(target=self._check_hibernation, daemon=True).start()

    def _on_spinner_change(self):
        self._refresh_preset_highlight()
        self._persist_settings()

    def _notify_started_in_tray(self):
        if TRAY_AVAILABLE and self.tray_icon is not None:
            try:
                self.tray_icon.notify(
                    self._t('Приложение запущено и свёрнуто в трей.'),
                    self._t('Таймер выключения ПК'))
            except Exception:
                pass

    # ============ Custom presets ============
    def _get_custom_presets(self):
        return list(self.settings.get("custom_presets", []))

    def _set_custom_presets(self, presets):
        self.settings["custom_presets"] = presets
        save_settings(self.settings)

    def _render_custom_presets(self):
        # Очищаем секцию
        for wdg in self.custom_preset_row.winfo_children():
            wdg.destroy()
        self._custom_preset_frames = []

        # Убираем кастомные из preset_buttons и styled
        self.preset_buttons = [b for b in self.preset_buttons if b[5] == "std"]
        self._styled = [(w, r) for (w, r) in self._styled
                        if r not in ("preset_custom", "custom_del")]

        customs = self._get_custom_presets()
        if not customs:
            self.custom_preset_section.pack_forget()
            self._refresh_preset_highlight()
            return

        self.custom_preset_section.pack(fill="x", pady=(10, 0))

        for idx, p in enumerate(customs):
            name = p.get("name", "?")
            d = int(p.get("d", 0)); h = int(p.get("h", 0))
            m = int(p.get("m", 0)); s = int(p.get("s", 0))

            # Фрейм-обёртка для пары кнопок
            grp = tk.Frame(self.custom_preset_row, bg=self.T["bg"])
            grp.pack(side="left", padx=3)
            self._custom_preset_frames.append(grp)

            # Основная кнопка пресета
            b = tk.Button(
                grp, text=name,
                bg=self.T["custom_bg"], fg=self.T["fg"],
                activebackground=self.T["custom_hover"],
                activeforeground=self.T["fg"],
                font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                padx=12, pady=7, cursor="hand2",
                command=lambda d=d, h=h, m=m, s=s:
                    self.apply_preset((None, d, h, m, s)))
            b.pack(side="left")
            self.preset_buttons.append((b, d, h, m, s, "custom", 0, ''))
            self._reg(b, "preset_custom")

            # Правый клик — тоже открывает меню (для совместимости)
            b.bind("<Button-3>",
                   lambda e, i=idx, nm=name: self._custom_preset_menu(e, i, nm))

            # Маленькая кнопка × для удаления
            del_btn = tk.Button(
                grp, text="✕",
                bg=self.T["custom_bg"], fg=self.T["fg_dim"],
                activebackground=self.T["red"],
                activeforeground=self.T["white"],
                font=("Segoe UI", 8, "bold"), relief="flat", bd=0,
                padx=5, pady=7, cursor="hand2",
                command=lambda i=idx: self._delete_custom_preset(i))
            del_btn.pack(side="left", padx=(1, 0))
            self._reg(del_btn, "custom_del")
            self._tooltips.append(Tooltip(del_btn, 'Удалить этот пресет', app=self))

        self._refresh_preset_highlight()

    def _custom_preset_menu(self, event, idx, name):
        """Правый клик — контекстное меню."""
        menu = tk.Menu(self.root, tearoff=0,
                       bg=self.T["bg_dark"], fg=self.T["fg"],
                       activebackground=self.T["preset_active"],
                       activeforeground=self.T["selected_fg"],
                       bd=0, font=("Segoe UI", 9))
        label = f"✕  {self._t('Удалить')} «{name}»"
        menu.add_command(label=label,
                         command=lambda: self._delete_custom_preset(idx))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _delete_custom_preset(self, idx):
        customs = self._get_custom_presets()
        if 0 <= idx < len(customs):
            removed = customs.pop(idx)
            self._set_custom_presets(customs)
            log_event(f"Custom preset removed: {removed.get('name', '?')}")
            self._render_custom_presets()

    def _open_add_preset_dialog(self):
        if self._preset_dlg is not None:
            try:
                if self._preset_dlg.winfo_exists():
                    self._preset_dlg.lift()
                    self._preset_dlg.attributes("-topmost", True)
                    return
            except Exception:
                pass
            self._preset_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["green"])
        self._preset_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(18, 6))
        tk.Label(top, text="✦", bg=T["bg"], fg=T["green"],
                 font=("Segoe UI", 20)).pack(side="left", padx=(0, 10))
        tk.Label(top, text=self._t('Новый пресет'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        name_frame = tk.Frame(inner, bg=T["bg"])
        name_frame.pack(padx=22, pady=(8, 4), fill="x")
        tk.Label(name_frame, text=self._t('Название'), bg=T["bg"], fg=T["fg_dim"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        name_var = tk.StringVar(value=self._t('Мой пресет'))
        name_entry = tk.Entry(
            name_frame, textvariable=name_var,
            bg=T["entry_bg"], fg=T["fg"], insertbackground=T["fg"],
            font=("Segoe UI", 11), relief="flat", bd=0,
            highlightthickness=1, highlightbackground=T["entry_border"],
            highlightcolor=T["green"])
        name_entry.pack(fill="x", ipady=6, pady=(4, 0))

        spin_row = tk.Frame(inner, bg=T["bg"])
        spin_row.pack(padx=22, pady=(14, 6))

        d_sp = Spinner(spin_row, 'Дни', 30, T=T, app=self)
        h_sp = Spinner(spin_row, 'Часы', 23, T=T, app=self)
        m_sp = Spinner(spin_row, 'Минуты', 59, T=T, app=self)
        s_sp = Spinner(spin_row, 'Секунды', 59, T=T, app=self)

        d_sp.pack(side="left", padx=6)
        tk.Label(spin_row, text=":", bg=T["bg"], fg=T["fg_dim"],
                 font=("Consolas", 24, "bold")).pack(side="left", pady=(28, 0))
        h_sp.pack(side="left", padx=6)
        tk.Label(spin_row, text=":", bg=T["bg"], fg=T["fg_dim"],
                 font=("Consolas", 24, "bold")).pack(side="left", pady=(28, 0))
        m_sp.pack(side="left", padx=6)
        tk.Label(spin_row, text=":", bg=T["bg"], fg=T["fg_dim"],
                 font=("Consolas", 24, "bold")).pack(side="left", pady=(28, 0))
        s_sp.pack(side="left", padx=6)

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(pady=(14, 18))

        def close_dlg():
            self._preset_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        def do_create():
            name = name_var.get().strip() or self._t('Без названия')
            if len(name) > 16:
                name = name[:16]
            d = d_sp.get(); h = h_sp.get(); m = m_sp.get(); s = s_sp.get()
            if d + h + m + s <= 0:
                self._show_warning_dialog(
                    self._t('Пустой пресет'),
                    self._t('Нельзя сохранить пресет, где всё время по нулям.'))
                return
            customs = self._get_custom_presets()
            customs.append({"name": name, "d": d, "h": h, "m": m, "s": s})
            self._set_custom_presets(customs)
            log_event(f"Custom preset added: {name}")
            self._render_custom_presets()
            close_dlg()

        tk.Button(btn_row, text=self._t('Отмена'),
                  bg=T["preset_bg"], fg=T["fg"],
                  activebackground=T["preset_hover"],
                  activeforeground=T["fg"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=22, pady=8, cursor="hand2",
                  command=close_dlg).pack(side="left", padx=6)
        tk.Button(btn_row, text=self._t('Создать'),
                  bg=T["btn_start"], fg=T["white"],
                  activebackground=T["btn_start_hov"],
                  activeforeground=T["white"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=22, pady=8, cursor="hand2",
                  command=do_create).pack(side="left", padx=6)

        def _center_dialog():
            try:
                dlg.update_idletasks()
                dw = dlg.winfo_reqwidth()
                dh = dlg.winfo_reqheight()
                if self.root.state() == "withdrawn":
                    sw2 = self.root.winfo_screenwidth()
                    sh2 = self.root.winfo_screenheight()
                    dx = (sw2 - dw) // 2
                    dy = (sh2 - dh) // 2
                else:
                    rx = self.root.winfo_rootx()
                    ry = self.root.winfo_rooty()
                    rw = self.root.winfo_width()
                    rh = self.root.winfo_height()
                    if rw <= 1 or rh <= 1:
                        sw2 = self.root.winfo_screenwidth()
                        sh2 = self.root.winfo_screenheight()
                        dx = (sw2 - dw) // 2
                        dy = (sh2 - dh) // 2
                    else:
                        dx = rx + (rw - dw) // 2
                        dy = ry + (rh - dh) // 2
                if dx < 0: dx = 0
                if dy < 0: dy = 0
                dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")
            except Exception:
                pass

        dlg.update_idletasks()
        _center_dialog()
        self.root.after(30, _center_dialog)

        def _drag_start(e):
            dlg._dx = e.x_root - dlg.winfo_x()
            dlg._dy = e.y_root - dlg.winfo_y()
        def _drag_move(e):
            dlg.geometry(f"+{e.x_root - dlg._dx}+{e.y_root - dlg._dy}")
        top.bind("<Button-1>", _drag_start)
        top.bind("<B1-Motion>", _drag_move)

        dlg.lift()
        dlg.attributes("-topmost", True)
        dlg.bind("<Escape>", lambda e: close_dlg())
        name_entry.focus_set()
        name_entry.select_range(0, "end")

    # ============ Hibernation ============
    def _hibernation_available(self):
        try:
            return os.path.exists("C:\\hiberfil.sys")
        except Exception:
            return True

    def _check_hibernation(self):
        if self._hibernation_available():
            return
        self._hibernation_warned = True
        self.root.after(0, lambda: self._show_warning_dialog(
            self._t('Гибернация выключена'),
            self._t('На этом компьютере гибернация отключена.') + "\n\n" +
            self._t('Включите её в параметрах электропитания Windows или выберите «Сон».')))

    # ============ Icon ============
    def _apply_icon(self):
        if not TRAY_AVAILABLE:
            return
        try:
            img = self._make_icon_image(active=False)
            ico_path = os.path.join(tempfile.gettempdir(), "shutdown_timer_icon.ico")
            try:
                img.save(ico_path, format="ICO",
                         sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
                self.root.iconbitmap(default=ico_path)
            except Exception:
                pass
            photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, photo)
            self._icon_photo = photo
        except Exception:
            pass

    # ============ Click-through ============
    def _set_click_through(self, enable):
        try:
            hwnd = self.mini.winfo_id()
            root_hwnd = ctypes.windll.user32.GetAncestor(hwnd, GA_ROOT)
            if root_hwnd:
                hwnd = root_hwnd
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enable:
                ex_style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED)
            else:
                ex_style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            self.mini.withdraw()
            self.mini.deiconify()
            self.mini.attributes("-topmost", True)
        except Exception:
            pass

    def _apply_game_mode(self):
        if self._game_mode:
            self._set_click_through(True)
            try:
                self.mini_pause.grid_remove()
                self.mini_expand.grid_remove()
                self.mini_close.grid_remove()
            except Exception:
                pass
        else:
            self._set_click_through(False)
            try:
                self.mini_pause.grid()
                self.mini_expand.grid()
                self.mini_close.grid()
            except Exception:
                pass
        self._mini_positioned = False
        self.root.after(50, self._reshow_mini)

    def _reshow_mini(self):
        if not self.shutdown_active:
            return
        if not self.mini.winfo_ismapped():
            return
        self.mini.update_idletasks()
        w = self.mini.winfo_reqwidth()
        h = self.mini.winfo_reqheight()
        x = self.mini.winfo_x()
        y = self.mini.winfo_y()
        cur_w = self.mini.winfo_width()
        right = x + cur_w
        new_x = right - w
        if new_x < 0:
            new_x = 0
        self.mini.geometry(f"{w}x{h}+{new_x}+{y}")
        if self._game_mode:
            self.root.after(20, lambda: self._set_click_through(True))

    def _toggle_game_mode(self, icon=None, item=None):
        self._game_mode = not self._game_mode
        self._persist_settings()
        self.root.after(0, self._apply_game_mode)

    def _get_pulse_style(self, left):
        T = self.T
        if left > 600:
            return T["green"], T["green"], 0
        if left > 300:
            return T["green"], T["green_b"], 1.0
        if left > 60:
            return T["orange"], T["orange_b"], 1.5
        return T["red"], T["red_b"], 2.0

    # ============ Sound ============
    def _init_sounds(self):
        if not WINSOUND_OK:
            return
        try:
            base = os.path.join(tempfile.gettempdir(), "shutdown_timer_sounds")
            os.makedirs(base, exist_ok=True)
            specs = {
                "60":  ("s60.wav",  [(660, 180)]),
                "30":  ("s30.wav",  [(660, 120), (None, 60), (880, 120)]),
                "10":  ("s10.wav",  [(880, 100), (None, 50), (880, 100),
                                     (None, 50), (880, 100)]),
                "5":   ("s5.wav",   [(990, 140)]),
                "4":   ("s4.wav",   [(990, 140)]),
                "3":   ("s3.wav",   [(990, 140)]),
                "2":   ("s2.wav",   [(990, 140)]),
                "1":   ("s1.wav",   [(1320, 350)]),
            }
            for key, (fname, tones) in specs.items():
                path = os.path.join(base, fname)
                if not os.path.exists(path):
                    self._write_tones(path, tones)
                self._sound_files[key] = path
        except Exception:
            self._sound_files = {}

    def _write_tones(self, path, tones):
        amplitude = int(32767 * 0.7)
        fade = int(SAMPLE_RATE * 0.008)
        with wave.open(path, 'w') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            for freq, dur_ms in tones:
                n = int(SAMPLE_RATE * dur_ms / 1000)
                if freq is None:
                    for _ in range(n):
                        w.writeframes(struct.pack('<h', 0))
                else:
                    for i in range(n):
                        if i < fade:
                            env = i / fade
                        elif i > n - fade:
                            env = (n - i) / fade
                        else:
                            env = 1.0
                        val = int(amplitude * env *
                                  math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
                        w.writeframes(struct.pack('<h', val))

    def _play(self, key):
        if not WINSOUND_OK:
            return
        path = self._sound_files.get(key)
        if not path:
            return
        try:
            winsound.PlaySound(
                path,
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:
            pass

    def _maybe_beep(self, left):
        for threshold in (60, 30, 10, 5, 4, 3, 2, 1):
            if left <= threshold and threshold not in self._beeped:
                self._beeped.add(threshold)
                self._play(str(threshold))
                return

    # ============ Presets ============
    def apply_preset(self, preset):
        _, d, h, m, s = preset
        if self.time_mode.get() != "duration":
            self.time_mode.set("duration")
            self._apply_time_mode()
            self._refresh_radio_fg()
        self.days.set_value(d)
        self.hours.set_value(h)
        self.minutes.set_value(m)
        self.seconds.set_value(s)
        self._refresh_preset_highlight()
        self._persist_settings()

    def _refresh_preset_highlight(self):
        T = self.T
        is_duration = self.time_mode.get() == "duration"
        cur = (self.days.get(), self.hours.get(),
               self.minutes.get(), self.seconds.get()) if is_duration else None
        for entry in self.preset_buttons:
            btn, d, h, m, s, kind = entry[:6]
            base_bg = T["custom_bg"] if kind == "custom" else T["preset_bg"]
            base_hover = T["custom_hover"] if kind == "custom" else T["preset_hover"]
            try:
                if is_duration and (d, h, m, s) == cur:
                    btn.config(bg=T["preset_active"],
                               activebackground=T["preset_active"],
                               fg=T["selected_fg"])
                else:
                    btn.config(bg=base_bg, activebackground=base_hover,
                               fg=T["fg"])
            except Exception:
                pass

    def _set_presets_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for entry in self.preset_buttons:
            entry[0].config(state=state)
        for rb in self.action_buttons.values():
            rb.config(state=state)
        try:
            self.mode_duration_btn.config(state=state)
            self.mode_attime_btn.config(state=state)
        except Exception:
            pass

    # ============ Wheel ============
    def _global_wheel(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if isinstance(widget, Spinner):
                widget.change(1 if event.delta > 0 else -1)
                self._persist_settings()
                return
            widget = widget.master

    # ============ Mini widget ============
    def _create_mini_window(self):
        T = self.T
        self.mini = tk.Toplevel(self.root)
        self.mini.overrideredirect(True)
        self.mini.attributes("-topmost", True)
        self.mini.configure(bg=T["green"])
        self.mini.withdraw()

        self._mini_inner = tk.Frame(self.mini, bg=T["bg_dark"])
        self._mini_inner.pack(fill="both", expand=True, padx=2, pady=2)

        self._mini_row = tk.Frame(self._mini_inner, bg=T["bg_dark"])
        self._mini_row.pack(fill="x")
        for c in range(5):
            self._mini_row.grid_columnconfigure(c, weight=0)
        self._mini_row.grid_rowconfigure(0, weight=1)

        self.mini_icon = tk.Label(self._mini_row, text="⏻", bg=T["bg_dark"],
                                  fg=T["green"], font=("Segoe UI", 15, "bold"))
        self.mini_icon.grid(row=0, column=0, padx=(14, 6), sticky="w")

        self.mini_time = tk.Label(self._mini_row, text="00:00:00", bg=T["bg_dark"],
                                  fg=T["green"], font=("Consolas", 22, "bold"))
        self.mini_time.grid(row=0, column=1, padx=(4, 12), sticky="")

        self.mini_pause = tk.Label(self._mini_row, text="⏸", bg=T["bg_dark"],
                                   fg=T["fg_dim"], font=("Segoe UI", 12), cursor="hand2")
        self.mini_pause.grid(row=0, column=2, padx=(0, 10), sticky="e")

        self.mini_expand = tk.Label(self._mini_row, text="⤢", bg=T["bg_dark"],
                                    fg=T["fg_dim"], font=("Segoe UI", 14), cursor="hand2")
        self.mini_expand.grid(row=0, column=3, padx=(0, 10), sticky="e")

        self.mini_close = tk.Label(self._mini_row, text="✕", bg=T["bg_dark"],
                                   fg=T["fg_dim"], font=("Segoe UI", 12), cursor="hand2")
        self.mini_close.grid(row=0, column=4, padx=(0, 14), sticky="e")

        self.mini_progress = tk.Canvas(self._mini_inner, height=3, width=1,
                                       bg=T["bg_dark"], highlightthickness=0, bd=0)
        self.mini_progress.pack(fill="x", pady=(2, 2))
        self._progress_rect = self.mini_progress.create_rectangle(
            0, 0, 0, 3, fill=T["green"], outline="")

        for lbl, hover in ((self.mini_pause, T["fg"]),
                           (self.mini_expand, T["fg"]),
                           (self.mini_close, T["red"])):
            lbl.bind("<Enter>", lambda e, l=lbl, c=hover: l.config(fg=c))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=self.T["fg_dim"]))

        self.mini_pause.bind("<Button-1>", lambda e: self.toggle_pause())
        self.mini_expand.bind("<Button-1>", lambda e: self._expand_from_mini())
        self.mini_close.bind("<Button-1>",  lambda e: self._close_from_mini())

        for wdg in (self.mini, self._mini_inner, self._mini_row,
                    self.mini_icon, self.mini_time):
            wdg.bind("<Button-1>", self._drag_start)
            wdg.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.mini.winfo_x()
        self._drag_y = e.y_root - self.mini.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.mini.geometry(f"+{x}+{y}")

    def _fit_mini(self):
        if not self.mini.winfo_exists() or not self.mini.winfo_ismapped():
            return
        self.mini.update_idletasks()
        w = self.mini.winfo_reqwidth()
        h = self.mini.winfo_reqheight()
        cur_w = self.mini.winfo_width()
        cur_h = self.mini.winfo_height()
        if w == cur_w and h == cur_h:
            return
        x = self.mini.winfo_x()
        y = self.mini.winfo_y()
        right = x + cur_w
        new_x = right - w
        if new_x < 0:
            new_x = 0
        self.mini.geometry(f"{w}x{h}+{new_x}+{y}")

    def _show_mini(self):
        if not self._mini_positioned:
            self.mini.update_idletasks()
            w = self.mini.winfo_reqwidth()
            h = self.mini.winfo_reqheight()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = sw - w - 30
            y = (sh - h) // 2
            self.mini.geometry(f"{w}x{h}+{x}+{y}")
            self._mini_positioned = True
        else:
            self._fit_mini()
        self.mini.deiconify()
        self.mini.lift()
        self.mini.attributes("-topmost", True)
        if self._game_mode:
            self.root.after(30, self._apply_game_mode)
        self.root.after(50, lambda: self._update_progress(
            max(0, int(round(self.end_time - time.time())))))

    def _expand_from_mini(self):
        self.mini.withdraw()
        self.root.deiconify()
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass
        self.root.lift()
        self.root.focus_force()

    def _close_from_mini(self):
        self.mini.withdraw()
        self.cancel_timer()
        self.root.deiconify()
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass
        self.root.lift()
        self.root.focus_force()

    # ============ Warning dialog ============
    def _show_warning_dialog(self, title, message):
        if self._warning_dlg is not None:
            try:
                if self._warning_dlg.winfo_exists():
                    self._warning_dlg.lift()
                    self._warning_dlg.attributes("-topmost", True)
                    return
            except Exception:
                pass
            self._warning_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["orange"])
        self._warning_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(20, 10))
        tk.Label(top, text="⚠", bg=T["bg"], fg=T["orange"],
                 font=("Segoe UI", 22)).pack(side="left", padx=(0, 12))
        tk.Label(top, text=title, bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        tk.Label(inner, text=message, bg=T["bg"], fg=T["fg_dim"],
                 justify="left", font=("Segoe UI", 10),
                 wraplength=440).pack(padx=22, pady=(0, 18), anchor="w")

        def close_dlg():
            self._warning_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        ok = tk.Button(inner, text=self._t('Понятно'),
                       bg=T["orange"], fg="#1a1a1a",
                       activebackground=T["orange_hi"],
                       activeforeground="#1a1a1a",
                       font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                       padx=26, pady=8, cursor="hand2",
                       command=close_dlg)
        ok.pack(pady=(0, 20))

        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dx = (sw - dw) // 2
        dy = (sh - dh) // 2
        if dx < 0: dx = 0
        if dy < 0: dy = 0
        dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")

        def _drag_start(e):
            dlg._dx = e.x_root - dlg.winfo_x()
            dlg._dy = e.y_root - dlg.winfo_y()
        def _drag_move(e):
            dlg.geometry(f"+{e.x_root - dlg._dx}+{e.y_root - dlg._dy}")
        top.bind("<Button-1>", _drag_start)
        top.bind("<B1-Motion>", _drag_move)

        dlg.lift()
        dlg.attributes("-topmost", True)
        dlg.bind("<Escape>", lambda e: close_dlg())
        dlg.bind("<Return>", lambda e: close_dlg())
        ok.focus_set()

    # ============ Log window ============
    def _open_log_window(self):
        if self._log_dlg is not None:
            try:
                if self._log_dlg.winfo_exists():
                    self._log_dlg.lift()
                    self._log_dlg.attributes("-topmost", True)
                    self._refresh_log_text()
                    return
            except Exception:
                pass
            self._log_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["green"])
        self._log_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(18, 8))
        tk.Label(top, text="📋", bg=T["bg"], fg=T["green"],
                 font=("Segoe UI", 18)).pack(side="left", padx=(0, 10))
        tk.Label(top, text=self._t('Журнал событий'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        self._log_size_lbl = tk.Label(inner, text="", bg=T["bg"],
                                      fg=T["fg_dim"], font=("Segoe UI", 9))
        self._log_size_lbl.pack(anchor="w", padx=22, pady=(0, 6))

        text_wrap = tk.Frame(inner, bg=T["entry_border"])
        text_wrap.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        self._log_text = tk.Text(
            text_wrap, height=16, width=72,
            bg=T["entry_bg"], fg=T["fg"], insertbackground=T["fg"],
            font=("Consolas", 9), relief="flat", bd=0, wrap="word")
        self._log_text.pack(padx=1, pady=1, fill="both", expand=True)

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(pady=(0, 18))

        def close_dlg():
            self._log_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        tk.Button(btn_row, text=self._t('Обновить'),
                  bg=T["preset_bg"], fg=T["fg"],
                  activebackground=T["preset_hover"],
                  activeforeground=T["fg"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=18, pady=8, cursor="hand2",
                  command=self._refresh_log_text).pack(side="left", padx=5)
        tk.Button(btn_row, text=self._t('Очистить'),
                  bg=T["btn_cancel"], fg=T["white"],
                  activebackground=T["btn_cancel_hov"],
                  activeforeground=T["white"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=18, pady=8, cursor="hand2",
                  command=self._clear_log).pack(side="left", padx=5)
        tk.Button(btn_row, text=self._t('Закрыть'),
                  bg=T["btn_start"], fg=T["white"],
                  activebackground=T["btn_start_hov"],
                  activeforeground=T["white"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=18, pady=8, cursor="hand2",
                  command=close_dlg).pack(side="left", padx=5)

        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dx = (sw - dw) // 2
        dy = (sh - dh) // 2
        if dx < 0: dx = 0
        if dy < 0: dy = 0
        dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")

        def _drag_start(e):
            dlg._dx = e.x_root - dlg.winfo_x()
            dlg._dy = e.y_root - dlg.winfo_y()
        def _drag_move(e):
            dlg.geometry(f"+{e.x_root - dlg._dx}+{e.y_root - dlg._dy}")
        top.bind("<Button-1>", _drag_start)
        top.bind("<B1-Motion>", _drag_move)

        dlg.lift()
        dlg.attributes("-topmost", True)
        dlg.bind("<Escape>", lambda e: close_dlg())
        self._refresh_log_text()

    def _refresh_log_text(self):
        try:
            if not self._log_text.winfo_exists():
                return
            n = len(_LOG_BUFFER)
            self._log_size_lbl.config(
                text=f"{self._t('Журнал в памяти')}  •  "
                     f"{self._t('записей')}: {n} ({self._t('макс.')} 500)")
            self._log_text.config(state="normal")
            self._log_text.delete("1.0", "end")
            self._log_text.insert("end", get_log_text())
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        except Exception:
            pass

    def _clear_log(self):
        try:
            clear_log_memory()
            log_event("=== Log cleared ===")
            self._refresh_log_text()
        except Exception:
            pass

    # ============ Close app ============
    def close_app(self):
        if self.shutdown_active:
            self._show_warning_dialog(
                self._t('Таймер запущен'),
                self._t('Нельзя закрыть приложение, пока идёт отсчёт.') + "\n\n" +
                self._t('Сначала отмените таймер.'))
            return
        self._really_quit()

    def _really_quit(self):
        self._persist_settings()
        self.stop_flag = True
        try:
            if KEYBOARD_OK:
                keyboard.unhook_all()
        except Exception:
            pass
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            os._exit(0)
        except Exception:
            pass

    # ============ Tray icons ============
    def _load_font(self, size):
        for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf", "segoeui.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _make_icon_image(self, active=False, text=""):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        color = self.T["green"] if active else self.T["red"]
        d.ellipse((2, 2, size - 2, size - 2), fill=color)
        if active and text:
            n = len(text)
            font_size = 28 if n <= 2 else (24 if n == 3 else (20 if n == 4 else 17))
            font = self._load_font(font_size)
            try:
                bbox = d.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = (size - tw) / 2 - bbox[0]
                ty = (size - th) / 2 - bbox[1]
                d.text((tx, ty), text, font=font, fill="white")
            except Exception:
                d.ellipse((24, 24, 40, 40), fill="white")
        else:
            d.arc((16, 16, 48, 48), start=300, end=240, fill="white", width=5)
            d.line((32, 12, 32, 32), fill="white", width=5)
        return img

    def _tray_time_text(self, seconds):
        if seconds >= 86400:
            return f"{seconds // 86400}{self._t('д')}"
        if seconds >= 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h}:{m:02d}"
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _format_full(self, seconds):
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if d > 0:
            return f"{d}{self._t('д')} {h:02d}:{m:02d}:{s:02d}"
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _update_tray_icon(self, active, text="", tooltip=None):
        if not self.tray_icon:
            return
        try:
            self.tray_icon.icon = self._make_icon_image(active, text)
            if tooltip is not None:
                self.tray_icon.title = tooltip
        except Exception:
            pass

    def _update_progress(self, left):
        if not self._total_duration or self._total_duration <= 0:
            return
        try:
            self.mini_progress.update_idletasks()
            w = self.mini_progress.winfo_width()
            if w <= 1:
                return
            ratio = max(0.0, min(1.0, left / self._total_duration))
            self.mini_progress.coords(self._progress_rect, 0, 0, w * ratio, 3)
        except Exception:
            pass

    # ============ Autorun ============
    def _autostart_command(self):
        if getattr(sys, 'frozen', False):
            exe = sys.executable
            script = ""
        else:
            exe = sys.executable
            if exe.lower().endswith("python.exe"):
                alt = exe[:-10] + "pythonw.exe"
                if os.path.exists(alt):
                    exe = alt
            script = os.path.abspath(sys.argv[0])
        cmd = f'"{exe}"'
        if script:
            cmd += f' "{script}"'
        if self.settings.get("start_minimized", False):
            cmd += " --minimized"
        return cmd

    def _startup_dir(self):
        return os.path.join(os.environ.get("APPDATA", ""),
                            "Microsoft", "Windows", "Start Menu",
                            "Programs", "Startup")

    def _startup_bat_path(self):
        return os.path.join(self._startup_dir(), "ShutdownTimer.bat")

    def _is_registry_autorun(self):
        if not WINREG_OK:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_KEY, 0, winreg.KEY_READ)
            try:
                val, _ = winreg.QueryValueEx(key, AUTORUN_NAME)
                return val == self._autostart_command()
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _set_registry_autorun(self, enable):
        if not WINREG_OK:
            return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                if enable:
                    winreg.SetValueEx(key, AUTORUN_NAME, 0, winreg.REG_SZ, self._autostart_command())
                else:
                    try:
                        winreg.DeleteValue(key, AUTORUN_NAME)
                    except FileNotFoundError:
                        pass
                return True
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _is_startup_autorun(self):
        return os.path.exists(self._startup_bat_path())

    def _set_startup_autorun(self, enable):
        try:
            path = self._startup_bat_path()
            if enable:
                cmd = self._autostart_command()
                with open(path, "w", encoding="utf-8") as f:
                    f.write("@echo off\r\n")
                    f.write(f'start "" {cmd}\r\n')
            else:
                if os.path.exists(path):
                    os.remove(path)
            return True
        except Exception:
            return False

    def _current_autorun_method(self):
        if self._is_registry_autorun():
            return "registry"
        if self._is_startup_autorun():
            return "startup"
        return "none"

    def _set_autorun_method(self, method):
        current = self._current_autorun_method()
        if current == method:
            self.settings["autorun_method"] = method
            save_settings(self.settings)
            return method
        self._set_registry_autorun(False)
        self._set_startup_autorun(False)
        if method == "registry":
            if not self._set_registry_autorun(True):
                if self._set_startup_autorun(True):
                    method = "startup"
                else:
                    method = "none"
        elif method == "startup":
            if not self._set_startup_autorun(True):
                method = "none"
        self.settings["autorun_method"] = method
        save_settings(self.settings)
        return method

    def _tray_set_registry(self, icon=None, item=None):
        self.root.after(0, lambda: self._set_autorun_method("registry"))

    def _tray_set_startup(self, icon=None, item=None):
        self.root.after(0, lambda: self._set_autorun_method("startup"))

    def _tray_disable_autorun(self, icon=None, item=None):
        self.root.after(0, lambda: self._set_autorun_method("none"))

    def _toggle_start_minimized(self, icon=None, item=None):
        self.settings["start_minimized"] = not self.settings.get("start_minimized", False)
        save_settings(self.settings)
        cur = self._current_autorun_method()
        if cur != "none":
            self.root.after(0, lambda c=cur: self._set_autorun_method(c))

    def _check_existing_shutdown(self):
        def _check():
            try:
                res = subprocess.run(["shutdown", "/a"], capture_output=True, text=True, timeout=5)
                found = (res.returncode == 0)
            except Exception:
                found = False
            if found:
                self.root.after(0, lambda: self._show_warning_dialog(
                    self._t('Обнаружено запланированное выключение'),
                    self._t('В системе было активно запланированное выключение Windows.') + "\n\n" +
                    self._t('Приложение его отменило, чтобы не конфликтовало.')))
        threading.Thread(target=_check, daemon=True).start()

    # ============ Tray setup ============
    def _build_tray_menu(self):
        autorun_menu = pystray.Menu(
            pystray.MenuItem(
                self._t('Через реестр'), self._tray_set_registry,
                checked=lambda item: self._current_autorun_method() == "registry"),
            pystray.MenuItem(
                self._t('Через папку Startup'), self._tray_set_startup,
                checked=lambda item: self._current_autorun_method() == "startup"),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                self._t('Отключить автозагрузку'), self._tray_disable_autorun,
                enabled=lambda item: self._current_autorun_method() != "none"),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                self._t('Запускать свёрнутым в трей'), self._toggle_start_minimized,
                checked=lambda item: self.settings.get("start_minimized", False)),
        )
        return pystray.Menu(
            pystray.MenuItem(self._t('Открыть окно'), self._tray_open, default=True),
            pystray.MenuItem(self._t('Показать виджет'), self._tray_show_mini,
                             enabled=lambda item: self.shutdown_active),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._t('🎮 Игровой режим'), self._toggle_game_mode,
                             checked=lambda item: self._game_mode),
            pystray.MenuItem(self._t('Автозапуск с Windows'), autorun_menu),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._t('Выход'), self._tray_quit),
        )

    def _rebuild_tray_menu(self):
        if not TRAY_AVAILABLE or not self.tray_icon:
            return
        try:
            self.tray_icon.menu = self._build_tray_menu()
            self.tray_icon.title = self._t('Таймер выключения ПК — не запущен')
            self.tray_icon.update_menu()
        except Exception:
            pass

    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return

        def _run_tray():
            try:
                menu = self._build_tray_menu()
                tray_img = self._make_icon_image(active=False)
                icon = pystray.Icon("shutdown_timer", tray_img,
                                    self._t('Таймер выключения ПК — не запущен'), menu)
                self.tray_icon = icon
                icon.run()
            except Exception:
                pass

        threading.Thread(target=_run_tray, daemon=True, name="tray").start()

    def _tray_open(self, icon=None, item=None):
        self.root.after(0, self._restore_main)

    def _tray_show_mini(self, icon=None, item=None):
        self.root.after(0, self._restore_mini)

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self._really_quit)

    def _restore_main(self):
        if self.mini.winfo_exists():
            self.mini.withdraw()
        self.root.deiconify()
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass
        self.root.lift()
        self.root.focus_force()
        try:
            self.root.attributes("-topmost", True)
            self.root.after(300, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def _restore_mini(self):
        if self.shutdown_active:
            self.root.withdraw()
            self._show_mini()

    def hide_to_tray(self):
        if self.shutdown_active:
            self.root.withdraw()
            self._show_mini()
            return
        if TRAY_AVAILABLE and self.tray_icon is not None:
            self.root.withdraw()
            try:
                self.tray_icon.notify(
                    self._t('Приложение свёрнуто в трей.'),
                    self._t('Таймер выключения ПК'))
            except Exception:
                pass
        else:
            self.root.iconify()

    # ============ Timer ============
    def _current_action(self):
        return self.action_var.get()

    def start_timer(self):
        if self.shutdown_active:
            return
        total = self._compute_total_seconds()
        if total <= 0:
            messagebox.showwarning(self._t('Таймер'),
                                   self._t('Установите время больше нуля.'))
            return
        action = self._current_action()
        meta = ACTIONS[action]
        if action == "hibernate" and not self._hibernation_available():
            self._show_warning_dialog(
                self._t('Гибернация выключена'),
                self._t('На этом компьютере гибернация отключена.') + "\n\n" +
                self._t('Включите её в параметрах электропитания Windows или выберите «Сон».'))
            return
        if meta["switch"] is not None:
            try:
                res = subprocess.run(["shutdown", meta["switch"], "/t", str(total)],
                                     capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(res.stderr.strip() or res.stdout.strip() or "shutdown failed")
            except Exception as e:
                messagebox.showerror(self._t('Ошибка'),
                                     self._t('Не удалось запустить:') + f"\n{e}")
                return
        self._persist_settings()
        self.shutdown_active = True
        self.paused = False
        self.paused_remaining = 0
        self.stop_flag = False
        self.end_time = time.time() + total
        self._total_duration = total
        self._beeped = set()
        self._status_key = 'Запущено'
        self._hint_key = 'Действие:'
        T = self.T
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text=self._t('⏸  Пауза'))
        self.cancel_btn.config(state="normal")
        self._set_presets_enabled(False)
        self.status.config(text=self._t('Запущено'), fg=T["green"])
        action_text = self._t(self._action_buttons_text_keys[action])
        action_clean = action_text.split("  ", 1)[-1].strip()
        self.hint.config(text=self._t('Действие:') + " " + action_clean)
        self.mini.configure(bg=T["green"])
        self.mini_time.config(text=self._format_full(total), fg=T["green"])
        self.mini_icon.config(fg=T["green"])
        self.mini_progress.itemconfig(self._progress_rect, fill=T["green"])
        self._last_tray_text = None
        self._update_tray_icon(True, self._tray_time_text(total),
                               self._t('Осталось') + " " + self._format_full(total))
        self.root.withdraw()
        self._show_mini()
        threading.Thread(target=self._countdown_loop, daemon=True).start()

    def toggle_pause(self):
        if not self.shutdown_active:
            return
        if self.paused:
            self._resume()
        else:
            self._pause()

    def _pause(self):
        self.paused_remaining = max(0, int(round(self.end_time - time.time())))
        action = self._current_action()
        meta = ACTIONS[action]
        if meta["switch"] is not None:
            try:
                subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
            except Exception:
                pass
        self.paused = True
        self._status_key = 'Пауза'
        T = self.T
        self.pause_btn.config(text=self._t('▶  Продолжить'))
        self.status.config(text=self._t('Пауза'), fg=T["orange"])
        self.mini_time.config(text=self._format_full(self.paused_remaining))
        self.mini_icon.config(fg=T["orange"])
        self.mini_time.config(fg=T["orange"])
        self.mini.configure(bg=T["orange"])
        self.mini_progress.itemconfig(self._progress_rect, fill=T["orange"])

    def _resume(self):
        total = self.paused_remaining
        if total <= 0:
            total = 1
        action = self._current_action()
        meta = ACTIONS[action]
        if meta["switch"] is not None:
            try:
                subprocess.run(["shutdown", meta["switch"], "/t", str(total)],
                               capture_output=True, text=True)
            except Exception:
                pass
        self.end_time = time.time() + total
        self.paused = False
        self._status_key = 'Запущено'
        T = self.T
        self.pause_btn.config(text=self._t('⏸  Пауза'))
        self.status.config(text=self._t('Запущено'), fg=T["green"])
        self.mini_icon.config(fg=T["green"])
        self.mini_time.config(fg=T["green"])
        self.mini.configure(bg=T["green"])
        self.mini_progress.itemconfig(self._progress_rect, fill=T["green"])

    def _safe_set_status(self, text):
        if self.shutdown_active and not self.paused:
            self.status.config(text=text, fg=self.T["green"])

    def _safe_set_mini(self, text, left, color):
        if not self.shutdown_active or self.paused:
            return
        self.mini_time.config(text=text, fg=color)
        self.mini_icon.config(fg=color)
        self.mini.configure(bg=color)
        self.mini_progress.itemconfig(self._progress_rect, fill=color)
        self._fit_mini()
        self._update_progress(left)

    def _execute_final_action(self):
        action = self._current_action()
        try:
            if action == "sleep":
                ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
            elif action == "hibernate":
                ctypes.windll.powrprof.SetSuspendState(1, 1, 0)
        except Exception:
            pass

    def _countdown_loop(self):
        while not self.stop_flag:
            if self.paused:
                time.sleep(0.15)
                continue
            left = int(round(self.end_time - time.time()))
            if left <= 0:
                self._execute_final_action()
                break
            self._maybe_beep(left)
            d = left // 86400
            h = (left % 86400) // 3600
            m = (left % 3600) // 60
            s = left % 60
            if d > 0:
                long_text = (self._t('Осталось:') + " " +
                             f"{d}{self._t('д')} {h:02d}:{m:02d}:{s:02d}")
                short_text = f"{d}{self._t('д')} {h:02d}:{m:02d}:{s:02d}"
            else:
                long_text = self._t('Осталось:') + f" {h:02d}:{m:02d}:{s:02d}"
                short_text = f"{h:02d}:{m:02d}:{s:02d}"
            normal, bright, freq = self._get_pulse_style(left)
            if freq > 0:
                phase = int(time.time() * freq) % 2 == 0
                color = bright if phase else normal
            else:
                color = normal
            self.root.after(0, lambda t=long_text: self._safe_set_status(t))
            self.root.after(0, lambda t=short_text, l=left, c=color:
                            self._safe_set_mini(t, l, c))
            tray_text = self._tray_time_text(left)
            if tray_text != self._last_tray_text:
                self._last_tray_text = tray_text
                self._update_tray_icon(True, tray_text,
                                       self._t('Осталось') + " " + short_text)
            time.sleep(0.25)

    def cancel_timer(self):
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
        except Exception:
            pass
        self.stop_flag = True
        self.shutdown_active = False
        self.paused = False
        self.paused_remaining = 0
        self._total_duration = 0
        self._status_key = 'Таймер отменён'
        self._hint_key = None
        T = self.T
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text=self._t('⏸  Пауза'))
        self.cancel_btn.config(state="disabled")
        self._set_presets_enabled(True)
        self.status.config(text=self._t('Таймер отменён'), fg=T["orange"])
        self.hint.config(text="")
        self.mini.configure(bg=T["green"])
        self.mini_time.config(fg=T["green"])
        self.mini_icon.config(fg=T["green"])
        self.mini_progress.itemconfig(self._progress_rect, fill=T["green"])
        self._last_tray_text = None
        self._update_tray_icon(False, "",
                               self._t('Таймер выключения ПК — не запущен'))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not acquire_single_instance():
        signal_existing_instance()
        time.sleep(0.15)
        sys.exit(0)

    App().run()