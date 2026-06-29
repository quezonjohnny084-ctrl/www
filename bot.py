import time, asyncio, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

from config import BOT_TOKEN, REF_COST, DAILY_COOLDOWN, CHANNEL, ADMIN_ID
import database as db

if not os.path.exists("accounts"):
    os.makedirs("accounts")

# ================= CHANNEL CHECK & BAN GUARD =================
async def joined(bot, uid):
    try:
        m = await bot.get_chat_member(CHANNEL, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


# ================= FILES =================
load = lambda f: [x.strip() for x in open(f) if x.strip()] if os.path.exists(f) else []
save = lambda f, d: open(f, "w").write("\n".join(d))


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not u:
        return
    
    if db.is_banned(u.id):
        await update.message.reply_text("❌ You have been banned from using this bot.")
        return

    is_new = db.add_user(u.id, u.username)

    # ================= REF SYSTEM =================
    referrer = None
    if is_new and context.args:
        try:
            ref_id = int(context.args[0])
            referrer = db.set_referral(u.id, ref_id)
        except:
            pass

    if referrer:
        try:
            await context.bot.send_message(
                referrer,
                f"🎉 Referral success!\n👤 {u.first_name} joined using your link"
            )
        except:
            pass

    data = db.get(u.id)
    refs = data[2] if data else 0

    kb = [
        [InlineKeyboardButton("🎁 DAILY CLAIM", callback_data="daily")],
        [InlineKeyboardButton("👑 VIP CLAIM", callback_data="vip")],
        [InlineKeyboardButton("👥 INVITE FRIENDS", callback_data="invite")],
        [InlineKeyboardButton("📊 MY REFERRALS", callback_data="refs")],
        [InlineKeyboardButton("🏆 LEADERBOARD", callback_data="lb")],
        [InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL.replace('@','')}")]
    ]

    if u.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 ADMIN PANEL", callback_data="admin_menu")])

    await update.message.reply_text(
        f"✨ 𝚑𝚎𝚕𝚕𝚘 :) 𝚠𝚎𝚕𝚌𝚘𝚖𝚎 𝚝𝚘 𝚏𝚛𝚎𝚎 𝚌𝚘𝚍𝚖 𝚊𝚌𝚌𝚘𝚞𝚗𝚝𝚜, 𝚝𝚑𝚒𝚜 𝚋𝚘𝚝 𝚠𝚊𝚜 𝚖𝚊𝚍𝚎 𝚋𝚢 @maisanyvokei 𝚏𝚘𝚛 𝚖𝚘𝚛𝚎 𝚚𝚞𝚎𝚜𝚝𝚒𝚘𝚗𝚜 𝚍𝚖 𝚖𝚎. 𝚊𝚕𝚕 𝚝𝚑𝚎 𝚍𝚊𝚒𝚕𝚢 𝚊𝚗𝚍 𝚟𝚒𝚙 𝚌𝚕𝚊𝚒𝚖𝚎𝚍 𝚊𝚛𝚎 𝚠𝚘𝚛𝚔𝚒𝚗𝚐 𝚊𝚌𝚌𝚘𝚞𝚗𝚝𝚜 𝙸 𝚌𝚊𝚗'𝚝 𝚜𝚎𝚗𝚍 𝚝𝚑𝚎 𝚏𝚞𝚕𝚕 𝚒𝚗𝚏𝚘 𝚌𝚊𝚞𝚜𝚎 𝚘𝚏 𝚕𝚒𝚗𝚎𝚜      note : you must join channel before claiming an account\n\n👥 Your Referrals: {refs}",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ================= ADMIN HANDLER =================
async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return

    state = context.user_data.get("admin_state")
    if not state:
        return

    text = update.message.text.strip() if update.message.text else ""

    # --- BAN USER ---
    if state == "ban_user_prompt":
        try:
            target_id = int(text)
            db.ban_user(target_id)
            context.user_data.pop("admin_state", None)
            await update.message.reply_text(f"✅ User ID <code>{target_id}</code> banned.", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("⚠️ Invalid ID. Paste a numeric User ID.")
        return

    # --- UNBAN USER ---
    if state == "unban_user_prompt":
        try:
            target_id = int(text)
            db.unban_user(target_id)
            context.user_data.pop("admin_state", None)
            await update.message.reply_text(f"✅ User ID <code>{target_id}</code> unbanned.", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("⚠️ Invalid ID. Paste a numeric User ID.")
        return

    # --- SEARCH USER ---
    if state == "search_user_prompt":
        try:
            target_id = int(text)
            user_data = db.search_user(target_id)
            context.user_data.pop("admin_state", None)
            if user_data:
                u_id, u_name, refs, ref_by, last_c = user_data
                uname = f"@{u_name}" if u_name else "None"
                await update.message.reply_text(
                    f"🔍 <b>User Found:</b>\n\n"
                    f"🆔 ID: <code>{u_id}</code>\n"
                    f"👤 Username: {uname}\n"
                    f"👥 Referrals: <code>{refs}</code>\n"
                    f"🔗 Referred By: <code>{ref_by if ref_by else 'Nobody'}</code>\n"
                    f"⏱ Last Claim: <code>{int(last_c) if last_c else 0}</code>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ User not found in database.")
        except ValueError:
            await update.message.reply_text("⚠️ Invalid ID. Paste a numeric User ID.")
        return

    # --- DELETE USER ---
    if state == "delete_user_prompt":
        try:
            target_id = int(text)
            db.delete_user(target_id)
            context.user_data.pop("admin_state", None)
            await update.message.reply_text(f"🗑️ User ID <code>{target_id}</code> has been fully deleted.", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("⚠️ Invalid ID. Paste a numeric User ID.")
        return

    # --- BROADCAST SYSTEM ---
    if state == "broadcast_prompt":
        context.user_data.pop("admin_state", None)
        all_users = db.get_all_users()
        if not all_users:
            await update.message.reply_text("❌ There are no users to broadcast to.")
            return

        status_msg = await update.message.reply_text("📣 Sending broadcast, please wait...")
        success, failed = 0, 0

        for u_row in all_users:
            target_id = u_row[0]
            try:
                if update.message.text:
                    await context.bot.send_message(chat_id=target_id, text=update.message.text, entities=update.message.entities)
                elif update.message.photo:
                    await context.bot.send_photo(chat_id=target_id, photo=update.message.photo[-1].file_id, caption=update.message.caption, caption_entities=update.message.caption_entities)
                elif update.message.video:
                    await context.bot.send_video(chat_id=target_id, video=update.message.video.file_id, caption=update.message.caption, caption_entities=update.message.caption_entities)
                success += 1
            except:
                failed += 1
            await asyncio.sleep(0.05)

        await status_msg.edit_text(f"📢 <b>Broadcast Complete!</b>\n\n✅ Delivered: <code>{success}</code>\n❌ Blocked/Failed: <code>{failed}</code>", parse_mode="HTML")
        return

    # --- STOCK HANDLING ---
    if state in ["add_daily", "add_vip"]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            await update.message.reply_text("⚠️ Invalid input. Send clean stock items.")
            return

        filename = "accounts/daily.txt" if state == "add_daily" else "accounts/vip.txt"
        current_items = load(filename)
        current_items.extend(lines)
        save(filename, current_items)
        context.user_data.pop("admin_state", None)

        await update.message.reply_text(f"✅ Added {len(lines)} item(s) to {'Daily' if state == 'add_daily' else 'VIP'} list!\nTotal: {len(current_items)}")


# ================= BUTTON ENGINE =================
async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
        
    uid = q.from_user.id
    
    # Pro-Move: Answer right away to stop the Telegram UI freezing loop completely
    try:
        await q.answer()
    except Exception:
        pass
    
    # Outer catch-all to ensure internal crashes never brick the UI responsiveness
    try:
        if db.is_banned(uid):
            await q.edit_message_text("❌ You have been banned from using this bot.")
            return

        # --- ADMIN CALLBACKS ---
        if q.data == "admin_menu":
            if uid != ADMIN_ID:
                await q.edit_message_text("❌ Access Denied.")
                return
            
            stats = db.get_stats()
            daily_stock = len(load("accounts/daily.txt"))
            vip_stock = len(load("accounts/vip.txt"))

            admin_kb = [
                [InlineKeyboardButton("➕ Add Daily Rewards", callback_data="add_daily"), 
                 InlineKeyboardButton("➕ Add VIP Rewards", callback_data="add_vip")],
                [InlineKeyboardButton("👥 View All Users", callback_data="view_users_0"),
                 InlineKeyboardButton("🔍 Search User", callback_data="prompt_search")],
                [InlineKeyboardButton("🚫 Ban User", callback_data="prompt_ban"),
                 InlineKeyboardButton("🟢 Unban User", callback_data="prompt_unban")],
                [InlineKeyboardButton("🗑️ Delete User", callback_data="prompt_delete"),
                 InlineKeyboardButton("📣 Broadcast", callback_data="prompt_broadcast")],
                [InlineKeyboardButton("⚠️ Reset Database", callback_data="confirm_reset_db")],
                [InlineKeyboardButton("↩️ Back to Main Menu", callback_data="back_main")]
            ]
            await q.edit_message_text(
                f"🛠 <b>ADMIN MANAGEMENT PANEL</b>\n\n"
                f"📊 <b>Bot Statistics:</b>\n"
                f"┣ Registered Users: <code>{stats['users']}</code>\n"
                f"┣ Banned Users: <code>{stats['banned']}</code>\n"
                f"┗ System Referrals: <code>{stats['referrals']}</code>\n\n"
                f"📦 <b>Reward Stock:</b>\n"
                f"┣ Daily Items: <code>{daily_stock}</code>\n"
                f"┗ VIP Items: <code>{vip_stock}</code>\n\n"
                f"Select an option below:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(admin_kb)
            )
            return

        if q.data in ["add_daily", "add_vip", "prompt_ban", "prompt_unban", "prompt_search", "prompt_delete", "prompt_broadcast"]:
            if uid != ADMIN_ID:
                await q.edit_message_text("❌ Access Denied.")
                return
            
            prompts = {
                "add_daily": "📥 Paste your <b>DAILY</b> items now (one per line or bulk text):",
                "add_vip": "📥 Paste your <b>VIP</b> items now (one per line or bulk text):",
                "prompt_ban": "🚫 <b>BAN USER</b>\n\nSend the numeric <b>User ID</b> you want to ban:",
                "prompt_unban": "🟢 <b>UNBAN USER</b>\n\nSend the numeric <b>User ID</b> you want to unban:",
                "prompt_search": "🔍 <b>SEARCH USER</b>\n\nSend the numeric <b>User ID</b> you want to check:",
                "prompt_delete": "🗑️ <b>DELETE USER</b>\n\nSend the numeric <b>User ID</b> to wipe completely from the bot database:",
                "prompt_broadcast": "📣 <b>GLOBAL BROADCAST</b>\n\nSend the message you want to broadcast. You can use text formatting, links, photos, or video items."
            }
            
            state_mapping = {
                "prompt_ban": "ban_user_prompt", "prompt_unban": "unban_user_prompt",
                "prompt_search": "search_user_prompt", "prompt_delete": "delete_user_prompt",
                "prompt_broadcast": "broadcast_prompt"
            }
            
            context.user_data["admin_state"] = state_mapping.get(q.data, q.data)
            await q.edit_message_text(prompts[q.data], parse_mode="HTML")
            return

        if q.data == "confirm_reset_db":
            if uid != ADMIN_ID:
                await q.edit_message_text("❌ Access Denied.")
                return
            await q.edit_message_text(
                "⚠️ <b>CRITICAL WARNING</b> ⚠️\n\nReset the database? This deletes all users, referral trees, and bans.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛑 YES, RESET ALL", callback_data="execute_reset_db")],
                    [InlineKeyboardButton("❌ NO, CANCEL", callback_data="admin_menu")]
                ])
            )
            return

        if q.data == "execute_reset_db":
            if uid != ADMIN_ID:
                await q.edit_message_text("❌ Access Denied.")
                return
            db.reset_all_data()
            await q.edit_message_text(
                "✅ <b>Database reset successfully!</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Admin Menu", callback_data="admin_menu")]])
            )
            return

        if q.data.startswith("view_users_"):
            if uid != ADMIN_ID:
                await q.edit_message_text("❌ Access Denied.")
                return
                
            page = int(q.data.split("_")[2])
            users = db.get_all_users()
            
            if not users:
                await q.edit_message_text("👥 No registered users yet.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Admin Menu", callback_data="admin_menu")]]))
                return

            per_page = 10
            total_pages = (len(users) + per_page - 1) // per_page
            start_idx = page * per_page
            end_idx = start_idx + per_page
            page_users = users[start_idx:end_idx]

            msg_text = f"👥 <b>REGISTERED USERS (Page {page + 1}/{total_pages})</b>\n\n"
            for u_id, u_name, refs in page_users:
                username_display = f"@{u_name}" if u_name else "No Username"
                username_display = username_display.replace("<", "&lt;").replace(">", "&gt;")
                msg_text += f"🆔 <code>{u_id}</code> — {username_display} ({refs} refs)\n"

            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"view_users_{page - 1}"))
            if end_idx < len(users):
                nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"view_users_{page + 1}"))

            users_kb = []
            if nav_buttons:
                users_kb.append(nav_buttons)
            users_kb.append([InlineKeyboardButton("↩️ Back to Admin Menu", callback_data="admin_menu")])

            await q.edit_message_text(msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(users_kb))
            return

        if q.data == "back_main":
            context.user_data.pop("admin_state", None) 
            data = db.get(uid)
            refs = data[2] if data else 0

            kb = [
                [InlineKeyboardButton("🎁 DAILY CLAIM", callback_data="daily")],
                [InlineKeyboardButton("👑 VIP CLAIM", callback_data="vip")],
                [InlineKeyboardButton("👥 INVITE FRIENDS", callback_data="invite")],
                [InlineKeyboardButton("📊 MY REFERRALS", callback_data="refs")],
                [InlineKeyboardButton("🏆 LEADERBOARD", callback_data="lb")],
                [InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL.replace('@','')}")]
            ]
            if uid == ADMIN_ID:
                kb.append([InlineKeyboardButton("🛠 ADMIN PANEL", callback_data="admin_menu")])

            await q.edit_message_text(f"✨ ZIA FREE CODM\n\n👥 Referrals: {refs}", reply_markup=InlineKeyboardMarkup(kb))
            return

        # --- USER CALLBACKS ---
        if q.data == "invite":
            botname = (await context.bot.get_me()).username
            link = f"https://t.me/{botname}?start={uid}"
            await q.message.reply_text(f"👥 Your Invite Link:\n\n{link}\n\nShare this to earn referrals!")
            return

        if not await joined(context.bot, uid):
            await q.edit_message_text("⚠️ Join channel first")
            return

        data = db.get(uid)
        if not data:
            await q.edit_message_text("❌ Error reading user from DB.")
            return
            
        refs = data[2]
        last = data[4]

        if q.data == "refs":
            await q.edit_message_text(f"👥 Your Referrals: {refs}")
            return

        if q.data == "lb":
            top_list = db.top()
            text = "🏆 <b>LEADERBOARD</b>\n\n"
            for i, (u, r) in enumerate(top_list, 1):
                name = u if u else 'Anonymous'
                name = name.replace("<", "&lt;").replace(">", "&gt;")
                text += f"{i}. {name} — {r} refs\n"
            await q.edit_message_text(text, parse_mode="HTML")
            return

        if q.data == "daily":
            now = time.time()
            if now - last < DAILY_COOLDOWN:
                remain = int(DAILY_COOLDOWN - (now - last))
                await q.edit_message_text(f"⏳ Wait {remain//3600}h before claiming your next daily reward.")
                return

            stock = load("accounts/daily.txt")
            if not stock:
                await q.edit_message_text("❌ Out of Daily Reward stock! Please contact the Admin.")
                return

            claimed_item = stock.pop(0)
            save("accounts/daily.txt", stock)
            db.update_time(uid, now)
            await q.edit_message_text(f"🎁 <b>DAILY REWARD CLAIMED!</b>\n\nHere is your reward:\n<code>{claimed_item}</code>", parse_mode="HTML")
            return

        if q.data == "vip":
            if refs < 2:
                await q.edit_message_text(f"❌ VIP claim requires at least <b>2 referrals</b>. You only have <b>{refs}</b>.", parse_mode="HTML")
                return

            stock = load("accounts/vip.txt")
            if not stock:
                await q.edit_message_text("❌ Out of VIP Reward stock! Please contact the Admin.")
                return

            db.deduct_referrals(uid, 2)
            claimed_item = stock.pop(0)
            save("accounts/vip.txt", stock)
            await q.edit_message_text(f"👑 <b>VIP REWARD CLAIMED!</b>\n\n2 referrals have been deducted. Here is your reward:\n<code>{claimed_item}</code>", parse_mode="HTML")
            return
            
    except Exception as e:
        print(f"🔥 Button processing error caught safely: {e}")


# ================= RUN =================
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, admin_input))

    print("🚀 BOT ACTIVE WITH PRODUCTION-GRADE SEAMLESS INTERACTIONS")
    app.run_polling(drop_pending_updates=True)