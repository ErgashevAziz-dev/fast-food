import requests
import logging
from uuid import uuid4
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton, ReplyKeyboardRemove
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
TOKEN = '7930486457:AAEeEoJcBYPaLgnkgQdO2gT3Fy-yAWgtlks'
ADMIN_GROUP_ID = -1003832599874  ## Adminlar guruhining ID sini yozing

logging.basicConfig(level=logging.INFO)

# ================== DATA ==================
API_URL = "http://127.0.0.1:8000/api/categories/"

def get_categories():
    try:
        r = requests.get(API_URL)
        if r.status_code == 200:
            data = r.json()
            cats = {}
            for c in data:
                name = c["name"]
                cats[name] = []
                for p in c["products"]:
                    # Price ni integer saqlaymiz
                    cats[name].append({"name": p["name"], "price": int(p["price"])})
            return cats
        return {}
    except Exception as e:
        print("API xatolik:", e)
        return {}

USERS = {}   # user_id -> user data
ORDERS = {}  # order_id -> order data


# ================== KEYBOARDS ==================
def main_menu():
    kb = [
        # 1-qator: Buyurtma berish
        [InlineKeyboardButton("🍔 BUYURTMA BERISH 🍟", callback_data="open_categories")],

        # 2-qator: Buyurtmalarim va Biz haqimizda yonma-yon
        [
            InlineKeyboardButton("🛒 BUYURTMALARIM", callback_data="cart"),
            InlineKeyboardButton("ℹ️ Biz haqimizda", callback_data="about")
        ],

        # 3-qator: Bog‘lanish
        [InlineKeyboardButton("📞 Bog‘lanish", callback_data="contact_us")]
    ]
    return InlineKeyboardMarkup(kb)




def categories_menu():
    categories = get_categories()

    kb = []
    for cat in categories:
        kb.append([
            InlineKeyboardButton(
                f"📂  {cat.upper()}  ",
                callback_data=f"cat|{cat}"
            )
        ])

    kb.append([InlineKeyboardButton("⬅️orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(kb)

def open_categories(update: Update, context: CallbackContext):
    kb = []
    query = update.callback_query
    query.answer()

    query.edit_message_text(
        text="📋 Kategoriyani tanlang:",
        reply_markup=categories_menu()
    )
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(kb)

def products_menu(category):
    categories = get_categories()
    kb = []
    for i, item in enumerate(categories.get(category, [])):
        price_display = f"{item['price']:,}".replace(",", ".")
        kb.append([InlineKeyboardButton(
            f"{item['name']} - {price_display} so'm",
            callback_data=f"add|{category}|{i}"
        )])
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(kb)

def cart_menu(user_id):
    kb = []
    cart = USERS[user_id]["cart"]

    for key, item in cart.items():
        kb.append([InlineKeyboardButton(
            f"{item['name']} x{item['qty']}",
            callback_data=f"edit|{key}"
        )])

    if cart:
        kb.append([InlineKeyboardButton("✅ Buyurtma berish", callback_data="order")])
        kb.append([InlineKeyboardButton("🗑 Savatchani tozalash", callback_data="clear")])

    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def edit_item_keyboard(key, qty):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data=f"dec|{key}"),
            InlineKeyboardButton(str(qty), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"inc|{key}")
        ],
        [InlineKeyboardButton("⬅️ Savatchaga qaytish", callback_data="cart")]
    ])

def confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Ha, tasdiqlayman", callback_data="confirm_order"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_order")
        ]
    ])

def calculate_total(cart):
    # Narxlarni integer sifatida hisoblaymiz
    return sum(int(item["price"]) * item["qty"] for item in cart.values())


def start_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def location_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Lokatsiyani yuborish", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# ================== START ==================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in USERS:
        USERS[user_id] = {"phone": None, "location": None, "address": None, "cart": {}, "step": "phone"}
    else:
        USERS[user_id]["step"] = "phone"  # qayta start bosilganda

    update.message.reply_text(
        "Miglavash | Delivery botiga xush kelibsiz! 🍽️"
    )

    update.message.reply_text(
        "Iltimos, telefon raqamingizni yuboring:",
        reply_markup=start_keyboard()
    )

