import os
import asyncio
import re
import requests
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# =====================================================================
# 🔐 إعداد المفاتيح والرموز السرية من بيئة العمل (لأمان منصة Railway)
# =====================================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8841710767:AAEAE50zDmziITW_WqdEgLLiGv6nk1n4Q2c")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6IG6cg8GRE3HSrhTTBbcC2Y3qVbMohncNhQ2uJqXY3kNQ")

# تهيئة عميل الذكاء الاصطناعي
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# قاعدة بيانات وهمية في الذاكرة للحسابات (يمكنك إدارتها بالكامل من البوت)
FACEBOOK_ACCOUNTS = {
    "acc_1": {
        "name": "حسابك الشخصي الأساسي 👤", 
        "token": "EAAX1A6RNqwkBSseGEB2MmVG8kLCva2Pk2t4a3XhREW9wShTcZCGxt8fy02xK4FoZBdYb8ZAnxbCq9NhuDxDEsidVyRA0QkYWPxuyWubVBDDQxtaq2FVAN0Bxy6g5qM7UhKbqVjZBjXAZB8MKk2X9Qi4pV8y0UUiyZANi6aLrFPbKDO0SlWRcy4EsX9xZCVTT0KSlUeumPpniQ072KlNi2f1ZAWvtbJEDUjAQFLJE2B7m7Nj7oFbp9ZCNPywZDZD", 
        "selected": True
    }
}

def get_accounts_keyboard():
    keyboard = []
    # عرض الحسابات الموجودة وتحديد حالتها
    for acc_id, info in FACEBOOK_ACCOUNTS.items():
        status_emoji = "✅" if info["selected"] else "❌"
        keyboard.append([InlineKeyboardButton(f"{status_emoji} {info['name']}", callback_data=f"toggle_{acc_id}")])
    
    # أزرار التحكم الديناميكية الجديدة
    keyboard.append([
        InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account"),
        InlineKeyboardButton("❌ حذف حساب", callback_data="manage_delete")
    ])
    return keyboard

def extract_post_id(url):
    """ دالة ذكية ومحدثة لاستخراج معرف المنشور (Post ID) من كافة أنواع روابط فيسبوك """
    # تنظيف الرابط من المسافات
    url = url.strip()
    
    # 1. البحث عن الأرقام المتتالية الـ IDs في الروابط التقليدية (مثل روابط المجموعات أو المعرفات الصريحة)
    id_match = re.search(r'(?:fbid=|permalink/|posts/|stories/|videos/|groups/[^/]+/permalink/|reels/)(\d+)', url)
    if id_match:
        return id_match.group(1)
        
    # 2. دعم الروابط التي تحتوي على المعرف كـ باراميتر id=
    id_param = re.search(r'[?&]id=(\d+)', url)
    if id_param:
        return id_param.group(1)
        
    # 3. دعم الروابط المركبة (صفحة/منشورات/معرف)
    compound_match = re.search(r'posts/.*?/(\d+)', url)
    if compound_match:
        return compound_match.group(1)
        
    # افتراضي في حال فشل الاستخراج بالكامل
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

    # تفعيل وتعطيل الحساب
    if data.startswith("toggle_"):
        acc_id = data.replace("toggle_", "")
        if acc_id in FACEBOOK_ACCOUNTS:
            FACEBOOK_ACCOUNTS[acc_id]["selected"] = not FACEBOOK_ACCOUNTS[acc_id]["selected"]
        
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    # بدء مسار إضافة حساب جديد
    elif data == "add_account":
        user_data["step"] = "add_acc_name"
        await query.message.reply_text("👤 حسناً، أرسل الآن **اسماً مستعاراً** للحساب الجديد لتتعرف عليه في القائمة:")

    # عرض قائمة الحسابات لحذف أحدها
    elif data == "manage_delete":
        if not FACEBOOK_ACCOUNTS:
            await query.message.reply_text("⚠️ لا توجد حسابات مسجلة لحذفها.")
            return
        keyboard = []
        for acc_id, info in FACEBOOK_ACCOUNTS.items():
            keyboard.append([InlineKeyboardButton(f"🗑️ حذف: {info['name']}", callback_data=f"del_{acc_id}")])
        keyboard.append([InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="back_to_main")])
        await query.edit_message_text("❌ اختر الحساب الذي ترغب في حذفه نهائياً من البوت:", reply_markup=InlineKeyboardMarkup(keyboard))

    # تنفيذ الحذف
    elif data.startswith("del_"):
        acc_id = data.replace("del_", "")
        if acc_id in FACEBOOK_ACCOUNTS:
            deleted_name = FACEBOOK_ACCOUNTS[acc_id]["name"]
            del FACEBOOK_ACCOUNTS[acc_id]
            await query.message.reply_text(f"🗑️ تم حذف الحساب **{deleted_name}** بنجاح.")
        
        # العودة للقائمة الرئيسية
        total_accs = len(FACEBOOK_ACCOUNTS)
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_text(f"🤖 **لوحة تحكم البوت الذكي المتكامل**\n\n📊 الحسابات المربوطة حالياً: **{total_accs}**.", reply_markup=InlineKeyboardMarkup(keyboard))

    # العودة للقائمة الرئيسية بدون إجراءات
    elif data == "back_to_main":
        total_accs = len(FACEBOOK_ACCOUNTS)
        keyboard = get_accounts_keyboard()
        keyboard.append([InlineKeyboardButton("➡️ الاعتماد والبدء في إرسال الرابط", callback_data="confirm_accounts")])
        await query.edit_message_text(f"🤖 **لوحة تحكم البوت الذكي المتكامل**\n\n📊 الحسابات المربوطة حالياً: **{total_accs}**.", reply_markup=InlineKeyboardMarkup(keyboard))

    # اعتماد الحسابات والانتقال لطلب الرابط
    elif data == "confirm_accounts":
        active_count = sum(1 for info in FACEBOOK_ACCOUNTS.values() if info["selected"])
        if active_count == 0:
            await query.message.reply_text("⚠️ يرجى تحديد حساب واحد على الأقل للمتابعة!")
            return
        
        user_data["step"] = "waiting_for_url"
        await query.edit_message_text(f"📥 تم اختيار **{active_count}** حسابات بنجاح.\n\n🔗 الآن، يرجى إرسال **رابط منشور فيسبوك** المستهدف:")

    # معالجة وضخ التعليق المحدد
    elif data.startswith("publish_"):
        option_index = int(data.replace("publish_", ""))
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
                await query.message.reply_text(f"❌ خطأ فني أثناء الاتصال بالخادم: {str(e)}")
            
            await asyncio.sleep(4)
            
        await query.message.reply_text("🏁 تمت العملية بالكامل بنجاح وتوقف البوت. للبدء مجدداً أرسل /start")
        user_data.clear()

