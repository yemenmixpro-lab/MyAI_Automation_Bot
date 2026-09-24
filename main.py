import os
import asyncio
import requests
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# =====================================================================
# 🔐 المفاتيح والرموز السرية المدمجة بأمان
# =====================================================================
TELEGRAM_TOKEN = "8841710767:AAEAE50zDmziITW_WqdEgLLiGv6nk1n4Q2c"
GEMINI_API_KEY = "AQ.Ab8RN6IG6cg8GRE3HSrhTTBbcC2Y3qVbMohncNhQ2uJqXY3kNQ"

FACEBOOK_ACCOUNTS = {
    "acc_1": {
        "name": "حسابك الشخصي الأساسي 👤", 
        "token": "EAAX1A6RNqwkBSseGEB2MmVG8kLCva2Pk2t4a3XhREW9wShTcZCGxt8fy02xK4FoZBdYb8ZAnxbCq9NhuDxDEsidVyRA0QkYWPxuyWubVBDDQxtaq2FVAN0Bxy6g5qM7UhKbqVjZBjXAZB8MKk2X9Qi4pV8y0UUiyZANi6aLrFPbKDO0SlWRcy4EsX9xZCVTT0KSlUeumPpniQ072KlNi2f1ZAWvtbJEDUjAQFLJE2B7m7Nj7oFbp9ZCNPywZDZD", 
        "selected": True
    }
}

# تهيئة عميل الذكاء الاصطناعي
ai_client = genai.Client(api_key=GEMINI_API_KEY)

def get_accounts_keyboard():
    keyboard = []
    for acc_id, info in FACEBOOK_ACCOUNTS.items():
        status_emoji = "✅" if info["selected"] else "❌"
        keyboard.append([InlineKeyboardButton(f"{status_emoji} {info['name']}", callback_data=f"toggle_{acc_id}")])
    return keyboard

def extract_post_id(url):
    if "posts/" in url:
        try:
            return url.split("posts/").split("/").split("?")
        except:
            pass
    elif "story_fbid=" in url:
        try:
            return url.split("story_fbid=").split("&")
        except:
            pass
    return "123456789_123456789"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    total_accs = len(FACEBOOK_ACCOUNTS)
    
    keyboard = get_accounts_keyboard()
    keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🤖 **لوحة تحكم البوت الذكي المتكامل**\n\n"
        f"📊 الحسابات المربوطة حالياً: **{total_accs}**.\n"
        f"👇 اختر الحساب النشط ثم اضغط على زر الاعتماد بالأسفل:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.query
    await query.answer()
    user_data = context.user_data
    data = query.data

    if data.startswith("toggle_"):
        acc_id = data.split("_")
        FACEBOOK_ACCOUNTS[acc_id]["selected"] = not FACEBOOK_ACCOUNTS[acc_id]["selected"]
        
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "confirm_accounts":
        active_count = sum(1 for info in FACEBOOK_ACCOUNTS.values() if info["selected"])
        if active_count == 0:
            await query.message.reply_text("⚠️ يرجى تحديد حساب واحد على الأقل للمتابعة!")
            return
        
        user_data["step"] = "waiting_for_url"
        await query.edit_message_text(f"📥 تم اختيار **{active_count}** حسابات.\n\n🔗 الآن، يرجى إرسال **رابط منشور فيسبوك** المستهدف:")

    elif data.startswith("publish_"):
        option_index = int(data.split("_"))
        chosen_comment = user_data["ai_options"][option_index]
        post_id = user_data.get("post_id")
        
        await query.edit_message_text(f"🚀 جاري معالجة ونشر التعليق المختار...\n💬 النص: '{chosen_comment}'")
        
        selected_accounts = [info for info in FACEBOOK_ACCOUNTS.values() if info["selected"]]
        
        for acc in selected_accounts:
            await query.message.reply_text(f"🔄 جاري الضخ والتعليق عبر: **{acc['name']}**...")
            
            fb_url = f"https://facebook.com{post_id}/comments"
            payload = {
                "message": chosen_comment,
                "access_token": acc["token"]
            }
            
            try:
                fb_response = requests.post(fb_url, data=payload)
                if fb_response.status_code == 200:
                    await query.message.reply_text(f"✅ تم النشر والتعليق عبر **{acc['name']}** بنجاح!")
                else:
                    await query.message.reply_text(f"❌ فشل النشر. السبب: {fb_response.json().get('error', {}).get('message', 'خطأ من فيسبوك')}")
            except Exception as e:
                await query.message.reply_text(f"❌ خطأ فني أثناء الاتصال بالسيرفر: {str(e)}")
            
            await asyncio.sleep(4)
            
        await query.message.reply_text("🏁 تمت العملية بالكامل بنجاح وتوقف البوت. للبدء مجدداً أرسل /start")
        user_data.clear()

async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    current_step = user_data.get("step")

    if current_step == "waiting_for_url":
        user_data["post_id"] = extract_post_id(text)
        user_data["step"] = "waiting_for_idea"
        await update.message.reply_text("🔗 تم حفظ الرابط بنجاح واستخرج المعرف.\n\n✍️ الآن اكتب لي الفكرة العامة أو التوجيه الذي تريده:")
        
    elif current_step == "waiting_for_idea":
        user_data["step"] = ""
        await update.message.reply_text("⏳ جاري توليد 3 صياغات ذكية ومختلفة بالذكاء الاصطناعي...")

        prompt = f"صغ 3 خيارات لتعليقات مختلفة وممتازة بالعامية، بناءً على الفكرة التالية: ({text}). افصل بين الخيارات بعلامة النجمة * فقط وبدون أرقام تسلسلية."
        
        try:
            response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            options = [o.strip() for o in response.text.split('*') if o.strip()]

            if len(options) >= 3:
                user_data["ai_options"] = options
                
                keyboard = [
                    [InlineKeyboardButton("1️⃣ نشر الخيار الأول", callback_data="publish_0")],
                    [InlineKeyboardButton("2️⃣ نشر الخيار الثاني", callback_data="publish_1")],
                    [InlineKeyboardButton("3️⃣ نشر الخيار الثالث", callback_data="publish_2")]
                ]
                
                await update.message.reply_text(
                    f"📝 **المسودات المقترحة من الذكاء الاصطناعي:**\n\n"
                    f"1️⃣ {options}\n\n"
                    f"2️⃣ {options}\n\n"
                    f"3️⃣ {options}\n\n"
                    f"👇 اختر الصياغة المناسبة ليتم كتابتها مباشرة دون أي تدخل منك:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ حدث خطأ في تنسيق النص، أرسل /start للمحاولة مجدداً.")
        except Exception as e:
            await update.message.reply_text(f"❌ فشل الاتصال بمحرك الذكاء الاصطناعي: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_inputs))
    
    print("[+] البوت جاهز تماماً وبانتظار الأوامر...")
    app.run_polling()

if __name__ == '__main__':
    main()
