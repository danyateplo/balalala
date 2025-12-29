import os
import asyncio
import logging
from flask import Flask, request, render_template, Response, stream_with_context
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler
from PIL import Image
import io

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ВАЖНО: template_folder='.' заставляет Flask искать HTML прямо здесь, без папок
app = Flask(__name__, template_folder='.')

# --- КОНФИГУРАЦИЯ ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# URL твоего приложения на Render (без слэша в конце). Пример: https://my-app.onrender.com
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Настройка Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# Ленивая инициализация бота
ptb_application = None

async def get_ptb_application():
    global ptb_application
    if ptb_application is None:
        ptb_application = Application.builder().token(TELEGRAM_TOKEN).build()
        await ptb_application.initialize()
        ptb_application.add_handler(CommandHandler("start", start_command))
        await ptb_application.start()
    return ptb_application

# --- ЛОГИКА БОТА ---
async def start_command(update: Update, context):
    if not WEBAPP_URL:
        await update.message.reply_text("Ошибка: WEBAPP_URL не задан в настройках Render.")
        return
    
    keyboard = [[InlineKeyboardButton("💬 Открыть чат", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        "Нажми кнопку, чтобы открыть чат с Gemini AI 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- ROUTES ---

@app.route('/')
def index():
    """Отдает HTML страницу"""
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Принимает сообщения от Telegram"""
    if not TELEGRAM_TOKEN: return "No Token", 500
    async def process():
        ptb = await get_ptb_application()
        update = Update.de_json(request.get_json(force=True), ptb.bot)
        await ptb.process_update(update)
    asyncio.run(process())
    return "OK"

@app.route('/set_webhook', methods=['GET'])
def set_webhook_route():
    """Автоматическая установка вебхука (просто открой эту ссылку)"""
    if not WEBAPP_URL or not TELEGRAM_TOKEN:
        return "Ошибка: Не заданы WEBAPP_URL или TELEGRAM_TOKEN", 400
    
    webhook_url = f"{WEBAPP_URL}/webhook"
    
    async def set_hook():
        ptb = await get_ptb_application()
        await ptb.bot.set_webhook(webhook_url)
        return f"Webhook успешно установлен на: {webhook_url}"
    
    try:
        result = asyncio.run(set_hook())
        return result
    except Exception as e:
        return f"Ошибка установки вебхука: {e}"

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Обработка запроса к Gemini"""
    user_msg = request.form.get('message', '')
    img_file = request.files.get('image')
    
    parts = []
    if user_msg: parts.append(user_msg)
    if img_file:
        img = Image.open(io.BytesIO(img_file.read()))
        parts.append(img)

    if not parts: return "Empty", 400

    def generate():
        try:
            response = model.generate_content(parts, stream=True)
            for chunk in response:
                if chunk.text: yield chunk.text
        except Exception as e:
            yield f"Error: {str(e)}"

    return Response(stream_with_context(generate()), content_type='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)