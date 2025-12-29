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

# Настройки из Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Если ошибка 429 повторяется, замени на 'gemini-1.5-flash'
    model = genai.GenerativeModel('models/gemini-2.5-flash')

ptb_app = None

async def init_bot():
    global ptb_app
    if ptb_app is None:
        ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()
        await ptb_app.initialize()
        ptb_app.add_handler(CommandHandler("start", start))
        await ptb_app.start()
    return ptb_app

async def start(update: Update, context):
    kbd = [[InlineKeyboardButton("✨ Gemini 2.0 Chat", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text("Бот готов! Нажми на кнопку ниже:", reply_markup=InlineKeyboardMarkup(kbd))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    async def task():
        bot = await init_bot()
        update = Update.de_json(request.get_json(force=True), bot.bot)
        await bot.process_update(update)
    asyncio.run(task())
    return "OK"

@app.route('/set_webhook')
def set_webhook():
    async def task():
        bot = await init_bot()
        await bot.bot.set_webhook(f"{WEBAPP_URL}/webhook")
        return "✅ Webhook set successfully!"
    return asyncio.run(task())

@app.route('/api/chat', methods=['POST'])
def chat():
    msg = request.form.get('message', '')
    file = request.files.get('image')
    content = []
    if msg: content.append(msg)
    if file:
        img = Image.open(io.BytesIO(file.read()))
        content.append(img)

    def generate():
        try:
            response = model.generate_content(content, stream=True)
            for chunk in response:
                if chunk.text: yield chunk.text
        except Exception as e:
            yield f"⚠️ Ошибка API: {str(e)}"

    return Response(stream_with_context(generate()), content_type='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
