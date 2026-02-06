import requests
import logging
from uuid import uuid4
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

# ================== SOZLAMALAR ==================
TOKEN = "8476294860:AAEvCdHlERD-Vg4C-IJwoCnE_52Iwy7sUQ4"
ADMIN_GROUP_ID = -1003832599874

logging.basicConfig(level=logging.INFO)

API_URL = "http://127.0.0.1:8000/api/categories/"

# ================== DATA ==================
USERS = {}
ORDERS = {}

def get_user(user_id):
    if user_id not in USERS:
        USERS[user_id] = {
            "cart": {},
            "phone": None,
            "location": None,
            "address": None,
            "step": None
        }
    return USERS[user_id]

def get_categories():
    try:
        r = requests.get(API_URL, timeout=5)
        if r.status_code == 200:
            data = r.json()
            result = {}
            for c in data:
                result[c["name"]] = []
                for p in c["products"]:
                    result[c["name"]].append({
                        "name": p["name"],
                        "price": int(p["price"])
                    })
            return result
    except Exception as e:
        print("API xato:", e)
    return {}

# ================== KEYBOARDS ==================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍔 BUYURTMA BERISH 🍟", callback_data="open_categories")],
        [
            InlineKeyboardButton("ℹ️ Biz haqimizda", callback_data="about"),
            InlineKeyboardButton("🛒 Buyurtmalarim", callback_data="cart")
        ],
        [InlineKeyboardButton("📞 Bog‘lanish", callback_data="contact")]
    ])

def categories_menu():
    kb = []
    for cat in get_categories():
        kb.append([InlineKeyboardButton(f"📂 {cat.upper()}", callback_data=f"cat|{cat}")])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def products_menu(category):
    kb = []
    items = get_categories().get(category, [])
    for i, item in enumerate(items):
        price = f"{item['price']:,}".replace(",", ".")
        kb.append([InlineKeyboardButton(
            f"{item['name']} - {price} so'm",
            callback_data=f"add|{category}|{i}"
        )])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="open_categories")])
    return InlineKeyboardMarkup(kb)

def cart_menu(user_id):
    user = get_user(user_id)
    kb = []
    for key, item in user["cart"].items():
        kb.append([InlineKeyboardButton(
            f"{item['name']} x{item['qty']}",
            callback_data=f"edit|{key}"
        )])
    if user["cart"]:
        kb.append([InlineKeyboardButton("✅ Buyurtma berish", callback_data="order")])
        kb.append([InlineKeyboardButton("🗑 Savatchani tozalash", callback_data="clear")])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def edit_keyboard(key, qty):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data=f"dec|{key}"),
            InlineKeyboardButton(str(qty), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"inc|{key}")
        ],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="cart")]
    ])

def confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlayman", callback_data="confirm"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
        ]
    ])

