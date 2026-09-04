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
private_lock_settings = {} 

def get_user_services(user_id):
    if user_id not in user_services_status:
        user_services_status[user_id] = {
            "storage": False,
            "monitor": False,
            "save_chats": False,
            "reply": False,
            "react": False,
            "lock": False,
            "sub": False,
            "fake": False
        }
    return user_services_status[user_id]

def get_lock_settings(user_id):
    if user_id not in private_lock_settings:
        private_lock_settings[user_id] = {
            "mode": "all", 
            "users": []    
        }
    return private_lock_settings[user_id]

def lock_menu_keyboard(user_id):
    s = get_user_services(user_id)
    is_locked = s.get("lock", False)
    toggle_btn_text = "إيقاف القفل 🔴" if is_locked else "تفعيل القفل ⚙️"
    
    lock_info = get_lock_settings(user_id)
    mode_text = "قفل الكل 🌐" if lock_info["mode"] == "all" else "قفل محددين 👥"
    mode_toggle_target = "lock_set_custom" if lock_info["mode"] == "all" else "lock_set_all"

    text = f"🔒 **قفل الخاص**\n• الوضع الحالي: `{mode_text}`"
    keyboard = [
        [InlineKeyboardButton(toggle_btn_text, callback_data="toggle_private_lock")],
        [InlineKeyboardButton(f"التحويل إلى: {'قفل محددين 👥' if lock_info['mode'] == 'all' else 'قفل الكل 🌐'}", callback_data=mode_toggle_target)],
    ]
    
    if lock_info["mode"] == "custom":
        keyboard.append([
            InlineKeyboardButton("➕ إضافة شخص", callback_data="lock_add_user"),
            InlineKeyboardButton("📋 عرض القائمة", callback_data="lock_show_users")
        ])
        keyboard.append([InlineKeyboardButton("🗑 حذف الكل", callback_data="lock_clear_users")])

    keyboard.append([InlineKeyboardButton("رجوع 🛑", callback_data="services")])
    return text, InlineKeyboardMarkup(keyboard)

