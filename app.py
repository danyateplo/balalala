import os
import asyncio
import logging
from flask import Flask, request, render_template, Response, stream_with_context
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='.')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Используем новейшую модель 2.0 Flash
    model = genai.GenerativeModel('gemini-2.0-flash')

ptb_application = None

async def get_ptb_application():
    global ptb_application
    if ptb_application is None:
        ptb_application = Application.builder().token(TELEGRAM_TOKEN).build()
        await ptb_application.initialize()
        ptb_application.add_handler(CommandHandler("start", start_command))
        await ptb_application.start()
    return ptb_application

async def start_command(update: Update, context):
    if not WEBAPP_URL:
        await update.message.reply_text("Ошибка: WEBAPP_URL не задан.")
        return
    keyboard = [[InlineKeyboardButton("✨ Открыть Gemini 2.0", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text("Нажми кнопку, чтобы войти в чат:", reply_markup=InlineKeyboardMarkup(keyboard))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    async def process():
        ptb = await get_ptb_application()
        update = Update.de_json(request.get_json(force=True), ptb.bot)
        await ptb.process_update(update)
    asyncio.run(process())
    return "OK"

@app.route('/set_webhook')
def set_webhook_route():
    async def set_hook():
        ptb = await get_ptb_application()
        await ptb.bot.set_webhook(f"{WEBAPP_URL}/webhook")
        return "Webhook set!"
    return asyncio.run(set_hook())

@app.route('/api/chat', methods=['POST'])
def chat_api():
    user_msg = request.form.get('message', '')
    img_file = request.files.get('image')
    parts = []
    if user_msg: parts.append(user_msg)
    if img_file:
        img = Image.open(io.BytesIO(img_file.read()))
        parts.append(img)

    def generate():
        try:
            response = model.generate_content(parts, stream=True)
            for chunk in response:
                if chunk.text: yield chunk.text
        except Exception as e:
            yield f"Ошибка: {str(e)}"

    return Response(stream_with_context(generate()), content_type='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