# ================== START ==================
def start(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    user["step"] = "phone"

    update.message.reply_text(
        "Miglavash | Delivery 🍔\n\nTelefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Telefon yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

def contact_handler(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if user["step"] != "phone":
        return
    user["phone"] = update.message.contact.phone_number
    user["step"] = "location"

    update.message.reply_text(
        "📍 Lokatsiyani yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Lokatsiya yuborish", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

def location_handler(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if user["step"] != "location":
        return
    loc = update.message.location
    user["location"] = (loc.latitude, loc.longitude)
    user["step"] = "address"

    update.message.reply_text(
        "🏠 Manzilni yozing:",
        reply_markup=ReplyKeyboardRemove()
    )

def address_handler(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if user["step"] != "address":
        return
    user["address"] = update.message.text
    user["step"] = "menu"

    update.message.reply_text(
        "Quyidagilardan birini tanlang 👇",
        reply_markup=main_menu()
    )

# ================== CALLBACK ==================
def callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    user_id = q.from_user.id
    user = get_user(user_id)
    data = q.data

    if data == "menu":
        q.edit_message_text("Tanlang 👇", reply_markup=main_menu())

    elif data == "open_categories":
        q.edit_message_text("📋 Kategoriya:", reply_markup=categories_menu())

    elif data.startswith("cat|"):
        cat = data.split("|")[1]
        q.edit_message_text(f"🍽 {cat.upper()}:", reply_markup=products_menu(cat))

    elif data.startswith("add|"):
        _, cat, idx = data.split("|")
        idx = int(idx)
        item = get_categories()[cat][idx]

        key = f"{cat}_{idx}"
        cart = user["cart"]
        if key not in cart:
            cart[key] = {"name": item["name"], "price": item["price"], "qty": 1}
        else:
            cart[key]["qty"] += 1

        q.answer(
            f"{item['name']} savatchaga qo‘shildi ✅\nSoni: {cart[key]['qty']}",
            show_alert=True
        )

    elif data == "cart":
        if not user["cart"]:
            q.edit_message_text("Savatcha bo‘sh", reply_markup=main_menu())
            return

        text = "🛒 Buyurtmalar:\n\n"
        total = 0
        for i in user["cart"].values():
            s = i["price"] * i["qty"]
            total += s
            text += f"{i['name']} x{i['qty']} = {s:,} so'm\n".replace(",", ".")
        text += f"\n💰 Jami: {total:,} so'm".replace(",", ".")

        q.edit_message_text(text, reply_markup=cart_menu(user_id))

    elif data.startswith("edit|"):
        key = data.split("|")[1]
        item = user["cart"][key]
        q.edit_message_text(
            f"{item['name']}",
            reply_markup=edit_keyboard(key, item["qty"])
        )

    elif data.startswith("inc|"):
        key = data.split("|")[1]
        user["cart"][key]["qty"] += 1
        q.edit_message_reply_markup(
            reply_markup=edit_keyboard(key, user["cart"][key]["qty"])
        )

    elif data.startswith("dec|"):
        key = data.split("|")[1]
        if user["cart"][key]["qty"] > 1:
            user["cart"][key]["qty"] -= 1
        q.edit_message_reply_markup(
            reply_markup=edit_keyboard(key, user["cart"][key]["qty"])
        )

    elif data == "clear":
        user["cart"].clear()
        q.edit_message_text("🗑 Savatcha tozalandi", reply_markup=main_menu())

    elif data == "order":
        q.edit_message_text("Buyurtmani tasdiqlaysizmi?", reply_markup=confirm_keyboard())

    elif data == "confirm":
        order_id = str(uuid4())[:8]

        name = q.from_user.first_name or "Mijoz"
        user_link = f"<a href='tg://user?id={user_id}'>{name}</a>"

        text = (
            f"🆕 YANGI BUYURTMA\n\n"
            f"👤 {user_link}\n"
            f"📞 {user['phone']}\n"
            f"🏠 {user['address']}\n\n"
        )

        total = 0
        for i in user["cart"].values():
            s = i["price"] * i["qty"]
            total += s
            text += f"- {i['name']} x{i['qty']} = {s:,} so'm\n".replace(",", ".")

        text += f"\n💰 Jami: {total:,} so'm".replace(",", ".")

        context.bot.send_message(ADMIN_GROUP_ID, text, parse_mode="HTML")
        lat, lon = user["location"]
        context.bot.send_location(ADMIN_GROUP_ID, lat, lon)

        user["cart"].clear()

        q.edit_message_text("✅ Buyurtma qabul qilindi!", reply_markup=main_menu())

    elif data == "cancel":
        q.edit_message_text("❌ Bekor qilindi", reply_markup=main_menu())

    elif data == "about":
        q.edit_message_text("Miglavash | Fast Food 🍔", reply_markup=main_menu())

    elif data == "contact":
        q.edit_message_text("📞 +998 98 100 69 90", reply_markup=main_menu())

# ================== MAIN ==================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))
    dp.add_handler(MessageHandler(Filters.location, location_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, address_handler))
    dp.add_handler(CallbackQueryHandler(callback))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