def sub_menu_keyboard(user_id):
    s = get_user_services(user_id)
    is_active = s.get("sub", False)
    toggle_btn_text = "إيقاف 🛑" if is_active else "تشغيل ⚙️"
    
    text = "💲 **اشتراك إجباري للخاص**"
    keyboard = [
        [InlineKeyboardButton("➕ تحديد قناة", callback_data="sub_set_channel"), InlineKeyboardButton("🗑 حذف الكل", callback_data="sub_delete_channel")],
        [InlineKeyboardButton(toggle_btn_text, callback_data="toggle_sub_status")],
        [InlineKeyboardButton("رجوع 🛑", callback_data="services")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

async def forward_or_send_media(target_chat_id, message, log_caption, user_cli, is_bot_target=False):
    try:
        file_path = await message.download()
        if file_path:
            if is_bot_target:
                if message.photo:
                    await bot.send_photo(chat_id=target_chat_id, photo=file_path, caption=log_caption)
                elif message.video:
                    await bot.send_video(chat_id=target_chat_id, video=file_path, caption=log_caption)
                elif message.audio:
                    await bot.send_audio(chat_id=target_chat_id, audio=file_path, caption=log_caption)
                elif message.voice:
                    await bot.send_voice(chat_id=target_chat_id, voice=file_path, caption=log_caption)
                elif message.sticker:
                    await bot.send_sticker(chat_id=target_chat_id, sticker=file_path)
                    await bot.send_message(chat_id=target_chat_id, text=log_caption)
                elif message.animation:
                    await bot.send_animation(chat_id=target_chat_id, animation=file_path, caption=log_caption)
                elif message.video_note:
                    await bot.send_video_note(chat_id=target_chat_id, video_note=file_path)
                    await bot.send_message(chat_id=target_chat_id, text=log_caption)
                else:
                    await bot.send_document(chat_id=target_chat_id, document=file_path, caption=log_caption)
            else:
                if message.photo:
                    await user_cli.send_photo(chat_id=target_chat_id, photo=file_path, caption=log_caption)
                elif message.video:
                    await user_cli.send_video(chat_id=target_chat_id, video=file_path, caption=log_caption)
                elif message.audio:
                    await user_cli.send_audio(chat_id=target_chat_id, audio=file_path, caption=log_caption)
                elif message.voice:
                    await user_cli.send_voice(chat_id=target_chat_id, video=file_path, caption=log_caption)
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
            if is_bot_target:
                await bot.send_message(chat_id=target_chat_id, text=log_caption)
            else:
                await user_cli.send_message(chat_id=target_chat_id, text=log_caption)
    except Exception as e:
        print(f"Failed to send media file: {e}")
        try:
            if is_bot_target:
                await bot.send_message(chat_id=target_chat_id, text=log_caption)
            else:
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
        is_save_chats_active = s.get("save_chats", False)
        storage_ch = storage_channels.get(user_id)

        if not is_monitor_active and not is_save_chats_active:
            return
        
        if message.outgoing:
            return

        if message.chat.type.value != "private":
            return
        if not message.from_user or message.from_user.is_bot or message.from_user.id in [777000, 42777]:
            return

        sender_id = message.from_user.id
        sender_name = message.from_user.first_name or "مستخدم"
        if message.from_user.last_name:
            sender_name += f" {message.from_user.last_name}"
        username_str = f"@{message.from_user.username}" if message.from_user.username else "بدون يوزر"

        msg_id = message.id
        current_time = datetime.now().strftime('%H:%M:%S %Y-%m-%d')

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
        original_messages_cache[user_id][msg_id] = {
            "message_obj": message,
            "text": msg_content_desc if msg_content_desc else "[محتوى نصي غير متوفر]",
            "media": message.media,
            "outgoing": message.outgoing
        }

        reply_info = ""
        if message.reply_to_message:
            reply_text_snippet = message.reply_to_message.text or message.reply_to_message.caption or "ميديا أو محتوى بدون نص"
            reply_info = f"\n↩️ **رد على رسالة:** `{reply_text_snippet[:50]}`\n"

        log_text = (
            f"📥 **تفاصيل الرسالة الواردة (خاص)**\n\n"
            f"• الاسم: {sender_name}\n"
            f"• الآيدي: `{sender_id}`\n"
            f"• اليوزر: {username_str}\n"
            f"• الوقت: {current_time}\n"
            f"• النوع: {media_type} {'(مؤقتة ⏱️)' if is_view_once else ''}\n"
            f"• رقم الرسالة: `{msg_id}`"
            f"{reply_info}\n"
            f"📝 **المحتوى:**\n{msg_content_desc if msg_content_desc else '[محتوى فارغ أو ميديا]'}"
        )
        
        if is_monitor_active:
            try:
                if message.media:
                    await forward_or_send_media(user_id, message, log_text, user_cli, is_bot_target=True)
                else:
                    await bot.send_message(chat_id=user_id, text=log_text)
            except Exception as e:
                print(f"Error sending to bot: {e}")

        if is_save_chats_active and storage_ch:
            try:
                target_chat_dest = int(storage_ch) if (storage_ch.lstrip("-").isdigit()) else storage_ch
                if message.media:
                    await forward_or_send_media(target_chat_dest, message, log_text, user_cli, is_bot_target=False)
                else:
                    await user_cli.send_message(chat_id=target_chat_dest, text=log_text)
            except Exception as e:
                print(f"Error saving to storage channel: {e}")

    @user_cli.on_edited_message(~filters.me)
    async def edited_messages_handler(client, message):
        s = get_user_services(user_id)
        if not s.get("monitor", False) and not s.get("save_chats", False):
            return

        if message.chat.type.value != "private":
            return
        if not message.from_user or message.from_user.is_bot or message.from_user.id in [777000, 42777]:
            return

        sender_name = message.from_user.first_name if message.from_user else "مستخدم"
        sender_id = message.from_user.id if message.from_user else 0
        username_str = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "بدون يوزر"
        msg_id = message.id
        new_text = message.text or message.caption or ""
        current_time = datetime.now().strftime('%H:%M:%S %Y-%m-%d')

        original_text = "[محتوى نصي غير متوفر]"
        if user_id in original_messages_cache and msg_id in original_messages_cache[user_id]:
            original_text = original_messages_cache[user_id][msg_id]["text"] or "[محتوى نصي غير متوفر]"

        edit_log = (
            "✏️ **تم تعديل رسالة!**\n\n"
            f"• الاسم: {sender_name}\n"
            f"• الآيدي: `{sender_id}`\n"
            f"• الوقت: {current_time}\n"
            f"• رقم الرسالة: `{msg_id}`\n\n"
            f"📜 **الأصلية:**\n{original_text}\n\n"
            f"📝 **بعد التعديل:**\n{new_text}"
        )

        if user_id in original_messages_cache:
            if msg_id in original_messages_cache[user_id]:
                original_messages_cache[user_id][msg_id]["text"] = new_text

        if s.get("monitor", False):
            try:
                if message.media:
                    await forward_or_send_media(user_id, message, edit_log, user_cli, is_bot_target=True)
                else:
                    await bot.send_message(chat_id=user_id, text=edit_log)
            except Exception as e:
                print(f"Error sending edit to bot: {e}")

        storage_ch = storage_channels.get(user_id)
        if s.get("save_chats", False) and storage_ch:
            try:
                target_chat_dest = int(storage_ch) if (storage_ch.lstrip("-").isdigit()) else storage_ch
                if message.media:
                    await forward_or_send_media(target_chat_dest, message, edit_log, user_cli, is_bot_target=False)
                else:
                    await client.send_message(chat_id=target_chat_dest, text=edit_log)
            except Exception as e:
                print(f"Error handling edited message for channel: {e}")

    @user_cli.on_deleted_messages()
    async def deleted_messages_handler(client, messages):
        s = get_user_services(user_id)
        if not s.get("monitor", False) and not s.get("save_chats", False):
            return

        for message in messages:
            if not hasattr(message, "chat") or not message.chat or message.chat.type.value != "private":
                continue

            msg_id = message.id
            cached_data = None
            if user_id in original_messages_cache and msg_id in original_messages_cache[user_id]:
                cached_data = original_messages_cache[user_id][msg_id]
            
            if cached_data and cached_data.get("outgoing"):
                continue

            current_time = datetime.now().strftime('%H:%M:%S %Y-%m-%d')
            original_text = cached_data["text"] if (cached_data and cached_data["text"]) else "[تم حذف الرسالة الأصلية من المرسل - المحتوى غير متوفر]"
            has_media = cached_data and cached_data["media"]

            delete_log = (
                "🗑 **تم حذف رسالة بواسطة الطرف الآخر!**\n\n"
                f"• الوقت: {current_time}\n"
                f"• رقم الرسالة: `{msg_id}`\n\n"
                f"📄 **المحتوى المحذوف:**\n{original_text}"
            )
            
            if s.get("monitor", False):
                try:
                    if has_media and cached_data and cached_data.get("message_obj"):
                        await forward_or_send_media(user_id, cached_data["message_obj"], delete_log, user_cli, is_bot_target=True)
                    else:
                        await bot.send_message(chat_id=user_id, text=delete_log)
                except Exception as e:
                    print(f"Error sending delete to bot: {e}")

            storage_ch = storage_channels.get(user_id)
            if s.get("save_chats", False) and storage_ch:
                try:
                    target_chat_dest = int(storage_ch) if (storage_ch.lstrip("-").isdigit()) else storage_ch
                    if has_media and cached_data and cached_data.get("message_obj"):
                        await forward_or_send_media(target_chat_dest, cached_data["message_obj"], delete_log, user_cli, is_bot_target=False)
                    else:
                        await client.send_message(chat_id=target_chat_dest, text=delete_log)
                except Exception as e:
                    print(f"Error handling deleted message for channel: {e}")

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
                    channels_text_display += f"• القناة (آيدي): `{ch}`\n"
                else:
                    ch_clean = ch.replace("@", "")
                    channels_text_display += f"• القناة: @{ch_clean}\n"
                    buttons.append([InlineKeyboardButton(f"اشتراك 🔔 (@{ch_clean})", url=f"https://t.me/{ch_clean}")])
            
            buttons.append([InlineKeyboardButton("تحقق من الاشتراك 🔄", callback_data=f"check_sub_{sender_id}")])
            keyboard = InlineKeyboardMarkup(buttons)
            
            try:
                await client.send_message(
                    chat_id=sender_id,
                    text=(
                        "⚠️ **عذراً، يجب الاشتراك في القنوات التالية للمراسلة:**\n\n"
                        f"{channels_text_display}\n"
                        "يرجى الاشتراك ثم اضغط تحقق 🤍."
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
            await callback_query.answer("⚠️ لم يتم تحديد قنوات.", show_alert=True)
            return

        all_joined = True
        for ch in channels:
            joined = await check_user_sub(client, ch, sender_id)
            if not joined:
                all_joined = False
                break

        if all_joined:
            await callback_query.answer("✅ تم التحقق بنجاح!", show_alert=True)
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_message(chat_id=sender_id, text="🎉 **تم بنجاح!** يمكنك إرسال رسالتك الآن.")
            except Exception:
                pass
        else:
            await callback_query.answer("❌ لم تقم بالاشتراك في كافة القنوات بعد!", show_alert=True)

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
        if not s.get("lock", False):
            return
        
        if not message.from_user or message.from_user.is_bot or message.outgoing:
            return

        lock_info = get_lock_settings(user_id)
        mode = lock_info["mode"]
        locked_users = lock_info["users"]

        should_delete = False
        if mode == "all":
            should_delete = True
        elif mode == "custom":
            sender_id = str(message.from_user.id)
            sender_username = f"@{message.from_user.username}" if message.from_user.username else ""
            if sender_id in locked_users or sender_username in locked_users:
                should_delete = True

        if should_delete:
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
        [InlineKeyboardButton("💡 الشرح", callback_data="help"), InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/its_h_q")]
    ]
    if user_id == DEVELOPER_ID:
        keyboard.append([
            InlineKeyboardButton("📢 إذاعة عامة", callback_data="admin_broadcast"),
            InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")
        ])
    return InlineKeyboardMarkup(keyboard)

def services_menu_keyboard(user_id):
    s = get_user_services(user_id)
    ico = lambda key: "✅" if s.get(key, False) else ""

    services_text = "🌐 قائـمة الخدمـات 💬"

    monitor_btn_text = f"🛡️ المراقبة {ico('monitor')}"
    save_chats_btn_text = f"💾 حفظ المحادثات {ico('save_chats')}"

    keyboard = [
        [InlineKeyboardButton("🌟 ستوري", callback_data="s_story"), InlineKeyboardButton("🔒 مقيد", callback_data="s_restricted")],
        [InlineKeyboardButton("🔄 نشر 24", callback_data="s_auto_post"), InlineKeyboardButton("📞 توجيه خاص", callback_data="s_forward")],
        [InlineKeyboardButton("🔄 رد 24", callback_data="s_auto_reply"), InlineKeyboardButton("⚡ تفاعل", callback_data="s_reaction")],
        [InlineKeyboardButton("👻 انتحال", callback_data="s_fake_acc"), InlineKeyboardButton(f"📱 تخزين {ico('storage')}", callback_data="s_channel")],
        [InlineKeyboardButton(f"📞 قفل الخاص {ico('lock')}", callback_data="s_private_lock"), InlineKeyboardButton(f"💲 اشتراك {ico('sub')}", callback_data="sub_menu")],
        [InlineKeyboardButton(monitor_btn_text, callback_data="toggle_monitor_direct"), InlineKeyboardButton(save_chats_btn_text, callback_data="toggle_save_chats_direct")],
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

    if data == "admin_stats":
        if user_id != DEVELOPER_ID:
            await callback_query.answer("⚠️ للمطور فقط!", show_alert=True)
            return
        await callback_query.answer()
        
        total_users = len(all_users_set)
        active_sessions_count = len(user_sessions)
        
        stats_text = (
            "📊 **إحصائيات البوت:**\n\n"
            f"• المستخدمين: `{total_users}`\n"
            f"• الجلسات النشطة: `{active_sessions_count}`"
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
            await callback_query.answer("⚠️ للمطور فقط!", show_alert=True)
            return
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_BROADCAST_MESSAGE"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="back_to_main")]])
        text = "📢 **إذاعة عامة**\n\nأرسل رسالة الإذاعة الآن:"
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

    elif data == "toggle_monitor_direct":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["monitor"] = not s["monitor"]

        sess_info = user_sessions.get(user_id)
        if s["monitor"] or s.get("save_chats", False):
            if sess_info:
                await start_save_chats_client(user_id, sess_info["session"], API_ID, API_HASH)
        else:
            if not s["monitor"] and not s.get("save_chats", False):
                await stop_save_chats_client(user_id)

        if s["monitor"]:
            await callback_query.answer("✅ تم تشغيل المراقبة بنجاح!", show_alert=True)
        else:
            await callback_query.answer("🛑 تم إيقاف المراقبة.", show_alert=True)

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

    elif data == "toggle_save_chats_direct":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        if not storage_channels.get(user_id):
            await callback_query.answer("⚠️ عذراً، يجب تحديد قناة التخزين أولاً لتفعيل ميزة حفظ المحادثات!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["save_chats"] = not s["save_chats"]

        sess_info = user_sessions.get(user_id)
        if s["save_chats"] or s.get("monitor", False):
            if sess_info:
                await start_save_chats_client(user_id, sess_info["session"], API_ID, API_HASH)
        else:
            if not s.get("monitor", False) and not s["save_chats"]:
                await stop_save_chats_client(user_id)

        if s["save_chats"]:
            await callback_query.answer("✅ تم تفعيل حفظ المحادثات بقناة التخزين بنجاح!", show_alert=True)
        else:
            await callback_query.answer("🛑 تم إيقاف حفظ المحادثات بقناة التخزين.", show_alert=True)

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

    elif data == "sub_menu":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
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
        text = "أرسل يوزر القناة أو الآيدي الرقمي (مثال: `@channel` أو `-100xxxx`):"
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "toggle_sub_status":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return
        if not sub_channels.get(user_id):
            await callback_query.answer("⚠️ حدد قنوات الاشتراك أولاً!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["sub"] = not s["sub"]

        if s["sub"]:
            sess_info = user_sessions.get(user_id)
            if sess_info:
                await start_sub_client(user_id, sess_info["session"], API_ID, API_HASH)
            await callback_query.answer("✅ تم التفعيل بنجاح!", show_alert=True)
        else:
            await stop_sub_client(user_id)
            await callback_query.answer("🛑 تم الإيقاف.", show_alert=True)

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
        await callback_query.answer("🔥 تم حذف القنوات وإيقاف الميزة!", show_alert=True)
        
        text, kb = sub_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "s_private_lock":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
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
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        s = get_user_services(user_id)
        s["lock"] = not s["lock"]
        
        if s["lock"]:
            sess_info = user_sessions.get(user_id)
            if sess_info:
                await start_private_lock_client(user_id, sess_info["session"], API_ID, API_HASH)
            await callback_query.answer("🔒 تم تفعيل القفل بنجاح!", show_alert=True)
        else:
            await stop_private_lock_client(user_id)
            await callback_query.answer("🔓 تم إيقاف القفل.", show_alert=True)

        text, kb = lock_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "lock_set_all":
        get_lock_settings(user_id)["mode"] = "all"
        await callback_query.answer("✅ تم تحويل وضع القفل إلى: (قفل الكل)")
        text, kb = lock_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "lock_set_custom":
        get_lock_settings(user_id)["mode"] = "custom"
        await callback_query.answer("✅ تم تحويل وضع القفل إلى: (قفل أشخاص محددين)")
        text, kb = lock_menu_keyboard(user_id)
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "lock_add_user":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_LOCK_USER"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="s_private_lock")]])
        text = "➕ أرسل آيدي الشخص الرقمي أو اليوزر المراد قفل الخاص بوجهه (مثال: `123456789` أو `@username`):"
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "lock_show_users":
        await callback_query.answer()
        lock_info = get_lock_settings(user_id)
        users = lock_info["users"]
        users_list_str = "\n".join([f"• `{u}`" for u in users]) if users else "لا توجد حسابات مضافة."
        text = f"📋 **قائمة الأشخاص المقفل عليهم الخاص:**\n\n{users_list_str}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🔙", callback_data="s_private_lock")]])
        try:
            await callback_query.message.edit_caption(caption=text, reply_markup=kb)
        except Exception:
            await callback_query.message.edit_text(text=text, reply_markup=kb)

    elif data == "lock_clear_users":
        get_lock_settings(user_id)["users"] = []
        await callback_query.answer("🗑 تم تفريغ قائمة الأشخاص بنجاح!", show_alert=True)
        text, kb = lock_menu_keyboard(user_id)
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
            await callback_query.message.edit_caption(caption=login_caption, reply_markup=login_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            try:
                await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=login_caption, reply_markup=login_keyboard)
            except Exception:
                await client.send_message(chat_id=user_id, text=login_caption, reply_markup=login_keyboard)

    elif data == "my_sessions":
        await callback_query.answer()
        if user_id not in user_sessions:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]])
            text = "📂 **الجلسات النشطة:**\n\n• لا توجد جلسات مسجلة."
        else:
            session_data = user_sessions[user_id]
            phone = session_data.get("phone", "حساب متصل")
            text = "📱 **إدارة الجلسة:**"
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
            f"📱 **معلومات الجلسة**\n\n"
            f"• الرقم: `{phone}`\n"
            f"• الحالة: متصل ✅"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 حذف الجلسة وخروج", callback_data="delete_session")],
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
            subscription_status = "مدفوع (متصل) ✅"
        else:
            sessions_count = 0
            subscription_status = "غير مسجل ❌"

        info_text = (
            "📊 **بيانات حسابك**\n\n"
            f"• الاسم: {user_name}\n"
            f"• الآيدي: `{account_id}`\n"
            f"• الحالة: {subscription_status}\n"
            f"• الجلسات: {sessions_count}"
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
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        current_ch = storage_channels.get(user_id, "غير مرتبطة ❌")
        text = (
            "📱 **قناة أو مجموعة التخزين**\n\n"
            f"• المكان الحالي: `{current_ch}`"
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
        text = "أرسل يوزر القناة أو الآيدي الرقمي (مثال: `@channel` أو `-100xxxx`):"
        
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
        s["save_chats"] = False
        await callback_query.answer("🗑 تم الحذف وإيقاف حفظ المحادثات للقناة!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_channel",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_reaction":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        if user_id not in reaction_data:
            reaction_data[user_id] = {"active": False, "task": None}

        r_data = reaction_data[user_id]

        text = "💬 **التفاعل التلقائي**"

        toggle_btn = "إيقاف 🔴" if r_data["active"] else "تشغيل ⚡"
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
            await callback_query.answer("⚡ تم التشغيل بنجاح!", show_alert=True)
        else:
            r_data["active"] = False
            s_status["react"] = False
            if r_data["task"]:
                r_data["task"].cancel()
                r_data["task"] = None
            await callback_query.answer("🔴 تم الإيقاف.", show_alert=True)

        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_reaction",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_auto_post":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        if user_id not in auto_post_data:
            auto_post_data[user_id] = {
                "active": False,
                "interval": 60,
                "caption": "مرحباً بكم ✨",
                "groups": [],
                "task": None
            }

        p_data = auto_post_data[user_id]
        text = "📌 **النشر التلقائي**"

        toggle_btn_text = "إيقاف ⏹" if p_data["active"] else "تشغيل 🟢"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("الكليشة 📝", callback_data="ap_caption"), InlineKeyboardButton("الوقت ⏱", callback_data="ap_time")],
            [InlineKeyboardButton("المجموعات 📂", callback_data="ap_groups"), InlineKeyboardButton(toggle_btn_text, callback_data="ap_toggle")],
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

    elif data == "ap_toggle":
        if user_id not in auto_post_data:
            auto_post_data[user_id] = {"active": False, "interval": 60, "caption": "نشر", "groups": [], "task": None}
        
        p_data = auto_post_data[user_id]
        if not p_data["active"]:
            if not p_data["groups"]:
                await callback_query.answer("⚠️ أضف مجموعات أولاً!", show_alert=True)
                return
            p_data["active"] = True
            p_data["task"] = asyncio.create_task(run_auto_post(user_id, client))
            await callback_query.answer("🟢 تم التفعيل بنجاح!", show_alert=True)
        else:
            p_data["active"] = False
            if p_data["task"]:
                p_data["task"].cancel()
                p_data["task"] = None
            await callback_query.answer("⏹ تم الإيقاف.", show_alert=True)
        
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
            caption="⏱ **تحديد الوقت**\n\nأرسل الوقت بالثواني (مثال: 60):",
            reply_markup=kb
        )

    elif data == "ap_caption":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_AUTO_POST_CAPTION"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="s_auto_post")]])
        await callback_query.message.edit_caption(
            caption="📝 **تحديد الكليشة**\n\nأرسل النص للنشر التلقائي:",
            reply_markup=kb
        )

    elif data == "ap_groups":
        await callback_query.answer()
        p_data = auto_post_data.get(user_id, {"groups": []})
        groups_list = "\n".join([f"• `{g}`" for g in p_data["groups"]]) if p_data["groups"] else "لا توجد مجموعات."
        
        text = (
            "📂 **إدارة المجموعات**\n\n"
            f"{groups_list}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("إضافة مجموعة ➕", callback_data="ap_add_group"), InlineKeyboardButton("حذف الكل 🗑", callback_data="ap_clear_groups")],
            [InlineKeyboardButton("رجوع 🔙", callback_data="s_auto_post")]
        ])
        await callback_query.message.edit_caption(caption=text, reply_markup=kb)

    elif data == "ap_add_group":
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_AUTO_POST_GROUP"}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="ap_groups")]])
        await callback_query.message.edit_caption(
            caption="➕ **إضافة مجموعة**\n\nأرسل يوزر أو آيدي المجموعة:",
            reply_markup=kb
        )

    elif data == "ap_clear_groups":
        if user_id in auto_post_data:
            auto_post_data[user_id]["groups"] = []
        await callback_query.answer("🗑 تم حذف المجموعات!", show_alert=True)
        
        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="ap_groups",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_auto_reply":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        if user_id not in auto_reply_data:
            auto_reply_data[user_id] = {
                "active": False,
                "reply_text": None,
                "client_instance": None
            }

        ar_data = auto_reply_data[user_id]
        text = "🤖 **الرد التلقائي**"

        toggle_btn_text = "إيقاف ⏹" if ar_data["active"] else "تشغيل ▶️"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("تعديل النص 💬", callback_data="ar_set_text"), InlineKeyboardButton(toggle_btn_text, callback_data="ar_toggle")],
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
            caption="💬 **تعديل نص الرد**\n\nأرسل النص الجديد:",
            reply_markup=kb
        )

    elif data == "ar_toggle":
        if user_id not in auto_reply_data:
            auto_reply_data[user_id] = {"active": False, "reply_text": None, "client_instance": None}

        ar_data = auto_reply_data[user_id]
        s_status = get_user_services(user_id)
        if not ar_data["active"]:
            if not ar_data["reply_text"]:
                await callback_query.answer("⚠️ عين نص الرد أولاً!", show_alert=True)
                return

            sess_info = user_sessions.get(user_id)
            if not sess_info:
                await callback_query.answer("⚠️ الجلسة غير متوفرة!", show_alert=True)
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
                        if not msg.from_user or msg.from_user.is_bot or msg.outgoing:
                            return
                        await asyncio.sleep(0.5)
                        await msg.reply(ar_data["reply_text"])
                    except Exception as e:
                        print(f"Auto reply error: {e}")

                await user_reply_cli.start()
                ar_data["client_instance"] = user_reply_cli
                ar_data["active"] = True
                s_status["reply"] = True
                await callback_query.answer("🟢 تم التفعيل بنجاح!", show_alert=True)
            except Exception as e:
                await callback_query.answer(f"❌ خطأ: {e}", show_alert=True)
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
            await callback_query.answer("⏹ تم الإيقاف.", show_alert=True)

        fake_query = SimpleNamespace(
            from_user=callback_query.from_user,
            data="s_auto_reply",
            message=callback_query.message,
            answer=callback_query.answer
        )
        return await callback_handler(client, fake_query)

    elif data == "s_story":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_STORY_TARGET"}
        story_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع ⛔", callback_data="services")]])
        story_caption = "🌟 **سحب الستوري**\n\nأرسل الآيدي أو اليوزر:"

        try:
            await callback_query.message.edit_caption(caption=story_caption, reply_markup=story_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=story_caption, reply_markup=story_keyboard)

    elif data == "s_restricted":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_RESTRICTED_LINK"}
        restricted_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع ⛔", callback_data="services")]])
        restricted_caption = "أرسل رابط المحتوى المقيد:"

        try:
            await callback_query.message.edit_caption(caption=restricted_caption, reply_markup=restricted_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=HELP_PHOTO_URL, caption=restricted_caption, reply_markup=restricted_keyboard)

    elif data == "s_forward":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return

        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_FORWARD_MESSAGE"}
        forward_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء 🚫", callback_data="services")]])
        forward_caption = "💬 أرسل الرسالة أو الميديا للتوجيه الخاص:"

        try:
            await callback_query.message.edit_caption(caption=forward_caption, reply_markup=forward_keyboard)
        except Exception:
            try:
                await callback_query.message.delete()
            except Exception:
                pass
            await client.send_photo(chat_id=user_id, photo=WELCOME_PHOTO_URL, caption=forward_caption, reply_markup=forward_keyboard)

    elif data == "s_fake_acc":
        if user_id not in user_sessions:
            await callback_query.answer("⚠️ يجب تسجيل الدخول أولاً!", show_alert=True)
            return
        await callback_query.answer()
        user_states[user_id] = {"step": "WAITING_FAKE_TARGET"}
        
        text = "أرسل يوزر الشخص المراد انتحاله (مثال: `@username`)" 
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
            await callback_query.answer("⚠️ لا توجد بيانات أصلية محفوظة!", show_alert=True)
            return

        await callback_query.answer("⏳ جاري استعادة حسابك...")
        sess_info = user_sessions[user_id]
        orig = original_user_data[user_id]

        try:
            temp_cli = Client(f"restore_cli_{user_id}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
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
            text = "✅ تم استعادة بيانات حسابك الأصلية بنجاح."
            
            try:
                await callback_query.message.edit_caption(caption=text, reply_markup=kb)
            except Exception:
                await callback_query.message.edit_text(text=text, reply_markup=kb)

        except Exception as e:
            await callback_query.answer(f"❌ خطأ: {e}", show_alert=True)

    elif data == "help":
        await callback_query.answer()
        help_text = (
            "💡 **دليل الاستخدام وشرح المميزات:**\n\n"
            "🔐 **1. طريقة تسجيل الدخول (`👤 دخول`):**\n"
            "• اضغط على زر **دخول** من القائمة الرئيسية.\n"
            "• أرسل رقم هاتفك مع الرمز الدولي (مثال: `+9647xxxxxxxx`).\n"
            "• أدخل كود التحقق بشكل مسافات (مثال: `5 2 3 8 9`).\n"
            "• إذا كان حسابك محمي بكلمة مرور، قم بإرسالها.\n\n"
            "⚙️ **2. شرح الخدمات المتاحة:**\n"
            "• 🛡️ **المراقبة:** لمراقبة رسائل وميديا الخاص الواردة.\n"
            "• 📱 **تخزين / 💾 حفظ المحادثات:** لحفظ وتوثيق كافة المحادثات بقناة مخصصة.\n"
            "• 📞 **قفل الخاص:** يتيح لك قفل الخاص بالكامل (الكل) أو تحديد أشخاص معينين لحذف رسائلهم تلقائياً واستثناء البقية.\n"
            "• 💲 **اشتراك إجباري:** لفرض اشتراك إجباري بقنواتك على من راسلك.\n"
            "• 🔄 **نشر 24 / رد 24:** خدمات التشغيل التلقائي.\n"
            "• 👻 **انتحال:** لتقليد معلومات وحسابات المستخدمين مؤقتاً."
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🛑", callback_data="back_to_main")]])
        
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
            print(f"Reaction error: {e}")
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
                    print(f"Auto post error: {err}")

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

    if state == "WAITING_BROADCAST_MESSAGE":
        if user_id != DEVELOPER_ID:
            user_states.pop(user_id, None)
            return
        
        user_states.pop(user_id, None)
        sent_count = 0
        fail_count = 0
        
        status_msg = await message.reply("⏳ جاري الإذاعة...")
        
        for uid in list(all_users_set):
            try:
                await message.copy(chat_id=uid)
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception:
                fail_count += 1
                
        await status_msg.edit_text(f"✅ **تمت الإذاعة بنجاح!**\n\n• نجاح: `{sent_count}`\n• فشل: `{fail_count}`")
        return

    if state == "WAITING_LOCK_USER":
        clean_target = text if text.lstrip("-").isdigit() else (text if text.startswith("@") else f"@{text}")
        lock_info = get_lock_settings(user_id)
        if clean_target not in lock_info["users"]:
            lock_info["users"].append(clean_target)
            await message.reply(f"✅ تمت إضافة الحساب إلى قائمة المقفل عليهم الخاص:\n`{clean_target}`")
        else:
            await message.reply("⚠️ الحساب مضاف مسبقاً للقائمة.")
        user_states.pop(user_id, None)
        return

    if state == "WAITING_FAKE_TARGET":
        user_states.pop(user_id, None)
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب تسجيل الدخول أولاً!")
            return

        target_username_input = text.replace("@", "").strip()
        msg_wait = await message.reply("⏳ جاري تطبيق الانتحال...")

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
                f"{clean_seed}_", f"_{clean_seed}", f"{clean_seed}v",
                f"{clean_seed}1", f"{clean_seed}7", f"{clean_seed}99"
            ]

            for usr in usernames_to_try:
                try:
                    await temp_cli.set_username(usr.replace("@", "").strip())
                    break
                except Exception:
                    continue

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

            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📞 استعادة الحساب الأصلي", callback_data="restore_account")]])
            await msg_wait.edit_text(f"✅ **تم الانتحال بنجاح!**\n• الهدف: `@{target_username_input}`", reply_markup=kb)

        except Exception as e:
            await msg_wait.edit_text(f"❌ خطأ: {e}")
        return

    if state == "WAITING_SUB_CHANNEL":
        clean_channel = text if text.lstrip("-").isdigit() else (text if text.startswith("@") else f"@{text}")
        if user_id not in sub_channels:
            sub_channels[user_id] = []
        if clean_channel not in sub_channels[user_id]:
            sub_channels[user_id].append(clean_channel)
        user_states.pop(user_id, None)
        
        text_menu, kb = sub_menu_keyboard(user_id)
        await message.reply(f"✅ تمت الإضافة بنجاح:\n`{clean_channel}`", reply_markup=kb)

    elif state == "WAITING_STORAGE_CHANNEL":
        clean_storage = text.strip()
        storage_channels[user_id] = clean_storage
        user_states.pop(user_id, None)
        await message.reply(f"✅ تم حفظ قناة التخزين: `{clean_storage}`\nيمكنك الآن تفعيل زر 'حفظ المحادثات' من قائمة الخدمات.")

    elif state == "WAITING_AUTO_POST_TIME":
        if text.isdigit() and int(text) > 0:
            auto_post_data[user_id]["interval"] = int(text)
            user_states.pop(user_id, None)
            await message.reply(f"✅ تم تحديث الوقت إلى: {text} ثانية.")
        else:
            await message.reply("❌ أرسل رقماً صحيحاً:")

    elif state == "WAITING_AUTO_POST_CAPTION":
        auto_post_data[user_id]["caption"] = text
        user_states.pop(user_id, None)
        await message.reply("✅ تم حفظ الكليشة بنجاح!")

    elif state == "WAITING_AUTO_REPLY_TEXT":
        if user_id not in auto_reply_data:
            auto_reply_data[user_id] = {"active": False, "reply_text": None, "client_instance": None}
        auto_reply_data[user_id]["reply_text"] = text
        user_states.pop(user_id, None)
        await message.reply("✅ تم حفظ نص الرد بنجاح!")

    elif state == "WAITING_AUTO_POST_GROUP":
        if user_id not in auto_post_data:
            auto_post_data[user_id] = {"active": False, "interval": 60, "caption": "", "groups": [], "task": None}
        
        clean_group = text if text.lstrip("-").isdigit() else text.replace("@", "").strip()
        if clean_group not in auto_post_data[user_id]["groups"]:
            auto_post_data[user_id]["groups"].append(clean_group)
            await message.reply(f"✅ تمت إضافة المجموعة:\n`{clean_group}`")
        else:
            await message.reply("⚠️ المجموعة مضافة مسبقاً.")
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
            await message.reply("أرسل كود التحقق (بشكل مسافات، مثال: `5 2 3 8 9`):")
        except PhoneNumberInvalid:
            await message.reply("❌ رقم الهاتف غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ خطأ: {e}")

    elif state == "WAITING_CODE":
        code = re.sub(r"\D", "", text)
        user_data = user_clients.get(user_id)
        if not user_data:
            await message.reply("❌ انتهت الجلسة.")
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
            if s_serv.get("monitor", False) or s_serv.get("save_chats", False):
                await start_save_chats_client(user_id, session_string, API_ID, API_HASH)

            await message.reply("✅ تم تسجيل الدخول بنجاح!")
        except SessionPasswordNeeded:
            user_states[user_id]["step"] = "WAITING_PASSWORD"
            await message.reply("🔐 الحساب محمي بكلمة مرور. أرسلها:")
        except PhoneCodeInvalid:
            await message.reply("❌ الكود خطأ، أعد المحاولة (بشكل مسافات مثل: `5 2 3 8 9`):")
        except Exception as e:
            await message.reply(f"❌ خطأ: {e}")

    elif state == "WAITING_PASSWORD":
        password = text
        user_data = user_clients.get(user_id)
        if not user_data:
            await message.reply("❌ انتهت الجلسة.")
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
            if s_serv.get("monitor", False) or s_serv.get("save_chats", False):
                await start_save_chats_client(user_id, session_string, API_ID, API_HASH)

            await message.reply("✅ تم تسجيل الدخول بنجاح!")
        except PasswordHashInvalid:
            await message.reply("❌ كلمة المرور غير صحيحة:")
        except Exception as e:
            await message.reply(f"❌ خطأ: {e}")

    elif state == "WAITING_RESTRICTED_LINK":
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب تسجيل الدخول أولاً!")
            return

        msg_wait = await message.reply("⏳ جاري جلب المحتوى المقيد...")
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
                    await msg_wait.edit_text("✅ تم السحب بنجاح!")
                else:
                    await msg_wait.edit_text("❌ تعذر الوصول للرسالة.")
            else:
                await msg_wait.edit_text("❌ رابط غير صالح.")
            await user_cli.stop()
        except Exception as e:
            await msg_wait.edit_text(f"❌ خطأ: {e}")
        finally:
            user_states.pop(user_id, None)

    elif state == "WAITING_STORY_TARGET":
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب تسجيل الدخول أولاً!")
            return

        msg_wait = await message.reply("⏳ جاري سحب الستوري...")
        try:
            user_cli = Client(f"user_story_{user_id}", session_string=sess_info["session"], api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await user_cli.start()

            target = text.strip()
            if target.isdigit():
                target = int(target)
            else:
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
                await msg_wait.edit_text(f"✅ تم سحب ({count}) ستوري بنجاح!")
            else:
                await msg_wait.edit_text("❌ لا توجد ستوريات نشطة.")
        except Exception as e:
            await msg_wait.edit_text(f"❌ خطأ: {e}")
        finally:
            user_states.pop(user_id, None)

    elif state == "WAITING_FORWARD_MESSAGE":
        sess_info = user_sessions.get(user_id)
        if not sess_info:
            await message.reply("⚠️ يجب تسجيل الدخول أولاً!")
            return

        msg_wait = await message.reply("⏳ جاري التوجيه...")
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
                            await user_cli.send_audio(chat_id=dialog.chat.id, video=media_path, caption=caption_text)
                        elif message.document and media_path:
                            await user_cli.send_document(chat_id=dialog.chat.id, document=media_path, caption=caption_text)
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
            await msg_wait.edit_text(f"✅ تم التوجيه بنجاح إلى ({success_count}) محادثة.")
        except Exception as e:
            await msg_wait.edit_text(f"❌ خطأ: {e}")
        finally:
            user_states.pop(user_id, None)

if __name__ == "__main__":
    print("جاري تشغيل البوت...")
    bot.run()