async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    current_step = user_data.get("step")

    # مسار إضافة الحساب: حفظ الاسم وطلب التوكن
    if current_step == "add_acc_name":
        user_data["new_acc_name"] = text
        user_data["step"] = "add_acc_token"
        await update.message.reply_text(f"🔑 تم حفظ الاسم: **{text}**\n\nأرسل الآن **Access Token** الخاص بهذا الحساب من فيسبوك:")
        
    # مسار إضافة الحساب: حفظ التوكن وإدراج الحساب بالقائمة
    elif current_step == "add_acc_token":
        acc_name = user_data.get("new_acc_name", "حساب غير مسمى")
        new_id = f"acc_{int(asyncio.get_event_loop().time())}" # توليد معرف فريد
        
        FACEBOOK_ACCOUNTS[new_id] = {
            "name": f"{acc_name} 👤",
            "token": text.strip(),
            "selected": True
        }
        user_data.clear()
        await update.message.reply_text(f"✨ تم إضافة حساب **{acc_name}** بنجاح إلى لوحة التحكم!\nأرسل /start لرؤيته وتفعيله.")

    # مسار استقبال الرابط واستخراج الـ ID بدقة
    elif current_step == "waiting_for_url":
        extracted_id = extract_post_id(text)
        user_data["post_id"] = extracted_id
        user_data["step"] = "waiting_for_idea"
        await update.message.reply_text(f"🔗 تم حفظ الرابط بنجاح.\n🆔 المعرف المستخرج: `{extracted_id}`\n\n✍️ الآن اكتب لي الفكرة العامة أو التوجيه الذي تريده للتعليق:")
        
    # مسار توليد التعليقات بواسطة جيميناي
    elif current_step == "waiting_for_idea":
        user_data["step"] = ""
        await update.message.reply_text("⏳ جاري توليد 3 صياغات ذكية ومختلفة بالذكاء الاصطناعي...")

        prompt = f"صغ 3 خيارات لتعليقات مختلفة وممتازة بالعامية، بناءً على الفكرة التالية: ({text}). افصل بين الخيارات بعلامة النجمة * فقط وبدون أرقام تسلسلية."
        
        try:

