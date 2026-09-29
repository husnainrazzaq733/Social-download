import os
import logging
import requests
import yt_dlp
import urllib.parse
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = '8085538707:AAG5m1nEl9-R1zUaG2zfjUQN-CGGXVj6DBs'
RAPIDAPI_KEY = '283f9eaddemsh86867cf21914b8fp1bb4d5jsn753539406598'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- DUMMY WEB SERVER FOR RENDER ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Bot is running!"

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# -----------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Assalam o Alaikum! Mujhe kisi bhi social media video ya photo ka link bhejein, aur main use download karke dunga.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Bus link paste karein aur bhejein.')

def download_instagram_rapidapi(url):
    host = 'instagram-reels-downloader-api.p.rapidapi.com'
    headers = {
        'x-rapidapi-host': host,
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    encoded_url = urllib.parse.quote(url)
    api_url = f'https://{host}/download?url={encoded_url}'
    
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            medias = data.get('data', {}).get('medias', [])
            media_list = []
            for media in medias:
                m_url = media.get('url')
                m_type = media.get('type')
                if m_url and m_type in ['video', 'image']:
                    media_list.append((m_url, m_type))
            return media_list
    return []

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text
    chat_id = update.message.chat_id
    
    status_msg = await update.message.reply_text('Processing your link... Please wait.')

    try:
        if 'instagram.com' in url:
            media_items = download_instagram_rapidapi(url)
            if media_items:
                await status_msg.edit_text('Uploading Instagram Media...')
                for m_url, m_type in media_items:
                    if m_type == 'video':
                        await context.bot.send_video(chat_id=chat_id, video=m_url)
                    else:
                        await context.bot.send_photo(chat_id=chat_id, photo=m_url)
                await status_msg.delete()
                return

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'downloads/{chat_id}_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
        }

        os.makedirs('downloads', exist_ok=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            await status_msg.edit_text('Uploading to Telegram...')
            with open(filename, 'rb') as file:
                await context.bot.send_video(chat_id=chat_id, video=file, supports_streaming=True)
            
            os.remove(filename)
            await status_msg.delete()
            
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        await status_msg.edit_text(f"Sorry, an error occurred: {str(e)}\n\n(Aksar Instagram/Facebook par login issue hota hai, ya phir link invalid hai)")

def main() -> None:
    # Start the dummy web server in a background thread
    server_thread = threading.Thread(target=run_dummy_server)
    server_thread.daemon = True
    server_thread.start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
