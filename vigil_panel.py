"""
VIGIL Yetkili Panel v2.2
Gereksinimler:  pip install customtkinter pillow
"""
import sys
import traceback
from pathlib import Path as _P

_LOG = _P.home() / "DiscordYetkiliTakip" / "hata.log"


def _log_crash(title=""):
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {title} ===\n{traceback.format_exc()}\n")
    except Exception:
        pass


import csv
import hmac
import hashlib
import math
import os
import random
import re
import json
import secrets
import shutil
import sqlite3
import struct
import subprocess
import threading
import time
import wave
import ast
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, Canvas, ttk

try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw
except ImportError as _e:
    if sys.stdin is not None and sys.stdout is not None:
        print("EKSİK PAKET:", _e)
        print("Çözüm:  pip install customtkinter pillow")
        input("Kapatmak için Enter'a bas...")
    else:
        try:
            from tkinter import messagebox
            messagebox.showerror("VIGIL - Eksik paket", f"{_e}\n\nÇözüm: pip install customtkinter pillow")
        except Exception:
            pass
    sys.exit(1)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

CURRENT_VERSION = "2.4.0"
FMT = "%Y-%m-%d %H:%M:%S"

APP_DIR = Path.home() / "DiscordYetkiliTakip"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = APP_DIR / "aktivite.sqlite3"
REPORT_DIR = APP_DIR / "raporlar"
REPORT_DIR.mkdir(exist_ok=True)
AVATAR_DIR = APP_DIR / "avatars"
AVATAR_DIR.mkdir(exist_ok=True)
SOUND_DIR = APP_DIR / "sounds"
SOUND_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = APP_DIR / "ayarlar.json"
POWERED_BY = "powered by vezo"

# ---------------------------------------------------------------------------
# PREMIUM KEY GİZLİ ANAHTARI
# Key'ler bu anahtarla imzalanır; bu sayede key'i bir bilgisayarda üretip
# başka bir bilgisayardaki uygulamada da doğrulayabilirsin.
# DAĞITMADAN ÖNCE KENDİNE ÖZEL bir değerle değiştir (ya da KEY_SECRET ortam değişkeni kullan).
# Not: Gerçek lisans koruması için sunucu gerekir; bu yöntem çevrimdışı çalışır.
# ---------------------------------------------------------------------------
def _load_key_secret():
    env = os.environ.get("REAL_KEY_SECRET")
    if env:
        return env.encode()
    try:
        s = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("key_secret")
        if s:
            return str(s).encode()
    except Exception:
        pass
    return b"REAL-degistir-beni-2026"   # eski key'ler geçerli kalsın diye varsayılan korunur


KEY_SECRET = _load_key_secret()


def set_key_secret(new_secret, settings_data=None):
    """İmza anahtarını çalışma anında değiştirir ve ayarlar.json'a kalıcı olarak yazar.
    Not: değiştirildiğinde, bu anahtarla üretilmiş ama henüz kullanılmamış eski key'ler
    artık doğrulanamaz (imzaları tutmaz)."""
    global KEY_SECRET
    KEY_SECRET = new_secret.encode()
    data = settings_data if settings_data is not None else load_settings()
    data["key_secret"] = new_secret
    save_settings(data)
    return KEY_SECRET


KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # 32 karakter, karışan harfler yok
KEY_DURATIONS = {"A": 7, "B": 30, "C": 90, "D": 365}   # key'in ilk harfi süreyi belirler
DEFAULT_ADMIN_PASSWORD = "rwexn123"
# Her şeye erişimi olan (kurucu) hesaplar ve ilk açılıştaki varsayılan şifreleri.
# Varsayılan şifreyle girilirse uygulama uyarır; Profil'den değiştir.
SUPER_USERS = {"rwexn": DEFAULT_ADMIN_PASSWORD, "vezo": "vezo123"}
PBKDF2_ITERS = 200_000

EVENT_TYPES = [
    "Mesaj gözlemi", "Ses kanalına giriş", "Ses kanalından çıkış",
    "Ses kanalı değiştirme", "AFK kanalına giriş", "AFK kanalından çıkış",
    "Sunucuya katılma (manuel gözlem)", "Sunucudan ayrılma (manuel gözlem)", "Diğer not",
]
DAY_NAMES = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

C = dict(
    bg="#05060a", panel="#0b0d14", panel2="#10131c", hover="#181c29", border="#1c2130",
    text="#e8eaf2", muted="#7b8296", accent="#6c7bff", accent_h="#8a96ff",
    ok="#3ecf8e", warn="#f5b73d", bad="#ef5b5b", gold="#d4a017",
)

PALETTE = [C["accent"], C["ok"], C["warn"], C["bad"], "#c77dff", "#4dd0e1", "#ff8fab", "#9aa3b8"]
EVENT_COLORS = {
    "Mesaj gözlemi": C["accent_h"], "Ses kanalına giriş": C["ok"], "Ses kanalından çıkış": C["bad"],
    "Ses kanalı değiştirme": C["warn"], "AFK kanalına giriş": "#ff9f6b", "AFK kanalından çıkış": "#c98a5a",
    "Sunucuya katılma (manuel gözlem)": "#4dd0e1", "Sunucudan ayrılma (manuel gözlem)": "#ff8fab",
    "Diğer not": C["muted"],
}
DEMO_NAMES = ["Arda", "Elif", "Mert", "Zeynep", "Kaan", "Selin", "Burak", "Defne", "Emre", "Ceren", "Yiğit", "Melis"]


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rel_time(text):
    try:
        sec = (datetime.now() - datetime.strptime(text, FMT)).total_seconds()
    except ValueError:
        return text
    if sec < 60:
        return "az önce"
    if sec < 3600:
        return f"{int(sec // 60)} dk önce"
    if sec < 86400:
        return f"{int(sec // 3600)} sa önce"
    return f"{int(sec // 86400)} gün önce"




# ============================== MARKA / LOGO ==============================
BRAND = "VIGIL"
_HEXP = lambda r: [(50 + r * math.cos(math.radians(a)), 50 + r * math.sin(math.radians(a)))
                   for a in (-90, -30, 30, 90, 150, 210)]
_HEX_OUT, _HEX_IN = _HEXP(47), _HEXP(42.6)
_LEFT = [(24, 28), (39, 28), (50, 60), (50, 79)]
_RIGHT = [(76, 28), (61, 28), (50, 60), (50, 79)]


def _hex2rgba(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def render_logo(size=256, fg="#ffffff", accent="#8a96ff", bg=None, ss=3):
    """VIGIL sembolünü (altıgen + V + çizgili yüzey) PIL ile çizer; dosya gerekmez."""
    from PIL import ImageChops
    px = size * ss
    s = px / 100
    fg_c, ac_c = _hex2rgba(fg), _hex2rgba(accent)
    img = Image.new("RGBA", (px, px), bg or (0, 0, 0, 0))
    P = lambda pts: [(x * s, y * s) for x, y in pts]
    ring = Image.new("L", (px, px), 0)
    rd = ImageDraw.Draw(ring)
    rd.polygon(P(_HEX_OUT), fill=255)
    rd.polygon(P(_HEX_IN), fill=0)
    layer = Image.new("RGBA", (px, px), fg_c)
    layer.putalpha(ring)
    img.alpha_composite(layer)
    ImageDraw.Draw(img).polygon(P(_LEFT), fill=fg_c)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).polygon(P(_RIGHT), fill=255)
    st = Image.new("L", (px, px), 0)
    sd = ImageDraw.Draw(st)
    for i in range(10):
        y = 28 + i * 5.6
        sd.rectangle((48 * s, y * s, 78 * s, (y + 2.8) * s), fill=255)
    layer = Image.new("RGBA", (px, px), fg_c)
    layer.putalpha(ImageChops.multiply(mask, st))
    img.alpha_composite(layer)
    cx, cy, r = 50 * s, 35 * s, 4.4 * s
    ImageDraw.Draw(img).ellipse((cx - r, cy - r, cx + r, cy + r), fill=ac_c)
    resample = getattr(Image, "Resampling", Image).LANCZOS
    return img.resize((size, size), resample)


_LOGO_CACHE = {}


def logo_image(px, fg="#ffffff", accent="#8a96ff"):
    key = (px, fg, accent)
    if key not in _LOGO_CACHE:
        img = render_logo(px * 2, fg, accent)
        _LOGO_CACHE[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(px, px))
    return _LOGO_CACHE[key]


# ============================== YARDIMCILAR ==============================
def now_text():
    return datetime.now().strftime(FMT)


def parse_dt(s):
    return datetime.strptime(s, FMT)


def hash_password(password, salt=None, algo="pbkdf2"):
    if salt is None:
        salt = secrets.token_hex(16)
    if algo == "pbkdf2":
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERS).hex()
    else:  # eski sürümden kalan hesaplar
        h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt


def verify_password(password, stored_hash, salt, algo="sha256"):
    h, _ = hash_password(password, salt, algo)
    return hmac.compare_digest(h, stored_hash)


def _key_sig(payload):
    d = hmac.new(KEY_SECRET, payload.encode(), hashlib.sha256).digest()
    return "".join(KEY_ALPHABET[b % 32] for b in d[:8])


def format_key(raw):
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def normalize_key(s):
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def generate_key(days=30):
    code = next(k for k, v in KEY_DURATIONS.items() if v == days)
    payload = code + "".join(secrets.choice(KEY_ALPHABET) for _ in range(7))
    return format_key(payload + _key_sig(payload))


def validate_key(text):
    """İmzası geçerliyse (gün, biçimli_key) döndürür, değilse None."""
    raw = normalize_key(text)
    if len(raw) != 16 or raw[0] not in KEY_DURATIONS:
        return None
    if not hmac.compare_digest(_key_sig(raw[:8]), raw[8:]):
        return None
    return KEY_DURATIONS[raw[0]], format_key(raw)


def fmt_dur(sec):
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m = r // 60
    return f"{h}s {m}dk" if h else f"{m}dk"


def voice_seconds(rows):
    """rows: tarihe göre ARTAN sıralı. Kullanıcı başına tahmini ses süresi."""
    opened, total = {}, {}
    for r in rows:
        try:
            t = datetime.strptime(r["happened_at"], FMT)
        except ValueError:
            continue
        uid, et = r["user_id"], r["event_type"]
        if et == "Ses kanalına giriş":
            opened[uid] = t
        elif et == "Ses kanalından çıkış" and uid in opened:
            d = (t - opened.pop(uid)).total_seconds()
            if 0 < d < 86400:
                total[uid] = total.get(uid, 0) + d
    return total


def build_report_text(title, rows, note=""):
    lines = [title, "=" * 60]
    if note:
        lines.append(note)
    names = {r["user_id"]: (r["display_name"] or r["user_id"]) for r in rows}
    lines.append(f"Toplam kayıt: {len(rows)}   Yetkili sayısı: {len(names)}")
    by_type, by_user = {}, {}
    for r in rows:
        by_type[r["event_type"]] = by_type.get(r["event_type"], 0) + 1
        by_user[r["user_id"]] = by_user.get(r["user_id"], 0) + 1
    voice = voice_seconds(rows)
    lines += ["", "OLAY DAĞILIMI", "-" * 60]
    for et, n in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"  {et:<40} {n:>5}")
    lines += ["", "YETKİLİ ÖZETİ", "-" * 60]
    for uid, n in sorted(by_user.items(), key=lambda x: -x[1]):
        v = f"   ses ≈ {fmt_dur(voice[uid])}" if uid in voice else ""
        lines.append(f"  {names[uid]} ({uid}) — {n} kayıt{v}")
    lines += ["", "ZAMAN ÇİZELGESİ", "-" * 60]
    for r in rows:
        ch = f" | {r['channel']}" if r["channel"] else ""
        lines.append(f"  {r['happened_at']} | {names[r['user_id']]} | {r['event_type']}{ch}")
    return "\n".join(lines)


def make_avatar_image(path, size):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    m = min(w, h)
    left, top = (w - m) // 2, (h - m) // 2
    img = img.crop((left, top, left + m, top + m))
    resample = getattr(Image, "Resampling", Image).LANCZOS
    img = img.resize((size * 2, size * 2), resample)
    mask = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 2 - 1, size * 2 - 1), fill=255)
    img.putalpha(mask)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ============================== OTOMATİK GÜNCELLEME ==============================
# version.json (sunucuda) örneği:
#   {"version": "2.4.0", "notes": "Neler yeni", "mandatory": false,
#    "py":  {"url": "https://.../real_panel.py",  "sha256": "..."},
#    "exe": {"url": "https://.../VIGIL_Panel.exe", "sha256": "..."}}
# Bunu publish_update.py otomatik üretir. Aşağıdaki adresi kendi barındırmana göre değiştir
# (ya da ayarlar.json içine "update_url" yaz / VIGIL_UPDATE_URL ortam değişkeni kullan).
UPDATE_URL = os.environ.get("VIGIL_UPDATE_URL", "https://raw.githubusercontent.com/KULLANICI/vigil-panel/main/version.json")
UPDATE_DIR = APP_DIR / "updates"
UPDATE_DIR.mkdir(exist_ok=True)
PENDING_FILE = UPDATE_DIR / "pending.json"
MAX_SCRIPT_BYTES = 8 * 1024 * 1024
MAX_EXE_BYTES = 300 * 1024 * 1024
SCRIPT_PATH = Path(__file__).resolve() if "__file__" in globals() else None


def parse_version(v):
    """'1.22' -> (1,22,0)   '2.01' -> (2,1,0)   'v2.0.1' -> (2,0,1)"""
    text = str(v).strip().lstrip("vV")
    if not re.fullmatch(r"\d+(\.\d+){0,3}", text):
        raise ValueError(f"geçersiz sürüm: {v!r}")
    nums = [int(x) for x in text.split(".")]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def _safe_url(u):
    p = urllib.parse.urlparse(str(u))
    return p.scheme == "https" or (p.scheme == "http" and p.hostname in ("127.0.0.1", "localhost"))


class Updater:
    """Arayüzden bağımsız: sürüm denetler, indirir, SHA-256 doğrular, kurar, gerekirse geri alır."""

    def __init__(self, manifest_url, current=None, script_path=None, exe_path=None, frozen=None):
        self.url = manifest_url
        self.current = current or CURRENT_VERSION
        self.script_path = Path(script_path) if script_path else SCRIPT_PATH
        self.exe_path = Path(exe_path) if exe_path else Path(sys.executable)
        self.frozen = getattr(sys, "frozen", False) if frozen is None else frozen

    # ---- ağ
    def _open(self, url, timeout=12):
        if not _safe_url(url):
            raise ValueError("Güvensiz adres (https gerekli)")
        req = urllib.request.Request(url, headers={"User-Agent": f"VIGIL/{self.current}",
                                                   "Cache-Control": "no-cache"})
        return urllib.request.urlopen(req, timeout=timeout)

    def _download(self, url, dest, limit, progress=None, cancel=None):
        digest = hashlib.sha256()
        done = 0
        with self._open(url, timeout=20) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            if total and total > limit:
                raise ValueError("Güncelleme dosyası beklenenden büyük")
            while True:
                if cancel and cancel():
                    raise RuntimeError("iptal edildi")
                chunk = r.read(64 * 1024)
                if not chunk:
                    break
                done += len(chunk)
                if done > limit:
                    raise ValueError("Güncelleme dosyası beklenenden büyük")
                digest.update(chunk)
                f.write(chunk)
                if progress:
                    progress(done, total)
        return digest.hexdigest()

    # ---- sürüm denetimi
    def check(self, skip_version=None):
        """Yeni sürüm varsa bilgi sözlüğü, yoksa None döndürür."""
        sep = "&" if "?" in self.url else "?"
        with self._open(f"{self.url}{sep}t={int(time.time())}") as r:
            raw = r.read(65536)
        data = json.loads(raw.decode("utf-8"))
        ver = str(data.get("version", "")).strip()
        newest = parse_version(ver)
        cur = parse_version(self.current)
        info = {
            "version": ver,
            "notes": str(data.get("notes", ""))[:900],
            "mandatory": bool(data.get("mandatory", False)),
            "current": self.current,
        }
        min_v = data.get("min_version")
        if min_v and cur < parse_version(min_v):
            info["mandatory"] = True
        if newest <= cur:
            return None
        if skip_version and ver == skip_version and not info["mandatory"]:
            return None        # bu sürüm geçen sefer sorun çıkarıp geri alındı
        kind = "exe" if self.frozen else "py"
        part = data.get(kind)
        if not isinstance(part, dict) or not part.get("url") or not re.fullmatch(r"[0-9a-fA-F]{64}", str(part.get("sha256", ""))):
            raise ValueError(f"Bu sürüm için {kind} paketi/sha256 bilgisi yok")
        if not _safe_url(part["url"]):
            raise ValueError("Güvensiz indirme adresi")
        info.update(kind=kind, url=part["url"], sha256=part["sha256"].lower())
        return info

    # ---- indirme + doğrulama
    def download(self, info, progress=None, cancel=None):
        dest = UPDATE_DIR / f"download_{info['version']}.{info['kind']}"
        limit = MAX_EXE_BYTES if info["kind"] == "exe" else MAX_SCRIPT_BYTES
        try:
            got = self._download(info["url"], dest, limit, progress, cancel)
            if got != info["sha256"]:
                raise ValueError("Doğrulama başarısız (SHA-256 uyuşmuyor); dosya bozuk veya değiştirilmiş")
            if info["kind"] == "py":
                text = dest.read_text(encoding="utf-8")
                ast.parse(text)                                   # sözdizimi bozuk dosya kurulmaz
                m = re.search(r'^CURRENT_VERSION\s*=\s*"([^"]+)"', text, re.M)
                if not m or parse_version(m.group(1)) != parse_version(info["version"]):
                    raise ValueError("Dosyanın içindeki sürüm, bildirilen sürümle uyuşmuyor")
            return dest
        except Exception:
            try:
                dest.unlink()
            except OSError:
                pass
            raise

    # ---- kurulum
    @staticmethod
    def _write_pending(data):
        PENDING_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def install(self, new_file, info):
        if info["kind"] == "exe":
            return self._install_exe(new_file, info)
        return self._install_script(new_file, info)

    def _install_script(self, new_file, info):
        target = self.script_path
        if target is None or not target.exists():
            raise RuntimeError("Çalışan dosya bulunamadı")
        backup = target.with_name(f"{target.name}.bak-{self.current}")
        shutil.copy2(target, backup)
        tmp = target.with_name(target.name + ".new")
        shutil.copyfile(new_file, tmp)
        last = None
        for _ in range(4):                    # OneDrive/antivirüs anlık kilitleyebilir
            try:
                os.replace(tmp, target)
                last = None
                break
            except OSError as e:
                last = e
                time.sleep(0.4)
        if last:
            raise last
        self._write_pending({"mode": "script", "target": str(target), "backup": str(backup),
                             "from": self.current, "to": info["version"], "ok": False, "rolled": False})
        try:
            new_file.unlink()
        except OSError:
            pass
        return target

    def _install_exe(self, new_file, info):
        cur = self.exe_path
        old = cur.with_name(cur.name + ".old")
        if old.exists():
            try:
                old.unlink()
            except OSError:
                pass
        os.replace(cur, old)                  # çalışan exe yeniden adlandırılabilir
        try:
            shutil.copyfile(new_file, cur)
        except Exception:
            os.replace(old, cur)              # kopyalanamadıysa eskisini geri koy
            raise
        self._write_pending({"mode": "exe", "target": str(cur), "backup": str(old),
                             "from": self.current, "to": info["version"], "ok": False, "rolled": False})
        try:
            new_file.unlink()
        except OSError:
            pass
        return cur

    # ---- yeniden başlatma
    def relaunch(self, target):
        env = dict(os.environ)
        args = [a for a in sys.argv[1:] if a != "--console"]
        flags = 0
        if os.name == "nt":
            flags = 0x00000008 | 0x00000200           # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        if self.frozen:
            env.pop("_MEIPASS2", None)
            env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"  # onefile alt süreç eski geçici klasörü paylaşmasın
            cmd = [str(target), *args]
        else:
            exe = sys.executable
            if os.name == "nt":
                pyw = Path(exe).with_name("pythonw.exe")
                if pyw.exists():
                    exe = str(pyw)               # konsolsuz başlat
            cmd = [exe, str(target), *args]
        subprocess.Popen(cmd, env=env, close_fds=True, creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---- başlangıç temizliği / geri alma
    @staticmethod
    def cleanup_old():
        """Eski .old exe ve yedeklerden son sürüm dışındakileri temizler."""
        try:
            cur = Path(sys.executable)
            old = cur.with_name(cur.name + ".old")
            if getattr(sys, "frozen", False) and old.exists():
                old.unlink()
        except Exception:
            pass
        try:
            if SCRIPT_PATH is not None:
                baks = sorted(SCRIPT_PATH.parent.glob(SCRIPT_PATH.name + ".bak-*"), key=lambda p: p.stat().st_mtime)
                for p in baks[:-1]:
                    p.unlink()
        except Exception:
            pass

    @staticmethod
    def mark_ok():
        try:
            d = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
            if not d.get("ok"):
                d["ok"] = True
                PENDING_FILE.write_text(json.dumps(d), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def rollback_if_needed():
        """Güncelleme sonrası ilk açılışta çökme olduysa eski sürüme döner. True = geri alındı."""
        try:
            d = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        except Exception:
            return False
        if d.get("ok") or d.get("rolled"):
            return False
        try:
            target, backup = Path(d["target"]), Path(d["backup"])
            if not backup.exists():
                return False
            if d["mode"] == "exe":
                bad = target.with_name(target.name + ".bad")
                if bad.exists():
                    bad.unlink()
                os.replace(target, bad)
                os.replace(backup, target)
            else:
                shutil.copyfile(backup, target)
            d["rolled"] = True
            PENDING_FILE.write_text(json.dumps(d), encoding="utf-8")
            cfg = load_settings()
            cfg["skip_update"] = d.get("to", "")
            save_settings(cfg)
            return True
        except Exception:
            return False


# ============================== AYARLAR / SES / JARVIS ==============================
def load_settings():
    data = {"sfx": True, "jarvis": True}
    try:
        data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return data


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _synth(parts, rate=22050):
    """Doğal sesli efektler üretir (16-bit mono PCM listesi).
    parça biçimi: (tür, süre, ses, boşluk, ...)
      ("bell",   dur, vol, gap, frekans)        -> yumuşak çan / cam sesi
      ("tock",   dur, vol, gap, frekans)        -> ahşap 'tık' (tuş hissi)
      ("swoosh", dur, vol, gap, f_baş, f_son)   -> hava / kayma sesi"""
    rnd = random.Random(7)
    tau = 2 * math.pi
    out = []
    for p in parts:
        kind, dur, vol, gap = p[0], p[1], p[2], p[3]
        n = max(1, int(rate * dur))
        if kind == "bell":
            f = p[4]
            for i in range(n):
                t, x = i / rate, i / n
                env = min(1.0, i / (rate * 0.003)) * math.exp(-6.0 * x)
                smp = (math.sin(tau * f * t) + 0.35 * math.sin(tau * f * 2.76 * t) * math.exp(-4 * x)
                       + 0.12 * math.sin(tau * f * 5.4 * t) * math.exp(-8 * x))
                out.append(int(max(-1.0, min(1.0, smp * env * vol * 0.55)) * 32767))
        elif kind == "tock":
            f, phase, lp = p[4], 0.0, 0.0
            for i in range(n):
                x = i / n
                phase += tau * f * (1 - 0.45 * x) / rate
                lp += 0.35 * ((rnd.random() * 2 - 1) - lp)
                smp = math.sin(phase) * math.exp(-9 * x) + lp * 0.9 * math.exp(-16 * x)
                env = min(1.0, i / (rate * 0.0012))
                out.append(int(max(-1.0, min(1.0, smp * env * vol * 0.8)) * 32767))
        else:  # swoosh
            f0, f1, lp = p[4], p[5], 0.0
            for i in range(n):
                x = i / n
                fc = f0 + (f1 - f0) * x
                a = 1 - math.exp(-tau * fc / rate)
                lp += a * ((rnd.random() * 2 - 1) - lp)
                env = math.sin(math.pi * x) ** 2
                out.append(int(max(-1.0, min(1.0, lp * env * vol * 1.1)) * 32767))
        out.extend([0] * int(rate * gap))
    return out


class SoundFX:
    """Dosya gerektirmez: sesler ilk açılışta kendisi üretilir (WAV). Windows'ta winsound kullanır."""
    VERSION = "v2"
    DEFS = {
        "click": [("tock", 0.050, 0.55, 0, 900)],
        "tick": [("tock", 0.035, 0.35, 0, 1300)],
        "switch": [("swoosh", 0.170, 0.70, 0, 500, 3500)],
        "open": [("bell", 0.24, 0.45, 0, 988)],
        "success": [("bell", 0.18, 0.45, 0.02, 784), ("bell", 0.40, 0.45, 0, 1175)],
        "error": [("tock", 0.14, 0.85, 0.05, 180), ("tock", 0.20, 0.85, 0, 150)],
        "chime": [("bell", 0.25, 0.45, 0.02, 880), ("bell", 0.55, 0.42, 0, 1318)],
        "startup": [("swoosh", 0.35, 0.50, 0.02, 200, 2500), ("bell", 0.30, 0.40, 0, 523),
                    ("bell", 0.30, 0.40, 0, 784), ("bell", 0.75, 0.45, 0, 1047)],
        "login": [("bell", 0.16, 0.45, 0, 523), ("bell", 0.16, 0.45, 0, 659),
                  ("bell", 0.16, 0.45, 0, 784), ("bell", 0.55, 0.45, 0, 1047)],
        "logout": [("bell", 0.16, 0.45, 0, 784), ("bell", 0.16, 0.45, 0, 659), ("bell", 0.55, 0.45, 0, 523)],
    }

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.busy_until = 0.0
        self.files, self.length = {}, {}
        self._win, self._player = None, None
        try:
            import winsound
            self._win = winsound
        except Exception:
            for cmd in (["afplay"], ["paplay"], ["aplay", "-q"]):
                if shutil.which(cmd[0]):
                    self._player = cmd
                    break
        for name, parts in self.DEFS.items():
            self.length[name] = sum(p[1] + p[3] for p in parts)
            path = SOUND_DIR / f"{name}_{self.VERSION}.wav"
            try:
                if not path.exists():
                    pcm = _synth(parts)
                    with wave.open(str(path), "wb") as w:
                        w.setnchannels(1)
                        w.setsampwidth(2)
                        w.setframerate(22050)
                        w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
                self.files[name] = str(path)
            except Exception:
                continue

    def play(self, name):
        if not self.enabled or name not in self.files:
            return
        now = time.monotonic()
        soft = name in ("click", "tick")
        if soft and now < self.busy_until:      # daha önemli bir ses çalıyorsa tıklama sesini bastırma
            return
        self.busy_until = now + (0.06 if soft else self.length[name] + 0.02)
        try:
            if self._win:
                self._win.PlaySound(self.files[name], self._win.SND_FILENAME | self._win.SND_ASYNC)
            elif self._player:
                subprocess.Popen(self._player + [self.files[name]],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


TTS_DIR = SOUND_DIR / "tts"
TTS_DIR.mkdir(exist_ok=True)
EDGE_VOICE = "tr-TR-AhmetNeural"      # kadın sesi istersen: "tr-TR-EmelNeural"


class Jarvis:
    """İnsana en yakın ses: Microsoft nöral Türkçe ses (edge-tts, internet gerekir).
    Cümleler önbelleğe alınır; edge-tts çalışmazsa Türkçe sistem sesine düşer.
    (Türkçe sistem sesi yoksa bozuk/İngilizce telaffuz yerine sessiz kalır.)"""
    PS_SCRIPT = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$v = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'tr*' } "
        "| Select-Object -First 1; "
        "if (-not $v) { exit 3 }; "
        "$s.SelectVoice($v.VoiceInfo.Name); "
        "$s.Rate = -1; $s.Volume = 100; $s.Speak($env:VIGIL_SPEAK)"
    )
    RETRY_SECONDS = 3600      # edge-tts kurulumu başarısızsa en fazla saatte bir tekrar dene

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.proc = None
        self._token = 0
        self._alias = None
        self._lock = threading.Lock()        # aynı anda tek ses çalsın (MCI yarış durumunu önler)
        self.edge_ok = False
        self.engine = "-"                    # son konuşmada kullanılan motor
        self.last_error = ""
        threading.Thread(target=self._ensure_edge, daemon=True).start()

    # -------- edge-tts kurulumu (artık kalıcı olarak pes etmez)
    def _ensure_edge(self):
        try:
            import edge_tts  # noqa: F401
            self.edge_ok = True
            return
        except Exception:
            pass
        if getattr(sys, "frozen", False):
            self.last_error = "edge-tts exe içinde yok"
            return
        cfg = load_settings()
        if time.time() - float(cfg.get("edge_last_try", 0) or 0) < self.RETRY_SECONDS:
            self.last_error = "edge-tts kurulu değil (yakın zamanda denendi)"
            return
        cfg["edge_last_try"] = time.time()
        cfg.pop("edge_tried", None)          # eski sürümün kalıcı 'bir kez denedim' bayrağı
        save_settings(cfg)
        try:
            flags = 0x08000000 if os.name == "nt" else 0
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "-q", "-U", "edge-tts"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180, creationflags=flags)
            import importlib
            importlib.invalidate_caches()
            import edge_tts  # noqa: F401
            self.edge_ok = True
        except Exception as e:
            self.edge_ok = False
            self.last_error = f"edge-tts kurulamadı: {e}"

    # -------- durdurma
    def stop(self):
        self._token += 1
        alias = self._alias
        try:
            if os.name == "nt" and alias:
                import ctypes
                ctypes.windll.winmm.mciSendStringW(f"stop {alias}", None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f"close {alias}", None, 0, None)
        except Exception:
            pass
        try:
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass
        self.proc = None

    # -------- nöral ses (mp3)
    @staticmethod
    def _valid_mp3(path):
        try:
            if path.stat().st_size < 1500:
                return False
            with open(path, "rb") as f:
                head = f.read(3)
            return head == b"ID3" or head[:1] == b"\xff"
        except OSError:
            return False

    def _edge_file(self, text):
        import asyncio
        import edge_tts
        key = hashlib.sha1(f"{EDGE_VOICE}|{text}".encode("utf-8")).hexdigest()[:16]
        path = TTS_DIR / f"{key}.mp3"
        if path.exists():
            if self._valid_mp3(path):
                return path
            try:
                path.unlink()                # önceki yarım/bozuk indirme: sil, yeniden üret
            except OSError:
                pass
        tmp = TTS_DIR / f"{key}.{secrets.token_hex(3)}.part"

        async def run():
            await edge_tts.Communicate(text, EDGE_VOICE, rate="-4%", pitch="-2Hz").save(str(tmp))

        try:
            asyncio.run(asyncio.wait_for(run(), 15))
            if not self._valid_mp3(tmp):
                raise RuntimeError("boş/bozuk ses dosyası")
            os.replace(tmp, path)            # ancak tamamen inince asıl dosya olur
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
        return path

    @staticmethod
    def _short_path(path):
        """MCI Türkçe karakter/boşluklu yollarda takılabilir; 8.3 kısa yol daha güvenli."""
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 1024):
                return buf.value
        except Exception:
            pass
        return str(path)

    def _play_file(self, path, token):
        if os.name == "nt":
            import ctypes
            mci = ctypes.windll.winmm.mciSendStringW
            alias = f"vigil_tts{token}"
            self._alias = alias
            try:
                if mci(f'open "{self._short_path(path)}" type mpegvideo alias {alias}', None, 0, None) != 0:
                    raise RuntimeError("mp3 açılamadı")
                if token == self._token:
                    mci(f"play {alias} wait", None, 0, None)
            finally:
                mci(f"close {alias}", None, 0, None)   # yalnızca KENDİ takma adını kapatır
                if self._alias == alias:
                    self._alias = None
            return
        for cmd in (["afplay"], ["mpg123", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
                    ["mpv", "--no-video", "--really-quiet"]):
            if shutil.which(cmd[0]):
                self.proc = subprocess.Popen(cmd + [str(path)], stdin=subprocess.DEVNULL,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.proc.wait()
                return
        raise RuntimeError("mp3 oynatıcı yok")

    # -------- yedek: Türkçe sistem sesi
    def _speak_system(self, text):
        quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.name == "nt":
            env = dict(os.environ)
            env["VIGIL_SPEAK"] = text
            exe = shutil.which("powershell") or "powershell"
            self.proc = subprocess.Popen(
                [exe, "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", self.PS_SCRIPT],
                env=env, creationflags=0x08000000, **quiet)
            if self.proc.wait() == 3:
                self.last_error = "Türkçe Windows sesi yüklü değil (Ayarlar > Zaman ve dil > Konuşma)"
                self.engine = "sessiz"
                return False
            return True
        elif sys.platform == "darwin" and shutil.which("say"):
            self.proc = subprocess.Popen(["say", "-v", "Yelda", text], **quiet)
            return True
        for cmd in (["espeak-ng", "-v", "tr"], ["espeak", "-v", "tr"], ["spd-say", "-l", "tr"]):
            if shutil.which(cmd[0]):
                self.proc = subprocess.Popen(cmd + [text], **quiet)
                return True
        return False

    def _worker(self, text, token):
        with self._lock:                      # eski konuşma bitmeden yenisi başlamasın
            if token != self._token:
                return                        # bu arada başka cümle istendi
            try:
                if not self.edge_ok:          # paket kurulumu bitmediyse kısa bekle
                    for _ in range(20):
                        if self.edge_ok or token != self._token:
                            break
                        time.sleep(0.25)
                if self.edge_ok:
                    path = self._edge_file(text)
                    if token == self._token:
                        self.engine = "edge"
                        self.last_error = ""
                        try:
                            self._play_file(path, token)
                        except Exception:
                            try:
                                path.unlink()   # çalınamayan dosya bozuktur; bir dahaki sefere yeniden üretilsin
                            except OSError:
                                pass
                            raise
                    return
            except Exception as e:
                self.last_error = f"edge-tts: {type(e).__name__}: {e}"
                try:
                    _log_crash("Jarvis edge-tts hatası")
                except Exception:
                    pass
            if token == self._token:
                try:
                    self.engine = "sistem"
                    self._speak_system(text)
                except Exception as e:
                    self.engine = "sessiz"
                    self.last_error = f"sistem sesi: {e}"

    def speak(self, text, force=False):
        if not (self.enabled or force) or not text:
            return False
        self.stop()
        threading.Thread(target=self._worker, args=(text, self._token), daemon=True).start()
        return True

    def status(self):
        names = {"edge": "Microsoft nöral ses (edge-tts)", "sistem": "Windows yedek sesi",
                 "sessiz": "ses çıkmadı"}
        base = names.get(self.engine, "henüz konuşmadı")
        return base + (f"  •  {self.last_error}" if self.last_error else "")


class JarvisOrb(ctk.CTkFrame):
    """Jarvis konuşurken beliren, nabız gibi atan mavi dairesel yapay-zeka göstergesi.
    Sessizken gizlidir; konuşma başlayınca büyüyüp parlar, konuşma bitince küçülüp kaybolur."""
    GLOW = ["#0b2550", "#123e82", "#1c63c9", "#2f8bff", "#8fcbff"]
    CORE = "#f2f8ff"

    def __init__(self, parent, size=32):
        super().__init__(parent, fg_color="transparent", width=size, height=size)
        self.size = size
        self.canvas = Canvas(self, width=size, height=size, bg=C["bg"], highlightthickness=0)
        self.canvas.pack()
        self.pack_propagate(False)
        self._phase = 0.0
        self._job = None
        self._speaking = False
        self._visible = False

    def _paint(self, amp):
        # NOT: '_draw' adı CTkFrame'in kendi metoduyla çakışıyordu -> TypeError
        try:
            if not self.canvas.winfo_exists():
                return
        except Exception:
            return
        c = self.canvas
        c.delete("all")
        cx = cy = self.size / 2
        for i, color in enumerate(self.GLOW):
            r = (cx - 2) * (0.32 + 0.14 * i) * (1 + amp * 0.22)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        core_r = max(2.0, (cx - 9) * (1 + amp * 0.40))
        c.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r, fill=self.CORE, outline="")

    def _tick(self):
        if not self._speaking:
            self._job = None
            return
        self._phase += 0.32
        amp = 0.5 + 0.5 * math.sin(self._phase)
        self._paint(amp)
        try:
            self._job = self.after(55, self._tick)
        except Exception:
            self._job = None

    def show(self):
        if not self._visible:
            try:
                self.pack(side="left", padx=(0, 8))
            except Exception:
                pass
            self._visible = True

    def hide(self):
        if self._visible:
            try:
                self.pack_forget()
            except Exception:
                pass
            self._visible = False
        try:
            self.canvas.delete("all")
        except Exception:
            pass

    def start_speaking(self):
        self.show()
        self._speaking = True
        if self._job is None:
            self._tick()

    def stop_speaking(self, delay_hide=650):
        self._speaking = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        self._paint(0.1)
        try:
            self.after(delay_hide, self.hide)
        except Exception:
            self.hide()


# ============================== YILDIZ ALANI (OPTİMİZE) ==============================
class Starfield:
    """Öğeler bir kez oluşturulur; her karede sadece koordinat güncellenir.
    Parlaklık değişimi her karede yalnızca 1/4 yıldız için yapılır."""

    def __init__(self, canvas, width, height, count=110):
        self.c = canvas
        self.w = max(width, 100)
        self.h = max(height, 100)
        self.palette = [f"#{v:02x}{v:02x}{min(255, v + 25):02x}" for v in range(45, 256, 14)]
        self.stars = []
        for _ in range(count):
            r = random.uniform(0.6, 2.0)
            x, y = random.uniform(0, self.w), random.uniform(0, self.h)
            item = self.c.create_oval(x - r, y - r, x + r, y + r, fill="#777788", outline="", tags="star")
            self.stars.append({
                "id": item, "x": x, "y": y, "r": r, "speed": 0.15 + r * 0.35,
                "phase": random.uniform(0, math.tau), "ts": random.uniform(0.05, 0.14),
                "base": random.uniform(0.55, 1.0), "idx": -1,
            })

    def resize(self, w, h):
        self.w, self.h = max(w, 100), max(h, 100)

    def tick(self, frame):
        n = len(self.palette) - 1
        for i, s in enumerate(self.stars):
            s["y"] += s["speed"]
            if s["y"] > self.h + 4:
                s["y"] = -4
                s["x"] = random.uniform(0, self.w)
            r, x, y = s["r"], s["x"], s["y"]
            self.c.coords(s["id"], x - r, y - r, x + r, y + r)
            if (i + frame) % 4 == 0:
                s["phase"] += s["ts"]
                idx = int(n * s["base"] * (0.45 + 0.55 * abs(math.sin(s["phase"]))))
                if idx != s["idx"]:
                    s["idx"] = idx
                    self.c.itemconfigure(s["id"], fill=self.palette[idx])


# ============================== UYGULAMA ==============================
class VigilApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"VIGIL  •  Yetkili Panel  v{CURRENT_VERSION}")
        self.geometry("1320x860")
        self.minsize(1100, 740)
        self.configure(fg_color=C["bg"])

        self.db = sqlite3.connect(DB_FILE)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")      # WAL ile güvenli, yazma çok daha hızlı
        self.db.execute("PRAGMA temp_store=MEMORY")
        self.db.execute("PRAGMA cache_size=-20000")       # ~20 MB sayfa önbelleği
        self.db.execute("PRAGMA busy_timeout=3000")
        self.init_db()

        self.settings = load_settings()
        self.sfx = SoundFX(self.settings["sfx"])
        self.jarvis = Jarvis(self.settings["jarvis"])
        self._jv_token = 0
        self.jarvis_lbl = None
        self.current_user = None
        self.current_page = "dash"
        self.pages = {}
        self._built = set()
        self._toast = None
        self._toast_token = 0
        self._fails = {}
        self._closing = False
        self._stars_on = False
        self._star_job = None
        self._frame = 0
        self._avatar_cache = {}
        self._anim = {}
        self._clock_job = None
        self._chat_job = None
        self._chat_sig_cache = None
        self.profile_win = None
        self._search_rows = {}
        self.report_rows = []
        self.current_report = ""
        self.editing_staff = None

        self.setup_styles()
        self.canvas = Canvas(self, bg=C["bg"], highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.starfield = Starfield(self.canvas, 1320, 860)
        self.bind("<Configure>", self.on_resize, add="+")
        self.bind_all("<ButtonPress-1>", self.on_any_click, add="+")

        self.after(300, self.set_window_icon)
        self.show_splash()

    def set_window_icon(self):
        try:
            from PIL import ImageTk
            self._icon = ImageTk.PhotoImage(render_logo(64, "#ffffff", "#8a96ff", bg=_hex2rgba("#0b0d14")))
            self.iconphoto(True, self._icon)
        except Exception:
            pass

    # ------------------------------ stil / küçük bileşenler ------------------------------
    def setup_styles(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Real.Treeview", background=C["panel"], fieldbackground=C["panel"],
                     foreground=C["text"], rowheight=28, borderwidth=0, font=("Segoe UI", 10))
        st.map("Real.Treeview", background=[("selected", "#262d57")], foreground=[("selected", "#ffffff")])
        st.configure("Real.Treeview.Heading", background=C["panel2"], foreground=C["muted"],
                     relief="flat", font=("Segoe UI", 10, "bold"))
        st.map("Real.Treeview.Heading", background=[("active", C["hover"])])

    def card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=C["panel"], corner_radius=12, border_width=1,
                            border_color=C["border"], **kw)

    def entry(self, parent, placeholder="", width=200, **kw):
        return ctk.CTkEntry(parent, width=width, placeholder_text=placeholder,
                            fg_color=C["bg"], border_color=C["border"], **kw)

    def button(self, parent, text, cmd, kind="ghost", width=110, height=32):
        colors = {
            "primary": (C["accent"], C["accent_h"]),
            "ghost": (C["panel2"], C["hover"]),
            "danger": ("#3a1518", "#5a1d22"),
            "success": ("#14301f", "#1d4a2e"),
            "gold": ("#3b2f0b", "#574413"),
        }[kind]
        extra = {"text_color": C["gold"]} if kind == "gold" else {}
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=height,
                             fg_color=colors[0], hover_color=colors[1], corner_radius=8, **extra)

    def label(self, parent, text, size=13, bold=False, color=None, **kw):
        return ctk.CTkLabel(parent, text=text, text_color=color or C["text"],
                            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"), **kw)

    def make_tree(self, parent, cols, height=10, selectmode="browse"):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        tree = ttk.Treeview(wrap, columns=[c[0] for c in cols], show="headings",
                            style="Real.Treeview", height=height, selectmode=selectmode)
        for cid, title, width in cols:
            tree.heading(cid, text=title)
            tree.column(cid, width=width, anchor="w", stretch=True)
        tree.tag_configure("odd", background=C["panel2"])
        sb = ctk.CTkScrollbar(wrap, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return wrap, tree

    def fill_tree(self, tree, rows):
        """rows: [(iid, values_tuple[, ekstra_etiketler])]"""
        tree.delete(*tree.get_children())
        for i, row in enumerate(rows):
            iid, vals = row[0], row[1]
            extra = tuple(row[2]) if len(row) > 2 else ()
            tree.insert("", "end", iid=str(iid), values=vals, tags=(("odd",) if i % 2 else ()) + extra)

    def confirm(self, text):
        win = ctk.CTkToplevel(self)
        win.title("Onay")
        self.center_window(win, 380, 170)
        self.sfx.play("open")
        win.bind("<Escape>", lambda e: win.destroy())
        win.configure(fg_color=C["bg"])
        win.transient(self)
        result = {"v": False}
        self.label(win, text, 13, wraplength=330).pack(pady=(30, 18), padx=20)
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack()

        def yes():
            result["v"] = True
            win.destroy()

        self.button(row, "Evet", yes, "danger", 100).pack(side="left", padx=6)
        self.button(row, "Vazgeç", win.destroy, "ghost", 100).pack(side="left", padx=6)
        win.after(120, lambda: win.winfo_exists() and win.grab_set())
        self.wait_window(win)
        return result["v"]

    def ask_text(self, prompt, title="Girdi"):
        """Kısa bir metin girişi ister. Kullanıcı vazgeçerse None, aksi halde (boş olabilen) metni döndürür."""
        win = ctk.CTkToplevel(self)
        win.title(title)
        self.center_window(win, 400, 210)
        self.sfx.play("open")
        win.configure(fg_color=C["bg"])
        win.transient(self)
        result = {"v": None}
        self.label(win, prompt, 13, wraplength=350, justify="left").pack(pady=(24, 10), padx=20)
        ent = self.entry(win, "", 320)
        ent.pack(pady=4)
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(pady=14)

        def ok():
            result["v"] = ent.get().strip()
            win.destroy()

        self.button(row, "Tamam", ok, "primary", 100).pack(side="left", padx=6)
        self.button(row, "Vazgeç", win.destroy, "ghost", 100).pack(side="left", padx=6)
        ent.bind("<Return>", lambda e: ok())
        win.bind("<Escape>", lambda e: win.destroy())
        win.after(120, lambda: win.winfo_exists() and win.grab_set())
        ent.focus_set()
        self.wait_window(win)
        return result["v"]

    def center_window(self, win, w, h):
        try:
            self.update_idletasks()
            h = min(h, max(300, self.winfo_screenheight() - 120))
            x = self.winfo_rootx() + (self.winfo_width() - w) // 2
            y = self.winfo_rooty() + (self.winfo_height() - h) // 2
            win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            win.geometry(f"{w}x{h}")

    # ------------------------------ TOAST ------------------------------
    def show_toast(self, message, success=True, duration=2600, parent=None, sound=True):
        if sound:
            self.sfx.play("success" if success else "error")
        host = parent if (parent is not None and parent.winfo_exists()) else self
        if self._toast is not None:
            try:
                self._toast.destroy()
            except Exception:
                pass
        self._toast_token += 1
        token = self._toast_token
        bg, border = ("#0f2a1a", "#1a5c2e") if success else ("#2a0f12", "#5c1a22")
        toast = ctk.CTkFrame(host, fg_color=bg, corner_radius=12, border_width=1, border_color=border)
        toast._is_toast = True
        self.label(toast, ("✓  " if success else "✕  ") + message, 14).pack(padx=22, pady=12)
        self._toast = toast
        start, end, steps = -0.12, 0.03, 14

        def alive():
            return token == self._toast_token and toast.winfo_exists()

        def slide_in(step=0):
            if not alive():
                return
            t = min(1.0, step / steps)
            eased = 1 - (1 - t) ** 3
            toast.place(relx=0.5, rely=start + (end - start) * eased, anchor="n")
            toast.tkraise()
            if step < steps:
                self.after(16, lambda: slide_in(step + 1))
            else:
                self.after(duration, lambda: slide_out(0))

        def slide_out(step=0):
            if not alive():
                return
            t = min(1.0, step / steps)
            toast.place(relx=0.5, rely=end + (start - end) * (t ** 2), anchor="n")
            if step < steps:
                self.after(16, lambda: slide_out(step + 1))
            else:
                toast.destroy()

        slide_in()

    # ------------------------------ arka plan ------------------------------
    def on_resize(self, event):
        if event.widget is self:
            self.starfield.resize(event.width, event.height)

    def start_stars(self):
        self.canvas.itemconfigure("star", state="normal")
        if not self._stars_on:
            self._stars_on = True
            self.animate_stars()

    def stop_stars(self):
        """Ana arayüz tüm pencereyi kapladığı için animasyonu tamamen durdur → CPU %0."""
        self._stars_on = False
        if self._star_job is not None:
            try:
                self.after_cancel(self._star_job)
            except Exception:
                pass
            self._star_job = None
        self.canvas.itemconfigure("star", state="hidden")

    def animate_stars(self):
        if not self._stars_on or self._closing:
            return
        if self.state() != "iconic":
            self._frame += 1
            self.starfield.tick(self._frame)
        self._star_job = self.after(40, self.animate_stars)

    def clear_window(self):
        for w in self.winfo_children():
            if w is self.canvas or getattr(w, "_is_toast", False):
                continue
            w.destroy()
        self.jarvis_lbl = None
        self.powered_by(self)

    def powered_by(self, parent):
        lbl = ctk.CTkLabel(parent, text=POWERED_BY, text_color="#5b6378",
                           font=ctk.CTkFont(size=10, slant="italic"))
        lbl.place(x=12, y=7)
        return lbl

    # ------------------------------ ses / Jarvis ------------------------------
    def on_any_click(self, event):
        try:
            w = event.widget
            while w is not None and not isinstance(w, str):
                if isinstance(w, (ttk.Treeview, ctk.CTkComboBox, ctk.CTkCheckBox, ctk.CTkSwitch)):
                    self.sfx.play("tick")
                    return
                if isinstance(w, ctk.CTkButton):
                    self.sfx.play("click")
                    return
                w = getattr(w, "master", None)
        except Exception:
            pass

    def fade_switch(self, action, steps=6, step_ms=16, low=0.86):
        """Pencereyi kısa bir süreliğine hafif saydamlaştırıp action()'ı çalıştırır, sonra geri getirir.
        Bazı Linux pencere yöneticileri -alpha'yı desteklemez; desteklemiyorsa sessizce es geçilir."""
        if self.perf:
            action()
            return
        try:
            self.attributes("-alpha")
        except Exception:
            action()
            return
        if getattr(self, "_fading", False):      # üst üste tıklamada animasyonlar çakışmasın
            action()
            return
        self._fading = True

        def fade(i, target, after=None):
            if self._closing:
                self._fading = False
                return
            try:
                cur = 1.0 - (1.0 - target) * (i / steps)
                self.attributes("-alpha", cur)
            except Exception:
                pass
            if i < steps:
                self.after(step_ms, lambda: fade(i + 1, target, after))
            elif after:
                after()
            else:
                self._fading = False

        def run_action():
            try:
                action()
            finally:
                fade(0, 1.0)

        fade(0, low, run_action)

    def set_pref(self, key, value):
        value = bool(value)
        self.settings[key] = value
        save_settings(self.settings)
        if key == "sfx":
            self.sfx.enabled = value
            if value:
                self.sfx.play("success")
        elif key == "perf":
            self._anim = {}                      # süren animasyonları iptal et
        else:
            self.jarvis.enabled = value
            if not value:
                self.jarvis.stop()

    def jarvis_say(self, spoken, shown=None, hold=6500, force=False):
        """Jarvis konuşur; ana arayüzdeyse üst bantta daktilo efektiyle yazar."""
        if not (self.jarvis.enabled or force):
            return
        shown = shown or spoken
        self._jv_token += 1
        token = self._jv_token
        self.sfx.play("chime")
        self.jarvis.speak(spoken, force=force)
        lbl = self.jarvis_lbl
        orb = getattr(self, "jarvis_orb", None)

        def alive():
            try:
                return token == self._jv_token and not self._closing and lbl is not None and lbl.winfo_exists()
            except Exception:
                return False

        def orb_alive():
            try:
                return orb is not None and orb.winfo_exists()
            except Exception:
                return False

        def clear():
            if alive():
                lbl.configure(text="")
            if orb_alive():
                orb.stop_speaking()

        def typing(i=0):
            if not alive():
                if orb_alive():
                    orb.stop_speaking(delay_hide=0)
                return
            lbl.configure(text=shown[:i])
            if i < len(shown):
                self.after(38, lambda: typing(i + 1))
            else:
                self.after(hold, clear)

        if orb_alive():
            orb.start_speaking()
        typing()

    def test_jarvis(self):
        self.jarvis_greet(force=True)
        # ses üretimi birkaç sn sürebilir; sonra hangi motorun kullanıldığını bildir
        self.after(4500, lambda: self.show_toast("Ses: " + self.jarvis.status(),
                                                  self.jarvis.engine in ("edge", "sistem"), 6500))

    # ------------------------------ otomatik güncelleme ------------------------------
    def update_url(self):
        return (self.settings.get("update_url") or UPDATE_URL or "").strip()

    def check_updates(self, manual=False):
        """Arka planda sürüm denetler; arayüz donmaz. Sessiz: hata/yok durumunda sadece manuelde bildirir."""
        url = self.update_url()
        if not url or "KULLANICI" in url:
            if manual:
                self.show_toast("Güncelleme adresi ayarlanmamış (real_panel.py içindeki UPDATE_URL)", False, 5000)
            return
        if getattr(self, "_upd_busy", False):
            return
        self._upd_busy = True
        self._upd_result = None
        skip = None if manual else (self.settings.get("skip_update") or None)

        def work():
            try:
                self._upd_result = ("ok", Updater(url).check(skip_version=skip))
            except Exception as e:
                self._upd_result = ("err", f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()
        self.after(300, lambda: self._poll_update(manual))

    def _poll_update(self, manual):
        if self._closing:
            return
        res = getattr(self, "_upd_result", None)
        if res is None:
            self.after(300, lambda: self._poll_update(manual))
            return
        self._upd_busy = False
        kind, val = res
        if kind == "err":
            if manual:
                self.show_toast(f"Güncelleme denetlenemedi: {val}", False, 5500)
        elif val is None:
            if manual:
                self.show_toast(f"Son sürümü kullanıyorsun (v{CURRENT_VERSION})")
        else:
            self.show_update_dialog(val)

    def show_update_dialog(self, info):
        old = getattr(self, "_upd_win", None)
        try:
            if old is not None and old.winfo_exists():
                return
        except Exception:
            pass
        mandatory = info["mandatory"]
        win = ctk.CTkToplevel(self)
        self._upd_win = win
        win.title("VIGIL Güncelleme")
        win.geometry("480x400")
        win.resizable(False, False)
        win.configure(fg_color=C["bg"])
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", self.on_closing if mandatory else win.destroy)
        card = ctk.CTkFrame(win, fg_color=C["panel"], corner_radius=14, border_width=1, border_color=C["border"])
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text="", image=logo_image(48)).pack(pady=(18, 4))
        self.label(card, "Yeni sürüm hazır", 18, True).pack()
        self.label(card, f"v{info['current']}   →   v{info['version']}", 14, True, C["accent_h"]).pack(pady=(4, 8))
        if mandatory:
            self.label(card, "Bu güncelleme zorunlu.", 11, color=C["warn"]).pack()
        self.label(card, info["notes"] or "Performans iyileştirmeleri ve hata düzeltmeleri.", 12,
                   color=C["muted"], wraplength=400, justify="center").pack(pady=(4, 10), padx=20)
        status = self.label(card, "", 12, color=C["muted"], wraplength=400)
        status.pack(pady=(2, 4))
        bar = ctk.CTkProgressBar(card, width=380, progress_color=C["accent"], fg_color=C["panel2"])
        bar.set(0)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(side="bottom", pady=(0, 18))
        b_up = self.button(row, "Şimdi Güncelle", lambda: self._start_update(info, win, b_up, b_later, bar, status),
                           "primary", 150, 38)
        b_up.pack(side="left", padx=6)
        b_later = self.button(row, "Sonra", win.destroy, "ghost", 100, 38)
        if not mandatory:
            b_later.pack(side="left", padx=6)
        win.after(150, lambda: win.winfo_exists() and win.grab_set())

    def _start_update(self, info, win, b_up, b_later, bar, status):
        b_up.configure(state="disabled")
        b_later.configure(state="disabled")
        bar.pack(pady=(4, 10))
        status.configure(text="İndiriliyor…", text_color=C["muted"])
        st = {"done": 0, "total": 0, "result": None}
        up = Updater(self.update_url())

        def work():
            try:
                st["result"] = ("ok", up.download(info, progress=lambda d, t: st.update(done=d, total=t)))
            except Exception as e:
                st["result"] = ("err", str(e))

        threading.Thread(target=work, daemon=True).start()

        def fail(msg):
            status.configure(text=f"Güncelleme başarısız: {msg}", text_color=C["bad"])
            b_up.configure(state="normal", text="Tekrar Dene")
            b_later.configure(state="normal")
            self.sfx.play("error")

        def poll():
            if self._closing or not win.winfo_exists():
                return
            if st["result"] is None:
                if st["total"]:
                    bar.set(st["done"] / st["total"])
                    status.configure(text=f"İndiriliyor…  %{int(100 * st['done'] / st['total'])}")
                else:
                    status.configure(text=f"İndiriliyor…  {st['done'] // 1024} KB")
                win.after(100, poll)
                return
            kind, val = st["result"]
            if kind == "err":
                fail(val)
                return
            bar.set(1)
            status.configure(text="Kuruluyor…")
            win.update_idletasks()
            try:
                target = up.install(val, info)
            except Exception as e:
                fail(str(e))
                return
            status.configure(text="Güncelleme tamamlandı, uygulama yeniden başlatılıyor…", text_color=C["ok"])
            self.sfx.play("success")
            self.after(900, lambda: self._relaunch_after_update(up, target))

        poll()

    def _relaunch_after_update(self, up, target):
        try:
            up.relaunch(target)
        except Exception as e:
            self.show_toast(f"Yeniden başlatılamadı, uygulamayı kendin aç: {e}", False, 8000)
            return
        self.on_closing()

    def jarvis_greet(self, force=False):
        if not self.current_user:
            return
        name = re.sub(r"[_.\-]+", " ", self.current_user["username"]).strip()
        tail = {"kurucu": "kurucu olarak giriş yaptın, her şey hazır.",
                "premium": "premium hesabınla giriş yaptın, iyi çalışmalar."}.get(
            self.current_user["role"], "giriş yaptın, iyi çalışmalar.")
        self.jarvis_say(f"Hoş geldin {name}, {tail}", f"Hoş geldin {name}", force=force)

    def logout(self):
        name = re.sub(r"[_.\-]+", " ", (self.current_user or {}).get("username", "")).strip()
        self.sfx.play("logout")
        if name:
            self.jarvis_say(f"Hoşça kal {name}, görüşmek üzere.")
        self.fade_switch(self.show_login)

    # ------------------------------ veritabanı ------------------------------
    def _ensure_column(self, table, col, ddl):
        cols = [r["name"] for r in self.db.execute(f"PRAGMA table_info({table})")]
        if col not in cols:
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

    def init_db(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'uye',
                premium_until TEXT,
                avatar_path TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                algo TEXT NOT NULL DEFAULT 'sha256'
            );
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_code TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                activated_by INTEGER,
                activated_at TEXT,
                expires_at TEXT,
                used INTEGER DEFAULT 0,
                days INTEGER NOT NULL DEFAULT 30
            );
            CREATE TABLE IF NOT EXISTS staff (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL,
                owner_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                happened_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'Manuel kayıt',
                owner_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'uye',
                message TEXT NOT NULL,
                at TEXT NOT NULL
            );
        """)
        # Çok eski veritabanlarında eksik olabilecek tüm sütunları tamamla
        for table, col, ddl in [
            ("users", "role", "TEXT NOT NULL DEFAULT 'uye'"),
            ("users", "premium_until", "TEXT"),
            ("users", "avatar_path", "TEXT DEFAULT ''"),
            ("users", "algo", "TEXT NOT NULL DEFAULT 'sha256'"),
            ("users", "banned", "INTEGER NOT NULL DEFAULT 0"),
            ("users", "ban_reason", "TEXT NOT NULL DEFAULT ''"),
            ("keys", "activated_by", "INTEGER"),
            ("keys", "activated_at", "TEXT"),
            ("keys", "expires_at", "TEXT"),
            ("keys", "used", "INTEGER DEFAULT 0"),
            ("keys", "days", "INTEGER NOT NULL DEFAULT 30"),
            ("staff", "display_name", "TEXT NOT NULL DEFAULT ''"),
            ("staff", "owner_id", "INTEGER"),
            ("events", "channel", "TEXT NOT NULL DEFAULT ''"),
            ("events", "details", "TEXT NOT NULL DEFAULT ''"),
            ("events", "source", "TEXT NOT NULL DEFAULT 'Manuel kayıt'"),
            ("events", "owner_id", "INTEGER"),
        ]:
            self._ensure_column(table, col, ddl)
        self.db.commit()
        self.db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_events_time ON events(happened_at);
            CREATE INDEX IF NOT EXISTS idx_events_owner ON events(owner_id);
            CREATE INDEX IF NOT EXISTS idx_events_user_time ON events(user_id, happened_at);
            CREATE INDEX IF NOT EXISTS idx_events_time_type ON events(happened_at, event_type);
            CREATE INDEX IF NOT EXISTS idx_events_owner_time ON events(owner_id, happened_at);
            CREATE INDEX IF NOT EXISTS idx_chat_id ON chat_messages(id);
        """)
        self.db.commit()
        if not self.db.execute("SELECT 1 FROM users WHERE username='rwexn'").fetchone():
            h, s = hash_password(DEFAULT_ADMIN_PASSWORD)
            self.db.execute(
                "INSERT INTO users(username,password_hash,salt,role,created_at,algo) VALUES(?,?,?,?,?,?)",
                ("rwexn", h, s, "kurucu", now_text(), "pbkdf2"))
            self.db.commit()
        # SUPER_USERS: hesap yoksa oluştur (kimse önceden 'vezo' adını kapıp yetki alamasın),
        # varsa rolünü kurucu yap -> kurucu paneli dahil her şeye erişir.
        for uname, default_pw in SUPER_USERS.items():
            row = self.db.execute("SELECT id, role FROM users WHERE username=? COLLATE NOCASE", (uname,)).fetchone()
            if row is None:
                h, s_ = hash_password(default_pw)
                self.db.execute(
                    "INSERT INTO users(username,password_hash,salt,role,created_at,algo) VALUES(?,?,?,?,?,?)",
                    (uname, h, s_, "kurucu", now_text(), "pbkdf2"))
            elif row["role"] != "kurucu":
                self.db.execute("UPDATE users SET role='kurucu', premium_until=NULL WHERE id=?", (row["id"],))
        self.db.commit()
        # kurucu hesabı her açılışta yanlışlıkla askıya alınmış olsa bile onarılır
        self.db.execute("UPDATE users SET banned=0, ban_reason='' WHERE role='kurucu' AND banned!=0")
        self.db.commit()
        adm = self.db.execute("SELECT id FROM users WHERE role='kurucu' ORDER BY id LIMIT 1").fetchone()
        if adm:
            self.db.execute("UPDATE events SET owner_id=? WHERE owner_id IS NULL", (adm["id"],))
            self.db.execute("UPDATE staff SET owner_id=? WHERE owner_id IS NULL", (adm["id"],))
            self.db.commit()

    # ------------------------------ rol / premium ------------------------------
    def is_premium_or_kurucu(self):
        return self.current_user["role"] in ("premium", "kurucu")

    can_view_unlimited = is_premium_or_kurucu

    def is_kurucu(self):
        return self.current_user["role"] == "kurucu"

    def owner_clause(self, alias="e"):
        if self.can_view_unlimited():
            return "", []
        return f" AND {alias}.owner_id=?", [self.current_user["id"]]

    def reload_user(self):
        row = self.db.execute("SELECT * FROM users WHERE id=?", (self.current_user["id"],)).fetchone()
        self.current_user = dict(row)
        self.check_premium_status()

    def check_premium_status(self):
        """Premium süresi dolduysa üyeliğe düşürür. Rol değiştiyse True döner."""
        u = self.current_user
        if u["role"] != "premium":
            return False
        until = u.get("premium_until")
        if until:
            try:
                if datetime.strptime(until, FMT) > datetime.now():
                    return False
            except ValueError:
                return False
            self.db.execute("UPDATE users SET role='uye', premium_until=NULL WHERE id=?", (u["id"],))
            self.db.commit()
            u["role"], u["premium_until"] = "uye", None
            return True
        return False

    def premium_days_left(self):
        u = self.current_user.get("premium_until")
        if not u:
            return None
        try:
            d = datetime.strptime(u, FMT) - datetime.now()
            return max(0, math.ceil(d.total_seconds() / 86400))
        except ValueError:
            return None

    def grant_premium(self, user_id, days):
        row = self.db.execute("SELECT premium_until FROM users WHERE id=?", (user_id,)).fetchone()
        base = datetime.now()
        if row and row["premium_until"]:
            try:
                cur = datetime.strptime(row["premium_until"], FMT)
                if cur > base:
                    base = cur
            except ValueError:
                pass
        until = (base + timedelta(days=days)).strftime(FMT)
        self.db.execute("UPDATE users SET role='premium', premium_until=? WHERE id=? AND role!='kurucu'",
                        (until, user_id))
        self.db.commit()
        return until

    def role_badge(self):
        r = self.current_user["role"]
        if r == "kurucu":
            return "Kurucu", C["gold"]
        if r == "premium":
            return "Premium +", C["ok"]
        return "Üye", C["muted"]

    def avatar_widget(self, parent, size):
        path = self.current_user.get("avatar_path") or ""
        if path and Path(path).exists():
            try:
                key = (path, size, Path(path).stat().st_mtime)
                if key not in self._avatar_cache:
                    self._avatar_cache[key] = make_avatar_image(path, size)
                return ctk.CTkLabel(parent, text="", image=self._avatar_cache[key], width=size, height=size)
            except Exception:
                pass
        return ctk.CTkLabel(parent, text=self.current_user["username"][:1].upper(), width=size, height=size,
                            corner_radius=size // 2, fg_color="#232a55",
                            font=ctk.CTkFont(size=int(size * 0.45), weight="bold"))

    # ============================== AÇILIŞ / GİRİŞ / KAYIT ==============================
    def show_splash(self):
        self.clear_window()
        self.start_stars()
        self.sfx.play("startup")
        frame = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=18, width=400, height=240,
                             border_width=1, border_color=C["border"])
        frame.place(relx=0.5, rely=0.5, anchor="center")
        frame.pack_propagate(False)
        ctk.CTkLabel(frame, text="", image=logo_image(76)).pack(pady=(34, 6))
        self.label(frame, "V  I  G  I  L", 22, True).pack()
        self.label(frame, "Başlatılıyor…", 12, color=C["muted"]).pack(pady=(2, 16))
        bar = ctk.CTkProgressBar(frame, width=260, progress_color=C["accent"], fg_color=C["panel2"])
        bar.pack()
        bar.set(0)

        def step(i=0):
            if self._closing or not bar.winfo_exists():
                return
            bar.set(i / 25)
            if i < 25:
                self.after(24, lambda: step(i + 1))
            else:
                self.after(150, self.show_login)

        step()

    def show_login(self):
        self.clear_window()
        self.current_user = None
        self.start_stars()
        if not getattr(self, "_upd_started", False):
            self._upd_started = True
            self.after(1500, self.check_updates)             # açılışta sessizce denetle
            self.after(4000, Updater.mark_ok)                 # güncelleme sonrası sorunsuz açıldı
            self.after(6000, Updater.cleanup_old)
        f = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=18, width=420, height=520,
                         border_width=1, border_color=C["border"])
        f.place(relx=0.5, rely=0.5, anchor="center")
        f.pack_propagate(False)
        ctk.CTkLabel(f, text="", image=logo_image(84)).pack(pady=(36, 8))
        self.label(f, "V  I  G  I  L", 26, True).pack()
        self.label(f, "Yetkili Aktivite Paneli", 13, color=C["muted"]).pack(pady=(2, 24))
        self.login_user = self.entry(f, "Kullanıcı adı", 290, height=40)
        self.login_user.pack(pady=7)
        self.login_pass = self.entry(f, "Şifre", 290, height=40, show="•")
        self.login_pass.pack(pady=7)
        show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Şifreyi göster", variable=show_var, text_color=C["muted"],
                        font=ctk.CTkFont(size=12), checkbox_width=18, checkbox_height=18,
                        command=lambda: self.login_pass.configure(show="" if show_var.get() else "•")
                        ).pack(anchor="w", padx=65, pady=(2, 10))
        self.button(f, "Giriş Yap", self.do_login, "primary", 290, 40).pack(pady=(8, 8))
        self.button(f, "Hesap Oluştur", self.show_register, "ghost", 290, 36).pack(pady=4)
        self.label(f, f"v{CURRENT_VERSION}", 11, color="#444a5c").pack(side="bottom", pady=14)
        self.login_user.bind("<Return>", lambda e: self.login_pass.focus_set())
        self.login_pass.bind("<Return>", lambda e: self.do_login())
        self.login_user.focus_set()

    def show_register(self):
        self.clear_window()
        self.start_stars()
        f = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=18, width=420, height=500,
                         border_width=1, border_color=C["border"])
        f.place(relx=0.5, rely=0.5, anchor="center")
        f.pack_propagate(False)
        self.sfx.play("switch")
        self.label(f, "Yeni Üye Hesabı", 22, True).pack(pady=(40, 6))
        self.label(f, "Harf, rakam, _ . - kullanabilirsin (3-20 karakter)", 12, color=C["muted"]).pack(pady=(0, 22))
        self.reg_user = self.entry(f, "Kullanıcı adı", 290, height=40)
        self.reg_user.pack(pady=6)
        self.reg_pass = self.entry(f, "Şifre (en az 6 karakter)", 290, height=40, show="•")
        self.reg_pass.pack(pady=6)
        self.reg_pass2 = self.entry(f, "Şifre tekrar", 290, height=40, show="•")
        self.reg_pass2.pack(pady=6)
        self.button(f, "Kayıt Ol", self.do_register, "primary", 290, 40).pack(pady=(20, 8))
        self.button(f, "← Girişe Dön", self.show_login, "ghost", 290, 34).pack()
        self.reg_pass2.bind("<Return>", lambda e: self.do_register())
        self.reg_user.focus_set()

    def do_login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()
        fk = username.lower()
        cnt, until = self._fails.get(fk, (0, 0))
        if time.time() < until:
            self.show_toast(f"Çok fazla deneme. {int(until - time.time()) + 1} sn bekle", False)
            return
        row = self.db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row or not verify_password(password, row["password_hash"], row["salt"], row["algo"]):
            cnt += 1
            self._fails[fk] = (0, time.time() + 30) if cnt >= 5 else (cnt, 0)
            self.show_toast("Kullanıcı adı veya şifre yanlış", False)
            return
        if row["banned"]:
            reason = row["ban_reason"] or "belirtilmedi"
            self.show_toast(f"Hesabın askıya alınmış (gerekçe: {reason})", False, 4500)
            return
        self._fails.pop(fk, None)
        if row["algo"] != "pbkdf2":  # eski hesapları sessizce güçlendir
            h, s = hash_password(password)
            self.db.execute("UPDATE users SET password_hash=?, salt=?, algo='pbkdf2' WHERE id=?",
                            (h, s, row["id"]))
            self.db.commit()
            row = self.db.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
        self.current_user = dict(row)
        expired = self.check_premium_status()
        self.sfx.play("login")
        self.fade_switch(lambda: self.build_main_ui("dash"))
        if row["role"] == "kurucu" and SUPER_USERS.get(row["username"].lower()) == password:
            self.show_toast("Varsayılan şifre kullanılıyor! Profil'den değiştir.", False, 4500)
        elif expired:
            self.show_toast("Premium süren doldu", False)
        else:
            self.show_toast(f"Hoş geldin {self.current_user['username']}!", sound=False)
        self.after(450, self.jarvis_greet)

    def do_register(self):
        u = self.reg_user.get().strip()
        p1, p2 = self.reg_pass.get(), self.reg_pass2.get()
        if not re.fullmatch(r"[A-Za-z0-9_.\-]{3,20}", u):
            self.show_toast("Kullanıcı adı geçersiz (3-20; harf, rakam, _ . -)", False)
            return
        if len(p1) < 6:
            self.show_toast("Şifre en az 6 karakter olmalı", False)
            return
        if p1 != p2:
            self.show_toast("Şifreler uyuşmuyor", False)
            return
        if self.db.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE", (u,)).fetchone():
            self.show_toast("Bu kullanıcı adı zaten var", False)
            return
        h, s = hash_password(p1)
        self.db.execute("INSERT INTO users(username,password_hash,salt,role,created_at,algo) VALUES(?,?,?,?,?,?)",
                        (u, h, s, "uye", now_text(), "pbkdf2"))
        self.db.commit()
        self.show_toast("Hesap oluşturuldu!")
        self.after(1000, self.show_login)

    # ============================== ANA ARAYÜZ ==============================
    def build_main_ui(self, page="dash"):
        self.clear_window()
        self.stop_stars()
        self._built.clear()
        self.pages = {}
        self.nav = {}

        shell = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        shell.place(x=0, y=0, relwidth=1, relheight=1)
        side = ctk.CTkFrame(shell, width=224, fg_color=C["panel"], corner_radius=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        self.powered_by(side)
        ctk.CTkLabel(side, text="", image=logo_image(54)).pack(pady=(30, 4))
        self.label(side, "V  I  G  I  L", 17, True).pack()
        self.label(side, "Yetkili Paneli", 11, color=C["muted"]).pack(pady=(0, 20))

        items = [("dash", "Özet"), ("staff", "Yetkililer"), ("event", "Kayıt Ekle"),
                 ("search", "Arama & Geçmiş"), ("report", "Raporlar"), ("chat", "Sohbet")]
        if self.is_kurucu():
            items.append(("admin", "Kurucu Paneli"))
        self.titles = dict(items)
        for key, text in items:
            b = ctk.CTkButton(side, text=text, anchor="w", height=38, corner_radius=8,
                              fg_color="transparent", hover_color=C["hover"], text_color=C["muted"],
                              font=ctk.CTkFont(size=13), command=lambda k=key: self.show_page(k))
            b.pack(fill="x", padx=12, pady=2)
            self.nav[key] = b

        # kullanıcı kartı
        user = ctk.CTkFrame(side, fg_color=C["panel2"], corner_radius=12)
        user.pack(side="bottom", fill="x", padx=12, pady=14)
        top = ctk.CTkFrame(user, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        self.avatar_widget(top, 40).pack(side="left")
        info = ctk.CTkFrame(top, fg_color="transparent")
        info.pack(side="left", padx=10)
        badge, color = self.role_badge()
        self.label(info, self.current_user["username"], 13, True).pack(anchor="w")
        self.label(info, badge, 11, color=color).pack(anchor="w")
        days = self.premium_days_left() if self.current_user["role"] == "premium" else None
        if days is not None:
            self.label(user, f"{days} gün kaldı", 11, color=C["muted"]).pack(anchor="w", padx=12)
        brow = ctk.CTkFrame(user, fg_color="transparent")
        brow.pack(fill="x", padx=10, pady=10)
        self.button(brow, "Profil", self.show_profile, "ghost", 88, 30).pack(side="left")
        self.button(brow, "Çıkış", self.logout, "danger", 80, 30).pack(side="right")

        content = ctk.CTkFrame(shell, fg_color=C["bg"], corner_radius=0)
        content.pack(side="left", fill="both", expand=True)
        head = ctk.CTkFrame(content, fg_color="transparent", height=64)
        head.pack(fill="x", padx=22, pady=(14, 0))
        self.page_title = self.label(head, "", 22, True)
        self.page_title.pack(side="left")
        jv_wrap = ctk.CTkFrame(head, fg_color="transparent")
        jv_wrap.pack(side="left", padx=22)
        try:
            self.jarvis_orb = JarvisOrb(jv_wrap, 30)
        except Exception:
            _log_crash("JarvisOrb oluşturulamadı")
            self.jarvis_orb = None
        self.jarvis_lbl = self.label(jv_wrap, "", 12, color=C["accent_h"])
        self.jarvis_lbl.pack(side="left")
        self.clock_label = self.label(head, datetime.now().strftime("%d.%m.%Y  %H:%M:%S"), 13, color=C["muted"])
        self.clock_label.pack(side="right")
        if getattr(self, "_clock_job", None):
            try:
                self.after_cancel(self._clock_job)
            except Exception:
                pass
        self._tick_clock()
        if getattr(self, "_chat_job", None):
            try:
                self.after_cancel(self._chat_job)
            except Exception:
                pass
        self._chat_job = None
        self._tick_chat_poll()

        self.page_host = ctk.CTkFrame(content, fg_color="transparent")
        self.page_host.pack(fill="both", expand=True, padx=22, pady=(4, 18))
        for key, _ in items:
            self.pages[key] = (ctk.CTkScrollableFrame(self.page_host, fg_color="transparent")
                               if key == "dash" else ctk.CTkFrame(self.page_host, fg_color="transparent"))

        self.titles = dict(items)
        self.show_page(page, silent=True)

    def _tick_clock(self):
        if self._closing:
            return
        try:
            if not self.clock_label.winfo_exists():
                return
            self.clock_label.configure(text=datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))
        except Exception:
            return
        self._clock_job = self.after(1000, self._tick_clock)

    def _chat_sig(self):
        r = self.db.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM chat_messages").fetchone()
        return (r[0], r[1])

    def _tick_chat_poll(self):
        if self._closing:
            return
        try:
            if (self.current_page == "chat" and hasattr(self, "chat_scroll")
                    and self.chat_scroll.winfo_exists() and self._chat_sig() != self._chat_sig_cache):
                self.refresh_chat()
        except Exception:
            pass
        self._session_guard()
        self._chat_job = self.after(4000, self._tick_chat_poll)

    def _session_guard(self):
        """Askıya alınan hesap uygulama açıkken bile birkaç saniye içinde fark edilip oturumu kapatılır."""
        if self._closing or not self.current_user:
            return
        try:
            row = self.db.execute("SELECT banned, ban_reason FROM users WHERE id=?",
                                  (self.current_user["id"],)).fetchone()
            if row and row["banned"]:
                reason = row["ban_reason"] or "belirtilmedi"
                self.current_user = None
                self.sfx.play("error")
                self.fade_switch(lambda: self.show_login())
                self.after(400, lambda: self.show_toast(f"Hesabın askıya alındı (gerekçe: {reason})", False, 5000))
        except Exception:
            pass

    def show_page(self, key, silent=False):
        if self.check_premium_status():
            self.build_main_ui(key)
            self.show_toast("Premium süren doldu", False)
            return
        if not silent and key != self.current_page:
            self.sfx.play("switch")
            self._show_page_now(key)           # alpha animasyonu kasma yaptığı için sayfa geçişinde kaldırıldı
            return
        self._show_page_now(key)

    def _show_page_now(self, key):
        builders = {
            "dash": (self.build_dashboard, self.refresh_dashboard),
            "staff": (self.build_staff, self.refresh_staff),
            "event": (self.build_event, self.refresh_event),
            "search": (self.build_search, self.run_search),
            "report": (self.build_report, self.make_report),
            "chat": (self.build_chat, self.refresh_chat),
            "admin": (self.build_admin, self.refresh_admin),
        }
        for k, fr in self.pages.items():
            fr.pack_forget()
            self.nav[k].configure(fg_color="transparent", text_color=C["muted"])
        self.nav[key].configure(fg_color=C["hover"], text_color=C["accent_h"])
        self.current_page = key
        self.page_title.configure(text=self.titles[key])
        build, refresh = builders[key]
        if key not in self._built:
            build(self.pages[key])
            self._built.add(key)
        self.pages[key].pack(fill="both", expand=True)
        if key in ("staff", "search", "report", "event", "admin"):
            tag = (self.db.total_changes, self.current_user["id"], self.current_user["role"])
            tags = self.__dict__.setdefault("_page_tags", {})
            stamp = tags.get(key)
            if stamp and stamp[0][0] == tag[0] and stamp[0][1:] == tag[1:] and time.monotonic() - stamp[1] < 60:
                return                          # son ziyaretten beri veri değişmedi: yeniden sorgulama/çizme
            refresh()
            tags[key] = (tag, time.monotonic())
            return
        refresh()

    # ============================== ÖZET ==============================
    def hover_card(self, card, glow="#3b4590"):
        def inside():
            try:
                x, y = card.winfo_pointerxy()
                return (card.winfo_rootx() <= x < card.winfo_rootx() + card.winfo_width()
                        and card.winfo_rooty() <= y < card.winfo_rooty() + card.winfo_height())
            except Exception:
                return False

        def enter(_e=None):
            try:
                card.configure(border_color=glow)
            except Exception:
                pass

        def leave(_e=None):
            try:
                if not inside():
                    card.configure(border_color=C["border"])
            except Exception:
                pass

        def bind_all(w):
            try:
                w.bind("<Enter>", enter, add="+")
                w.bind("<Leave>", leave, add="+")
            except Exception:
                pass
            for ch in w.winfo_children():
                bind_all(ch)

        bind_all(card)

    @property
    def perf(self):
        return bool(self.settings.get("perf", False))

    def animate_number(self, label, target, key):
        if self.perf:
            try:
                label.configure(text=str(target))
            except Exception:
                pass
            return
        token = self._anim.get(key, 0) + 1
        self._anim[key] = token
        steps = 18

        def step(i=0):
            if self._anim.get(key) != token or self._closing:
                return
            try:
                if not label.winfo_exists():
                    return
                e = 1 - (1 - i / steps) ** 3
                label.configure(text=str(int(round(target * e))))
            except Exception:
                return
            if i < steps:
                self.after(22, lambda: step(i + 1))

        step()

    def build_dashboard(self, p):
        for c in range(4):
            p.grid_columnconfigure(c, weight=1, uniform="d")
        self._anim = getattr(self, "_anim", {})
        self.stat, self.spark = {}, {}

        # --- karşılama bandı
        ban = self.card(p)
        ban.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        left = ctk.CTkFrame(ban, fg_color="transparent")
        left.pack(side="left", padx=18, pady=14)
        h = datetime.now().hour
        greet = ("Günaydın" if 5 <= h < 12 else "İyi günler" if h < 18 else
                 "İyi akşamlar" if h < 23 else "İyi geceler")
        self.label(left, f"{greet}, {self.current_user['username']}", 20, True).pack(anchor="w")
        self.banner_sub = self.label(left, "", 12, color=C["muted"])
        self.banner_sub.pack(anchor="w", pady=(2, 0))
        right = ctk.CTkFrame(ban, fg_color="transparent")
        right.pack(side="right", padx=14)
        self.button(right, "+ Kayıt Ekle", lambda: self.show_page("event"), "primary", 120, 34).pack(side="left", padx=4)
        self.button(right, "Rapor", lambda: self.show_page("report"), "ghost", 80, 34).pack(side="left", padx=4)
        self.demo_btn = self.button(right, "Örnek Veri Yükle", self.toggle_demo, "success", 150, 34)
        self.demo_btn.pack(side="left", padx=4)

        # --- istatistik kartları + mini grafik
        for i, (k, t, col) in enumerate([("today", "Bugünkü Kayıt", C["accent_h"]),
                                         ("staff", "Toplam Yetkili", C["ok"]),
                                         ("total", "Toplam Kayıt", "#c77dff"),
                                         ("voice", "Bugün Ses Girişi", C["warn"])]):
            c = self.card(p)
            c.grid(row=1, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0), pady=(0, 10))
            self.label(c, t, 12, color=C["muted"]).pack(anchor="w", padx=16, pady=(14, 0))
            val = self.label(c, "0", 30, True)
            val.pack(anchor="w", padx=16)
            sub = self.label(c, "", 11, color=C["muted"])
            sub.pack(anchor="w", padx=16)
            sp = Canvas(c, bg=C["panel"], highlightthickness=0, height=38)
            sp.pack(fill="x", padx=12, pady=(4, 12))
            self.stat[k] = (val, sub)
            self.spark[k] = [sp, [], col]
            sp.bind("<Configure>", lambda e, k=k: self.debounce("sp" + k, lambda: self.draw_spark(k)))
            self.hover_card(c)

        # --- 7 günlük grafik + liderlik
        cc = self.card(p)
        cc.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        self.label(cc, "Son 7 Gün Aktivite", 14, True).pack(anchor="w", padx=16, pady=(12, 0))
        self.chart = Canvas(cc, bg=C["panel"], highlightthickness=0, height=210)
        self.chart.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.chart_data, self._chart_p = [], 1.0
        self.chart.bind("<Configure>", lambda e: self.debounce("chart", self.draw_chart))
        self.hover_card(cc)

        tc = self.card(p)
        tc.grid(row=2, column=3, sticky="nsew", padx=(8, 0), pady=(0, 10))
        self.label(tc, "En Aktif (7 gün)", 14, True).pack(anchor="w", padx=16, pady=(12, 6))
        self.top_box = ctk.CTkFrame(tc, fg_color="transparent")
        self.top_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.hover_card(tc)

        # --- ısı haritası + halka grafik
        hc = self.card(p)
        hc.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        hh = ctk.CTkFrame(hc, fg_color="transparent")
        hh.pack(fill="x", padx=16, pady=(12, 0))
        self.label(hh, "Yoğunluk Haritası (30 gün)", 14, True).pack(side="left")
        self.heat_info = self.label(hh, "", 11, color=C["muted"])
        self.heat_info.pack(side="right")
        self.heat = Canvas(hc, bg=C["panel"], highlightthickness=0, height=190)
        self.heat.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.heat_data = [[0] * 24 for _ in range(7)]
        self.heat.bind("<Configure>", lambda e: self.debounce("heat", self.draw_heat))
        self.heat.bind("<Motion>", self.on_heat_move)
        self.heat.bind("<Leave>", lambda e: self.heat_info.configure(text=self._heat_peak_text))
        self._heat_peak_text = ""
        self.hover_card(hc)

        dc = self.card(p)
        dc.grid(row=3, column=2, columnspan=2, sticky="nsew", padx=(8, 0), pady=(0, 10))
        self.label(dc, "Olay Dağılımı (30 gün)", 14, True).pack(anchor="w", padx=16, pady=(12, 0))
        self.donut = Canvas(dc, bg=C["panel"], highlightthickness=0, height=190)
        self.donut.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.donut_data, self._donut_p = [], 1.0
        self.donut.bind("<Configure>", lambda e: self.debounce("donut", self.draw_donut))
        self.hover_card(dc)

        # --- canlı akış
        fc = self.card(p)
        fc.grid(row=4, column=0, columnspan=4, sticky="nsew")
        self.label(fc, "Canlı Akış", 14, True).pack(anchor="w", padx=16, pady=(12, 4))
        self.feed_box = ctk.CTkFrame(fc, fg_color="transparent")
        self.feed_box.pack(fill="x", padx=12, pady=(0, 12))

    # ---- çizim yardımcıları
    def draw_spark(self, key):
        cv, data, color = self.spark[key]
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 20 or h < 12 or len(data) < 2:
            return
        mn, mx = min(data), max(data)
        rng = (mx - mn) or 1
        pts = []
        for i, v in enumerate(data):
            pts += [2 + (w - 4) * i / (len(data) - 1), h - 4 - (h - 10) * (v - mn) / rng]
        cv.create_polygon([2, h] + pts + [w - 2, h], fill=lerp_color(C["panel"], color, 0.16), outline="")
        cv.create_line(pts, fill=color, width=2, smooth=True)
        x, y = pts[-2], pts[-1]
        cv.create_oval(x - 3.5, y - 3.5, x + 3.5, y + 3.5, fill=color, outline=C["panel"], width=2)

    def draw_chart(self):
        cv = self.chart
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        data = self.chart_data
        if w < 80 or h < 80 or not data:
            return
        pl, pb, pt = 34, 26, 16
        mx = max([v for _, v in data] + [1])
        for i in range(4):
            y = pt + (h - pt - pb) * i / 3
            cv.create_line(pl, y, w - 6, y, fill=C["border"])
            cv.create_text(pl - 6, y, text=str(round(mx * (1 - i / 3))), fill=C["muted"],
                           anchor="e", font=("Segoe UI", 8))
        slot = (w - pl - 10) / len(data)
        bw = min(46, slot * 0.5)
        prog = self._chart_p
        for i, (lab, v) in enumerate(data):
            x0 = pl + slot * i + (slot - bw) / 2
            y1 = h - pb
            y0 = y1 - (h - pt - pb) * (v / mx) * prog
            last = i == len(data) - 1
            cv.create_rectangle(x0, y0, x0 + bw, y1, fill=C["accent"] if last else "#3a4280", outline="")
            if last:
                cv.create_rectangle(x0, y0, x0 + bw, y0 + 3, fill=C["accent_h"], outline="")
            if prog > 0.85:
                cv.create_text(x0 + bw / 2, y0 - 9, text=str(v), fill=C["text"], font=("Segoe UI", 9, "bold"))
            cv.create_text(x0 + bw / 2, y1 + 12, text=lab, fill=C["muted"], font=("Segoe UI", 9))

    def animate_chart(self):
        if self.perf:
            self._chart_p = 1.0
            self.draw_chart()
            return
        token = self._anim.get("chart", 0) + 1
        self._anim["chart"] = token
        steps = 20

        def step(i=0):
            if self._anim.get("chart") != token or self._closing:
                return
            try:
                if not self.chart.winfo_exists():
                    return
                self._chart_p = 1 - (1 - i / steps) ** 3
                self.draw_chart()
            except Exception:
                return
            if i < steps:
                self.after(20, lambda: step(i + 1))

        step()

    def draw_heat(self):
        cv = self.heat
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 120 or h < 80:
            return
        left, top, bottom = 30, 4, 16
        cw, ch = (w - left - 4) / 24, (h - top - bottom) / 7
        mx = max(max(r) for r in self.heat_data) or 1
        self._heat_geo = (left, top, cw, ch)
        for d in range(7):
            cv.create_text(left - 6, top + ch * d + ch / 2, text=DAY_NAMES[d], fill=C["muted"],
                           anchor="e", font=("Segoe UI", 8))
            for hr in range(24):
                v = self.heat_data[d][hr]
                col = lerp_color(C["panel2"], C["accent"], 0.18 + 0.82 * (v / mx) ** 0.7) if v else C["panel2"]
                x, y = left + cw * hr, top + ch * d
                cv.create_rectangle(x + 1, y + 1, x + cw - 1, y + ch - 1, fill=col, outline="")
        for hr in range(0, 24, 3):
            cv.create_text(left + cw * hr + cw / 2, h - 7, text=f"{hr:02d}", fill=C["muted"], font=("Segoe UI", 8))

    def on_heat_move(self, e):
        geo = getattr(self, "_heat_geo", None)
        if not geo:
            return
        left, top, cw, ch = geo
        hr, d = int((e.x - left) // cw), int((e.y - top) // ch)
        if 0 <= hr < 24 and 0 <= d < 7:
            self.heat_info.configure(text=f"{DAY_NAMES[d]} {hr:02d}:00  —  {self.heat_data[d][hr]} kayıt")
        else:
            self.heat_info.configure(text=self._heat_peak_text)

    def draw_donut(self):
        cv = self.donut
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        data = self.donut_data
        total = sum(c for _, c in data)
        if w < 160 or h < 80:
            return
        if not total:
            cv.create_text(w / 2, h / 2, text="Henüz veri yok", fill=C["muted"], font=("Segoe UI", 11))
            return
        size = min(h - 12, w * 0.45)
        cx, cy, r = size / 2 + 14, h / 2, size / 2 - 8
        start, sweep = 90.0, 360 * self._donut_p
        for i, (name, c) in enumerate(data):
            ext = -(c / total) * sweep
            if abs(ext) > 3:
                cv.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=ext + 1.2,
                              style="arc", width=16, outline=PALETTE[i % len(PALETTE)])
            start += ext
        cv.create_text(cx, cy - 8, text=str(total), fill=C["text"], font=("Segoe UI", 20, "bold"))
        cv.create_text(cx, cy + 14, text="kayıt", fill=C["muted"], font=("Segoe UI", 9))
        lx, ly = cx + r + 30, max(8, cy - len(data) * 11)
        for i, (name, c) in enumerate(data):
            y = ly + i * 22
            cv.create_rectangle(lx, y + 3, lx + 10, y + 13, fill=PALETTE[i % len(PALETTE)], outline="")
            cv.create_text(lx + 18, y + 8, text=f"{name[:26]}", fill=C["text"], anchor="w", font=("Segoe UI", 9))
            cv.create_text(w - 14, y + 8, text=f"{c}  ({c * 100 // total}%)", fill=C["muted"],
                           anchor="e", font=("Segoe UI", 9))

    def animate_donut(self):
        if self.perf:
            self._donut_p = 1.0
            self.draw_donut()
            return
        token = self._anim.get("donut", 0) + 1
        self._anim["donut"] = token
        steps = 22

        def step(i=0):
            if self._anim.get("donut") != token or self._closing:
                return
            try:
                if not self.donut.winfo_exists():
                    return
                self._donut_p = 1 - (1 - i / steps) ** 3
                self.draw_donut()
            except Exception:
                return
            if i < steps:
                self.after(20, lambda: step(i + 1))

        step()

    def debounce(self, key, fn, ms=35):
        """Peş peşe gelen olayları (pencere boyutlandırma vb.) tek çizime indirger."""
        jobs = self.__dict__.setdefault("_deb_jobs", {})
        old = jobs.get(key)
        if old is not None:
            try:
                self.after_cancel(old)
            except Exception:
                pass
        jobs[key] = self.after(ms, fn)

    def _ensure_dash_rows(self):
        """Liderlik ve akış satırları bir kez oluşturulur, sonra sadece metinleri güncellenir (widget yarat/yık yok)."""
        if getattr(self, "_top_rows", None):
            return
        self._top_rows = []
        self._top_empty = self.label(self.top_box, "Henüz veri yok", 12, color=C["muted"])
        for i in range(5):
            row = ctk.CTkFrame(self.top_box, fg_color="transparent")
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill="x")
            rk = self.label(line, f"#{i + 1}", 12, True)
            rk.pack(side="left")
            nm = self.label(line, "", 12)
            nm.pack(side="left")
            ct = self.label(line, "", 12, True, C["accent_h"])
            ct.pack(side="right")
            bar = ctk.CTkProgressBar(row, height=6, fg_color=C["panel2"])
            bar.pack(fill="x", pady=(3, 0))
            self._top_rows.append((row, rk, nm, ct, bar))
        self._feed_rows = []
        self._feed_empty = self.label(self.feed_box,
                                      "Henüz kayıt yok. 'Örnek Veri Yükle' ile paneli doldurabilirsin.", 12,
                                      color=C["muted"])
        for i in range(8):
            row = ctk.CTkFrame(self.feed_box, fg_color=C["panel2"] if i % 2 == 0 else "transparent",
                               corner_radius=8, height=34)
            row.pack_propagate(False)
            dot = self.label(row, "●", 12)
            dot.pack(side="left", padx=(12, 8))
            nm = self.label(row, "", 12, True)
            nm.pack(side="left")
            ev = self.label(row, "", 12)
            ev.pack(side="left")
            ch = self.label(row, "", 12, color=C["muted"])
            ch.pack(side="left")
            tm = self.label(row, "", 11, color=C["muted"])
            tm.pack(side="right", padx=12)
            self._feed_rows.append((row, dot, nm, ev, ch, tm))

    def refresh_dashboard(self, force=False):
        # Veri değişmediyse (bu bağlantıdaki toplam yazma sayısı + gün) ve 45 sn geçmediyse yeniden çizme.
        sig = (self.db.total_changes, date.today(), self.current_user["id"], self.current_user["role"])
        now_t = time.monotonic()
        if (not force and sig == getattr(self, "_dash_sig", None)
                and now_t - getattr(self, "_dash_t", 0) < 45):
            return
        self._dash_sig, self._dash_t = sig, now_t

        oc, op = self.owner_clause("e")
        today = date.today()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        start7 = days[0].isoformat() + " 00:00:00"
        start30 = (today - timedelta(days=29)).isoformat() + " 00:00:00"

        # --- 7 günlük sayılar: tek sorgu
        per_day = {r["d"]: (r["c"], r["v"] or 0) for r in self.db.execute(
            "SELECT substr(e.happened_at,1,10) AS d, COUNT(*) AS c, "
            "SUM(e.event_type='Ses kanalına giriş') AS v FROM events e "
            "WHERE e.happened_at>=?" + oc + " GROUP BY d", [start7, *op])}
        daily = [per_day.get(d.isoformat(), (0, 0))[0] for d in days]
        voice = [per_day.get(d.isoformat(), (0, 0))[1] for d in days]
        total = self.db.execute(f"SELECT COUNT(*) FROM events e WHERE 1=1{oc}", op).fetchone()[0]
        staff_days = {r["d"]: r["c"] for r in self.db.execute(
            "SELECT substr(added_at,1,10) AS d, COUNT(*) AS c FROM staff GROUP BY d")}
        staff_n = sum(staff_days.values())
        staff_series = [sum(c for dd, c in staff_days.items() if dd <= d.isoformat()) for d in days]
        total_series = [total - sum(daily[i + 1:]) for i in range(7)]

        diff = daily[-1] - daily[-2]
        self.animate_number(self.stat["today"][0], daily[-1], "s_today")
        self.stat["today"][1].configure(text=f"dün {daily[-2]}  ({'+' if diff >= 0 else ''}{diff})",
                                        text_color=C["ok"] if diff >= 0 else C["bad"])
        self.animate_number(self.stat["staff"][0], staff_n, "s_staff")
        self.stat["staff"][1].configure(text="izlenen yetkili")
        self.animate_number(self.stat["total"][0], total, "s_total")
        self.stat["total"][1].configure(text=f"son 7 günde {sum(daily)}")
        self.animate_number(self.stat["voice"][0], voice[-1], "s_voice")
        self.stat["voice"][1].configure(text=f"7 günde {sum(voice)} giriş")
        for k, series in (("today", daily), ("staff", staff_series), ("total", total_series), ("voice", voice)):
            self.spark[k][1] = series
            self.draw_spark(k)

        self.chart_data = [(DAY_NAMES[d.weekday()], n) for d, n in zip(days, daily)]
        self.animate_chart()

        # --- liderlik (satırlar yeniden kullanılır)
        self._ensure_dash_rows()
        top = self.db.execute(
            "SELECT e.user_id, COALESCE(s.display_name,'') AS n, COUNT(*) AS c FROM events e "
            "LEFT JOIN staff s ON s.user_id=e.user_id WHERE e.happened_at>=?" + oc +
            " GROUP BY e.user_id ORDER BY c DESC LIMIT 5", [start7, *op]).fetchall()
        if top:
            self._top_empty.pack_forget()
        else:
            self._top_empty.pack(pady=20)
        rank_cols = [C["gold"], "#b8c0d0", "#c98a5a", C["muted"], C["muted"]]
        for i, (row, rk, nm, ct, bar) in enumerate(self._top_rows):
            if i < len(top):
                r = top[i]
                rk.configure(text_color=rank_cols[i])
                nm.configure(text="  " + (r["n"] or r["user_id"])[:18])
                ct.configure(text=str(r["c"]))
                bar.configure(progress_color=rank_cols[i] if i < 3 else C["accent"])
                bar.set(r["c"] / top[0]["c"])
                row.pack(fill="x", pady=4)
            else:
                row.pack_forget()

        # --- ısı haritası
        grid = [[0] * 24 for _ in range(7)]
        # tarih+saat (13 karakter) bazında gruplama: ~700 satır; strftime'dan çok daha hızlı
        for r in self.db.execute(
                "SELECT substr(e.happened_at,1,13) AS dh, COUNT(*) AS c FROM events e "
                "WHERE e.happened_at>=?" + oc + " GROUP BY dh", [start30, *op]):
            try:
                d = date.fromisoformat(r["dh"][:10])
                grid[d.weekday()][int(r["dh"][11:13])] += r["c"]
            except ValueError:
                continue
        self.heat_data = grid
        peak = max(((grid[d][hr], d, hr) for d in range(7) for hr in range(24)))
        self._heat_peak_text = f"En yoğun: {DAY_NAMES[peak[1]]} {peak[2]:02d}:00" if peak[0] else ""
        self.heat_info.configure(text=self._heat_peak_text)
        self.draw_heat()

        # --- halka
        dist = self.db.execute(
            "SELECT e.event_type AS t, COUNT(*) AS c FROM events e WHERE e.happened_at>=?" + oc +
            " GROUP BY e.event_type ORDER BY c DESC LIMIT 6", [start30, *op]).fetchall()
        self.donut_data = [(r["t"], r["c"]) for r in dist]
        self.animate_donut()

        # --- canlı akış (satırlar yeniden kullanılır)
        rows = self.db.execute(
            "SELECT e.user_id, e.event_type, e.channel, e.happened_at, COALESCE(s.display_name,'') AS display_name "
            "FROM events e LEFT JOIN staff s ON s.user_id=e.user_id WHERE 1=1" + oc +
            " ORDER BY e.happened_at DESC LIMIT 8", op).fetchall()
        if rows:
            self._feed_empty.pack_forget()
        else:
            self._feed_empty.pack(pady=14)
        for i, (row, dot, nm, ev, ch, tm) in enumerate(self._feed_rows):
            if i < len(rows):
                r = rows[i]
                col = EVENT_COLORS.get(r["event_type"], C["muted"])
                dot.configure(text_color=col)
                nm.configure(text=(r["display_name"] or r["user_id"])[:24])
                ev.configure(text="  " + r["event_type"], text_color=col)
                ch.configure(text=f"  •  {r['channel']}" if r["channel"] else "")
                tm.configure(text=rel_time(r["happened_at"]))
                row.pack(fill="x", pady=1)
            else:
                row.pack_forget()

        has_demo = self.db.execute("SELECT COUNT(*) FROM events WHERE source='Örnek veri' AND owner_id=?",
                                   (self.current_user["id"],)).fetchone()[0] > 0
        self.demo_btn.configure(text="Örnek Veriyi Temizle" if has_demo else "Örnek Veri Yükle",
                                fg_color="#3a1518" if has_demo else "#14301f",
                                hover_color="#5a1d22" if has_demo else "#1d4a2e")
        peak_txt = f"  •  {self._heat_peak_text.lower()}" if self._heat_peak_text else ""
        self.banner_sub.configure(text=f"Bugün {daily[-1]} kayıt  •  {staff_n} yetkili izleniyor{peak_txt}")

    # ---- örnek veri
    def toggle_demo(self):
        uid = self.current_user["id"]
        has = self.db.execute("SELECT COUNT(*) FROM events WHERE source='Örnek veri' AND owner_id=?",
                              (uid,)).fetchone()[0] > 0
        if has:
            if not self.confirm("Örnek veriler silinsin mi?\n(Kendi girdiğin kayıtlara dokunulmaz)"):
                return
            self.db.execute("DELETE FROM events WHERE source='Örnek veri' AND owner_id=?", (uid,))
            self.db.execute("DELETE FROM staff WHERE user_id LIKE '90000000000000%' AND NOT EXISTS "
                            "(SELECT 1 FROM events WHERE events.user_id=staff.user_id)")
            self.db.commit()
            self.refresh_dashboard(force=True)
            self.show_toast("Örnek veri temizlendi")
            return
        n = self.seed_demo()
        self.refresh_dashboard(force=True)
        self.show_toast(f"{n} örnek kayıt yüklendi")

    def seed_demo(self):
        uid, now = self.current_user["id"], datetime.now()
        channels = ["Genel Sohbet", "Yetkili Odası", "Destek Hattı", "Toplantı", "Oyun-1", "Müzik"]
        hour_w = [1, 1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 5, 6, 6, 6, 7, 8, 9, 10, 10, 9, 8, 5, 3]
        ids = []
        for i, name in enumerate(DEMO_NAMES):
            sid = f"90000000000000{i:04d}"
            ids.append(sid)
            self.db.execute("INSERT OR IGNORE INTO staff(user_id,display_name,added_at,owner_id) VALUES(?,?,?,?)",
                            (sid, name, (now - timedelta(days=random.randint(10, 29))).strftime(FMT), uid))
        rows = []
        for sid in ids:
            activity = random.uniform(0.4, 1.0)
            for d in range(30):
                day = (now - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
                if random.random() > activity * 0.92:
                    continue
                for _ in range(random.choice([1, 1, 2])):
                    hr = random.choices(range(24), weights=hour_w)[0]
                    t0 = day + timedelta(hours=hr, minutes=random.randint(0, 59))
                    if t0 > now:
                        continue
                    ch = random.choice(channels)
                    dur = random.randint(15, 150)
                    rows.append((sid, "Ses kanalına giriş", ch, t0))
                    t1 = t0 + timedelta(minutes=dur)
                    if t1 <= now:
                        rows.append((sid, "Ses kanalından çıkış", ch, t1))
                    for _ in range(random.randint(0, 4)):
                        tm = t0 + timedelta(minutes=random.randint(0, dur))
                        if tm <= now:
                            rows.append((sid, "Mesaj gözlemi", random.choice(channels), tm))
                    if random.random() < 0.12:
                        tm = t0 + timedelta(minutes=dur // 2)
                        if tm <= now:
                            rows.append((sid, "Ses kanalı değiştirme", random.choice(channels), tm))
        self.db.executemany(
            "INSERT INTO events(user_id,event_type,channel,details,happened_at,source,owner_id) VALUES(?,?,?,?,?,?,?)",
            [(s, et, ch, "", t.strftime(FMT), "Örnek veri", uid) for s, et, ch, t in rows])
        self.db.commit()
        return len(rows)

    # ============================== YETKİLİLER ==============================
    def build_staff(self, p):
        form = self.card(p)
        form.pack(fill="x", pady=(0, 10))
        self.staff_mode = self.label(form, "Yetkili Ekle", 14, True)
        self.staff_mode.grid(row=0, column=0, columnspan=6, sticky="w", padx=16, pady=(12, 6))
        self.staff_id = self.entry(form, "Discord ID", 210)
        self.staff_id.grid(row=1, column=0, padx=(16, 6), pady=(0, 14))
        self.staff_name = self.entry(form, "Görünen ad", 220)
        self.staff_name.grid(row=1, column=1, padx=6, pady=(0, 14))
        self.button(form, "Kaydet", self.save_staff, "primary", 100).grid(row=1, column=2, padx=6, pady=(0, 14))
        self.button(form, "Temizle", self.clear_staff_form, "ghost", 90).grid(row=1, column=3, padx=6, pady=(0, 14))
        self.staff_id.bind("<Return>", lambda e: self.save_staff())
        self.staff_name.bind("<Return>", lambda e: self.save_staff())

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        self.staff_filter = self.entry(bar, "Ara (ad veya ID)", 280)
        self.staff_filter.pack(side="left")
        self.staff_filter.bind("<KeyRelease>", lambda e: self.refresh_staff())
        self.button(bar, "Sil", self.delete_staff, "danger", 80).pack(side="right")
        self.button(bar, "Düzenle", self.edit_staff, "ghost", 90).pack(side="right", padx=6)

        w, self.staff_tree = self.make_tree(p, [("n", "Görünen ad", 260), ("i", "Discord ID", 200),
                                                ("c", "Kayıt", 80), ("l", "Son aktivite", 130), ("a", "Eklenme", 150)], 14)
        w.pack(fill="both", expand=True)
        self.staff_tree.bind("<Double-1>", lambda e: self.edit_staff())

    def clear_staff_form(self):
        self.staff_id.delete(0, "end")
        self.staff_name.delete(0, "end")
        self.staff_mode.configure(text="Yetkili Ekle")

    def edit_staff(self):
        sel = self.staff_tree.selection()
        if not sel:
            self.show_toast("Listeden bir yetkili seç", False)
            return
        vals = self.staff_tree.item(sel[0], "values")
        self.clear_staff_form()
        sid, sname = str(vals[1]), str(vals[0])
        self.staff_id.insert(0, sid)
        self.staff_name.insert(0, sname if sname != "(isimsiz)" else "")
        self.staff_mode.configure(text=f"Düzenleniyor: {sid}")

    def delete_staff(self):
        sel = self.staff_tree.selection()
        if not sel:
            self.show_toast("Listeden bir yetkili seç", False)
            return
        uid = sel[0]
        row = self.db.execute("SELECT owner_id FROM staff WHERE user_id=?", (uid,)).fetchone()
        if not row or not (self.is_kurucu() or row["owner_id"] == self.current_user["id"]):
            self.show_toast("Bu yetkiliyi sadece ekleyen veya kurucu silebilir", False)
            return
        if self.confirm(f"{uid} silinsin mi?\n(Kayıtları silinmez)"):
            self.db.execute("DELETE FROM staff WHERE user_id=?", (uid,))
            self.db.commit()
            self.refresh_staff()
            self.show_toast("Yetkili silindi")

    def save_staff(self):
        uid, name = self.staff_id.get().strip(), self.staff_name.get().strip()
        if not uid.isdigit() or len(uid) > 25:
            self.show_toast("ID sadece rakam olmalı", False)
            return
        self.db.execute(
            "INSERT INTO staff(user_id,display_name,added_at,owner_id) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name",
            (uid, name, now_text(), self.current_user["id"]))
        self.db.commit()
        self.clear_staff_form()
        self.refresh_staff()
        self.show_toast("Yetkili kaydedildi")

    def refresh_staff(self):
        oc, op = self.owner_clause("e")
        q = f"%{self.staff_filter.get().strip()}%"
        rows = self.db.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM events e WHERE e.user_id=s.user_id" + oc + ") AS cnt, "
            "(SELECT MAX(e.happened_at) FROM events e WHERE e.user_id=s.user_id" + oc + ") AS last_ev "
            "FROM staff s WHERE s.user_id LIKE ? OR s.display_name LIKE ? "
            "ORDER BY s.display_name COLLATE NOCASE", [*op, *op, q, q]).fetchall()
        self.fill_tree(self.staff_tree, [
            (r["user_id"], (r["display_name"] or "(isimsiz)", r["user_id"], r["cnt"],
                                            rel_time(r["last_ev"]) if r["last_ev"] else "-", r["added_at"]))
            for r in rows])

    # ============================== KAYIT EKLE ==============================
    def _section_head(self, parent, title, subtitle=None, accent=None):
        """Kart içinde başlık + ince renkli ayraç çizgisi çizer."""
        h = ctk.CTkFrame(parent, fg_color="transparent")
        h.pack(fill="x", padx=18, pady=(16, 10))
        top = ctk.CTkFrame(h, fg_color="transparent")
        top.pack(fill="x")
        bar = ctk.CTkFrame(top, width=4, height=16, corner_radius=2, fg_color=accent or C["accent"])
        bar.pack(side="left", padx=(0, 8))
        self.label(top, title, 15, True).pack(side="left")
        if subtitle:
            self.label(h, subtitle, 11, color=C["muted"]).pack(anchor="w", padx=(12, 0), pady=(3, 0))

    def _field(self, parent, label_text, widget, hint=None):
        """Üstte küçük etiket, altında widget olan tek bir form alanı döndürür."""
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        self.label(cell, label_text, 11, True, color=C["muted"]).pack(anchor="w", pady=(0, 4))
        widget_factory = widget(cell)
        widget_factory.pack(fill="x")
        if hint:
            self.label(cell, hint, 10, color=C["muted"]).pack(anchor="w", pady=(3, 0))
        return cell, widget_factory

    def build_event(self, p):
        wrap = ctk.CTkScrollableFrame(p, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        f1 = self.card(wrap)
        f1.pack(fill="x", pady=(0, 12))
        self._section_head(f1, "① Yetkili Seç", "Kaydın hangi yetkiliye ait olduğunu seç")
        body1 = ctk.CTkFrame(f1, fg_color="transparent")
        body1.pack(fill="x", padx=18, pady=(0, 18))
        body1.grid_columnconfigure((0, 1), weight=1, uniform="ev")

        c1, self.ev_filter = self._field(body1, "Yetkili ara",
                                         lambda m: self.entry(m, "Ad veya Discord ID yazarak filtrele", 220))
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.ev_filter.bind("<KeyRelease>", lambda e: self.filter_event_staff())
        c2, self.event_staff = self._field(body1, "Yetkili",
                                           lambda m: ctk.CTkComboBox(m, state="readonly", fg_color=C["bg"],
                                                                      border_color=C["border"]))
        c2.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        f2 = self.card(wrap)
        f2.pack(fill="x", pady=(0, 12))
        self._section_head(f2, "② Olay Detayları", "Ne oldu, nerede oldu, ne zaman oldu", accent=C["ok"])
        body2 = ctk.CTkFrame(f2, fg_color="transparent")
        body2.pack(fill="x", padx=18, pady=(0, 6))
        body2.grid_columnconfigure((0, 1), weight=1, uniform="ev")

        c3, self.event_type = self._field(body2, "Olay türü",
                                          lambda m: ctk.CTkComboBox(m, values=EVENT_TYPES, state="readonly",
                                                                     fg_color=C["bg"], border_color=C["border"]))
        self.event_type.set(EVENT_TYPES[0])
        c3.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))

        c4, self.event_channel = self._field(body2, "Kanal",
                                             lambda m: self.entry(m, "Kanal adı (isteğe bağlı)", 220))
        c4.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 12))

        def _mk_time(m):
            tf = ctk.CTkFrame(m, fg_color="transparent")
            self.event_time = self.entry(tf, "YYYY-AA-GG SS:DD:SS (boş = şimdi)", 220)
            self.event_time.pack(side="left", fill="x", expand=True)
            self.button(tf, "Şimdi", lambda: (self.event_time.delete(0, "end"),
                                              self.event_time.insert(0, now_text())),
                       "ghost", 72).pack(side="left", padx=(8, 0))
            return tf

        c5, _ = self._field(body2, "Tarih / saat", _mk_time)
        c5.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))

        c6, self.event_source = self._field(body2, "Kaynak",
                                            lambda m: ctk.CTkComboBox(m, values=["Manuel gözlem", "CSV içe aktarma",
                                                                                  "Diğer"], state="readonly",
                                                                       fg_color=C["bg"], border_color=C["border"]))
        self.event_source.set("Manuel gözlem")
        c6.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 12))

        c7, self.event_details = self._field(body2, "Detay",
                                             lambda m: ctk.CTkTextbox(m, height=90, fg_color=C["bg"],
                                                                       border_width=1, border_color=C["border"]))
        c7.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        f3 = self.card(wrap)
        f3.pack(fill="x")
        row3 = ctk.CTkFrame(f3, fg_color="transparent")
        row3.pack(fill="x", padx=18, pady=16)
        self.button(row3, "✓  Kaydı Ekle", self.add_event, "primary", 170, 40).pack(side="left")
        self.event_status = self.label(row3, "", 12, color=C["muted"])
        self.event_status.pack(side="left", padx=16)
        self._staff_values = []

    def refresh_event(self):
        rows = self.db.execute("SELECT * FROM staff ORDER BY display_name COLLATE NOCASE").fetchall()
        self._staff_values = [f"{r['display_name'] or '(isimsiz)'} — {r['user_id']}" for r in rows]
        self.filter_event_staff()

    def filter_event_staff(self):
        q = self.ev_filter.get().strip().lower()
        vals = [v for v in self._staff_values if q in v.lower()] if q else list(self._staff_values)
        self.event_staff.configure(values=vals or [""])
        self.event_staff.set(vals[0] if vals else "")

    def add_event(self):
        s = self.event_staff.get()
        uid = s.rsplit(" — ", 1)[1].strip() if " — " in s else ""
        if not uid:
            self.show_toast("Yetkili seçmelisin (önce Yetkililer sekmesinden ekle)", False)
            return
        when = self.event_time.get().strip() or now_text()
        try:
            parse_dt(when)
        except ValueError:
            self.show_toast("Tarih biçimi yanlış (YYYY-AA-GG SS:DD:SS)", False)
            return
        self.db.execute(
            "INSERT INTO events(user_id,event_type,channel,details,happened_at,source,owner_id) VALUES(?,?,?,?,?,?,?)",
            (uid, self.event_type.get(), self.event_channel.get().strip(),
             self.event_details.get("1.0", "end").strip(), when, self.event_source.get(), self.current_user["id"]))
        self.db.commit()
        self.event_status.configure(text=f"Son eklenen: {s} → {self.event_type.get()} ({when})")
        self.event_channel.delete(0, "end")
        self.event_time.delete(0, "end")
        self.event_details.delete("1.0", "end")
        self.show_toast("Kayıt eklendi")

    # ============================== ARAMA & GEÇMİŞ ==============================
    def build_search(self, p):
        top = self.card(p)
        top.pack(fill="x", pady=(0, 10))
        self._section_head(top, "Filtrele", "Yetkili, olay türü ve tarih aralığına göre daralt")
        r1 = ctk.CTkFrame(top, fg_color="transparent")
        r1.pack(fill="x", padx=18, pady=(0, 6))

        c1, self.s_query = self._field(r1, "Yetkili ara", lambda m: self.entry(m, "Ad veya Discord ID", 220))
        c1.pack(side="left", padx=(0, 10))
        self.s_query.bind("<Return>", lambda e: self.run_search())
        c2, self.s_type = self._field(r1, "Olay türü",
                                      lambda m: ctk.CTkComboBox(m, values=["Tümü"] + EVENT_TYPES, width=220,
                                                                 state="readonly", fg_color=C["bg"],
                                                                 border_color=C["border"]))
        self.s_type.set("Tümü")
        c2.pack(side="left", padx=10)
        c3, self.s_from = self._field(r1, "Başlangıç", lambda m: self.entry(m, "YYYY-AA-GG", 140))
        c3.pack(side="left", padx=10)
        c4, self.s_to = self._field(r1, "Bitiş", lambda m: self.entry(m, "YYYY-AA-GG", 140))
        c4.pack(side="left", padx=10)

        r2 = ctk.CTkFrame(top, fg_color="transparent")
        r2.pack(fill="x", padx=18, pady=(10, 16))
        self.button(r2, "🔍  Ara", self.run_search, "primary", 100).pack(side="left", padx=(0, 6))
        self.button(r2, "Temizle", self.clear_search, "ghost", 90).pack(side="left", padx=6)
        self.button(r2, "Kişi Raporu", self.make_user_report, "ghost", 110).pack(side="left", padx=6)
        self.button(r2, "CSV Dışa Aktar", self.export_search_csv, "ghost", 130).pack(side="left", padx=6)
        self.button(r2, "CSV İçe Aktar", self.import_csv, "ghost", 120).pack(side="left", padx=6)
        self.button(r2, "Seçileni Sil", self.delete_events, "danger", 110).pack(side="right")

        results = self.card(p)
        results.pack(fill="both", expand=True, pady=(0, 10))
        rh = ctk.CTkFrame(results, fg_color="transparent")
        rh.pack(fill="x", padx=18, pady=(14, 6))
        self.label(rh, "Sonuçlar", 14, True).pack(side="left")
        self.s_info = self.label(rh, "", 11, color=C["muted"])
        self.s_info.pack(side="left", padx=12)
        w, self.s_tree = self.make_tree(results, [("t", "Tarih", 150), ("n", "Yetkili", 170),
                                                   ("i", "Discord ID", 160), ("e", "Olay", 230),
                                                   ("c", "Kanal", 150), ("s", "Kaynak", 120)], 12, "extended")
        w.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        detail = self.card(p)
        detail.pack(fill="x")
        self.label(detail, "Kayıt Detayı", 12, True, color=C["muted"]).pack(anchor="w", padx=16, pady=(10, 2))
        self.s_detail = self.label(detail, "Listeden bir kayıt seç.", 12, color=C["muted"],
                                   justify="left", wraplength=1000)
        self.s_detail.pack(anchor="w", padx=16, pady=(0, 12))
        self.s_tree.bind("<<TreeviewSelect>>", self.on_search_select)

    def clear_search(self):
        self.s_query.delete(0, "end")
        self.s_from.delete(0, "end")
        self.s_to.delete(0, "end")
        self.s_type.set("Tümü")
        self.run_search()

    def search_rows(self, order="DESC", force_uid=None):
        q = self.s_query.get().strip()
        et = self.s_type.get()
        d1, d2 = self.s_from.get().strip(), self.s_to.get().strip()
        sql = ("SELECT e.*, COALESCE(s.display_name,'') AS display_name FROM events e "
               "LEFT JOIN staff s ON s.user_id=e.user_id WHERE 1=1")
        params = []
        oc, op = self.owner_clause("e")
        sql += oc
        params += op
        if force_uid:
            sql += " AND e.user_id=?"
            params.append(force_uid)
        elif q:
            sql += " AND (e.user_id LIKE ? OR s.display_name LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        if et and et != "Tümü":
            sql += " AND e.event_type=?"
            params.append(et)
        for val, op_, suffix in ((d1, ">=", " 00:00:00"), (d2, "<=", " 23:59:59")):
            if val:
                try:
                    date.fromisoformat(val)
                except ValueError:
                    self.show_toast("Tarih biçimi YYYY-AA-GG olmalı", False)
                    return None, False
                sql += f" AND e.happened_at {op_} ?"
                params.append(val + suffix)
        limit = 2000 if self.can_view_unlimited() else 50
        sql += f" ORDER BY e.happened_at {order} LIMIT ?"
        rows = self.db.execute(sql, params + [limit + 1]).fetchall()
        truncated = len(rows) > limit
        return rows[:limit], truncated

    def run_search(self):
        rows, truncated = self.search_rows()
        if rows is None:
            return
        self._search_rows = {r["id"]: dict(r) for r in rows}
        self.fill_tree(self.s_tree, [
            (r["id"], (r["happened_at"], r["display_name"] or "-", r["user_id"], r["event_type"],
                       r["channel"], r["source"])) for r in rows])
        msg = f"{len(rows)} kayıt gösteriliyor"
        if truncated:
            msg += "  •  " + ("Üye limiti: 50 kayıt (Premium ile sınırsız)" if not self.can_view_unlimited()
                              else "İlk 2000 kayıt gösteriliyor, filtreyi daralt")
        self.s_info.configure(text=msg, text_color=C["warn"] if truncated else C["muted"])
        self.s_detail.configure(text="Listeden bir kayıt seç.")

    def on_search_select(self, _e=None):
        sel = self.s_tree.selection()
        if len(sel) == 1:
            r = self._search_rows.get(int(sel[0]))
            if r:
                self.s_detail.configure(text=f"{r['event_type']}  •  {r['channel'] or 'kanal yok'}\n"
                                             f"{r['details'] or 'Detay girilmemiş.'}")

    def delete_events(self):
        sel = [int(i) for i in self.s_tree.selection()]
        if not sel:
            self.show_toast("Silmek için kayıt seç", False)
            return
        allowed = [i for i in sel if self.is_kurucu() or self._search_rows[i]["owner_id"] == self.current_user["id"]]
        if not allowed:
            self.show_toast("Sadece kendi eklediğin kayıtları silebilirsin", False)
            return
        if self.confirm(f"{len(allowed)} kayıt kalıcı olarak silinsin mi?"):
            self.db.executemany("DELETE FROM events WHERE id=?", [(i,) for i in allowed])
            self.db.commit()
            self.run_search()
            self.show_toast(f"{len(allowed)} kayıt silindi")

    def export_search_csv(self):
        if not self._search_rows:
            self.show_toast("Dışa aktarılacak kayıt yok", False)
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"kayitlar_{date.today().isoformat()}.csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["user_id", "display_name", "event_type", "channel", "details", "happened_at", "source"])
            for r in self._search_rows.values():
                w.writerow([r["user_id"], r["display_name"], r["event_type"], r["channel"],
                            r["details"], r["happened_at"], r["source"]])
        self.show_toast(f"Kaydedildi: {Path(path).name}")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        ok = bad = 0
        owner = self.current_user["id"]
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                heads = {h.strip() for h in (reader.fieldnames or [])}
                if not {"user_id", "event_type", "happened_at"}.issubset(heads):
                    self.show_toast("CSV başlıkları: user_id,event_type,happened_at[,channel,details]", False, 4200)
                    return
                for raw in reader:
                    row = {k.strip(): (v or "").strip() for k, v in raw.items() if k and isinstance(v, (str, type(None)))}
                    uid, when, et = row.get("user_id", ""), row.get("happened_at", ""), row.get("event_type", "")
                    try:
                        parse_dt(when)
                    except ValueError:
                        bad += 1
                        continue
                    if not uid.isdigit() or not et:
                        bad += 1
                        continue
                    self.db.execute("INSERT OR IGNORE INTO staff(user_id,display_name,added_at,owner_id) VALUES(?,?,?,?)",
                                    (uid, "", now_text(), owner))
                    self.db.execute(
                        "INSERT INTO events(user_id,event_type,channel,details,happened_at,source,owner_id) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (uid, et, row.get("channel", ""), row.get("details", ""), when, "CSV içe aktarma", owner))
                    ok += 1
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.show_toast(f"İçe aktarma hatası: {e}", False, 4200)
            return
        self.run_search()
        self.show_toast(f"{ok} kayıt eklendi" + (f", {bad} satır atlandı" if bad else ""), bad == 0, 3600)

    def make_user_report(self):
        sel = self.s_tree.selection()
        uid = self._search_rows[int(sel[0])]["user_id"] if sel else None
        if not uid and self.s_query.get().strip().isdigit():
            uid = self.s_query.get().strip()
        if not uid:
            self.show_toast("Listeden bir kayıt seç ya da ID ara", False)
            return
        rows, truncated = self.search_rows("ASC", force_uid=uid)
        if not rows:
            self.show_toast("Bu kişi için kayıt yok", False)
            return
        note = "Not: Üye hesabı en fazla 50 kayıt görür." if not self.can_view_unlimited() else ""
        text = build_report_text(f"VIGIL KİŞİ RAPORU — {rows[0]['display_name'] or uid} ({uid})", rows, note)
        path = REPORT_DIR / f"kisi_{uid}_{date.today().isoformat()}.txt"
        path.write_text(text, encoding="utf-8")
        self.show_toast(f"Rapor kaydedildi: {path.name}")

    # ============================== RAPORLAR ==============================
    def build_report(self, p):
        top = self.card(p)
        top.pack(fill="x", pady=(0, 10))
        self._section_head(top, "Günlük Rapor", "Bir gün seç, raporu oluştur, TXT ya da CSV olarak indir")
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        nav = ctk.CTkFrame(row, fg_color=C["bg"], corner_radius=8)
        nav.pack(side="left")
        self.button(nav, "◀", lambda: self.shift_report_day(-1), "ghost", 34).pack(side="left", padx=(2, 0), pady=2)
        self.report_date = self.entry(nav, "", 120, justify="center")
        self.report_date.insert(0, date.today().isoformat())
        self.report_date.pack(side="left", padx=4, pady=2)
        self.button(nav, "▶", lambda: self.shift_report_day(1), "ghost", 34).pack(side="left", padx=(0, 2), pady=2)
        self.button(row, "Bugün", lambda: self.set_report_day(date.today()), "ghost", 80).pack(side="left", padx=8)
        self.button(row, "📄  Rapor Oluştur", self.make_report, "primary", 150).pack(side="left", padx=(8, 4))
        self.button(row, "TXT Kaydet", self.save_report, "ghost", 110).pack(side="left", padx=4)
        self.button(row, "CSV Kaydet", self.save_report_csv, "ghost", 110).pack(side="left", padx=4)
        self.report_date.bind("<Return>", lambda e: self.make_report())

        body = self.card(p)
        body.pack(fill="both", expand=True)
        self.report_text = ctk.CTkTextbox(body, font=ctk.CTkFont(family="Consolas", size=12),
                                          fg_color=C["panel"], border_width=0, wrap="word")
        self.report_text.pack(fill="both", expand=True, padx=4, pady=4)
        self._style_report_tags(self.report_text)

    def _style_report_tags(self, box):
        """Rapor metnine görsel hiyerarşi kazandıran etiketler (başlık/bölüm/ayraç/veri)."""
        box.tag_config("h1", foreground=C["gold"])
        box.tag_config("sep", foreground=C.get("border", "#333"))
        box.tag_config("h2", foreground=C["accent_h"])
        box.tag_config("stat", foreground=C["ok"])
        box.tag_config("uid", foreground=C["muted"])
        box.tag_config("empty", foreground=C["muted"])

    def _insert_styled_report(self, box, text):
        box.delete("1.0", "end")
        try:
            lines = text.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if i == 0:
                    tag = "h1"
                elif stripped and set(stripped) in ({"="}, {"-"}):
                    tag = "sep"
                elif stripped.isupper() and stripped and not stripped[0].isdigit():
                    tag = "h2"
                elif stripped.startswith("Toplam kayıt"):
                    tag = "stat"
                elif not stripped:
                    tag = "empty"
                else:
                    tag = None
                start = box.index("end-1c")
                box.insert("end", line + "\n")
                end = box.index("end-1c")
                if tag:
                    box.tag_add(tag, start, end)
        except Exception:
            # Eski customtkinter sürümlerinde tag desteği yoksa sade metne düş
            box.delete("1.0", "end")
            box.insert("1.0", text)

    def set_report_day(self, d):
        self.report_date.delete(0, "end")
        self.report_date.insert(0, d.isoformat())
        self.make_report()

    def shift_report_day(self, delta):
        try:
            d = date.fromisoformat(self.report_date.get().strip())
        except ValueError:
            d = date.today()
        self.set_report_day(d + timedelta(days=delta))

    def make_report(self):
        try:
            day = date.fromisoformat(self.report_date.get().strip())
        except ValueError:
            self.show_toast("Tarih formatı YYYY-AA-GG olmalı", False)
            return False
        oc, op = self.owner_clause("e")
        limit = 5000 if self.can_view_unlimited() else 50
        rows = self.db.execute(
            "SELECT e.*, COALESCE(s.display_name,'') AS display_name FROM events e "
            "LEFT JOIN staff s ON s.user_id=e.user_id WHERE e.happened_at BETWEEN ? AND ?" + oc +
            " ORDER BY e.happened_at LIMIT ?",
            [f"{day} 00:00:00", f"{day} 23:59:59", *op, limit]).fetchall()
        self.report_rows = [dict(r) for r in rows]
        note = "Not: Üye hesabı en fazla 50 kayıt görür." if not self.can_view_unlimited() else ""
        self.current_report = build_report_text(f"VIGIL RAPOR — {day}", rows, note)
        self._insert_styled_report(self.report_text, self.current_report)
        return True

    def save_report(self):
        if not self.make_report():
            return
        if not self.current_report:
            return
        day = self.report_date.get().strip()
        path = REPORT_DIR / f"rapor_{day}.txt"
        path.write_text(self.current_report, encoding="utf-8")
        self.show_toast(f"Kaydedildi: {path.name}")

    def save_report_csv(self):
        if not self.make_report():
            return
        if not self.report_rows:
            self.show_toast("Bu gün için kayıt yok", False)
            return
        path = REPORT_DIR / f"rapor_{self.report_date.get().strip()}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["tarih", "yetkili", "discord_id", "olay", "kanal", "detay", "kaynak"])
            for r in self.report_rows:
                w.writerow([r["happened_at"], r["display_name"], r["user_id"], r["event_type"],
                            r["channel"], r["details"], r["source"]])
        self.show_toast(f"Kaydedildi: {path.name}")

    # ============================== PROFİL ==============================
    def show_profile(self):
        if self.profile_win is not None and self.profile_win.winfo_exists():
            self.profile_win.focus()
            return
        win = ctk.CTkToplevel(self)
        self.profile_win = win
        win.title("Profil Ayarları")
        self.center_window(win, 480, 720)
        self.sfx.play("open")
        win.configure(fg_color=C["bg"])
        win.transient(self)
        win.after(150, lambda: win.winfo_exists() and win.grab_set())

        f = ctk.CTkScrollableFrame(win, fg_color=C["panel"], corner_radius=12)
        f.pack(fill="both", expand=True, padx=14, pady=14)

        self.avatar_widget(f, 96).pack(pady=(14, 6))
        self.button(f, "Resim Seç", lambda: self.change_avatar(win), "ghost", 130).pack()
        badge, color = self.role_badge()
        self.label(f, self.current_user["username"], 18, True).pack(pady=(12, 0))
        self.label(f, badge, 13, color=color).pack()
        until = self.current_user.get("premium_until")
        if self.current_user["role"] == "premium" and until:
            self.label(f, f"Bitiş: {until}  ({self.premium_days_left()} gün)", 12, color=C["muted"]).pack(pady=(2, 0))

        self.label(f, "Ses & Jarvis", 14, True).pack(pady=(22, 6))
        sfx_var = ctk.BooleanVar(value=self.sfx.enabled)
        jv_var = ctk.BooleanVar(value=self.jarvis.enabled)
        ctk.CTkSwitch(f, text="Ses efektleri (tıklama, geçiş)", variable=sfx_var,
                      command=lambda: self.set_pref("sfx", sfx_var.get())).pack(anchor="w", padx=70, pady=4)
        ctk.CTkSwitch(f, text="Jarvis sesli karşılama", variable=jv_var,
                      command=lambda: self.set_pref("jarvis", jv_var.get())).pack(anchor="w", padx=70, pady=4)
        perf_var = ctk.BooleanVar(value=self.perf)
        ctk.CTkSwitch(f, text="Performans modu (animasyonları azalt)", variable=perf_var,
                      command=lambda: self.set_pref("perf", perf_var.get())).pack(anchor="w", padx=70, pady=4)
        self.button(f, "Jarvis'i Test Et", self.test_jarvis, "ghost", 190).pack(pady=8)

        self.label(f, "Sürüm & Güncelleme", 14, True).pack(pady=(22, 4))
        self.label(f, f"Yüklü sürüm: v{CURRENT_VERSION}", 12, color=C["muted"]).pack()
        self.button(f, "Güncellemeleri Denetle", lambda: self.check_updates(manual=True), "ghost", 190).pack(pady=8)

        self.label(f, "Şifre Değiştir", 14, True).pack(pady=(24, 6))
        self.old_pass = self.entry(f, "Mevcut şifre", 280, show="•")
        self.old_pass.pack(pady=4)
        self.new_pass1 = self.entry(f, "Yeni şifre (en az 6)", 280, show="•")
        self.new_pass1.pack(pady=4)
        self.new_pass2 = self.entry(f, "Yeni şifre tekrar", 280, show="•")
        self.new_pass2.pack(pady=4)
        self.button(f, "Şifreyi Güncelle", lambda: self.change_password(win), "ghost", 190).pack(pady=8)

        if not self.is_kurucu():
            self.label(f, "Premium Key", 14, True).pack(pady=(22, 2))
            self.label(f, "Premium: sınırsız kayıt görüntüleme ve tüm kayıtlara erişim", 11,
                       color=C["muted"], wraplength=360).pack()
            self.key_entry = self.entry(f, "XXXX-XXXX-XXXX-XXXX", 280, justify="center")
            self.key_entry.pack(pady=(8, 4))
            self.key_entry.bind("<Return>", lambda e: self.activate_key(win))
            self.key_status = self.label(f, "", 12, wraplength=340)
            self.key_status.pack(pady=2)
            self.button(f, "Key'i Aktifleştir", lambda: self.activate_key(win), "success", 190, 36).pack(pady=8)
        self.button(f, "Kapat", win.destroy, "ghost", 120).pack(pady=(16, 10))

    def change_avatar(self, win):
        path = filedialog.askopenfilename(parent=win, filetypes=[("Resim", "*.png *.jpg *.jpeg *.webp")])
        if not path:
            return
        dest = AVATAR_DIR / f"user_{self.current_user['id']}.png"
        try:
            if Path(path).stat().st_size > 15 * 1024 * 1024:
                self.show_toast("Resim çok büyük (en fazla 15 MB)", False, parent=win)
                return
            img = Image.open(path).convert("RGBA")
            img.thumbnail((256, 256))
            img.save(dest)
            self.db.execute("UPDATE users SET avatar_path=? WHERE id=?", (str(dest), self.current_user["id"]))
            self.db.commit()
            self.current_user["avatar_path"] = str(dest)
            win.destroy()
            self.build_main_ui(self.current_page)
            self.show_toast("Profil resmi güncellendi")
        except Exception:
            self.show_toast("Resim yüklenemedi", False, parent=win)

    def change_password(self, win):
        row = self.db.execute("SELECT * FROM users WHERE id=?", (self.current_user["id"],)).fetchone()
        if not verify_password(self.old_pass.get(), row["password_hash"], row["salt"], row["algo"]):
            self.show_toast("Mevcut şifre yanlış", False, parent=win)
            return
        p1, p2 = self.new_pass1.get(), self.new_pass2.get()
        if len(p1) < 6 or p1 != p2:
            self.show_toast("Şifreler uyuşmuyor veya 6 karakterden kısa", False, parent=win)
            return
        h, s = hash_password(p1)
        self.db.execute("UPDATE users SET password_hash=?, salt=?, algo='pbkdf2' WHERE id=?",
                        (h, s, self.current_user["id"]))
        self.db.commit()
        for e in (self.old_pass, self.new_pass1, self.new_pass2):
            e.delete(0, "end")
        self.show_toast("Şifre başarıyla değiştirildi", parent=win)

    def activate_key(self, win):
        def fail(msg):
            self.key_status.configure(text=msg, text_color=C["bad"])
            self.show_toast(msg, False, parent=win)

        text = self.key_entry.get()
        if not normalize_key(text):
            fail("Önce key'i yaz")
            return
        res = validate_key(text)
        row = None
        if res:
            days, code = res
            row = self.db.execute("SELECT * FROM keys WHERE key_code=?", (code,)).fetchone()
        else:  # eski sürümde üretilmiş (imzasız) key'ler için geri uyumluluk
            raw = normalize_key(text)
            code = format_key(raw) if len(raw) == 16 else None
            row = self.db.execute("SELECT * FROM keys WHERE key_code=?", (code,)).fetchone() if code else None
            if not row:
                fail("Geçersiz key. Harfleri ve rakamları kontrol et.")
                return
            days = row["days"] or 30
        if row and row["used"]:
            fail("Bu key daha önce kullanılmış")
            return
        uid = self.current_user["id"]
        if row:
            cur = self.db.execute("UPDATE keys SET used=1, activated_by=?, activated_at=? WHERE id=? AND used=0",
                                  (uid, now_text(), row["id"]))
            if cur.rowcount == 0:
                fail("Bu key daha önce kullanılmış")
                return
        else:
            self.db.execute("INSERT INTO keys(key_code,created_at,activated_by,activated_at,used,days) "
                            "VALUES(?,?,?,?,1,?)", (code, now_text(), uid, now_text(), days))
        until = self.grant_premium(uid, days)
        self.db.execute("UPDATE keys SET expires_at=? WHERE key_code=?", (until, code))
        self.db.commit()
        self.reload_user()
        win.destroy()
        self.build_main_ui(self.current_page)
        self.show_toast(f"Premium aktif! {days} gün eklendi", duration=3600)

    # ============================== GENEL SOHBET ==============================
    def build_chat(self, p):
        try:
            self._build_chat_inner(p)
        except Exception:
            _log_crash("Sohbet sayfası kurulamadı")
            self.label(p, "Sohbet şu an yüklenemedi. Lütfen tekrar dene.", 12, color=C["bad"]).pack(pady=20)

    def _build_chat_inner(self, p):
        card = self.card(p)
        card.pack(fill="both", expand=True)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 8))
        dot = ctk.CTkFrame(head, width=10, height=10, corner_radius=5, fg_color=C["ok"])
        dot.pack(side="left", padx=(0, 8))
        self.label(head, "Genel Sohbet", 15, True).pack(side="left")
        self.label(head, "·  tüm kullanıcılar görür ve yazabilir", 11,
                   color=C["muted"]).pack(side="left", padx=(8, 0))

        box_wrap = ctk.CTkFrame(card, fg_color=C["bg"], corner_radius=10)
        box_wrap.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.chat_scroll = ctk.CTkScrollableFrame(box_wrap, fg_color="transparent")
        self.chat_scroll.pack(fill="both", expand=True, padx=4, pady=4)
        self.chat_scroll.grid_columnconfigure(0, weight=1)
        self._chat_bubbles = {}
        self._chat_next_row = 1
        self.chat_empty = self.label(self.chat_scroll, "Henüz mesaj yok — ilk mesajı sen yaz.", 12,
                                     color=C["muted"])
        self.chat_empty.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        pill = ctk.CTkFrame(row, fg_color=C["bg"], corner_radius=10)
        pill.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_entry = ctk.CTkEntry(pill, placeholder_text="Mesajını yaz…", fg_color="transparent",
                                       border_width=0)
        self.chat_entry.pack(fill="x", expand=True, padx=10, pady=8)
        self.chat_entry.bind("<Return>", lambda e: self.send_chat_message())
        self.button(row, "Gönder  ➤", self.send_chat_message, "primary", 110).pack(side="left")

    def _chat_role_color(self, role):
        return {"kurucu": C["gold"], "premium": C["ok"]}.get(role, C["accent_h"])

    def refresh_chat(self):
        if not hasattr(self, "chat_scroll"):
            return   # build_chat başarısız olduysa sessizce çık, refresh patlamasın
        try:
            self._refresh_chat_inner()
        except Exception:
            _log_crash("Sohbet yenilenemedi")

    CHAT_LIMIT = 80          # ekranda tutulan en fazla mesaj (eskiden 150 mesaj x ~7 widget her yenilemede yeniden kuruluyordu)
    CHAT_BATCH = 10          # bir seferde en fazla bu kadar baloncuk kur; arayüz donmasın

    def _make_bubble(self, r, row):
        """Hafif tk widget'larıyla baloncuk (CTk widget'ı ~10x daha pahalı)."""
        mine = r["user_id"] == self.current_user["id"]
        bg = C["panel"] if mine else C["panel2"]
        color = self._chat_role_color(r["role"])
        b = tk.Frame(self.chat_scroll, bg=bg, highlightthickness=0, bd=0)
        b.grid(row=row, column=0, sticky="ew", padx=4, pady=3)
        b.grid_columnconfigure(1, weight=1)
        tk.Frame(b, width=3, bg=color, bd=0).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(6, 10), pady=8)
        head = tk.Frame(b, bg=bg, bd=0)
        head.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 0))
        name = r["username"] + (" 👑" if r["role"] == "kurucu" else " ⭐" if r["role"] == "premium" else "")
        tk.Label(head, text=name, bg=bg, fg=color, font=("Segoe UI", 10, "bold"), bd=0).pack(side="left")
        tk.Label(head, text=r["at"], bg=bg, fg=C["muted"], font=("Segoe UI", 8), bd=0).pack(side="left", padx=8)
        if self.is_kurucu():
            tk.Button(head, text="Sil", command=lambda mid=r["id"]: self.delete_chat_message(mid),
                      bg=C["hover"], fg=C["text"], activebackground=C["border"], activeforeground=C["text"],
                      relief="flat", bd=0, padx=8, pady=0, font=("Segoe UI", 8), cursor="hand2").pack(side="right")
        tk.Label(b, text=r["message"], bg=bg, fg=C["text"], font=("Segoe UI", 10), justify="left", anchor="w",
                 wraplength=640, bd=0).grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(2, 8))
        return b

    def _refresh_chat_inner(self):
        """Artımlı yenileme: yalnızca yeni mesajlar eklenir, silinenler/çok eskiler kaldırılır."""
        self._chat_sig_cache = self._chat_sig()
        rows = list(reversed(self.db.execute(
            "SELECT * FROM chat_messages ORDER BY id DESC LIMIT ?", (self.CHAT_LIMIT,)).fetchall()))
        self._chat_render_id = getattr(self, "_chat_render_id", 0) + 1     # süren eski toplu kurulumu iptal eder
        render_id = self._chat_render_id
        keep = {r["id"] for r in rows}
        for mid in [m for m in self._chat_bubbles if m not in keep]:
            try:
                self._chat_bubbles.pop(mid).destroy()
            except Exception:
                pass
        if not rows:
            self.chat_empty.grid(row=0, column=0, sticky="w", padx=10, pady=10)
            return
        self.chat_empty.grid_remove()
        todo = [r for r in rows if r["id"] not in self._chat_bubbles]
        if not todo:
            return
        next_row = getattr(self, "_chat_next_row", 1)
        first_load = not self._chat_bubbles

        def build_batch():
            nonlocal next_row
            if render_id != self._chat_render_id or self._closing:
                return
            try:
                if not self.chat_scroll.winfo_exists():
                    return
            except Exception:
                return
            for r in todo[:self.CHAT_BATCH]:
                if r["id"] in self._chat_bubbles:
                    continue
                self._chat_bubbles[r["id"]] = self._make_bubble(r, next_row)
                next_row += 1
            del todo[:self.CHAT_BATCH]
            self._chat_next_row = next_row
            if todo:
                self.after(1, build_batch)
            else:
                self.after(30, self._chat_scroll_bottom)

        build_batch()

    def _chat_scroll_bottom(self):
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def send_chat_message(self):
        text = self.chat_entry.get().strip()
        if not text:
            return
        if len(text) > 500:
            self.show_toast("Mesaj çok uzun (en fazla 500 karakter)", False)
            return
        self.db.execute(
            "INSERT INTO chat_messages(user_id, username, role, message, at) VALUES(?,?,?,?,?)",
            (self.current_user["id"], self.current_user["username"], self.current_user["role"], text, now_text()))
        self.db.commit()
        self.chat_entry.delete(0, "end")
        self.refresh_chat()

    def delete_chat_message(self, message_id):
        if not self.is_kurucu():
            return
        if not self.confirm("Bu mesaj silinsin mi?"):
            return
        self.db.execute("DELETE FROM chat_messages WHERE id=?", (message_id,))
        self.db.commit()
        self.refresh_chat()
        self.show_toast("Mesaj silindi")

    # ============================== KURUCU PANELİ ==============================
    def build_admin(self, p):
        if not self.is_kurucu():
            return
        p.grid_columnconfigure((0, 1), weight=1, uniform="a")
        p.grid_rowconfigure(0, weight=1)
        p.grid_rowconfigure(1, weight=0)

        kf = self.card(p)
        kf.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.label(kf, "Premium Key Üret", 15, True).pack(anchor="w", padx=16, pady=(14, 6))
        r = ctk.CTkFrame(kf, fg_color="transparent")
        r.pack(fill="x", padx=14, pady=4)
        self.key_days = ctk.CTkComboBox(r, values=["7 gün", "30 gün", "90 gün", "365 gün"], width=120,
                                        state="readonly", fg_color=C["bg"], border_color=C["border"])
        self.key_days.set("30 gün")
        self.key_days.pack(side="left")
        self.key_count = ctk.CTkComboBox(r, values=["1", "5", "10"], width=70, state="readonly",
                                         fg_color=C["bg"], border_color=C["border"])
        self.key_count.set("1")
        self.key_count.pack(side="left", padx=8)
        self.button(r, "Oluştur", self.create_keys, "primary", 90).pack(side="left")
        self.button(r, "Kopyala", self.copy_selected_key, "ghost", 80).pack(side="left", padx=6)
        w, self.key_tree = self.make_tree(kf, [("k", "Key", 170), ("d", "Süre", 60), ("s", "Durum", 80),
                                               ("u", "Kullanan", 100)], 12)
        w.pack(fill="both", expand=True, padx=12, pady=(8, 8))
        self.label(kf, "Key imzalıdır: başka bilgisayarda da doğrulanır.\nSınırsız tek kullanım için sunucu gerekir.",
                   11, color=C["muted"], justify="left").pack(anchor="w", padx=16, pady=(0, 12))

        uf = self.card(p)
        uf.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.label(uf, "Hesaplar", 15, True).pack(anchor="w", padx=16, pady=(14, 6))
        r2 = ctk.CTkFrame(uf, fg_color="transparent")
        r2.pack(fill="x", padx=14, pady=4)
        self.grant_days = ctk.CTkComboBox(r2, values=["7 gün", "30 gün", "90 gün", "365 gün"], width=100,
                                          state="readonly", fg_color=C["bg"], border_color=C["border"])
        self.grant_days.set("30 gün")
        self.grant_days.pack(side="left")
        self.button(r2, "Premium Ver", self.admin_grant, "success", 100).pack(side="left", padx=6)
        self.button(r2, "Premium Al", self.admin_revoke, "ghost", 90).pack(side="left")
        r3 = ctk.CTkFrame(uf, fg_color="transparent")
        r3.pack(fill="x", padx=14, pady=(2, 4))
        self.button(r3, "Şifre Sıfırla", self.admin_reset_pw, "ghost", 110).pack(side="left")
        self.button(r3, "Hesabı Sil", self.admin_delete, "danger", 100).pack(side="left", padx=6)
        r4 = ctk.CTkFrame(uf, fg_color="transparent")
        r4.pack(fill="x", padx=14, pady=(0, 4))
        self.button(r4, "Askıya Al", self.admin_ban, "danger", 105).pack(side="left")
        self.button(r4, "Askıyı Kaldır", self.admin_unban, "success", 120).pack(side="left", padx=6)
        w2, self.user_tree = self.make_tree(uf, [("i", "ID", 40), ("u", "Kullanıcı", 100), ("r", "Rol", 65),
                                                 ("s", "Durum", 70), ("p", "Premium bitiş", 130)], 12)
        self.user_tree.tag_configure("kurucu", foreground=C["gold"])
        self.user_tree.tag_configure("premium", foreground=C["ok"])
        self.user_tree.tag_configure("banned", foreground=C["bad"])
        w2.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        sf = self.card(p)
        sf.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(10, 0))
        self.label(sf, "Key İmza Anahtarı", 14, True).pack(anchor="w", padx=16, pady=(12, 2))
        self.label(sf, "Premium key'ler bu gizli değerle imzalanır. Değiştirirsen, daha önce üretilip "
                       "henüz kullanılmamış tüm key'ler geçersiz olur.", 11, color=C["muted"],
                   justify="left", wraplength=900).pack(anchor="w", padx=16, pady=(0, 6))
        kr = ctk.CTkFrame(sf, fg_color="transparent")
        kr.pack(fill="x", padx=16, pady=(0, 14))
        self.key_secret_label = self.label(kr, self._masked_key_secret(), 13, color=C["accent_h"])
        self.key_secret_label.pack(side="left", padx=(0, 10))
        self.button(kr, "Yeni Anahtar Oluştur", self.regenerate_key_secret, "gold", 160).pack(side="left")
        self.button(kr, "Özel Anahtar Gir", self.set_custom_key_secret, "ghost", 140).pack(side="left", padx=6)

    def refresh_admin(self):
        if not self.is_kurucu():
            return
        rows = self.db.execute(
            "SELECT k.*, u.username FROM keys k LEFT JOIN users u ON u.id=k.activated_by "
            "ORDER BY k.id DESC LIMIT 100").fetchall()
        self.fill_tree(self.key_tree, [
            (r["key_code"], (r["key_code"], f"{r['days']}g", "KULLANILDI" if r["used"] else "AKTİF",
                             r["username"] or "-")) for r in rows])
        users = self.db.execute("SELECT id, username, role, premium_until, banned FROM users ORDER BY id").fetchall()
        self.fill_tree(self.user_tree, [
            (r["id"], (r["id"], r["username"], r["role"], "Askıda" if r["banned"] else "Aktif",
                       r["premium_until"] or "-"),
             ("banned",) if r["banned"] else ((r["role"],) if r["role"] in ("kurucu", "premium") else ()))
            for r in users])

    # ---- imza anahtarı (key secret) işlemleri
    def _masked_key_secret(self):
        s = KEY_SECRET.decode(errors="replace")
        if len(s) <= 6:
            return "Mevcut anahtar: " + "•" * len(s)
        return f"Mevcut anahtar: {s[:3]}{'•' * (len(s) - 6)}{s[-3:]}"

    def regenerate_key_secret(self):
        if not self.is_kurucu():
            return
        if not self.confirm("Yeni bir imza anahtarı oluşturulsun mu?\n"
                            "Henüz kullanılmamış tüm key'ler bundan sonra geçersiz olur."):
            return
        new_secret = secrets.token_urlsafe(24)
        set_key_secret(new_secret, self.settings)
        self.key_secret_label.configure(text=self._masked_key_secret())
        self.show_toast("Yeni imza anahtarı oluşturuldu")

    def set_custom_key_secret(self):
        if not self.is_kurucu():
            return
        val = self.ask_text("Yeni imza anahtarını gir (en az 12 karakter):", "Özel İmza Anahtarı")
        if val is None:
            return
        if len(val) < 12:
            self.show_toast("Anahtar en az 12 karakter olmalı", False)
            return
        if not self.confirm("Bu anahtar kaydedilsin mi?\n"
                            "Henüz kullanılmamış tüm key'ler bundan sonra geçersiz olur."):
            return
        set_key_secret(val, self.settings)
        self.key_secret_label.configure(text=self._masked_key_secret())
        self.show_toast("İmza anahtarı güncellendi")

    def _days(self, combo):
        return int(combo.get().split()[0])

    def create_keys(self):
        days, n = self._days(self.key_days), int(self.key_count.get())
        made = []
        for _ in range(n):
            code = generate_key(days)
            self.db.execute("INSERT OR IGNORE INTO keys(key_code,created_at,days) VALUES(?,?,?)",
                            (code, now_text(), days))
            made.append(code)
        self.db.commit()
        self.clipboard_clear()
        self.clipboard_append("\n".join(made))
        self.refresh_admin()
        self.show_toast(f"{n} key oluşturuldu ve kopyalandı" if n > 1 else f"Key kopyalandı: {made[0]}")

    def copy_selected_key(self):
        sel = self.key_tree.selection()
        if not sel:
            self.show_toast("Listeden bir key seç", False)
            return
        self.clipboard_clear()
        self.clipboard_append(sel[0])
        self.show_toast("Key kopyalandı")

    def _selected_user(self):
        sel = self.user_tree.selection()
        if not sel:
            self.show_toast("Listeden bir hesap seç", False)
            return None
        return self.db.execute("SELECT * FROM users WHERE id=?", (int(sel[0]),)).fetchone()

    def admin_grant(self):
        u = self._selected_user()
        if not u:
            return
        if u["role"] == "kurucu":
            self.show_toast("Kurucuya premium verilmez", False)
            return
        days = self._days(self.grant_days)
        self.grant_premium(u["id"], days)
        self.refresh_admin()
        self.show_toast(f"{u['username']} → +{days} gün premium")

    def admin_revoke(self):
        u = self._selected_user()
        if not u or u["role"] == "kurucu":
            return
        self.db.execute("UPDATE users SET role='uye', premium_until=NULL WHERE id=?", (u["id"],))
        self.db.commit()
        self.refresh_admin()
        self.show_toast(f"{u['username']} premium kaldırıldı")

    def admin_ban(self):
        u = self._selected_user()
        if not u:
            return
        if u["role"] == "kurucu":
            self.show_toast("Kurucu hesabı askıya alınamaz", False)
            return
        if u["id"] == self.current_user["id"]:
            self.show_toast("Kendini askıya alamazsın", False)
            return
        if u["banned"]:
            self.show_toast(f"{u['username']} zaten askıda", False)
            return
        reason = self.ask_text("Askıya alma gerekçesi (opsiyonel):", f"'{u['username']}' askıya alınsın mı?")
        if reason is None:
            return
        if not self.confirm(f"'{u['username']}' askıya alınsın mı?\nHesap giriş yapamaz hale gelecek."):
            return
        self.db.execute("UPDATE users SET banned=1, ban_reason=? WHERE id=?", (reason, u["id"]))
        self.db.commit()
        self.refresh_admin()
        self.show_toast(f"{u['username']} askıya alındı")

    def admin_unban(self):
        u = self._selected_user()
        if not u:
            return
        if not u["banned"]:
            self.show_toast(f"{u['username']} zaten aktif", False)
            return
        self.db.execute("UPDATE users SET banned=0, ban_reason='' WHERE id=?", (u["id"],))
        self.db.commit()
        self.refresh_admin()
        self.show_toast(f"{u['username']} tekrar aktif")

    def admin_reset_pw(self):
        u = self._selected_user()
        if not u:
            return
        temp = secrets.token_urlsafe(6)
        h, s = hash_password(temp)
        self.db.execute("UPDATE users SET password_hash=?, salt=?, algo='pbkdf2' WHERE id=?", (h, s, u["id"]))
        self.db.commit()
        self.clipboard_clear()
        self.clipboard_append(temp)
        self.show_toast(f"{u['username']} yeni şifre (kopyalandı): {temp}", duration=6000)

    def admin_delete(self):
        u = self._selected_user()
        if not u:
            return
        if u["role"] == "kurucu" or u["id"] == self.current_user["id"]:
            self.show_toast("Kurucu hesabı silinemez", False)
            return
        if self.confirm(f"'{u['username']}' hesabı silinsin mi?"):
            # silinen hesabın kayıtları kurucuya devredilir (sahipsiz kalmasın)
            self.db.execute("UPDATE events SET owner_id=? WHERE owner_id=?", (self.current_user["id"], u["id"]))
            self.db.execute("UPDATE staff SET owner_id=? WHERE owner_id=?", (self.current_user["id"], u["id"]))
            self.db.execute("DELETE FROM users WHERE id=?", (u["id"],))
            self.db.commit()
            self.refresh_admin()
            self.show_toast("Hesap silindi")

    # ============================== KAPANIŞ ==============================
    def report_callback_exception(self, exc, val, tb):
        _log_crash("Arayüz hatası")
        try:
            self.show_toast(f"Hata: {val}", False, 5000)
        except Exception:
            pass

    def on_closing(self):
        self._closing = True
        try:
            self.db.execute("PRAGMA optimize")
        except Exception:
            pass
        self.stop_stars()
        for job in (getattr(self, "_clock_job", None), getattr(self, "_chat_job", None)):
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        try:
            self.db.close()
        finally:
            self.destroy()


_CONSOLE_HIDDEN = False


def _hide_console():
    """python.exe ile açılınca arkada kalan siyah CMD penceresini gizler.
    Hata ayıklamak için:  python real_panel.py --console"""
    global _CONSOLE_HIDDEN
    if os.name != "nt" or "--console" in sys.argv:
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE
            _CONSOLE_HIDDEN = True
    except Exception:
        pass


def main():
    _hide_console()
    app = VigilApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log_crash("Başlangıç hatası")
        try:                                   # güncelleme sonrası ilk açılış çöktüyse eski sürüme dön
            _pend = json.loads(PENDING_FILE.read_text(encoding="utf-8")) if PENDING_FILE.exists() else {}
            if _pend and Updater.rollback_if_needed():
                Updater(UPDATE_URL).relaunch(Path(_pend["target"]))
                sys.exit(0)
        except SystemExit:
            raise
        except Exception:
            _log_crash("Geri alma hatası")
        if not _CONSOLE_HIDDEN and sys.stdin is not None and sys.stdout is not None:
            try:
                traceback.print_exc()
                print(f"\nHata kaydedildi: {_LOG}")
                input("Kapatmak için Enter'a bas...")
            except Exception:
                pass
        else:  # konsolsuz exe: hatayı pencerede göster
            try:
                from tkinter import messagebox
                messagebox.showerror("VIGIL - Hata", f"Program başlatılamadı.\n\nDetay: {_LOG}")
            except Exception:
                pass
