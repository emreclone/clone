import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InputMediaPhoto
from tqdm.asyncio import tqdm

API_TOKEN = "1527359681:AAHQDMnmPpDPdnSJe3oIHg6BOy9Tngjm6E8"
CHANNEL_ID = "@sikayetimvar2"
BASE_URL = "https://www.sikayetvar.com/casino"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

def load_sent_ids():
    try:
        with open("sent_ids.txt", "r", encoding="utf-8") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

def save_sent_id(complaint_id):
    with open("sent_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{complaint_id}\n")

async def get_complaints_page(session, page=1):
    url = f"{BASE_URL}?page={page}"
    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
        text = await resp.text()
        soup = BeautifulSoup(text, 'html.parser')
        complaints = []

        cards = soup.select("article.card-v2.ga-v.ga-c")
        for card in cards:
            site_tag = card.select_one(".company-name a")
            site = site_tag.get_text(strip=True) if site_tag else "Bilinmiyor"

            title_tag = card.select_one("h2.complaint-title a")
            title = title_tag.get_text(strip=True) if title_tag else "Başlık Yok"

            link = title_tag['href'] if title_tag else None
            if link and not link.startswith("http"):
                link = "https://www.sikayetvar.com" + link

            complaint_id = card.get('data-id')

            complaints.append({
                "id": complaint_id,
                "site": site,
                "title": title,
                "url": link
            })
        return complaints

async def get_complaint_details(session, url):
    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
        text = await resp.text()
        soup = BeautifulSoup(text, 'html.parser')

        text_tag = soup.select_one("div.complaint-detail-description")
        if text_tag:
            text = text_tag.get_text(separator="\n", strip=True)
        else:
            text = "Metin bulunamadı."

        text = re.sub(r"🔗\s*Detaylı Göster.*", "", text, flags=re.DOTALL)

        photos = []
        attachments_div = soup.select_one("div.complaint-attachments-container")
        if attachments_div:
            imgs = attachments_div.select("img")
            for img in imgs:
                src = img.get("src")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    photos.append(src)

        return {"text": text, "photos": photos}

async def send_complaint(complaint, session):
    site = complaint["site"]
    title = complaint["title"]
    url = complaint["url"]

    details = await get_complaint_details(session, url)
    text = details["text"]
    photos = details["photos"]

    message_text = (
        f"<b>📌 YENİ ŞİKAYET!</b>\n"
        f"🏷️ <b>Site:</b> {site}\n\n"
        f"📝 <b>Başlık:</b> {title}\n\n"
        f"{text}\n\n"
        f"👑 <b>Şikayet İçin Ulaşım:</b> <a href='http://t.me/Sikayet_destekk_bot'>Buraya Tıkla</a>\n"
        f"🏦 <b>Güvenilir Siteler:</b> <a href='https://heylink.me/CAS%C4%B0NOOK/'>heylink.me/CASİNOOK</a>"
    )

    for attempt in range(3):
        try:
            if photos:
                media = [InputMediaPhoto(media=photos[0], caption=message_text, parse_mode='HTML')]
                for p in photos[1:]:
                    media.append(InputMediaPhoto(media=p))
                await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
            else:
                await bot.send_message(chat_id=CHANNEL_ID, text=message_text, disable_web_page_preview=True)

            print(f"✅ Şikayet gönderildi: {title}")
            return True
        except Exception as e:
            print(f"⚠️ Hata ({attempt + 1}/3): {e}")
            await asyncio.sleep(2)
    print(f"❌ Şikayet 3 kez denenmesine rağmen gönderilemedi: {title}")
    return False

async def countdown(seconds):
    print(f"\n⏳ Geri sayım başlatıldı: {seconds // 60} dakika\n")
    async for i in tqdm(range(seconds), desc="⏳ Bekleme Süresi", ncols=100):
        remaining = seconds - i
        mins, secs = divmod(remaining, 60)
        print(f"⏱ Kalan: {mins:02}:{secs:02}", end="\r")
        await asyncio.sleep(1)
    print("\n🟢 Bekleme süresi sona erdi.\n")

async def main():
    last_sent_ids = load_sent_ids()
    page = 1
    async with aiohttp.ClientSession() as session:
        while True:
            complaints = await get_complaints_page(session, page)
            if not complaints:
                print("Yeni şikayet bulunamadı. Diğer sayfaya geçiliyor.")
                page += 1
                if page > 100:
                    page = 1
                await asyncio.sleep(10)
                continue

            for complaint in complaints:
                if complaint["id"] not in last_sent_ids:
                    if re.search(r'casino|bahis|bet', complaint["site"], re.I):
                        success = await send_complaint(complaint, session)
                        if success:
                            last_sent_ids.add(complaint["id"])
                            save_sent_id(complaint["id"])
                            await countdown(3600)  # sadece başarılı paylaşım sonrası 1 saat bekle
                            break  # döngüyü kırıp baştan başla
            else:
                print("Yeni uygun şikayet bulunamadı. Sayfa artırılıyor.")
                page += 1
                if page > 100:
                    page = 1

if __name__ == "__main__":
    asyncio.run(main())
