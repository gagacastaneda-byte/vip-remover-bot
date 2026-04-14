import os
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

members = {}
notified = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    chat_id = int(context.args[0])
    context.job_queue.run_repeating(kick_expired, interval=3600, data=chat_id, name="kicker")
    context.job_queue.run_repeating(send_reminders, interval=3600, data=chat_id, name="reminders")
    await update.message.reply_text(f"✅ Bot démarré pour le canal {chat_id}")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = int(context.args[0])
    days = int(context.args[1])
    username = context.args[2] if len(context.args) > 2 else str(user_id)
    expiry = datetime.now() + timedelta(days=days)
    members[user_id] = {"expiry": expiry, "username": username}
    notified[user_id] = []
    await update.message.reply_text(f"✅ {username} ajouté pour {days} jours (expire le {expiry.strftime('%d/%m/%Y')})")

async def extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = int(context.args[0])
    days = int(context.args[1])
    if user_id in members:
        members[user_id]["expiry"] += timedelta(days=days)
        username = members[user_id]["username"]
    else:
        username = str(user_id)
        members[user_id] = {"expiry": datetime.now() + timedelta(days=days), "username": username}
    notified[user_id] = []
    await update.message.reply_text(f"✅ Accès prolongé de {days} jours pour {username}")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not members:
        await update.message.reply_text("Aucun membre actif.")
        return
    msg = "📋 Membres actifs :\n"
    for uid, data in members.items():
        msg += f"• {data['username']} (ID: {uid}) → expire le {data['expiry'].strftime('%d/%m/%Y')}\n"
    await update.message.reply_text(msg)

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for uid, data in list(members.items()):
        days_left = (data["expiry"] - now).days
        for d in [3, 2, 1]:
            if days_left == d and d not in notified.get(uid, []):
                try:
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"⚠️ Ton accès VIP expire dans {d} jour(s) ! Contacte l'admin pour renouveler."
                    )
                    notified.setdefault(uid, []).append(d)
                except Exception as e:
                    print(f"Impossible de notifier {uid}: {e}")

async def kick_expired(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    now = datetime.now()
    expired = [uid for uid, data in list(members.items()) if data["expiry"] < now]
    for uid in expired:
        username = members[uid]["username"]
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=uid)
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=uid)
            del members[uid]
            notified.pop(uid, None)
            await context.bot.send_message(chat_id=uid, text="❌ Ton accès VIP a expiré. Contacte l'admin pour renouveler.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"😢 {username} nous a quittés... En espérant que ça ne dure pas trop longtemps !")
        except Exception as e:
            print(f"Erreur pour {uid}: {e}")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("extend", extend))
app.add_handler(CommandHandler("check", check))
app.run_polling()
