import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiohttp
import html

# ===== CONFIGURATION =====
TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
DEFAULT_LANG = "en"

# ===== LOGGING SETUP =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== TOKEN VALIDATION =====
if not TOKEN:
    logger.error("❌ NO TOKEN FOUND! Please set TELEGRAM_TOKEN environment variable.")
    exit(1)

logger.info(f"✅ Token loaded successfully! First 10 chars: {TOKEN[:10]}...")

# ===== TRANSLATION ENGINES =====
# Google Translate API (free, no key needed for basic use)
# For production, consider using DeepL API [citation:12]

async def translate_google(text, target_lang, source_lang="auto"):
    """Translate using Google Translate API"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0 and data[0]:
                        translated = ""
                        for item in data[0]:
                            if item and len(item) > 0:
                                translated += item[0]
                        return translated
                return None
    except Exception as e:
        logger.error(f"Google Translate error: {str(e)}")
        return None

async def translate_libretranslate(text, target_lang, source_lang="auto"):
    """Translate using LibreTranslate (free, open source)"""
    try:
        url = "https://libretranslate.com/translate"
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("translatedText")
                return None
    except Exception as e:
        logger.error(f"LibreTranslate error: {str(e)}")
        return None

async def translate_text(text, target_lang, source_lang="auto"):
    """Translate text with fallback engines"""
    # Try Google Translate first
    result = await translate_google(text, target_lang, source_lang)
    if result:
        return result, "Google Translate"
    
    # Fallback to LibreTranslate
    result = await translate_libretranslate(text, target_lang, source_lang)
    if result:
        return result, "LibreTranslate"
    
    return None, None

# ===== LANGUAGE SUPPORT =====
# Supported languages with their names and emoji flags [citation:5]
LANGUAGES = {
    "en": {"name": "English", "flag": "🇺🇸"},
    "es": {"name": "Spanish", "flag": "🇪🇸"},
    "fr": {"name": "French", "flag": "🇫🇷"},
    "de": {"name": "German", "flag": "🇩🇪"},
    "it": {"name": "Italian", "flag": "🇮🇹"},
    "pt": {"name": "Portuguese", "flag": "🇵🇹"},
    "ru": {"name": "Russian", "flag": "🇷🇺"},
    "ja": {"name": "Japanese", "flag": "🇯🇵"},
    "ko": {"name": "Korean", "flag": "🇰🇷"},
    "zh": {"name": "Chinese", "flag": "🇨🇳"},
    "ar": {"name": "Arabic", "flag": "🇸🇦"},
    "hi": {"name": "Hindi", "flag": "🇮🇳"},
    "tr": {"name": "Turkish", "flag": "🇹🇷"},
    "nl": {"name": "Dutch", "flag": "🇳🇱"},
    "id": {"name": "Indonesian", "flag": "🇮🇩"}
}

def detect_language_code(text):
    """Simple language detection based on common patterns"""
    # This is a basic detection - for production, use langdetect or similar
    text_lower = text.lower()
    
    # Check for common patterns
    if any(c in text_lower for c in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
        return "ru"
    elif any(c in text_lower for c in "ñáéíóúü¿¡"):
        return "es"
    elif any(c in text_lower for c in "àâäæçéèêëîïôœùûüÿ"):
        return "fr"
    elif any(c in text_lower for c in "äöüß"):
        return "de"
    elif any(c in text_lower for c in "абвгдежзийклмнопрстуфхцчшщъьюя"):
        return "bg"  # Bulgarian/other Cyrillic
    elif any(c in text_lower for c in "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"):
        return "ja"
    elif any(c in text_lower for c in "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"):
        return "ko"
    elif any(c in text_lower for c in "ضصثقفغعهخحجدشسيبلاتنمكطظ"):
        return "ar"
    else:
        return "en"  # Default to English

# ===== BOT COMMAND HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    user_lang = context.user_data.get("lang", DEFAULT_LANG)
    user_name = update.effective_user.first_name
    
    welcome = (
        f"🌐 *Welcome to MultiLangg Bot, {user_name}!*\n\n"
        f"I can translate messages between multiple languages instantly!\n\n"
        f"📝 *What I can do:*\n"
        f"• Translate text to any supported language\n"
        f"• Auto-detect source language\n"
        f"• Multi-engine translation (Google, LibreTranslate)\n"
        f"• Support for 15+ languages\n\n"
        f"🔧 *Commands:*\n"
        f"/start - Show this message\n"
        f"/help - Get help\n"
        f"/lang - Change your preferred language\n"
        f"/translate - Translate a message\n"
        f"/detect - Detect language of text\n"
        f"/stats - Your usage statistics\n\n"
        f"💡 *How to use:*\n"
        f"1. Send any text message\n"
        f"2. Reply to a message with /translate to translate it\n"
        f"3. Use /lang to set your default language\n\n"
        f"📊 *Supported Languages:*\n"
        f"English 🇺🇸 | Spanish 🇪🇸 | French 🇫🇷\n"
        f"German 🇩🇪 | Italian 🇮🇹 | Portuguese 🇵🇹\n"
        f"Russian 🇷🇺 | Japanese 🇯🇵 | Korean 🇰🇷\n"
        f"Chinese 🇨🇳 | Arabic 🇸🇦 | Hindi 🇮🇳\n"
        f"Turkish 🇹🇷 | Dutch 🇳🇱 | Indonesian 🇮🇩"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌐 Translate", callback_data="translate")],
        [InlineKeyboardButton("⚙️ Set Language", callback_data="lang")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = (
        "🤖 *Help Center*\n\n"
        "📝 *How to use this bot:*\n\n"
        "1️⃣ *Direct Translation:*\n"
        "Send any text and I'll translate it to your preferred language\n\n"
        "2️⃣ *Reply Translation:*\n"
        "Reply to a message with /translate to translate it\n\n"
        "3️⃣ *Change Language:*\n"
        "Use /lang to change your default language\n\n"
        "4️⃣ *Detect Language:*\n"
        "Use /detect to identify the language of any text\n\n"
        "🔧 *Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/lang - Change language\n"
        "/translate - Translate a message\n"
        "/detect - Detect language\n"
        "/stats - Your usage statistics\n\n"
        "⚡ *Tips:*\n"
        "• I auto-detect source language\n"
        "• Multiple translation engines for reliability\n"
        "• Your language preference is saved\n"
        "• Works in groups too!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change user language preference"""
    keyboard = []
    row = []
    for i, (code, lang) in enumerate(LANGUAGES.items()):
        button = InlineKeyboardButton(f"{lang['flag']} {lang['name']}", callback_data=f"setlang_{code}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌐 *Select your preferred language:*\n\n"
        "Choose the language you want your translations to be in:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate a message by replying"""
    if update.message.reply_to_message:
        text_to_translate = update.message.reply_to_message.text
        if not text_to_translate:
            await update.message.reply_text("❌ Please reply to a text message to translate.")
            return
        
        target_lang = context.user_data.get("lang", DEFAULT_LANG)
        await translate_and_send(update, text_to_translate, target_lang)
    else:
        await update.message.reply_text(
            "❌ Please reply to a message you want to translate.\n\n"
            "💡 Example: Reply to a message with /translate"
        )

async def detect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect language of a message"""
    if update.message.reply_to_message:
        text = update.message.reply_to_message.text
        if not text:
            await update.message.reply_text("❌ Please reply to a text message.")
            return
        
        detected_lang = detect_language_code(text)
        lang_name = LANGUAGES.get(detected_lang, {}).get("name", "Unknown")
        flag = LANGUAGES.get(detected_lang, {}).get("flag", "🌐")
        
        await update.message.reply_text(
            f"🔍 *Language Detection*\n\n"
            f"📝 *Text:* {text[:50]}...\n"
            f"🌐 *Detected Language:* {flag} {lang_name}\n\n"
            f"💡 You can translate this message by replying with /translate",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Please reply to a message to detect its language."
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = update.effective_user.id
    translated = context.user_data.get("translated_count", 0)
    lang = context.user_data.get("lang", DEFAULT_LANG)
    lang_name = LANGUAGES.get(lang, {}).get("name", "English")
    
    stats_text = (
        f"📊 *Your Statistics*\n\n"
        f"👤 *User ID:* {user_id}\n"
        f"🌐 *Preferred Language:* {lang_name}\n"
        f"📝 *Translations:* {translated}\n"
        f"⚡ *Status:* Active\n\n"
        f"Keep translating to learn new languages!"
    )
    await update.message.reply_text(stats_text, parse_mode="Markdown")

async def translate_and_send(update: Update, text, target_lang):
    """Translate text and send result"""
    processing = await update.message.reply_text(
        f"🔄 *Translating...*\n⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    try:
        # Detect source language
        source_lang = detect_language_code(text)
        source_name = LANGUAGES.get(source_lang, {}).get("name", "Unknown")
        target_name = LANGUAGES.get(target_lang, {}).get("name", "English")
        
        # Translate
        translated, engine = await translate_text(text, target_lang, source_lang)
        
        await processing.delete()
        
        if translated:
            # Update user stats
            context.user_data["translated_count"] = context.user_data.get("translated_count", 0) + 1
            
            await update.message.reply_text(
                f"🌐 *Translation Result*\n\n"
                f"📝 *Original:*\n{text}\n\n"
                f"📖 *Translated:*\n{translated}\n\n"
                f"🔍 *Details:*\n"
                f"• From: {source_name}\n"
                f"• To: {target_name}\n"
                f"• Engine: {engine}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ *Translation Failed*\n\n"
                "Could not translate the text. Please try again.\n\n"
                "💡 Tips:\n"
                "• Make sure the text is not too long\n"
                "• Try a different language\n"
                "• Check your internet connection",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        await processing.delete()
        await update.message.reply_text(
            f"❌ *Error*\n\n{str(e)}",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and translate them if user has a preferred language"""
    text = update.message.text.strip()
    
    if not text:
        return
    
    # Check if user has a preferred language
    user_lang = context.user_data.get("lang", DEFAULT_LANG)
    
    # Auto-translate if user has a language set (and not the default command messages)
    if user_lang and not text.startswith('/'):
        await translate_and_send(update, text, user_lang)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        help_text = (
            "🤖 *How to use this bot:*\n\n"
            "1. Send any text to translate\n"
            "2. Reply with /translate to translate\n"
            "3. Use /lang to change language\n\n"
            "Works in groups too!"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown")
    
    elif data == "translate":
        await query.edit_message_text(
            "🌐 *Ready to translate!*\n\n"
            "Send me any text message or reply to a message with /translate.\n\n"
            "You can also set your preferred language with /lang.",
            parse_mode="Markdown"
        )
    
    elif data == "lang":
        keyboard = []
        row = []
        for code, lang in LANGUAGES.items():
            button = InlineKeyboardButton(f"{lang['flag']} {lang['name']}", callback_data=f"setlang_{code}")
            row.append(button)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌐 *Select your preferred language:*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif data.startswith("setlang_"):
        lang_code = data.replace("setlang_", "")
        context.user_data["lang"] = lang_code
        
        lang_name = LANGUAGES.get(lang_code, {}).get("name", "English")
        flag = LANGUAGES.get(lang_code, {}).get("flag", "🌐")
        
        await query.edit_message_text(
            f"✅ *Language changed!*\n\n"
            f"🌐 *Preferred Language:* {flag} {lang_name}\n\n"
            f"Now I'll translate all messages to {lang_name} automatically!\n\n"
            f"💡 Send a message to test it out!",
            parse_mode="Markdown"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ===== MAIN APPLICATION =====
def main():
    """Start the bot"""
    logger.info("🚀 Starting MultiLangg Bot...")
    logger.info(f"🤖 Bot Username: @MultiLanggBot")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("detect", detect_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Add message handler for text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    logger.info("✅ Bot is ready! Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
