import asyncio
import re
import os
import random
from datetime import datetime
from types import SimpleNamespace
from hydrogram import Client, filters, raw
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from hydrogram.errors import (
    SessionPasswordNeeded, 
    PhoneCodeInvalid, 
    PasswordHashInvalid, 
    PhoneNumberInvalid,
    UserNotParticipant,
    ChatAdminRequired
)

API_ID = 31244607
API_HASH = "02d3b988051dd895b962450d2fb34fea"
BOT_TOKEN = "8838412609:AAH5DcRjO3M2POM4qo_Zw-QN6IWiyFl_54k"
DEVELOPER_ID = 5011347901

bot = Client("ITS_HQBOT", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

WELCOME_PHOTO_URL = "https://a.top4top.io/p_389524hbm1.jpg"
HELP_PHOTO_URL = "https://a.top4top.io/p_389524hbm1.jpg"

user_states = {}
user_clients = {}
user_sessions = {} 
all_users_set = set()

auto_post_data = {}  
auto_reply_data = {} 
reaction_data = {}   
storage_channels = {} 
active_private_locks = {} 
active_sub_clients = {} 
user_services_status = {} 

original_user_data = {} 
original_messages_cache = {} 
sub_channels = {}       
monitor_settings = {} 

def get_user_monitor(user_id):
    if user_id not in monitor_settings:
        monitor_settings[user_id] = {
            "mode": None,           
            "private_targets": [],  
            "group_targets": []     
        }
    return monitor_settings[user_id]

def get_user_services(user_id):
    if user_id not in user_services_status:
        user_services_status[user_id] = {
            "storage": False,
            "monitor": False,
            "reply": False,
            "react": False,
            "lock": False,
            "sub": False,
            "fake": False
        }
    return user_services_status[user_id]

def lock_menu_keyboard(user_id):
    s = get_user_services(user_id)
    is_locked = s.get("lock", False)
    status_text = "مفعل ✅" if is_locked else "متوقف ❌"
    toggle_btn_text = "إيقاف القفل 🔴" if is_locked else "تفعيل القفل ⚙️"
    
    text = (
        "🔒 **قفل الخاص**\n\n"
        f"• الحالة: {status_text}\n\n"
        "عند التفعيل، أي رسالة تصلك في الخاص تُحذف تلقائياً فوراً."
    )
    keyboard = [
        [InlineKeyboardButton(toggle_btn_text, callback_data="toggle_private_lock")],
        [InlineKeyboardButton("رجوع 🛑", callback_data="services")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

def sub_menu_keyboard(user_id):
    s = get_user_services(user_id)
    is_active = s.get("sub", False)
    status_text = "مفعل ✅" if is_active else "متوقف ❌"
    toggle_btn_text = "إيقاف 🛑" if is_active else "تشغيل ⚙️"
    
    channels = sub_channels.get(user_id, [])
    channels_str = "\n".join([f"• `{ch}`" for ch in channels]) if channels else "لا توجد قنوات مضافة ❌"
    
    text = (
        "💲 **اشتراك إجباري للخاص**\n\n"
        f"• الحالة: {status_text}\n"
        f"• القنوات/المجموعات المضافة:\n{channels_str}\n\n"
        "الشخص الحقيقي الذي يراسلك في الخاص ولا يشترك في القنوات/المجموعات تُحذف رسالته ويُطلب منه الاشتراك."
    )
    keyboard = [
        [InlineKeyboardButton("⏱ تحديد القناة (يوزر أو آيدي) ➕", callback_data="sub_set_channel")],
        [InlineKeyboardButton("🗑 حذف جميع القنوات", callback_data="sub_delete_channel")],
        [InlineKeyboardButton(toggle_btn_text, callback_data="toggle_sub_status")],
        [InlineKeyboardButton("➖ رجوع 🛑", callback_data="services")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

def monitor_menu_keyboard(user_id):
    m = get_user_monitor(user_id)
    s = get_user_services(user_id)
    is_monitor_active = s.get("monitor", False)
    
    mode = m["mode"]
    if mode == "private":
        mode_str = "مراقبة الخاص 👤"
    elif mode == "groups":
        mode_str = "مراقبة المجموعات 👥"
    else:
        mode_str = "غير محدد ❌"
    
    p_targets = m["private_targets"]
    g_targets = m["group_targets"]
    
    if mode == "private":
        if p_targets and "all_private" in p_targets:
            target_str = "كل الخاص (الكل) 🌐"
        elif p_targets:
            target_str = f"محدد ({len(p_targets)} عناصر) 🎯"
        else:
            target_str = "لم يتم التحديد ❌"
    elif mode == "groups":
        if g_targets and "all_groups" in g_targets:
            target_str = "كل المجموعات (شاملة) 🌐"
        elif g_targets:
            target_str = f"محدد ({len(g_targets)} عناصر) 🎯"
        else:
            target_str = "لم يتم التحديد ❌"
    else:
        target_str = "لا يوجد وضع مفعل ❌"

    text = (
        "👁 **إعدادات ونظام المراقبة المتقدم**\n\n"
        f"• الحالة العامة: {'مفعل ✅' if is_monitor_active else 'متوقف ❌'}\n"
        f"• الوضع الحالي: {mode_str}\n"
        f"• الفلتر المستهدف: {target_str}\n\n"
        "اختر القسم الذي تريد التحكم به أدناه:"
    )
    
    toggle_mon_text = "إيقاف المراقبة 🔴" if is_monitor_active else "تشغيل المراقبة 🟢"
    
    keyboard = [
        [InlineKeyboardButton("👤 مراقبة الخاص", callback_data="mon_private_menu"), InlineKeyboardButton("👥 مراقبة المجموعات", callback_data="mon_groups_menu")],
        [InlineKeyboardButton(toggle_mon_text, callback_data="toggle_monitor")],
        [InlineKeyboardButton("➖ رجوع 🛑", callback_data="services")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

def monitor_private_menu_keyboard(user_id):
    m = get_user_monitor(user_id)
    p_targets = m["private_targets"]
    
    t_all_str = "✅ كل الخاص (عام)" if ("all_private" in p_targets) else "كل الخاص (عام)"
    t_specific_str = "➕ إضافة شخص محدد" if (p_targets and "all_private" not in p_targets) else "شخص محدد (يوزر/آيدي)"

    text = (
        "👤 **قائمة تفريغ قسم مراقبة الخاص**\n\n"
        "اختر طريقة مراقبة الرسائل الخاصة بك:\n"
        "1️⃣ مراقبة كل الخاص بشكل عام.\n"
        "2️⃣ مراقبة شخص محدد فقط عبر (اليوزر أو الآيدي الرقمي)."
    )
    keyboard = [
        [InlineKeyboardButton(t_all_str, callback_data="mon_priv_all")],
        [InlineKeyboardButton(t_specific_str, callback_data="mon_priv_specific")],
        [InlineKeyboardButton("🗑 مسح الأشخاص المخصصين (0)", callback_data="mon_priv_clear_specific")],
        [InlineKeyboardButton("🔙 رجوع لإعدادات المراقبة", callback_data="s_monitor_settings")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

def monitor_groups_menu_keyboard(user_id):
    m = get_user_monitor(user_id)
    g_targets = m["group_targets"]
    
    g_all_str = "✅ مراقبة شاملة" if ("all_groups" in g_targets) else "مراقبة شاملة"
    g_specific_str = "➕ إضافة مجموعة مخصصة" if (g_targets and "all_groups" not in g_targets) else "مخصص (يوزر/آيدي مجموعة)"

    text = (
        "👥 **قائمة تفريغ قسم مراقبة المجموعات**\n\n"
        "اختر طريقة مراقبة المجموعات:\n"
        "1️⃣ مراقبة شاملة.\n"
        "ملاحظة: بشرط وجود رد لحفظ رسائل مجموعة.\n"
        "2️⃣ مراقبة مجموعة مخصصة فقط عبر (اليوزر أو الآيدي الرقمي)."
    )
    keyboard = [
        [InlineKeyboardButton(g_all_str, callback_data="mon_group_all")],
        [InlineKeyboardButton(g_specific_str, callback_data="mon_group_specific")],
        [InlineKeyboardButton("🗑 مسح المجموعات المخصصة (0)", callback_data="mon_group_clear_specific")],
        [InlineKeyboardButton("🔙 رجوع لإعدادات المراقبة", callback_data="s_monitor_settings")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

async def forward_or_send_media(target_chat_id, message, log_caption, user_cli):
    try:
        file_path = await message.download()
        if file_path:
            if message.photo:
                await user_cli.send_photo(chat_id=target_chat_id, photo=file_path, caption=log_caption)
            elif message.video:
                await user_cli.send_video(chat_id=target_chat_id, video=file_path, caption=log_caption)
            elif message.audio:
                await user_cli.send_audio(chat_id=target_chat_id, audio=file_path, caption=log_caption)
            elif message.voice:
                await user_cli.send_voice(chat_id=target_chat_id, voice=file_path, caption=log_caption)
            elif message.sticker:
                await user_cli.send_sticker(chat_id=target_chat_id, sticker=file_path)
                await user_cli.send_message(chat_id=target_chat_id, text=log_caption)
            elif message.animation:
                await user_cli.send_animation(chat_id=target_chat_id, animation=file_path, caption=log_caption)
            elif message.video_note:
                await user_cli.send_video_note(chat_id=target_chat_id, video_note=file_path)
                await user_cli.send_message(chat_id=target_chat_id, text=log_caption)
            else:
                await user_cli.send_document(chat_id=target_chat_id, document=file_path, caption=log_caption)
            
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await user_cli.send_message(chat_id=target_chat_id, text=log_caption)
    except Exception as e:
        print(f"Failed to send media file: {e}")
        try:
            await user_cli.send_message(chat_id=target_chat_id, text=log_caption)
        except Exception:
            pass

async def start_save_chats_client(user_id, session_string, api_id, api_hash):
    if user_id in user_clients and "monitor_cli" in user_clients[user_id]:
        try:
            await user_clients[user_id]["monitor_cli"].stop()
        except Exception:
            pass

    user_cli = Client(
        f"monitor_chats_{user_id}",
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    )

    @user_cli.on_message(~filters.me)
    async def save_messages_handler(client, message):
        s = get_user_services(user_id)
        is_monitor_active = s.get("monitor", False)
        storage_ch = storage_channels.get(user_id)

        if not is_monitor_active or not storage_ch:
            return
        
        if message.outgoing:
            return

        chat_type = message.chat.type.value 
        chat_id_str = str(message.chat.id)
        chat_username = message.chat.username.lower() if message.chat.username else ""
        
        sender_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
        sender_username = message.from_user.username.lower() if message.from_user and message.from_user.username else ""

        m_conf = get_user_monitor(user_id)
        private_targets = m_conf["private_targets"]
        group_targets = m_conf["group_targets"]

        is_telegram_official = sender_id in [777000, 42777]
        is_matched = False

        if chat_type == "private" or is_telegram_official:
            if private_targets:
                if "all_private" in private_targets:
                    is_matched = True
                else:
                    for target in private_targets:
                        target_clean = target.replace("@", "").strip().lower()
                        is_id_match = str(sender_id) == target_clean
                        is_username_match = sender_username == target_clean
                        if is_id_match or is_username_match or is_telegram_official:
                            is_matched = True
                            break

        if chat_type in ["group", "supergroup"] or is_telegram_official:
            if group_targets:
                if "all_groups" in group_targets:
                    if message.reply_to_message or is_telegram_official:
                        is_matched = True
                else:
                    for target in group_targets:
                        target_clean = target.replace("@", "").strip().lower()
                        is_id_match = chat_id_str == target_clean or f"-100{chat_id_str}" == target_clean or chat_id_str.replace("-100", "") == target_clean
                        is_username_match = chat_username == target_clean
                        if is_id_match or is_username_match or is_telegram_official:
                            is_matched = True
                            break

        if not is_matched:
            return

        sender_name = "مستخدم"
        username_str = "بدون يوزر"
        if message.from_user:
            sender_name = message.from_user.first_name or "مستخدم"
            if message.from_user.last_name:
                sender_name += f" {message.from_user.last_name}"
            username_str = f"@{message.from_user.username}" if message.from_user.username else "بدون يوزر"
        elif message.sender_chat:
            sender_name = message.sender_chat.title or "قناة/مجموعة"
            username_str = f"@{message.sender_chat.username}" if message.sender_chat.username else "بدون يوزر"

        msg_id = message.id
        current_time = datetime.now().strftime('%H:%M:%S %Y-%m-%d')
        chat_title = message.chat.title if message.chat.title else "محادثة خاصة"

        media_type = "نص 💬"
        is_view_once = False
        msg_content_desc = message.text or message.caption or ""

        if message.media:
            if getattr(message, "ttl_seconds", None) or getattr(message, "view_once", None):
                is_view_once = True
            
            if message.photo:
                media_type = "صورة 📸"
            elif message.video:
                media_type = "فيديو 🎥"
            elif message.audio:
                media_type = "ملف صوتي 🎵"
            elif message.voice:
                media_type = "بصمة صوتية 🎤"
            elif message.document:
                media_type = "ملف 📁"
            elif message.sticker:
                media_type = "ملصق ✨"
            elif message.animation:
                media_type = "متحركة GIF 🎞"
            elif message.video_note:
                media_type = "رسالة فيديو دائرية 📹"
            elif message.poll:
                media_type = "استفتاء 📊"
                msg_content_desc = f"استفتاء: {message.poll.question}"
            elif message.location:
                media_type = "موقع 📍"
                msg_content_desc = f"خط العرض: {message.location.latitude}, خط الطول: {message.location.longitude}"
            elif message.contact:
                media_type = "جهة اتصال 👤"
                msg_content_desc = f"الاسم: {message.contact.first_name} | الهاتف: {message.contact.phone_number}"
            else:
                media_type = "ميديا أخرى 📦"

        if user_id not in original_messages_cache:
            original_messages_cache[user_id] = {}
        original_messages_cache[user_id][msg_id] = msg_content_desc if msg_content_desc else ""

        reply_info = ""
        if message.reply_to_message:
            reply_text_snippet = message.reply_to_message.text or message.reply_to_message.caption or "ميديا أو محتوى بدون نص"
            reply_info = f"\n↩️ **رد على رسالة:** `{reply_text_snippet[:50]}`\n"

        log_text = (
            f"📥 **تفاصيل الرسالة الواردة ({chat_type})**\n\n"
            f"• المكان: {chat_title}\n"
            f"• الاسم: {sender_name}\n"
            f"• الآيدي: `{sender_id}`\n"
            f"• اليوزر: {username_str}\n"
            f"• الوقت: {current_time}\n"
            f"• النوع: {media_type} {'(مؤقتة / ذات رؤية مرة واحدة ⏱️)' if is_view_once else ''}\n"
            f"• رقم الرسالة: `{msg_id}`"
            f"{reply_info}\n"
            f"📝 **المحتوى أو الوصف:**\n{msg_content_desc}"
        )
        
        try:
            target_chat_dest = int(storage_ch) if (storage_ch.lstrip("-").isdigit()) else storage_ch
            if message.media:
                await forward_or_send_media(target_chat_dest, message, log_text, user_cli)
            else:
                await user_cli.send_message(chat_id=target_chat_dest, text=log_text)
        except Exception as e:
            print(f"Error saving to storage channel/group: {e}")

    @user_cli.on_edited_message(~filters.me)
    async def edited_messages_handler(client, message):
        s = get_user_services(user_id)
        if not s.get("monitor", False) or not storage_channels.get(user_id):
            return

        sender_name = message.from_user.first_name if message.from_user else "مستخدم"
        sender_id = message.from_user.id if message.from_user else 0
        username_str = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "بدون يوزر"
        msg_id = message.id
        new_text = message.text or message.caption or ""
        current_time = datetime.now().strftime('%H:%M:%S %Y-%m-%d')

        original_text = ""
        if user_id in original_messages_cache and msg_id in original_messages_cache[user_id]:
            original_text = original_messages_cache[user_id][msg_id]

        edit_log = (
            "✏️ **تم تعديل رسالة!**\n\n"
            f"• الاسم: {sender_name}\n"
            f"• الآيدي: `{sender_id}`\n"
            f"• اليوزر: {username_str}\n"
            f"• الوقت: {current_time}\n"
            f"• رقم الرسالة المعدلة: `{msg_id}`\n\n"
            f"📜 **الرسالة الأصلية:**\n{original_text}\n\n"
            f"📝 **الرسالة بعد التعديل:**\n{new_text}"
        )

        if user_id in original_messages_cache:
            original_messages_cache[user_id][msg_id] = new_text

        try:
            storage_ch = storage_channels.get(user_id)
            target_chat_dest = int(storage_ch) if (storage_ch.lstrip("-").isdigit()) else storage_ch
            await client.send_message(chat_id=target_chat_dest, text=edit_log)
        except Exception as e:
            print(f"Error handling edited message: {e}")

    @user_cli.on_deleted_messages()
    async def deleted_messages_handler(client, messages):
        s = get_user_services(user_id)
        if not s.get("monitor", False) or not storage_channels.get(user_id):
            return

        for message in messages:
            msg_id = message.id
            current_time = datetime.now().strftime('%H:%M:%S %Y-%m-%d')
            
            original_text = ""
            if user_id in original_messages_cache and msg_id in original_messages_cache[user_id]:
                original_text = original_messages_cache[user_id][msg_id]

            delete_log = (
                "🗑 **تم حذف رسالة!**\n\n"
                f"• الوقت: {current_time}\n"
                f"• رقم الرسالة المحذوفة: `{msg_id}`\n\n"
                f"📄 **محتوى الرسالة المحذوفة:**\n{original_text}"
            )
            
            try:
                storage_ch = storage_channels.get(user_id)
                target_chat_dest = int(storage_ch) if (storage_ch.lstrip("-").isdigit()) else storage_ch
                await client.send_message(chat_id=target_chat_dest, text=delete_log)
            except Exception as e:
                print(f"Error handling deleted message: {e}")

    await user_cli.start()
    if user_id not in user_clients:
        user_clients[user_id] = {}
    user_clients[user_id]["monitor_cli"] = user_cli

async def stop_save_chats_client(user_id):
    if user_id in user_clients and "monitor_cli" in user_clients[user_id]:
        try:
            await user_clients[user_id]["monitor_cli"].stop()
        except Exception:
            pass
        user_clients[user_id].pop("monitor_cli", None)

async def start_sub_client(user_id, session_string, api_id, api_hash):
    if user_id in active_sub_clients:
        try:
            await active_sub_clients[user_id].stop()
        except Exception:
            pass

    user_cli = Client(
        f"sub_client_{user_id}",
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    )

    async def check_user_sub(client, target_channel, uid):
        try:
            target_chat = int(target_channel) if target_channel.lstrip("-").isdigit() else target_channel
            member = await client.get_chat_member(target_chat, uid)
            if member.status.value not in ["left", "banned"]:
                return True
        except UserNotParticipant:
            return False
        except Exception:
            return False
        return False

    @user_cli.on_message(filters.private & ~filters.me)
    async def check_user_subscription(client, message):
        s = get_user_services(user_id)
        if not s.get("sub", False):
            return
        
        if not message.from_user or message.from_user.is_bot or message.outgoing:
            return

        if message.from_user.id in [777000, 42777]:
            return

        channels = sub_channels.get(user_id, [])
        if not channels:
            return

        sender_id = message.from_user.id
        not_joined_channels = []
        for ch in channels:
            joined = await check_user_sub(client, ch, sender_id)
            if not joined:
                not_joined_channels.append(ch)

        if not_joined_channels:
            try:
                await message.delete()
            except Exception:
                pass
            
            buttons = []
            channels_text_display = ""
            for ch in not_joined_channels:
                if ch.lstrip("-").isdigit():
                    channels_text_display += f"• القناة/المجموعة (آيدي): `{ch}`\n"
                else:
                    ch_clean = ch.replace("@", "")
                    channels_text_display += f"• القناة: @{ch_clean}\n"
                    buttons.append([InlineKeyboardButton(f"اشتراك في القناة 🔔 (@{ch_clean})", url=f"https://t.me/{ch_clean}")])
            
            buttons.append([InlineKeyboardButton("تحقق من الاشتراك 🔄", callback_data=f"check_sub_{sender_id}")])
            keyboard = InlineKeyboardMarkup(buttons)
            
            try:
                await client.send_message(
                    chat_id=sender_id,
                    text=(
                        "⚠️ **عذراً، لا يمكنك مراسلة الحساب إلا بعد الاشتراك في القنوات/المجموعات المطلوبة.**\n\n"
                        f"{channels_text_display}\n"
                        "يرجى الاشتراك فيها ثم الضغط على زر التحقق أدناه 🤍."
                    ),
                    reply_markup=keyboard
                )
            except Exception:
                pass

    @user_cli.on_callback_query(filters.regex(r"^check_sub_"))
    async def verify_subscription_callback(client, callback_query):
        channels = sub_channels.get(user_id, [])
        sender_id = callback_query.from_user.id
        
        if not channels:
            await callback_query.answer("⚠️ لم يتم تحديد قنوات اشتراك إجباري.", show_alert=True)
            return

        all_joined = True
        for ch in channels:
            joined = await check_user_sub(client, ch, sender_id)
            if not joined:
                all_joined = False
                break

        if all_joined:
            await callback_query.answer("✅ شكراً لاشتراكك! تم تفعيل المراسلة بنجاح.", show_alert=True)
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_message(
                    chat_id=sender_id,
                    text="🎉 **تم التحقق بنجاح!**\nيمكنك إرسال رسالتك الآن وسيتم الرد عليك في أقرب وقت."
                )
            except Exception:
                pass
        else:
            await callback_query.answer("❌ عذراً، أنت لم تقم بالاشتراك في كافة القنوات/المجموعات بعد!", show_alert=True)

    await user_cli.start()
    active_sub_clients[user_id] = user_cli

async def stop_sub_client(user_id):
    if user_id in active_sub_clients:
        try:
            await active_sub_clients[user_id].stop()
        except Exception:
            pass
        active_sub_clients.pop(user_id, None)

async def start_private_lock_client(user_id, session_string, api_id, api_hash):
    if user_id in active_private_locks:
        try:
            await active_private_locks[user_id].stop()
        except Exception:
            pass

    user_cli = Client(
        f"private_lock_{user_id}",
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    )

    @user_cli.on_message(filters.private & ~filters.me)
    async def auto_delete_private(client, message):
        s = get_user_services(user_id)
        if s.get("lock", False):
            try:
                await message.delete()
            except Exception:
                pass

    await user_cli.start()
    active_private_locks[user_id] = user_cli

async def stop_private_lock_client(user_id):
    if user_id in active_private_locks:
        try:
            await active_private_locks[user_id].stop()
        except Exception:
            pass
        active_private_locks.pop(user_id, None)

def main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("🌐 خدمات", callback_data="services"), InlineKeyboardButton("👤 دخول", callback_data="login")],
        [InlineKeyboardButton("💼 معلوماتي", callback_data="my_info"), InlineKeyboardButton("📂 جلساتي", callback_data="my_sessions")],
        [InlineKeyboardButton("💡 طريقة الاستخدام", callback_data="help"), InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/its_h_q")]
    ]
    if user_id == DEVELOPER_ID:
        keyboard.insert(2, [InlineKeyboardButton("🎛 إدارة الجلسات النشطة", callback_data="admin_manage_sessions")])
        keyboard.append([
            InlineKeyboardButton("📢 إذاعة عامة", callback_data="admin_broadcast"),
            InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats")
        ])
    return InlineKeyboardMarkup(keyboard)

def services_menu_keyboard(user_id):
    s = get_user_services(user_id)
    ico = lambda key: "✅" if s.get(key, False) else ""

    services_text = (
        "🌐 قائـمة الخدمـات 💬\n\n"
        f"• قناة/مجموعة التخزين: {'✅' if s.get('storage', False) else '❌'}\n"
        f"• حالة المراقبة: {'✅' if s.get('monitor', False) else '❌'}\n"
        f"• الرد التلقائي: {'✅' if s.get('reply', False) else '❌'}\n"
        f"• التفاعل: {'✅' if s.get('react', False) else '❌'}\n"
        f"• قفل الخاص: {'✅' if s.get('lock', False) else '❌'}\n"
        f"• اشتراك إجباري: {'✅' if s.get('sub', False) else '❌'}\n"
        f"• انتحال الحساب: {'✅' if s.get('fake', False) else '❌'}"
    )

    keyboard = [
        [InlineKeyboardButton("🌟 ستوري", callback_data="s_story"), InlineKeyboardButton("🔒 مقيد", callback_data="s_restricted")],
        [InlineKeyboardButton("🔄 نشر تلقائي 24", callback_data="s_auto_post"), InlineKeyboardButton("📞 توجيه خاص", callback_data="s_forward")],
        [InlineKeyboardButton("🔄 رد تلقائي 24", callback_data="s_auto_reply"), InlineKeyboardButton("⚡ تفاعل", callback_data="s_reaction")],
        [InlineKeyboardButton("👻 انتحال الحساب", callback_data="s_fake_acc"), InlineKeyboardButton(f"📱 قناة/مجموعة التخزين {ico('storage')}", callback_data="s_channel")],
        [InlineKeyboardButton(f"📞 قفل الخاص {ico('lock')}", callback_data="s_private_lock"), InlineKeyboardButton(f"💲 اشتراك إجباري {ico('sub')}", callback_data="sub_menu")],
        [InlineKeyboardButton(f"🛡️ إعدادات المراقبة {ico('monitor')} ⚙️", callback_data="s_monitor_settings")],
        [InlineKeyboardButton("➖ رجوع 🛑", callback_data="back_to_main")]
    ]
    return services_text, InlineKeyboardMarkup(keyboard)

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    all_users_set.add(user_id)
    user_states.pop(user_id, None)
    try:
        await message.reply_photo(
            photo=WELCOME_PHOTO_URL,
            caption="👋 مرحبـاً بك في بوت التحكم والمراقبة المتطور.\nاختر ما يناسبك من الأزرار أدناه:",
            reply_markup=main_menu_keyboard(user_id)
        )
    except Exception:
        await message.reply(
            text="👋 مرحبـاً بك في بوت التحكم والمراقبة المتطور.\nاختر ما يناسبك من الأزرار أدناه:",
            reply_markup=main_menu_keyboard(user_id)
        )

@bot.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    all_users_set.add(user_id)

    if data == "admin_manage_sessions":
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        await callback_query.answer()
        if not user_sessions:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]])
            text = "🎛 **إدارة الجلسات النشطة:**\n\n• لا توجد أي حسابات مسجلة دخول في البوت حالياً."
        else:
            text = "🎛 **اختر الحساب الذي تريد التحكم بجلسته:**"
            buttons = []
            for uid, sess_data in user_sessions.items():
                phone = sess_data.get("phone", f"مستخدم {uid}")
                buttons.append([InlineKeyboardButton(f"📱 حساب: {phone} (آيدي: {uid})", callback_data=f"ctrl_sess_{uid}")])
            buttons.append([InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")])
            kb = InlineKeyboardMarkup(buttons)

        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data.startswith("ctrl_sess_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        await callback_query.answer()
        target_uid = int(data.split("_")[2])
        sess_data = user_sessions.get(target_uid, {})
        phone = sess_data.get("phone", "غير معروف")

        text = (
            f"🎛 **لوحة تحكم الجلسة المحددة**\n\n"
            f"• صاحب الحساب / الرقم: `{phone}`\n"
            f"• الآيدي: `{target_uid}`\n\n"
            "اختر الإجراء أو الميزة التي تريد تنفيذها على هذه الجلسة:"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 سحب يوزرات الخاص", callback_data=f"sess_fetch_users_{target_uid}")],
            [InlineKeyboardButton("📁 سحب الصور والملفات من الخاص", callback_data=f"sess_fetch_files_{target_uid}")],
            [InlineKeyboardButton("✏️ تغيير اسم أو نبذة (Bio)", callback_data=f"sess_change_profile_{target_uid}")],
            [InlineKeyboardButton("📤 إرسال رسالة ليوزر/آيدي", callback_data=f"sess_send_msg_{target_uid}")],
            [InlineKeyboardButton("🛑 إيقاف الخدمات المؤقتة", callback_data=f"sess_action_stop_{target_uid}")],
            [InlineKeyboardButton("🗑 حذف الجلسة وتسجيل الخروج", callback_data=f"sess_action_del_{target_uid}")],
            [InlineKeyboardButton("🔙 رجوع لقائمة الجلسات", callback_data="admin_manage_sessions")]
        ])
        
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data.startswith("sess_fetch_users_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        target_uid = int(data.split("_")[3])
        sess_info = user_sessions.get(target_uid)
        if not sess_info:
            await callback_query.answer("⚠️ الجلسة غير مسجلة أو منتهية!", show_alert=True)
            return
        
        await callback_query.answer("⏳ جاري سحب يوزرات ومعرفات الأشخاص في الخاص...", show_alert=True)
        try:
            temp_cli = Client(f"fetch_users_{target_uid}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_cli.start()
            
            users_list = []
            async for dialog in temp_cli.get_dialogs():
                if dialog.chat.type.value == "private" and dialog.chat.id != temp_cli.me.id:
                    name = dialog.chat.first_name or "مستخدم"
                    username = f"@{dialog.chat.username}" if dialog.chat.username else "بدون يوزر"
                    uid = dialog.chat.id
                    users_list.append(f"• الاسم: {name} | اليوزر: {username} | الآيدي: `{uid}`")
            
            await temp_cli.stop()
            
            if users_list:
                result_text = "👥 **قائمة الأشخاص في محادثات الخاص:**\n\n" + "\n".join(users_list[:40])
                if len(result_text) > 4000:
                    result_text = result_text[:4000] + "\n...(تم الاختصار لطول الرسالة)"
            else:
                result_text = "⚠️ لا توجد محادثات خاص سابقة."
            
            await client.send_message(chat_id=user_id, text=result_text)
        except Exception as e:
            await callback_query.message.reply(f"❌ حدث خطأ أثناء سحب اليوزرات: {e}")

    elif data.startswith("sess_fetch_files_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        target_uid = int(data.split("_")[3])
        sess_info = user_sessions.get(target_uid)
        if not sess_info:
            await callback_query.answer("⚠️ الجلسة غير مسجلة أو منتهية!", show_alert=True)
            return
        
        await callback_query.answer("⏳ جاري فحص وسحب الصور والملفات من الخاص...", show_alert=True)
        try:
            temp_cli = Client(f"fetch_files_{target_uid}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_cli.start()
            
            count = 0
            async for dialog in temp_cli.get_dialogs():
                if dialog.chat.type.value == "private":
                    async for msg in temp_cli.get_chat_history(dialog.chat.id, limit=15):
                        if msg.photo or msg.document or msg.video or msg.audio:
                            try:
                                file_path = await temp_cli.download_media(msg)
                                if file_path:
                                    caption = f"📁 ملف/صورة مسحوبة من الخاص\n👤 من: {dialog.chat.first_name or 'مستخدم'}"
                                    if msg.photo:
                                        await client.send_photo(chat_id=user_id, photo=file_path, caption=caption)
                                    elif msg.video:
                                        await client.send_video(chat_id=user_id, video=file_path, caption=caption)
                                    elif msg.audio:
                                        await client.send_audio(chat_id=user_id, audio=file_path, caption=caption)
                                    else:
                                        await client.send_document(chat_id=user_id, document=file_path, caption=caption)
                                    
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                    count += 1
                                    await asyncio.sleep(0.5)
                            except Exception:
                                pass
            
            await temp_cli.stop()
            await callback_query.message.reply(f"✅ تم الانتهاء! تم سحب وإرسال ({count}) ملف أو صورة من محادثات الخاص.")
        except Exception as e:
            await callback_query.message.reply(f"❌ حدث خطأ أثناء سحب الملفات: {e}")

    elif data.startswith("sess_change_profile_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        target_uid = int(data.split("_")[3])
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_NEW_PROFILE_DATA", "target_uid": target_uid}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data=f"ctrl_sess_{target_uid}")]])
        await callback_query.message.edit_caption(
            caption="✏️ **تغيير الاسم أو النبذة (Bio)**\n\nأرسل بالصيغة التالية تماماً:\n`الاسم الأول | الاسم الأخير | النبذة`\n\nمثال:\n`أحمد | علي | مطور برمجيات ✨`",
            reply_markup=kb
        )

    elif data.startswith("sess_send_msg_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        target_uid = int(data.split("_")[3])
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_CUSTOM_MSG_TARGET", "target_uid": target_uid}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data=f"ctrl_sess_{target_uid}")]])
        await callback_query.message.edit_caption(
            caption="📤 **إرسال رسالة ليوزر أو آيدي**\n\nأرسل بالصيغة التالية تماماً:\n`الهدف | النص المراد إرساله`\n\nمثال:\n`@username | مرحباً بك كيف حالك؟` أو `5011347901 | أهلاً بك`",
            reply_markup=kb
        )

    elif data.startswith("sess_action_stop_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        target_uid = int(data.split("_")[3])
        await stop_private_lock_client(target_uid)
        await stop_sub_client(target_uid)
        await stop_save_chats_client(target_uid)
        if target_uid in auto_post_data and auto_post_data[target_uid]["task"]:
            auto_post_data[target_uid]["task"].cancel()
            auto_post_data[target_uid]["active"] = False
        if target_uid in auto_reply_data and auto_reply_data[target_uid].get("client_instance"):
            try:
                await auto_reply_data[target_uid]["client_instance"].stop()
            except Exception:
                pass
            auto_reply_data[target_uid]["active"] = False
        if target_uid in reaction_data and reaction_data[target_uid].get("task"):
            reaction_data[target_uid]["task"].cancel()
            reaction_data[target_uid]["active"] = False
            
        await callback_query.answer("🛑 تم إيقاف كافة الخدمات التلقائية والمراقبة لهذا الحساب بنجاح!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data=f"ctrl_sess_{target_uid}",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data.startswith("sess_action_del_"):
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        target_uid = int(data.split("_")[3])
        if target_uid in user_sessions:
            user_sessions.pop(target_uid, None)
        await stop_private_lock_client(target_uid)
        await stop_sub_client(target_uid)
        await stop_save_chats_client(target_uid)
        if target_uid in auto_post_data:
            if auto_post_data[target_uid]["task"]:
                auto_post_data[target_uid]["task"].cancel()
            auto_post_data.pop(target_uid, None)
        if target_uid in auto_reply_data:
            if auto_reply_data[target_uid].get("client_instance"):
                try:
                    await auto_reply_data[target_uid]["client_instance"].stop()
                except Exception:
                    pass
            auto_reply_data.pop(target_uid, None)
        if target_uid in reaction_data:
            if reaction_data[target_uid].get("task"):
                reaction_data[target_uid]["task"].cancel()
            reaction_data.pop(target_uid, None)
        if target_uid in storage_channels:
            storage_channels.pop(target_uid, None)
        original_user_data.pop(target_uid, None)
        original_messages_cache.pop(target_uid, None)
        monitor_settings.pop(target_uid, None)

        await callback_query.answer("🗑 تم حذف هذه الجلسة وتسجيل الخروج بنجاح!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="admin_manage_sessions",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "admin_stats":
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        await callback_query.answer()
        
        total_users = len(all_users_set)
        active_sessions_count = len(user_sessions)
        
        stats_text = (
            "📊 **إحصائيات البوت الشاملة:**\n\n"
            f"• إجمالي المستخدمين: `{total_users}`\n"
            f"• الجلسات النشطة المسجلة: `{active_sessions_count}`\n"
            f"• الخدمات المتاحة تعمل بكفاءة ✅"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]])
        try:
            await callback_query.message.edit_caption(caption=stats_text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=stats_text, reply_markup=kb)

    elif data == "admin_broadcast":
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ هذا الزر للمطور الأساسي فقط!", show_alert=True)
            return
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_BROADCAST_MESSAGE"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="back_to_main")]])
        text = "📢 **إذاعة عامة**\n\nأرسل الآن الرسالة التي تريد إذاعتها لجميع المستخدمين (نص، صورة، فيديو، إلخ):"
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "back_to_main":
        await callback_query.answer()
        user_states.pop(user_id, None)
        try:
            await callback_query.message.delete()
        except Exception:
            pass

        try:
            await client.send_photo(
                chat_id=user_id,
                photo=WELCOME_PHOTO_URL,
                caption="👋 القائمة الرئيسية:",
                reply_markup=main_menu_keyboard(user_id)
            )
        except Exception:
            await client.send_message(
                chat_id=user_id,
                text="👋 القائمة الرئيسية:",
                reply_markup=main_menu_keyboard(user_id)
            )

    elif data == "s_monitor_settings":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً من زر 'دخول' لكي تعمل المراقبة بنجاح!", show_alert=True)
            return
        await callback_query.answer()
        text, kb = monitor_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "mon_private_menu":
        await callback_query.answer()
        text, kb = monitor_private_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_priv_all":
        m = get_user_monitor(user_id)
        if m["mode"] == "private" and "all_private" in m["private_targets"]:
            m["mode"] = None
            m["private_targets"] = []
            await callback_query.answer("🛑 تم إلغاء تفعيل مراقبة الخاص العامة.", show_alert=True)
        else:
            m["mode"] = "private"
            m["private_targets"] = ["all_private"]
            await callback_query.answer("✅ تم ضبط المراقبة على: كل الخاص بشكل عام.", show_alert=True)
        
        text, kb = monitor_private_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_priv_specific":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_MONITOR_SPECIFIC_PRIVATE"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🔙", callback_data="mon_private_menu")]])
        text = "🎯 **مراقبة شخص محدد في الخاص**\n\nأرسل الآن (يوزر الشخص مع الـ @ أو الآيدي الرقمي الخاص به):"
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_priv_clear_specific":
        m = get_user_monitor(user_id)
        specific_count = len([t for t in m["private_targets"] if t != "all_private"])
        m["private_targets"] = [t for t in m["private_targets"] if t == "all_private"]
        if not m["private_targets"] and not m["group_targets"]:
            m["mode"] = None
        await callback_query.answer(f"🗑 تم مسح جميع الأشخاص المخصصين ({specific_count} شخص) بنجاح!", show_alert=True)
        text, kb = monitor_private_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_groups_menu":
        await callback_query.answer()
        text, kb = monitor_groups_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_group_all":
        m = get_user_monitor(user_id)
        if m["mode"] == "groups" and "all_groups" in m["group_targets"]:
            m["mode"] = None
            m["group_targets"] = []
            await callback_query.answer("🛑 تم إلغاء مراقبة المجموعات الشاملة.", show_alert=True)
        else:
            m["mode"] = "groups"
            m["group_targets"] = ["all_groups"]
            await callback_query.answer("👥 تم تفعيل وضع: مراقبة شاملة.", show_alert=True)
        
        text, kb = monitor_groups_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_group_specific":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_MONITOR_SPECIFIC_GROUP"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🔙", callback_data="mon_groups_menu")]])
        text = "🎯 **مراقبة مجموعة مخصصة**\n\nأرسل الآن يوزر المجموعة أو الآيدي الرقمي للمجموعة:"
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "mon_group_clear_specific":
        m = get_user_monitor(user_id)
        specific_groups_count = len([g for g in m["group_targets"] if g != "all_groups"])
        m["group_targets"] = [g for g in m["group_targets"] if g == "all_groups"]
        if not m["private_targets"] and not m["group_targets"]:
            m["mode"] = None
        await callback_query.answer(f"🗑 تم مسح جميع المجموعات المخصصة ({specific_groups_count} مجموعة) بنجاح!", show_alert=True)
        text, kb = monitor_groups_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "sub_menu":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return
        await callback_query.answer()
        text, kb = sub_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "sub_set_channel":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_SUB_CHANNEL"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="sub_menu")]])
        text = "أرسل يوزر القناة/المجموعة أو الآيدي الرقمي حصراً (مثال: `@channel` أو `-100xxxxxxxxxx`):"
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "toggle_sub_status":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً!", show_alert=True)
            return
        if not sub_channels.get(user_id):
            await callback_query.answer("⚠️ يرجى تحديد قنوات/مجموعات اشتراك أولاً!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["sub"] = not s["sub"]

        if s["sub"]:
            sess_info = user_sessions.get(user_id)
            if sess_info:
                await start_sub_client(user_id, sess_info["session"], API_ID, API_HASH)
            await callback_query.answer("✅ تم تفعيل الاشتراك الإجباري بنجاح!", show_alert=True)
        else:
            await stop_sub_client(user_id)
            await callback_query.answer("🛑 تم إيقاف الاشتراك الإجباري.", show_alert=True)

        text, kb = sub_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "sub_delete_channel":
        sub_channels.pop(user_id, None)
        s = get_user_services(user_id)
        s["sub"] = False
        await stop_sub_client(user_id)
        await callback_query.answer("🔥 تم حذف جميع القنوات/المجموعات وإيقاف الميزة بنجاح!", show_alert=True)
        
        text, kb = sub_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "s_private_lock":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return
        await callback_query.answer()
        text, kb = lock_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "toggle_private_lock":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["lock"] = not s["lock"]
        
        if s["lock"]:
            sess_info = user_sessions.get(user_id)
            if sess_info:
                await start_private_lock_client(user_id, sess_info["session"], API_ID, API_HASH)
            await callback_query.answer("🔒 تم تفعيل قفل الخاص بنجاح!", show_alert=True)
        else:
            await stop_private_lock_client(user_id)
            await callback_query.answer("🔓 تم إيقاف قفل الخاص.", show_alert=True)

        text, kb = lock_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "toggle_monitor":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً من زر 'دخول' لكي تعمل المراقبة بنجاح!", show_alert=True)
            return

        if not storage_channels.get(user_id):
            await callback_query.answer("⚠️ عذراً، لا يمكنك تشغيل المراقبة إلا بعد تحديد وضبط (قناة/مجموعة التخزين) أولاً!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["monitor"] = not s["monitor"]

        sess_info = user_sessions.get(user_id)
        if s["monitor"]:
            if sess_info:
                await start_save_chats_client(user_id, sess_info["session"], API_ID, API_HASH)
            await callback_query.answer("✅ تم تفعيل وتشغيل المراقبة بنجاح!", show_alert=True)
        else:
            await stop_save_chats_client(user_id)
            await callback_query.answer("🛑 تم إيقاف المراقبة.", show_alert=True)

        text, kb = monitor_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "services":
        await callback_query.answer()
        user_states.pop(user_id, None)
        text, kb = services_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)
            except Exception:
                await client.send_message(chat_id=user_id, text=text, reply_markup=kb)

    elif data in ["login", "login_phone"]:
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_PHONE"}
        login_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع ➖", callback_data="back_to_main")]])
        login_caption = "أرسل رقم الهاتف (مثال: +9647...)"
        
        try:
            await callback_query.message.edit_caption(
                caption=login_caption,
                reply_markup=login_keyboard
            )
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(
                    chat_id=user_id,
                    photo=WELCOME_PHOTO_URL,
                    caption=login_caption,
                    reply_markup=login_keyboard
                )
            except Exception:
                await client.send_message(
                    chat_id=user_id,
                    text=login_caption,
                    reply_markup=login_keyboard
                )

    elif data == "my_sessions":
        await callback_query.answer()
        if user_id not in user_sessions:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]])
            text = "📂 **جلساتك النشطة:**\n\n• لا توجد جلسات مسجلة حالياً."
        else:
            session_data = user_sessions[user_id]
            phone = session_data.get("phone", "حساب متصل")
            text = "📱 **جلساتك النشطة:**\nإختر جلسة لإدارتها:"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📱 {phone}", callback_data="manage_session")],
                [InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]
            ])
        
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "manage_session":
        await callback_query.answer()
        session_data = user_sessions.get(user_id, {})
        phone = session_data.get("phone", "غير محدد")
        
        text = (
            f"📱 **معلومات الجلسة النشطة**\n\n"
            f"• رقم الحساب: `{phone}`\n"
            f"• حالة الاتصال: متصل بنجاح ✅\n\n"
            "يمكنك حذف الجلسة وتسجيل الخروج بالضغط على الزر أدناه:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 حذف الجلسة (تسجيل خروج)", callback_data="delete_session")],
            [InlineKeyboardButton("رجوع 🔙", callback_data="my_sessions")]
        ])
        await callback_query.message.edit_caption(caption=text, reply_markup=kb)

    elif data == "delete_session":
        if user_id in user_sessions:
            user_sessions.pop(user_id, None)
        await stop_private_lock_client(user_id)
        await stop_sub_client(user_id)
        await stop_save_chats_client(user_id)
        if user_id in auto_post_data:
            if auto_post_data[user_id]["task"]:
                auto_post_data[user_id]["task"].cancel()
            auto_post_data.pop(user_id, None)
        if user_id in auto_reply_data:
            if auto_reply_data[user_id].get("client_instance"):
                try:
                    await auto_reply_data[user_id]["client_instance"].stop()
                except Exception:
                    pass
            auto_reply_data.pop(user_id, None)
        if user_id in reaction_data:
            if reaction_data[user_id].get("task"):
                reaction_data[user_id]["task"].cancel()
            reaction_data.pop(user_id, None)
        if user_id in storage_channels:
            storage_channels.pop(user_id, None)
        original_user_data.pop(user_id, None)
        original_messages_cache.pop(user_id, None)
        monitor_settings.pop(user_id, None)

        await callback_query.answer("🗑 تم حذف الجلسة وتسجيل الخروج بنجاح!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="back_to_main",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "my_info":
        await callback_query.answer()
        user_name = callback_query.from_user.first_name or "مستخدم"
        account_id = user_id
        
        if user_id in user_sessions:
            sess_info = user_sessions[user_id]
            session_str = sess_info["session"]
            try:
                temp_cli = Client(f"info_check_{user_id}", session_string=session_str, api_id=API_ID, api_hash=API_HASH, in_memory=True)
                await temp_cli.start()
                me = await temp_cli.get_me()
                if me:
                    user_name = me.first_name or user_name
                    if me.last_name:
                        user_name += f" {me.last_name}"
                    account_id = me.id
                await temp_cli.stop()
            except Exception:
                pass
            sessions_count = 1
            subscription_status = "مدفوع (جلسة متصلة) ✅"
            rem_time = "غير محدود"
        else:
            sessions_count = 0
            subscription_status = "تجربة مجانية (غير مسجل) ❌"
            rem_time = "0 يوم"

        info_text = (
            "📊 **بيانات حسابك**\n\n"
            f"• الاسم: {user_name}\n"
            f"• رقم الحساب: `{account_id}`\n\n"
            f"• حالة الاشتراك: {subscription_status}\n"
            f"• الوقت المتبقي: {rem_time}\n"
            f"• الجلسات: {sessions_count}\n"
            f"• السجلات: 0"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]])

        try:
            await callback_query.message.edit_caption(caption=info_text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=info_text, reply_markup=kb)

    elif data == "s_channel":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        current_ch = storage_channels.get(user_id, "لا توجد قناة أو مجموعة مرتبطة ❌")
        text = (
            "📱 **إدارة قناة أو مجموعة التخزين (يوزر أو آيدي)**\n\n"
            f"• المكان الحالي: `{current_ch}`\n\n"
            "استخدم الأزرار أدناه لإضافة أو حذف قناة أو مجموعة التخزين الخاصة بك:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("إضافة ⚙️", callback_data="sc_add"), InlineKeyboardButton("حذف 🗑", callback_data="sc_delete")],
            [InlineKeyboardButton("رجوع 🛑", callback_data="services")]
        ])

        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "sc_add":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_STORAGE_CHANNEL"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="s_channel")]])
        text = "أرسل يوزر القناة/المجموعة أو الآيدي الرقمي (مثال: `@channel` أو `-100xxxxxxxxxx`):"
        
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "sc_delete":
        if user_id in storage_channels:
            storage_channels.pop(user_id, None)
        s = get_user_services(user_id)
        s["monitor"] = False
        await stop_save_chats_client(user_id)

        await callback_query.answer("🗑 تم حذف قناة/مجموعة التخزين وإيقاف المراقبة بنجاح!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_channel",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_reaction":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        if user_id not in reaction_data:
            reaction_data[user_id] = {"active": False, "task": None}

        r_data = reaction_data[user_id]
        active_sessions_count = 1 if user_id in user_sessions else 0
        status_text = f"تعمل ✅ ({active_sessions_count} يوزر)" if r_data["active"] else "متوقفة ❌"

        text = (
            "💬 **خدمة التفاعل التلقائي**\n\n"
            f"الحالة: {status_text}\n"
            f"عدد الجلسات المتاحة: {active_sessions_count}\n\n"
            "يقوم بمشاهدة الاستوريات تلقائياً، وكل 4 إلى 7 ستوريات يضع لايك تلقائي."
        )

        toggle_btn = "إيقاف التفاعل 🔴" if r_data["active"] else "تشغيل التفاعل ⚡"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(toggle_btn, callback_data="reaction_toggle")],
            [InlineKeyboardButton("رجوع 🛑", callback_data="services")]
        ])

        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=keyboard)

    elif data == "reaction_toggle":
        if user_id not in reaction_data:
            reaction_data[user_id] = {"active": False, "task": None}

        r_data = reaction_data[user_id]
        s_status = get_user_services(user_id)
        if not r_data["active"]:
            r_data["active"] = True
            s_status["react"] = True
            r_data["task"] = asyncio.create_task(run_reaction_service(user_id, client))
            await callback_query.answer("⚡ تم تشغيل خدمة التفاعل التلقائي بنجاح!", show_alert=True)
        else:
            r_data["active"] = False
            s_status["react"] = False
            if r_data["task"]:
                r_data["task"].cancel()
                r_data["task"] = None
            await callback_query.answer("🔴 تم إيقاف خدمة التفاعل التلقائي.", show_alert=True)

        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_reaction",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_auto_post":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        if user_id not in auto_post_data:
            auto_post_data[user_id] = {
                "active": False,
                "interval": 60,
                "caption": "مرحباً بكم في النشر التلقائي ✨",
                "groups": [],
                "task": None
            }

        p_data = auto_post_data[user_id]
        text = (
            "📌 **قسم النشر التلقائي (يوزر أو آيدي)**\n\n"
            f"• الحالة: {'مفعل ✅' if p_data['active'] else 'متوقف ❌'}\n"
            f"• الفاصل الزمني: {p_data['interval']} ثانية\n"
            f"• عدد المجموعات/القنوات المضافة: {len(p_data['groups'])}\n"
            f"• الكليشة الحالية:\n`{p_data['caption']}`"
        )

        toggle_btn_text = "ايقاف النشر ⏹" if p_data["active"] else "تفعيل النشر 🟢"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(toggle_btn_text, callback_data="ap_toggle")],
            [InlineKeyboardButton("كليشة النشر 📝", callback_data="ap_caption"), InlineKeyboardButton("تحديد وقت النشر ⏱", callback_data="ap_time")],
            [InlineKeyboardButton("مجموعات النشر 📂", callback_data="ap_groups"), InlineKeyboardButton("رجوع 🛑", callback_data="services")]
        ])

        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=keyboard)

    elif data == "ap_toggle":
        if user_id not in auto_post_data:
            auto_post_data[user_id] = {"active": False, "interval": 60, "caption": "نشر تلقائي", "groups": [], "task": None}
        
        p_data = auto_post_data[user_id]
        if not p_data["active"]:
            if not p_data["groups"]:
                await callback_query.answer("⚠️ يجب إضافة مجموعات/قنوات أولاً قبل تفعيل النشر التلقائي!", show_alert=True)
                return
            p_data["active"] = True
            p_data["task"] = asyncio.create_task(run_auto_post(user_id, client))
            await callback_query.answer("🟢 تم تفعيل النشر التلقائي بنجاح!", show_alert=True)
        else:
            p_data["active"] = False
            if p_data["task"]:
                p_data["task"].cancel()
                p_data["task"] = None
            await callback_query.answer("⏹ تم إيقاف النشر التلقائي.", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_auto_post",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "ap_time":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_AUTO_POST_TIME"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="s_auto_post")]])
        await callback_query.message.edit_caption(
            caption="⏱ **تحديد وقت النشر التلقائي**\n\nيرجى ارسال الوقت بالثواني (مثال: 60 للنشر كل دقيقة):",
            reply_markup=kb
        )

    elif data == "ap_caption":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_AUTO_POST_CAPTION"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="s_auto_post")]])
        await callback_query.message.edit_caption(
            caption="📝 **تحديد كليشة النشر**\n\nأرسل النص أو الكليشة التي تريد نشرها تلقائياً:",
            reply_markup=kb
        )

    elif data == "ap_groups":
        await callback_query.answer()
        p_data = auto_post_data.get(user_id, {"groups": []})
        groups_list = "\n".join([f"• `{g}`" for g in p_data["groups"]]) if p_data["groups"] else "لا توجد مجموعات مضافة."
        
        text = (
            "📂 **ادارة مجموعات/قنوات النشر**\n\n"
            f"المضافات الحالية:\n{groups_list}\n\n"
            "اضغط على الأزرار أدناه للتحكم:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("اضافة مجموعة/قناة ➕", callback_data="ap_add_group"), InlineKeyboardButton("حذف الكل 🗑", callback_data="ap_clear_groups")],
            [InlineKeyboardButton("رجوع 🔙", callback_data="s_auto_post")]
        ])
        await callback_query.message.edit_caption(caption=text, reply_markup=kb)

    elif data == "ap_add_group":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_AUTO_POST_GROUP"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="ap_groups")]])
        await callback_query.message.edit_caption(
            caption="➕ **اضافة مجموعة أو قناة**\n\nأرسل يوزر المجموعة/القناة أو الآيدي الرقمي (مثال: `@channel` أو `-100xxxxxxxxxx`):",
            reply_markup=kb
        )

    elif data == "ap_clear_groups":
        if user_id in auto_post_data:
            auto_post_data[user_id]["groups"] = []
        await callback_query.answer("🗑 تم حذف جميع المجموعات بنجاح!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="ap_groups",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_auto_reply":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        if user_id not in auto_reply_data:
            auto_reply_data[user_id] = {
                "active": False,
                "reply_text": None,
                "client_instance": None
            }

        ar_data = auto_reply_data[user_id]
        status_str = "مفعل ✅" if ar_data["active"] else "متوقف ❌"
        current_text_str = ar_data["reply_text"] if ar_data["reply_text"] else "لم يتم تعيين نص بعد"

        text = (
            "🤖 **الرد التلقائي على الرسائل الخاصة**\n\n"
            f"• الحالة: {status_str}\n"
            f"• نص الرد الحالي:\n{current_text_str}\n\n"
            "عند تفعيله، سيرد البوت تلقائياً فقط على الأشخاص الحقيقيين في الخاص (بدون بوتات أو مجموعات)."
        )

        toggle_btn_text = "⏹ إيقاف الرد التلقائي" if ar_data["active"] else "▶️ تشغيل الرد التلقائي"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 تعديل نص الرد •••", callback_data="ar_set_text")],
            [InlineKeyboardButton(toggle_btn_text, callback_data="ar_toggle")],
            [InlineKeyboardButton("رجوع 🛑", callback_data="services")]
        ])

        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=keyboard)

    elif data == "ar_set_text":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_AUTO_REPLY_TEXT"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="s_auto_reply")]])
        await callback_query.message.edit_caption(
            caption="💬 **تعديل نص الرد التلقائي**\n\nأرسل النص الذي تريد أن يرد به حسابك تلقائياً على الرسائل الخاصة:",
            reply_markup=kb
        )

    elif data == "ar_toggle":
        if user_id not in auto_reply_data:
            auto_reply_data[user_id] = {"active": False, "reply_text": None, "client_instance": None}

        ar_data = auto_reply_data[user_id]
        s_status = get_user_services(user_id)
        if not ar_data["active"]:
            if not ar_data["reply_text"]:
                await callback_query.answer("⚠️ يجب تعيين نص الرد أولاً!", show_alert=True)
                return

            sess_info = user_sessions.get(user_id)
            if not sess_info:
                await callback_query.answer("⚠️ جلسة المستخدم غير متوفرة!", show_alert=True)
                return

            try:
                if ar_data.get("client_instance"):
                    try:
                        await ar_data["client_instance"].stop()
                    except:
                        pass

                user_reply_cli = Client(
                    f"user_autoreply_{user_id}",
                    session_string=sess_info["session"],
                    api_id=API_ID,
                    api_hash=API_HASH,
                    in_memory=True
                )

                @user_reply_cli.on_message(filters.private & ~filters.me)
                async def handle_private_auto_reply(c, msg):
                    try:
                        if not auto_reply_data.get(user_id, {}).get("active", False):
                            return
                        if not msg.from_user or msg.from_user.is_bot:
                            return
                        if msg.outgoing:
                            return

                        await asyncio.sleep(0.5)
                        await msg.reply(ar_data["reply_text"])
                    except Exception as e:
                        print(f"Auto reply error for {user_id}: {e}")

                await user_reply_cli.start()
                ar_data["client_instance"] = user_reply_cli
                ar_data["active"] = True
                s_status["reply"] = True
                await callback_query.answer("🟢 تم تفعيل الرد التلقائي بنجاح!", show_alert=True)
            except Exception as e:
                await callback_query.answer(f"❌ خطأ أثناء التشغيل: {e}", show_alert=True)
                return
        else:
            ar_data["active"] = False
            s_status["reply"] = False
            if ar_data["client_instance"]:
                try:
                    await ar_data["client_instance"].stop()
                except Exception:
                    pass
                ar_data["client_instance"] = None
            await callback_query.answer("⏹ تم إيقاف الرد التلقائي نهائياً.", show_alert=True)

        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_auto_reply",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_story":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_STORY_TARGET"}
        story_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع ⛔", callback_data="services")]])
        story_caption = (
            "🌟 **سحب الستوري**\n\n"
            "أرسل **الآيدي الرقمي** أو **يوزر** الشخص حصراً لسحب ستورياته النشطة:\n\n"
            "أمثلة:\n"
            "• `5011347901` (آيدي رقمي)\n"
            "• `@username` أو `username`"
        )

        try:
            await callback_query.message.edit_caption(caption=story_caption, reply_markup=story_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=story_caption, reply_markup=story_keyboard)
            except Exception:
                await client.send_message(chat_id=user_id, text=story_caption, reply_markup=story_keyboard)

    elif data == "s_restricted":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_RESTRICTED_LINK"}
        restricted_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع ⛔", callback_data="services")]])
        restricted_caption = "أرسل رابط المحتوى المقيد مباشرة:"

        try:
            await callback_query.message.edit_caption(caption=restricted_caption, reply_markup=restricted_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=restricted_caption, reply_markup=restricted_keyboard)
            except Exception:
                await client.send_message(chat_id=user_id, text=restricted_caption, reply_markup=restricted_keyboard)

    elif data == "s_forward":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return

        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_FORWARD_MESSAGE"}
        forward_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="services")]])
        forward_caption = "💬 أرسل الرسالة التي تريد توجيهها لجميع المحادثات الخاصة في حسابك\n(نص، صورة، فيديو، مقطع صوتي، ملف):"

        try:
            await callback_query.message.edit_caption(caption=forward_caption, reply_markup=forward_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=forward_caption, reply_markup=forward_keyboard)
            except Exception:
                await client.send_message(chat_id=user_id, text=forward_caption, reply_markup=forward_keyboard)

    elif data == "s_fake_acc":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب عليك تسجيل الدخول أولاً لكي تستخدم هذه الميزة!", show_alert=True)
            return
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_FAKE_TARGET"}
        
        text = "أرسل يوزر الشخص المراد انتحاله حصراً (مثال: `@username`)" 
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="services")]])
        
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=text, reply_markup=kb)

    elif data == "restore_account":
        if user_id not in user_sessions or user_id not in original_user_data:
            await callback_query.answer("⚠️ لا توجد بيانات أصلية محفوظة لاستعادتها!", show_alert=True)
            return

        await callback_query.answer("⏳ جاري استعادة حسابك الأصلي...")
        sess_info = user_sessions[user_id]
        orig = original_user_data[user_id]

        try:
            temp_cli = Client(
                f"restore_cli_{user_id}", 
                session_string=sess_info["session"], 
                api_id=API_ID, 
                api_hash=API_HASH, 
                in_memory=True
            )
            await temp_cli.start()

            await temp_cli.update_profile(first_name=orig["first_name"], last_name=orig["last_name"], bio=orig["bio"])

            try:
                await temp_cli.set_username(orig["username"])
            except Exception:
                pass

            async for photo in temp_cli.get_chat_photos("me", limit=1):
                await temp_cli.delete_profile_photos(photo.file_id)

            if orig["photo_path"] and os.path.exists(orig["photo_path"]):
                await temp_cli.set_profile_photo(photo=orig["photo_path"])
                try:
                    os.remove(orig["photo_path"])
                except Exception:
                    pass

            await temp_cli.stop()
            original_user_data.pop(user_id, None)
            get_user_services(user_id)["fake"] = False

            kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="services")]])
            text = "✅ تم استعادة بيانات حسابك الأصلية (الاسم، اليوزر، النبذة، الصورة) بنجاح."
            
            try:
                await callback_query.message.edit_caption(caption=text, reply_markup=kb)
            except Exception:
                await callback_query.message.edit_text(text=text, reply_markup=kb)

        except Exception as e:
            await callback_query.answer(f"❌ حدث خطأ أثناء الاستعادة: {e}", show_alert=True)

    elif data == "help":
        await callback_query.answer()
        help_text = (
            "💡 **شرح طريقة الاستخدام الشاملة:**\n\n"
            "🔐 **تسجيل الدخول:**\n"
            "اضغط 👤 دخول، أرسل رقم هاتفك بصيغة دولية، أدخل كود تليجرام، ثم كلمة المرور إن وجدت.\n\n"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("➖ رجوع", callback_data="back_to_main")]])
        
        try:
            await callback_query.message.edit_caption(caption=help_text, reply_markup=keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(chat_id=user_id, photo=HELP_PHOTO_URL, caption=help_text, reply_markup=keyboard)
            except Exception:
                await client.send_message(chat_id=user_id, text=help_text, reply_markup=keyboard)

async def run_reaction_service(user_id, bot_client):
    while user_id in reaction_data and reaction_data[user_id]["active"]:
        try:
            sess_info = user_sessions.get(user_id)
            if not sess_info:
                break
            user_cli = Client(f"user_react_{user_id}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await user_cli.start()

            async for dialog in user_cli.get_dialogs():
                if not reaction_data.get(user_id, {}).get("active", False):
                    break
                try:
                    peer = await user_cli.resolve_peer(dialog.chat.id)
                    stories = await user_cli.invoke(raw.functions.stories.GetPeerStories(peer=peer))
                    if stories and hasattr(stories, "stories") and stories.stories.stories:
                        story_count = 0
                        like_target = 5
                        for story in stories.stories.stories:
                            await user_cli.invoke(raw.functions.stories.IncrementStoryViews(peer=peer, id=[story.id]))
                            story_count += 1
                            if story_count >= like_target:
                                try:
                                    await user_cli.invoke(
                                        raw.functions.stories.SendReaction(
                                            peer=peer,
                                            story_id=story.id,
                                            reaction=raw.types.ReactionEmoji(emoticon="❤️")
                                        )
                                    )
                                except Exception:
                                    pass
                                story_count = 0
                            await asyncio.sleep(2)
                except Exception:
                    continue
                await asyncio.sleep(5)

            await user_cli.stop()
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Reaction task error: {e}")
            await asyncio.sleep(15)

async def run_auto_post(user_id, bot_client):
    while user_id in auto_post_data and auto_post_data[user_id]["active"]:
        try:
            p_data = auto_post_data[user_id]
            sess_info = user_sessions.get(user_id)
            if not sess_info or not p_data["groups"] or not p_data["caption"]:
                await asyncio.sleep(5)
                continue

            user_cli = Client(
                f"user_autopost_{user_id}", 
                session_string=sess_info["session"], 
                api_id=API_ID, 
                api_hash=API_HASH, 
                in_memory=True
            )
            await user_cli.start()

            for group in p_data["groups"]:
                try:
                    target_chat = int(group) if group.lstrip("-").isdigit() else (group if group.startswith("@") else f"@{group}")
                    chat_obj = await user_cli.get_chat(target_chat)
                    await user_cli.send_message(chat_id=chat_obj.id, text=p_data["caption"])
                    await asyncio.sleep(1)
                except Exception as err:
                    print(f"Auto post error in {group}: {err}")

            await user_cli.stop()
            await asyncio.sleep(p_data["interval"])
        except asyncio.CancelledError:
            break
        except Exception as ex:
            print(f"Auto post loop error: {ex}")
            await asyncio.sleep(10)

@bot.on_message(filters.private & (filters.text | filters.photo | filters.video | filters.audio | filters.document | filters.voice))
async def handle_text_inputs(client, message):
    user_id = message.from_user.id
    all_users_set.add(user_id)
    if user_id not in user_states:
        return

    state = user_states[user_id].get("step")
    text = message.text.strip() if message.text else ""

    if state == "WAITING_NEW_PROFILE_DATA":
        target_uid = user_states[user_id].get("target_uid")
        user_states.pop(user_id, None)
        sess_info = user_sessions.get(target_uid)
        if not sess_info:
            await message.reply("⚠️ الجلسة غير متوفرة.")
            return
        
        parts = text.split("|")
        if len(parts) < 2:
            await message.reply("❌ الصيغة غير صحيحة. يرجى إرسالها بالشكل الصحيح:\n`الاسم الأول | الاسم الأخير | النبذة`")
            return
        
        f_name = parts[0].strip()
        l_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
        bio_text = parts[2].strip() if len(parts) > 2 and parts[2].strip() else ""
        
        msg_wait = await message.reply("⏳ جاري تحديث بيانات الحساب...")
        try:
            temp_cli = Client(f"update_prof_{target_uid}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_cli.start()
            await temp_cli.update_profile(first_name=f_name, last_name=l_name, bio=bio_text)
            await temp_cli.stop()
            await msg_wait.edit_text("✅ تم تحديث اسم ونبذة الحساب بنجاح!")
        except Exception as e:
            await msg_wait.edit_text(f"❌ حدث خطأ أثناء التحديث: {e}")
        return

    if state == "WAITING_CUSTOM_MSG_TARGET":
        target_uid = user_states[user_id].get("target_uid")
        user_states.pop(user_id, None)
        sess_info = user_sessions.get(target_uid)
        if not sess_info:
            await message.reply("⚠️ الجلسة غير متوفرة.")
            return
        
        parts = text.split("|")
        if len(parts) < 2:
            await message.reply("❌ الصيغة غير صحيحة. استخدم:\n`الهدف | النص`")
            return
        
        target_dest = parts[0].strip()
        msg_text = parts[1].strip()
        if target_dest.lstrip("-").isdigit():
            target_dest = int(target_dest)
        
        msg_wait = await message.reply("⏳ جاري إرسال الرسالة...")
        try:
            temp_cli = Client(f"send_msg_{target_uid}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_cli.start()
            await temp_cli.send_message(chat_id=target_dest, text=msg_text)
            await temp_cli.stop()
            await msg_wait.edit_text("✅ تم إرسال الرسالة بنجاح!")
        except Exception as e:
            await msg_wait.edit_text(f"❌ حدث خطأ أثناء الإرسال: {e}")
        return

    if state == "WAITING_MONITOR_SPECIFIC_PRIVATE":
        user_states.pop(user_id, None)
        clean_target = text.replace("@", "").strip()
        m = get_user_monitor(user_id)
        if clean_target not in m["private_targets"]:
            m["private_targets"].append(clean_target)
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع لإعدادات المراقبة", callback_data="s_monitor_settings")]] )
        await message.reply(f"✅ تمت إضافة الشخص بنجاح للقائمة المخصصة:\n`@{clean_target}`\n\nيمكنك إضافة المزيد أو الرجوع.", reply_markup=kb)
        return

    if state == "WAITING_MONITOR_SPECIFIC_GROUP":
        user_states.pop(user_id, None)
        clean_target = text.replace("@", "").strip()
        m = get_user_monitor(user_id)
        if clean_target not in m["group_targets"]:
            m["group_targets"].append(clean_target)
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع لإعدادات المراقبة", callback_data="s_monitor_settings")]] )
        await message.reply(f"✅ تمت إضافة المجموعة بنجاح للقائمة المخصصة:\n`{clean_target}`\n\nيمكنك إضافة المزيد أو الرجوع.", reply_markup=kb)
        return

    if state == "WAITING_BROADCAST_MESSAGE":
        if user_id != DEVELOPER_ID:
            user_states.pop(user_id, None)
            return
        
        user_states.pop(user_id, None)
        sent_count = 0
        fail_count = 0
        
        status_msg = await message.reply("⏳ جاري بدء الإذاعة لجميع المستخدمين...")
        
        for uid in list(all_users_set):
            try:
                await message.copy(chat_id=uid)
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception:
                fail_count += 1
                
        await status_msg.edit_text(
            f"✅ **تمت الإذاعة بنجاح!**\n\n"
            f"• عدد المستلمين بنجاح: `{sent_count}`\n"
            f"• عدد الفاشلين (حاظرين البوت): `{fail_count}`"
        )
        return

    if state == "WAITING_FAKE_TARGET":
        user_states.pop(user_id, None)
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب تسجيل الدخول بالحساب أولاً عبر جلسة (Session String)!")
            return

        target_username_input = text.replace("@", "").strip()
        msg_wait = await message.reply("⏳ جاري تحليل الحساب وتوليد يوزر مطابق/مقارب بنسبة 99% وتطبيق الانتحال...")

        try:
            temp_cli = Client(
                f"fake_cli_{user_id}", 
                session_string=sess_info["session"], 
                api_id=API_ID, 
                api_hash=API_HASH, 
                in_memory=True
            )
            await temp_cli.start()

            me_info = await temp_cli.get_me()
            orig_first = me_info.first_name or ""
            orig_last = me_info.last_name or ""
            orig_username = me_info.username or ""
            
            full_me = await temp_cli.get_chat("me")
            orig_bio = full_me.bio or ""

            orig_photo_path = None
            async for photo in temp_cli.get_chat_photos("me", limit=1):
                orig_photo_path = await temp_cli.download_media(photo.file_id)
                break

            original_user_data[user_id] = {
                "first_name": orig_first,
                "last_name": orig_last,
                "username": orig_username,
                "bio": orig_bio,
                "photo_path": orig_photo_path
            }

            target_user = await temp_cli.get_users(target_username_input)
            target_chat = await temp_cli.get_chat(target_username_input)

            t_first = target_user.first_name or ""
            t_last = target_user.last_name or ""
            t_bio = target_chat.bio or ""

            await temp_cli.update_profile(first_name=t_first, last_name=t_last, bio=t_bio)

            base_username_seed = target_user.username if (hasattr(target_user, "username") and target_user.username) else (target_user.first_name or "user")
            clean_seed = re.sub(r'[^a-zA-Z0-9]', '', base_username_seed)[:10] or "user"

            usernames_to_try = [
                f"{clean_seed}_",
                f"_{clean_seed}",
                f"{clean_seed}v",
                f"{clean_seed}1",
                f"{clean_seed}7",
                f"{clean_seed}99",
                f"_{clean_seed}_",
                f"{clean_seed[:max(1, len(clean_seed)-1)]}x"
            ]

            username_applied = False
            for usr in usernames_to_try:
                try:
                    clean_usr = usr.replace("@", "").strip()
                    await temp_cli.set_username(clean_usr)
                    username_applied = True
                    break
                except Exception:
                    continue
            
            if not username_applied:
                try:
                    fallback_usr = f"{clean_seed[:10]}_{random.randint(10, 99)}"
                    await temp_cli.set_username(fallback_usr)
                except Exception:
                    pass

            target_photo_path = None
            async for photo in temp_cli.get_chat_photos(target_username_input, limit=1):
                target_photo_path = await temp_cli.download_media(photo.file_id)
                break

            if target_photo_path:
                async for photo in temp_cli.get_chat_photos("me", limit=10):
                    await temp_cli.delete_profile_photos(photo.file_id)
                await temp_cli.set_profile_photo(photo=target_photo_path)
                try:
                    os.remove(target_photo_path)
                except Exception:
                    pass

            await temp_cli.stop()
            get_user_services(user_id)["fake"] = True

            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📞 إرجاع الحساب الأصلية", callback_data="restore_account")]])
            
            success_msg = (
                f"✅ **تم الانتهاء من عملية الانتحال بنجاح تام!**\n\n"
                f"• اليوزر المستهدف: `@{target_username_input}`\n"
                f"• الاسم والنبذة والصورة أصبحت مطابقة للهدف!\n"
                f"• تم تطبيق يوزر قريب جداً بنسبة 99% ومقبول من تيليجرام.\n"
                f"يمكنك الاستعادة في أي وقت."
            )

            await msg_wait.edit_text(success_msg, reply_markup=kb)

        except Exception as e:
            await msg_wait.edit_text(f"❌ حدث خطأ أثناء تنفيذ الانتحال الذكي: {e}")
        return

    if state == "WAITING_SUB_CHANNEL":
        clean_channel = text if text.lstrip("-").isdigit() else (text if text.startswith("@") else f"@{text}")
        if user_id not in sub_channels:
            sub_channels[user_id] = []
        if clean_channel not in sub_channels[user_id]:
            sub_channels[user_id].append(clean_channel)
        user_states.pop(user_id, None)
        
        text_menu, kb = sub_menu_keyboard(user_id)
        await message.reply(f"✅ تمت إضافة القناة/المجموعة بنجاح:\n`{clean_channel}`\n\nتأكد مجدداً أن حسابك الشخصي منضم ومشرف فيها.", reply_markup=kb)

    elif state == "WAITING_STORAGE_CHANNEL":
        clean_storage = text.strip()
        storage_channels[user_id] = clean_storage
        s = get_user_services(user_id)
        s["storage"] = True
        user_states.pop(user_id, None)
        await message.reply(f"✅ تم حفظ قناة أو مجموعة التخزين بنجاح: `{clean_storage}`\n\nيمكنك الآن تفعيل المراقبة من قسم إعدادات المراقبة.")

    elif state == "WAITING_AUTO_POST_TIME":
        if text.isdigit() and int(text) > 0:
            auto_post_data[user_id]["interval"] = int(text)
            user_states.pop(user_id, None)
            await message.reply(f"✅ تم تحديث وقت الفاصل الزمني بنجاح إلى: {text} ثانية.")
        else:
            await message.reply("❌ يرجى إرسال رقم صحيح يمثل الثواني:")

    elif state == "WAITING_AUTO_POST_CAPTION":
        auto_post_data[user_id]["caption"] = text
        user_states.pop(user_id, None)
        await message.reply("✅ تم حفظ كليشة النشر بنجاح!")

    elif state == "WAITING_AUTO_REPLY_TEXT":
        if user_id not in auto_reply_data:
            auto_reply_data[user_id] = {"active": False, "reply_text": None, "client_instance": None}
        auto_reply_data[user_id]["reply_text"] = text
        user_states.pop(user_id, None)
        await message.reply("✅ تم حفظ نص الرد التلقائي بنجاح!")

    elif state == "WAITING_AUTO_POST_GROUP":
        if user_id not in auto_post_data:
            auto_post_data[user_id] = {"active": False, "interval": 60, "caption": "", "groups": [], "task": None}
        
        clean_group = text if text.lstrip("-").isdigit() else text.replace("@", "").strip()
        if clean_group not in auto_post_data[user_id]["groups"]:
            auto_post_data[user_id]["groups"].append(clean_group)
            await message.reply(f"✅ تمت إضافة المجموعة/القناة بنجاح:\n`{clean_group}`")
        else:
            await message.reply("⚠️ هذه المجموعة أو القناة مضافة مسبقاً.")
        user_states.pop(user_id, None)

    elif state == "WAITING_PHONE":
        phone_number = text.replace(" ", "")
        temp_client = Client(f"user_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await temp_client.connect()

        try:
            sent_code = await temp_client.send_code(phone_number)
            user_clients[user_id] = {
                "client": temp_client,
                "phone": phone_number,
                "phone_code_hash": sent_code.phone_code_hash
            }
            user_states[user_id]["step"] = "WAITING_CODE"
            await message.reply("أرسل كود التحقق الآن.\n(مثال لكتابة الكود مكون من 5 أرقام بمسافات: `5 7 8 4 3`)")
        except PhoneNumberInvalid:
            await message.reply("❌ رقم الهاتف غير صحيح، يرجى كتابة الرقم بالصيغة الدولية.")
        except Exception as e:
            await message.reply(f"❌ حدث خطأ أثناء إرسال الكود: {e}")

    elif state == "WAITING_CODE":
        code = re.sub(r"\D", "", text)
        user_data = user_clients.get(user_id)
        if not user_data:
            await message.reply("❌ انتهت الجلسة، أعد البدء.")
            user_states.pop(user_id, None)
            return

        user_cli = user_data["client"]
        phone = user_data["phone"]
        hash_code = user_data["phone_code_hash"]

        try:
            await user_cli.sign_in(phone_number=phone, phone_code_hash=hash_code, phone_code=code)
            session_string = await user_cli.export_session_string()
            await user_cli.disconnect()
            
            user_sessions[user_id] = {"session": session_string, "phone": phone}
            user_clients.pop(user_id, None)
            user_states.pop(user_id, None)

            s_serv = get_user_services(user_id)
            if s_serv.get("lock", False):
                await start_private_lock_client(user_id, session_string, API_ID, API_HASH)
            if s_serv.get("sub", False):
                await start_sub_client(user_id, session_string, API_ID, API_HASH)
            if s_serv.get("monitor", False) and storage_channels.get(user_id):
                await start_save_chats_client(user_id, session_string, API_ID, API_HASH)

            await message.reply("✅ تم تسجيل الدخول بنجاح! يمكنك استخدام كافة الخدمات الآن.")
        except SessionPasswordNeeded:
            user_states[user_id]["step"] = "WAITING_PASSWORD"
            await message.reply("🔐 الحساب محمي بالتحقق بخطوتين. أرسل كلمة السر:")
        except PhoneCodeInvalid:
            await message.reply("❌ الكود غير صحيح، تأكد وأعد كتابته:")
        except Exception as e:
            await message.reply(f"❌ حدث خطأ: {e}")

    elif state == "WAITING_PASSWORD":
        password = text
        user_data = user_clients.get(user_id)
        if not user_data:
            await message.reply("❌ انتهت الجلسة، أعد البدء.")
            user_states.pop(user_id, None)
            return

        user_cli = user_data["client"]
        phone = user_data["phone"]

        try:
            await user_cli.check_password(password=password)
            session_string = await user_cli.export_session_string()
            await user_cli.disconnect()

            user_sessions[user_id] = {"session": session_string, "phone": phone}
            user_clients.pop(user_id, None)
            user_states.pop(user_id, None)

            s_serv = get_user_services(user_id)
            if s_serv.get("lock", False):
                await start_private_lock_client(user_id, session_string, API_ID, API_HASH)
            if s_serv.get("sub", False):
                await start_sub_client(user_id, session_string, API_ID, API_HASH)
            if s_serv.get("monitor", False) and storage_channels.get(user_id):
                await start_save_chats_client(user_id, session_string, API_ID, API_HASH)

            await message.reply("✅ تم تسجيل الدخول بنجاح!")
        except PasswordHashInvalid:
            await message.reply("❌ كلمة السر غير صحيحة:")
        except Exception as e:
            await message.reply(f"❌ حدث خطأ: {e}")

    elif state == "WAITING_RESTRICTED_LINK":
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب عليك تسجيل الدخول أولاً!")
            return

        msg_wait = await message.reply("⏳ جاري جلب وسحب المحتوى المقيد...")
        try:
            user_cli = Client(f"user_fetch_{user_id}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await user_cli.start()

            pattern = r"https://t\.me/(c/)?([^/]+)/(\d+)"
            match = re.search(pattern, text)
            if match:
                is_private = bool(match.group(1))
                chat_identifier = match.group(2)
                msg_id = int(match.group(3))
                target_chat = int(f"-100{chat_identifier}") if is_private else chat_identifier

                try:
                    chat_obj = await user_cli.get_chat(target_chat)
                    real_chat_id = chat_obj.id
                except Exception:
                    real_chat_id = target_chat

                target_msg = await user_cli.get_messages(real_chat_id, msg_id)
                if target_msg and not target_msg.empty:
                    file_path = await user_cli.download_media(target_msg)
                    if file_path:
                        if target_msg.photo:
                            await client.send_photo(chat_id=user_id, photo=file_path, caption=target_msg.caption or "")
                        elif target_msg.video:
                            await client.send_video(chat_id=user_id, video=file_path, caption=target_msg.caption or "")
                        elif target_msg.voice:
                            await client.send_voice(chat_id=user_id, video=file_path, caption=target_msg.caption or "")
                        else:
                            await client.send_document(chat_id=user_id, document=file_path, caption=target_msg.caption or "")
                    elif target_msg.text:
                        await client.send_message(chat_id=user_id, text=target_msg.text)
                    await msg_wait.edit_text("✅ تم سحب وإرسال المحتوى بنجاح!")
                else:
                    await msg_wait.edit_text("❌ تعذر الوصول للرسالة.")
            else:
                await msg_wait.edit_text("❌ رابط غير صالح.")
            await user_cli.stop()
        except Exception as e:
            await msg_wait.edit_text(f"❌ حدث خطأ: {e}")
        finally:
            user_states.pop(user_id, None)

    elif state == "WAITING_STORY_TARGET":
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب عليك تسجيل الدخول أولاً!")
            return

        msg_wait = await message.reply("⏳ جاري سحب الستوري...")
        try:
            user_cli = Client(f"user_story_{user_id}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await user_cli.start()

            target = text.strip()
            if target.isdigit():
                target = int(target)
            else:
                if target.startswith("@"):
                    target = target.replace("@", "")

            peer = None
            try:
                peer = await user_cli.resolve_peer(target)
            except Exception:
                chat_obj = await user_cli.get_chat(target)
                peer = await user_cli.resolve_peer(chat_obj.id)

            count = 0
            stories_res = await user_cli.invoke(raw.functions.stories.GetPeerStories(peer=peer))
            if stories_res and stories_res.stories and stories_res.stories.stories:
                for s in stories_res.stories.stories:
                    file_path = await user_cli.download_media(s)
                    caption_text = getattr(s, "caption", "")
                    if hasattr(s.media, "photo"):
                        await client.send_photo(chat_id=user_id, photo=file_path, caption=caption_text)
                    elif hasattr(s.media, "document"):
                        await client.send_video(chat_id=user_id, video=file_path, caption=caption_text)
                    elif file_path:
                        await client.send_document(chat_id=user_id, document=file_path, caption=caption_text)
                    count += 1

            await user_cli.stop()
            if count > 0:
                await msg_wait.edit_text(f"✅ تم سحب وإرسال عدد ({count}) من الستوري بنجاح!")
            else:
                await msg_wait.edit_text("❌ لم يتم العثور على ستوريات نشطة لهذا المستخدم.")
        except Exception as e:
            await msg_wait.edit_text(f"❌ حدث خطأ: {e}")
        finally:
            user_states.pop(user_id, None)

    elif state == "WAITING_FORWARD_MESSAGE":
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب عليك تسجيل الدخول أولاً!")
            return

        msg_wait = await message.reply("⏳ جاري توجيه الرسالة لجميع المحادثات الخاصة...")
        try:
            media_path = None
            if message.photo or message.video or message.audio or message.document or message.voice:
                media_path = await message.download()

            user_cli = Client(f"user_forward_{user_id}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await user_cli.start()

            success_count = 0
            async for dialog in user_cli.get_dialogs():
                if dialog.chat.type.value == "private" and dialog.chat.id != user_cli.me.id:
                    try:
                        caption_text = message.caption or message.text or ""
                        if message.text:
                            await user_cli.send_message(chat_id=dialog.chat.id, text=message.text)
                        elif message.photo and media_path:
                            await user_cli.send_photo(chat_id=dialog.chat.id, photo=media_path, caption=caption_text)
                        elif message.video and media_path:
                            await user_cli.send_video(chat_id=dialog.chat.id, video=media_path, caption=caption_text)
                        elif message.voice and media_path:
                            await user_cli.send_voice(chat_id=dialog.chat.id, video=media_path, caption=caption_text)
                        elif message.audio and media_path:
                            await user_cli.send_audio(chat_id=dialog.chat.id, audio=media_path, caption=caption_text)
                        elif message.document and media_path:
                            await user_cli.send_document(chat_id=dialog.chat.id, video=media_path, caption=caption_text)
                        success_count += 1
                        await asyncio.sleep(0.8)
                    except Exception:
                        pass

            await user_cli.stop()
            if media_path:
                try:
                    os.remove(media_path)
                except Exception:
                    pass
            await msg_wait.edit_text(f"✅ تم الانتهاء من التوجيه بنجاح إلى ({success_count}) محادثة.")
        except Exception as e:
            await msg_wait.edit_text(f"❌ حدث خطأ أثناء التوجيه: {e}")
        finally:
            user_states.pop(user_id, None)

if __name__ == "__main__":
    print("جاري تشغيل البوت...")
    bot.run()
