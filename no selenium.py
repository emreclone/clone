import os
import re
import json
import time
import asyncio
import requests
from datetime import datetime
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# === AYARLAR ===
ANNOUNCE_CHANNEL = "https://t.me/ustaslot"
POSTED_LOG_FILE = "posted_log.json"

# === GİRİŞ BİLGİLERİ ===
if not os.path.exists("config.txt"):
    print("HATA: config.txt dosyası eksik!")
    input("Kapatmak için Enter tuşuna bas...")
    exit()

try:
    with open("config.txt", "r") as f:
        api_id, api_hash, phone = f.read().strip().split(',')
except:
    print("HATA: config.txt içeriği hatalı. Format: 123456,api_hash,+905xxxxxxxxx")
    input("Kapatmak için Enter tuşuna bas...")
    exit()

session = phone.replace('+', '').replace(' ', '')
client = TelegramClient(session, int(api_id), api_hash)

# === KAYITLAR ===
posted_keys = set()
lock = asyncio.Lock()

if os.path.exists(POSTED_LOG_FILE):
    with open(POSTED_LOG_FILE, "r", encoding="utf-8") as f:
        try:
            log_data = json.load(f)
            for entry in log_data:
                posted_keys.add(entry["key"])
        except json.JSONDecodeError:
            log_data = []
else:
    log_data = []

# === MESAJ FORMATLAYICI ===
def format_message(link, code):
    return (
        f"\U0001F9FE Kod: <code>{code}</code>\n"
        f"\U0001F517 Link: {link}\n\n"
        f"\U0001F451 <a href='https://t.me/ustaslot'>Usta Slot & Kod Kanal</a>\n"
        f"\U0001F48D <a href='https://t.me/sikayetimvar2'>Şikayetim Var</a>\n"
        f"\U0001F3F9 <a href='https://t.me/OKCASINOO'>Slot Ve Nakit Ödül</a>\n"
        f"\U0001F3E6 <a href='https://heylink.me/CAS%C4%B0NOOK/'>Güvenilir Siteler</a>"
    )

# === GEÇERLİ MESAJ KONTROLÜ ===
def is_valid_message(text, message):
    link_match = re.search(r'https?://[^\s]+', text)
    lines = text.strip().split('\n')
    code_candidate = next((line.strip() for line in lines if re.fullmatch(r'[A-Za-z0-9\-]{4,20}', line.strip())), None)
    has_media = isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument))
    return link_match and code_candidate and not has_media

# === MESAJ İŞLEYİCİ ===
async def process_message(text):
    lines = text.strip().split('\n')
    code = next((line.strip() for line in lines if re.fullmatch(r'[A-Za-z0-9\-]{4,20}', line.strip())), None)
    link = next((l.strip() for l in lines if 'http' in l), None)
    if not code or not link:
        return

    key = f"{code.lower()}|{link.lower()}"

    async with lock:
        if key in posted_keys:
            print(f"[!] Daha önce paylaşıldı: {key}")
            return

        sent = await client.send_message(ANNOUNCE_CHANNEL, text)
        print(f"[→] Paylaşıldı: {key}")

        posted_keys.add(key)
        log_data.append({
            "key": key,
            "timestamp": datetime.now().isoformat(),
            "raw_message": text,
            "message_id": sent.id,
            "channel_id": sent.peer_id.channel_id
        })

        with open(POSTED_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    try:
        await asyncio.sleep(1)
        formatted = format_message(link, code)
        await sent.edit(formatted, parse_mode='html', link_preview=False)
        print(f"[✓] Formatlı şekilde güncellendi.")
    except Exception as e:
        print(f"[X] Güncelleme hatası: {e}")

# === YENİ MESAJ DİNLER ===
@client.on(events.NewMessage)
async def handler_new(event):
    if is_valid_message(event.raw_text, event.message):
        await process_message(event.raw_text)

# === ANA FONKSİYON ===
async def main():
    try:
        await client.start(phone)
    except SessionPasswordNeededError:
        password = input("Telegram şifreniz (2FA): ")
        await client.sign_in(password=password)

    print(f"[✓] Giriş yapıldı: {phone}")

    if not os.path.exists("groups.txt"):
        print("HATA: groups.txt bulunamadı!")
        input("Enter ile kapat...")
        exit()

    with open("groups.txt", "r") as f:
        groups = [line.strip() for line in f if line.strip()]

    for group in groups:
        try:
            await client.get_entity(group)
            print(f"[+] Dinleniyor: {group}")
        except Exception as e:
            print(f"[!] Grup alınamadı: {group} → {e}")

    print("🟢 Bot aktif. Mesajlar dinleniyor...")
    await client.run_until_disconnected()

# === BAŞLAT ===
asyncio.run(main())