def contact_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if USERS[user_id]["step"] != "phone":
        return  # agar hozir telefon bosqichi bo'lmasa, hech narsa qilmaymiz
    USERS[user_id]["phone"] = update.message.contact.phone_number
    USERS[user_id]["step"] = "location"
    update.message.reply_text(
        "Iltimos, lokatsiyani yuboring:",
        reply_markup=location_keyboard()
    )

def location_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if USERS[user_id]["step"] != "location":
        return  # faqat lokatsiya bosqichi uchun
    loc = update.message.location
    USERS[user_id]["location"] = (loc.latitude, loc.longitude)
    USERS[user_id]["step"] = "address"
    update.message.reply_text(
        "Manzilni to'liq yozing:\n\nMasalan: 12-uy, 3-podyezd, 4-qavat",
        reply_markup=ReplyKeyboardRemove()
    )

def address_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if USERS[user_id]["step"] != "address":
        return  # faqat address bosqichi uchun
    USERS[user_id]["address"] = update.message.text
    USERS[user_id]["step"] = "menu"
    update.message.reply_text(
        "Quyidagilardan birini tanlang 👇",
        reply_markup=main_menu()
    )

def about_menu():
    kb = [
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(kb)

def contact_menu():
    kb = [
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(kb)


# ================== CALLBACK ==================
def callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    user_id = q.from_user.id
    data = q.data

    if data == "menu":
        q.edit_message_text("Quyidagilardan birini tanlang 👇", reply_markup=main_menu())


    elif data.startswith("cat|"):

        cat = data.split("|")[1]

        # Mazzali so'zini qo'shamiz

        header = f"MAZZALI {cat.upper()}LAR \n\n" 

        q.edit_message_text(

            text=header,

            reply_markup=products_menu(cat)

        )

    elif data.startswith("add|"):
        _, cat, idx = data.split("|")
        idx = int(idx)
        categories = get_categories()
        items = categories.get(cat, [])
        if idx >= len(items):
            q.answer("Mahsulot topilmadi")
            return
        item = items[idx]

        cart = USERS[user_id]["cart"]
        key = f"{cat}_{idx}"
        if key not in cart:
            cart[key] = {"name": item["name"], "price": int(item["price"]), "qty": 1}
        elif cart[key]["qty"] < 5:
            cart[key]["qty"] += 1

        q.answer(f"{item['name']} savatchaga qo‘shildi ✅ x{cart[key]['qty']}")

    elif data == "cart":
        cart = USERS[user_id]["cart"]
        if not cart:
            q.answer("Siz hali hanuz hech narsa buyurtma bermagansiz")
            q.edit_message_text("Siz hali hanuz hech narsa buyurtma bermagansiz", reply_markup=main_menu())
            return

        total = calculate_total(cart)
        total_display = f"{total:,}".replace(",", ".")

        text = "🛒 Buyurtmalarim:\n\n"
        for i in cart.values():
            item_total = int(i["price"]) * i["qty"]
            item_display = f"{item_total:,}".replace(",", ".")
            text += f"{i['name']} x{i['qty']} = {item_display} so'm\n"
        text += f"\n💰 Jami: {total_display} so'm"
        q.edit_message_text(text, reply_markup=cart_menu(user_id))

    elif data.startswith("edit|"):
        key = data.split("|")[1]
        item = USERS[user_id]["cart"][key]
        q.edit_message_text(f"{item['name']}\nNarx: {int(item['price']):,} so'm".replace(",", "."),
                            reply_markup=edit_item_keyboard(key, item["qty"]))

    elif data.startswith("inc|"):
        key = data.split("|")[1]
        if USERS[user_id]["cart"][key]["qty"] < 10:
            USERS[user_id]["cart"][key]["qty"] += 1
        item = USERS[user_id]["cart"][key]
        q.edit_message_reply_markup(reply_markup=edit_item_keyboard(key, item["qty"]))

    elif data.startswith("dec|"):
        key = data.split("|")[1]
        if USERS[user_id]["cart"][key]["qty"] > 1:
            USERS[user_id]["cart"][key]["qty"] -= 1
        item = USERS[user_id]["cart"][key]
        q.edit_message_reply_markup(reply_markup=edit_item_keyboard(key, item["qty"]))

    elif data == "clear":
        USERS[user_id]["cart"] = {}
        q.edit_message_text("Buyurtmalar tozalandi", reply_markup=main_menu())

    elif data == "back_to_categories":
        q.edit_message_text(
            text="📋 Kategoriyani tanlang:",
            reply_markup=categories_menu()
        )

    elif data == "back_main":
        q.edit_message_text(
            text="Quyidagilardan birini tanlang 👇",
            reply_markup=main_menu()
        )

    elif data == "order":
        cart = USERS[user_id]["cart"]
        if not cart:
            q.answer("Siz hali hanuz hech narsa buyurtma bermagansiz")
            return

        total = calculate_total(cart)
        total_display = f"{total:,}".replace(",", ".")

        text = "❗ Buyurtmani tasdiqlaysizmi?\n\n"
        for i in cart.values():
            item_total = int(i["price"]) * i["qty"]
            item_display = f"{item_total:,}".replace(",", ".")
            text += f"{i['name']} x{i['qty']} = {item_display} so'm\n"
        text += f"\n💰 Jami: {total_display} so'm"
        q.edit_message_text(text, reply_markup=confirm_keyboard())

    elif data == "confirm_order":
        q.edit_message_reply_markup(reply_markup=None)
        cart = USERS[user_id]["cart"]
        total = calculate_total(cart)
        total_display = f"{total:,}".replace(",", ".")
        order_id = str(uuid4())[:8]

        ORDERS[order_id] = cart
        USERS[user_id]["cart"] = {}

        # Foydalanuvchiga xabar
        context.bot.send_message(chat_id=user_id,
                                 text="✅ Buyurtma qabul qilindi!\n\nOperatorlarimiz hozir siz bilan bog‘lanishadi.")
        context.bot.send_message(chat_id=user_id, text="Quyidagilardan birini tanlang 👇", reply_markup=main_menu())

        # Adminga
        # text = f"🆕 BUYURTMA\n🆔 {order_id}\n📞 {USERS[user_id]['phone']}\n🏠 {USERS[user_id]['address']}\n\n"
        user_chat = context.bot.get_chat(user_id)
        name = user_chat.first_name or "Noma'lum"
        username = f"@{user_chat.username}" if user_chat.username else "Username yo'q"
    
        text = (
            f"🆕 *YANGI BUYURTMA*\n"
            # f"🆔 *ID:* `{order_id}`\n"
            f"👤 *Mijoz:* {name}\n"
            f"🔤 *Username:* {username}\n"
            f"📞 *Telefon:* {USERS[user_id]['phone']}\n"
            f"🏠 *Manzil:* {USERS[user_id]['address']}\n\n"
            f"*Buyurtma tarkibi:* \n"
        )
        for i in cart.values():
            item_total = int(i["price"]) * i["qty"]
            item_display = f"{item_total:,}".replace(",", ".")
            text += f"- {i['name']} x{i['qty']} = {item_display} so'm\n"
        text += f"\n💰 Jami: {total_display} so'm"

        context.bot.send_message(ADMIN_GROUP_ID, text)
        lat, lon = USERS[user_id]["location"]
        context.bot.send_location(ADMIN_GROUP_ID, lat, lon)

    elif data == "cancel_order":
        q.edit_message_text("❌ Buyurtma bekor qilindi")
        context.bot.send_message(chat_id=user_id, text="Quyidagilardan birini tanlang 👇", reply_markup=main_menu())

    elif data == "about":
        q.edit_message_text(
            text=(
                "🍔 *Miglavash | Delivery* haqida:\n\n"
                "Bizning fast-food restoranimiz sizga tez va mazali taomlarni yetkazib beradi.\n"
                "Har doim sifat va tezlikni birinchi o‘ringa qo‘yganmiz!"
            ),
            reply_markup=about_menu(),
            parse_mode="Markdown"
        )

    elif data == "contact_us":
        q.edit_message_text(
            text=(
                "📞 Bog‘lanish:\n\n"
                "Telefon: +998 90 123 45 67\n"
                "Telegram: @miglavash_support\n"
                "Email: info@miglavash.uz"
            ),
            reply_markup=contact_menu()
        )

# ================== MAIN ==================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))
    dp.add_handler(MessageHandler(Filters.location, location_handler))
    dp.add_handler(CallbackQueryHandler(open_categories, pattern="^open_categories$"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, address_handler))
    dp.add_handler(CallbackQueryHandler(callback))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
