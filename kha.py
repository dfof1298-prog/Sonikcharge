import telebot
from telebot import types
from telebot.types import LabeledPrice, PreCheckoutQuery
from datetime import datetime, timedelta
import json
import threading
import time
import random
import logging

TOKEN = "8124255326:AAHcUCZw3xSWBVhFo0ArokZ7-sB08aHLt3s"
CHANNEL_ID = -1003808682791
DATA_FILE = "premium_members.json"
ADMIN_ID = 7077116674

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

PLANS = {
    "1": {"name": "1 Week",  "price": 100, "days": 7,  "emoji": "✨"},
    "2": {"name": "2 Weeks", "price": 150, "days": 14, "emoji": "🔥"},
    "3": {"name": "3 Weeks", "price": 200, "days": 21, "emoji": "💎"},
}

pending_invoices = {}
pending_gift = {}

def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save data: {e}")

def welcome_text():
    return "<b>Welcome to the Exclusive Experience</b>\n\nUnlock premium content • VIP access • Elevated journey\n\n<b>Choose your plan and elevate today</b> 🌌"

def success_message(plan_name: str, expire: str, link: str) -> str:
    return (
        "<b>Payment Successful</b>\n\n"
        f"Plan activated → <code>{plan_name}</code>\n"
        f"Expires on → <code>{expire}</code>\n\n"
        "<b>Your exclusive invite link:</b>\n"
        f"<a href='{link}'>{link}</a>\n\n"
        "Enjoy your premium access 🌟"
    )

def main_menu_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Subscribe Now", callback_data="subscribe"))
    return kb

def choice_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("For Myself", callback_data="self"),
        types.InlineKeyboardButton("Gift to Friend", callback_data="gift")
    )
    kb.add(types.InlineKeyboardButton("Back", callback_data="back_main"))
    return kb

def plans_keyboard(target_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for k, p in PLANS.items():
        label = f"{p['emoji']} {p['name']} – {p['price']:,} Stars"
        kb.add(types.InlineKeyboardButton(label, callback_data=f"plan_{k}_{target_id}"))
    kb.add(types.InlineKeyboardButton("Back", callback_data="back_choice"))
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        welcome_text(),
        reply_markup=main_menu_keyboard(),
        disable_web_page_preview=True
    )

@bot.callback_query_handler(func=lambda c: c.data == "subscribe")
def show_subscribe_options(call):
    try:
        bot.edit_message_text(
            "<b>Who would you like to activate the subscription for?</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=choice_keyboard(),
            disable_web_page_preview=True
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Edit failed in subscribe: {e}")

@bot.callback_query_handler(func=lambda c: c.data in ["self", "gift", "back_main", "back_choice"])
def handle_choice(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if call.data == "back_main":
        try:
            bot.edit_message_text(
                welcome_text(),
                chat_id, msg_id,
                reply_markup=main_menu_keyboard(),
                disable_web_page_preview=True
            )
        except:
            pass
        return

    if call.data == "back_choice":
        try:
            bot.edit_message_text(
                "<b>Who would you like to activate the subscription for?</b>",
                chat_id, msg_id,
                reply_markup=choice_keyboard(),
                disable_web_page_preview=True
            )
        except:
            pass
        return

    if call.data == "gift":
        try:
            bot.edit_message_text(
                "<b>Send the numeric user ID of your friend:</b>\n\nExample: <code>123456789</code>",
                chat_id, msg_id,
                reply_markup=None
            )
            pending_gift[chat_id] = {"mode": "gift", "msg_id": msg_id}
            bot.register_next_step_handler_by_chat_id(chat_id, process_gift_id)
        except Exception as e:
            logger.error(f"Edit for gift failed: {e}")
        return

    # self
    try:
        bot.edit_message_text(
            "<b>Select your desired duration</b>",
            chat_id, msg_id,
            reply_markup=plans_keyboard(call.from_user.id),
            disable_web_page_preview=True
        )
    except:
        pass

def process_gift_id(message):
    chat_id = message.chat.id
    try:
        uid = int(message.text.strip())
        if uid <= 0:
            raise ValueError
        pending_gift[chat_id]["target_id"] = uid

        bot.edit_message_text(
            "<b>Select your desired duration</b>",
            chat_id,
            pending_gift[chat_id]["msg_id"],
            reply_markup=plans_keyboard(uid)
        )
        del pending_gift[chat_id]
    except:
        bot.reply_to(message, "Invalid user ID.\nPlease send a valid numeric ID.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("plan_"))
def process_plan(call):
    try:
        _, plan_key, target_str = call.data.split("_")
        target_id = int(target_str)
        plan = PLANS[plan_key]
    except:
        bot.answer_callback_query(call.id, "Invalid plan", show_alert=True)
        return

    payload = f"{plan_key}_{target_id}_{int(time.time())}_{random.randint(10000,99999)}"
    pending_invoices[target_id] = payload

    prices = [LabeledPrice(label=plan['name'], amount=plan['price'])]

    try:
        bot.send_invoice(
            call.message.chat.id,
            f"{plan['name']} Access",
            f"Exclusive access for {plan['days']} days",
            provider_token='',
            currency="XTR",
            prices=prices,
            start_parameter="premium-access",
            invoice_payload=payload
        )
        bot.answer_callback_query(call.id, "Opening payment...")
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        bot.answer_callback_query(call.id, "Cannot create invoice", show_alert=True)

@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout_handler(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def handle_success(message):
    payload = message.successful_payment.invoice_payload
    try:
        plan_key, target_str, _, _ = payload.split("_")
        target_id = int(target_str)
        plan = PLANS[plan_key]
    except:
        bot.send_message(message.chat.id, "Payment error. Contact support.")
        return

    pending_invoices.pop(target_id, None)

    expire_dt = datetime.now() + timedelta(days=plan["days"])
    expire_str = expire_dt.strftime("%Y-%m-%d %H:%M")

    try:
        invite = bot.create_chat_invite_link(CHANNEL_ID, member_limit=1, name=f"Premium-{target_id}")
        link = invite.invite_link
    except Exception as e:
        logger.error(f"Invite link failed: {e}")
        bot.send_message(message.chat.id, "Payment OK but link generation failed.")
        return

    data = load_data()
    data[str(target_id)] = {
        "plan": plan["name"],
        "expire": expire_str,
        "activated_by": message.from_user.id,
        "activated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_data(data)

    msg = success_message(plan["name"], expire_str, link)

    try:
        bot.send_message(target_id, msg, disable_web_page_preview=True)
    except:
        pass

    if target_id != message.from_user.id:
        bot.send_message(
            message.chat.id,
            f"<b>Gift sent successfully!</b>\n\n{msg}",
            disable_web_page_preview=True
        )

def expiration_monitor():
    while True:
        try:
            data = load_data()
            now = datetime.now()
            to_remove = []
            for uid_str, info in list(data.items()):
                try:
                    exp = datetime.strptime(info["expire"], "%Y-%m-%d %H:%M")
                    if exp < now:
                        bot.ban_chat_member(CHANNEL_ID, int(uid_str))
                        bot.unban_chat_member(CHANNEL_ID, int(uid_str))
                        to_remove.append(uid_str)
                except:
                    pass
            for uid in to_remove:
                data.pop(uid, None)
            if to_remove:
                save_data(data)
        except:
            pass
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=expiration_monitor, daemon=True).start()
    bot.infinity_polling(timeout=20)