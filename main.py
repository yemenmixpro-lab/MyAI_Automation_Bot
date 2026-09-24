import os
import asyncio
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# =====================================================================
# 🔐 إعداد المفاتيح والرموز السرية من بيئة العمل (لأمان منصة Railway)
# =====================================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8841710767:AAEAE50zDmziITW_WqdEgLLiGv6nk1n4Q2c")

# قاعدة بيانات وهمية في الذاكرة للحسابات
FACEBOOK_ACCOUNTS = {
    "acc_1": {
        "name": "حسابك الشخصي الأساسي 👤", 
        "token": "EAAX1A6RNqwkBSseGEB2MmVG8kLCva2Pk2t4a3XhREW9wShTcZCGxt8fy02xK4FoZBdYb8ZAnxbCq9NhuDxDEsidVyRA0QkYWPxuyWubVBDDQxtaq2FVAN0Bxy6g5qM7UhKbqVjZBjXAZB8MKk2X9Qi4pV8y0UUiyZANi6aLrFPbKDO0SlWRcy4EsX9xZCVTT0KSlUeumPpniQ072KlNi2f1ZAWvtbJEDUjAQFLJE2B7m7Nj7oFbp9ZCNPywZDZD", 
        "selected": True
    }
}

def get_accounts_keyboard():
    keyboard = []
    for acc_id, info in FACEBOOK_ACCOUNTS.items():
        status_emoji = "✅" if info["selected"] else "❌"
        keyboard.append([InlineKeyboardButton(f"{status_emoji} {info['name']}", callback_data=f"toggle_{acc_id}")])
    
    keyboard.append([
        InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account"),
        InlineKeyboardButton("❌ حذف حساب", callback_data="manage_delete")
    ])
    return keyboard

def extract_post_id(url):
    url = url.strip()
    id_match = re.search(r'(?:fbid=|permalink/|posts/|stories/|videos/|groups/[^/]+/permalink/|reels/)(\d+)', url)
    if id_match:
        return id_match.group(1)
    id_param = re.search(r'[?&]id=(\d+)', url)
    if id_param:
        return id_param.group(1)
    compound_match = re.search(r'posts/.*?/(\d+)', url)
    if compound_match:
        return compound_match.group(1)
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
        f"👇 اختر الحساب النشط أو أضف حسابات جديدة من الأزرار بالأسفل:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data = context.user_data
    data = query.data

    if data.startswith("toggle_"):
        acc_id = data.replace("toggle_", "")
        if acc_id in FACEBOOK_ACCOUNTS:
            FACEBOOK_ACCOUNTS[acc_id]["selected"] = not FACEBOOK_ACCOUNTS[acc_id]["selected"]
        
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_account":
        user_data["step"] = "add_acc_name"
        await query.message.reply_text("👤 حسناً، أرسل الآن **اسماً مستعاراً** للحساب الجديد:")

    elif data == "manage_delete":
        if not FACEBOOK_ACCOUNTS:
            await query.message.reply_text("⚠️ لا توجد حسابات مسجلة لحذفها.")
            return
        keyboard = []
        for acc_id, info in FACEBOOK_ACCOUNTS.items():
            keyboard.append([InlineKeyboardButton(f"🗑️ حذف: {info['name']}", callback_data=f"del_{acc_id}")])
        keyboard.append([InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="back_to_main")])
        await query.edit_message_text("❌ اختر الحساب الذي ترغب في حذفه نهائياً:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_"):
        acc_id = data.replace("del_", "")
        if acc_id in FACEBOOK_ACCOUNTS:
            deleted_name = FACEBOOK_ACCOUNTS[acc_id]["name"]
            del FACEBOOK_ACCOUNTS[acc_id]
            await query.message.reply_text(f"🗑️ تم حذف الحساب **{deleted_name}** بنجاح.")
        
        total_accs = len(FACEBOOK_ACCOUNTS)
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_text(f"🤖 **لوحة تحكم البوت الذكي المتكامل**\n\n📊 الحسابات المربوطة حالياً: **{total_accs}**.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_to_main":
        total_accs = len(FACEBOOK_ACCOUNTS)
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_text(f"🤖 **لوحة تحكم البوت الذكي المتكامل**\n\n📊 الحسابات المربوطة حالياً: **{total_accs}**.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "confirm_accounts":
        active_count = sum(1 for info in FACEBOOK_ACCOUNTS.values() if info["selected"])
        if active_count == 0:
            await query.message.reply_text("⚠️ يرجى تحديد حساب واحد على الأقل للمتابعة!")
            return
        
        user_data["step"] = "waiting_for_url"
        await query.edit_message_text(f"📥 تم اختيار **{active_count}** حسابات بنجاح.\n\n🔗 الآن، يرجى إرسال **رابط منشور فيسبوك** المستهدف:")

async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    current_step = user_data.get("step")

    if current_step == "add_acc_name":
        user_data["new_acc_name"] = text
        user_data["step"] = "add_acc_token"
        await update.message.reply_text(f"🔑 تم حفظ الاسم: **{text}**\n\nأرسل الآن **Access Token** الخاص بالحساب:")
        
    elif current_step == "add_acc_token":
        acc_name = user_data.get("new_acc_name", "حساب غير مسمى")
        new_id = f"acc_{int(asyncio.get_event_loop().time())}"
        
        FACEBOOK_ACCOUNTS[new_id] = {
            "name": f"{acc_name} 👤",
            "token": text.strip(),
            "selected": True
        }
        user_data.clear()
        await update.message.reply_text(f"✨ تم إضافة حساب **{acc_name}** بنجاح!\nأرسل /start لرؤيته وتفعيله.")

    elif current_step == "waiting_for_url":
        user_data["post_id"] = extract_post_id(text)
        user_data["step"] = "waiting_for_comment_text"
        await update.message.reply_text("🔗 تم حفظ الرابط بنجاح.\n\n✍️ الآن اكتب **نص التعليق** الذي تريد نشره مباشرة:")
        
    elif current_step == "waiting_for_comment_text":
        post_id = user_data.get("post_id")
        chosen_comment = text
        user_data.clear() # تصفير الخطوات مباشرة
        
        await update.message.reply_text(f"🚀 جاري معالجة ونشر التعليق...\n💬 النص: '{chosen_comment}'")
        
        selected_accounts = [info for info in FACEBOOK_ACCOUNTS.values() if info["selected"]]
        
        for acc in selected_accounts:
            await update.message.reply_text(f"🔄 جاري النشر عبر: **{acc['name']}**...")
            
            fb_url = f"https://facebook.com{post_id}/comments"
            payload = {
                "message": chosen_comment,
                "access_token": acc["token"]
            }
            
            try:
                fb_response = requests.post(fb_url, data=payload)
                if fb_response.status_code == 200:
                    await update.message.reply_text(f"✅ تم النشر عبر **{acc['name']}** بنجاح!")
                else:
                    await update.message.reply_text(f"❌ فشل النشر. السبب: {fb_response.json().get('error', {}).get('message', 'خطأ من فيسبوك')}")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ فني: {str(e)}")
            
            await asyncio.sleep(4)
            
        await update.message.reply_text("🏁 تمت العملية بالكامل بنجاح. للبدء مجدداً أرسل /start")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_inputs))
    
    print("[+] البوت جاهز بدون ذكاء اصطناعي...")
    app.run_polling()

if __name__ == '__main__':
    main()
