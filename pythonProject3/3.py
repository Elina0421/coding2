import json
import csv
from datetime import datetime
import http.client
import time

# Конфигурация бота
BOT_TOKEN = "8133916829:AAH45Im8CXSEtz5CHMe2Ai5_zl8eDZPEpGA"  # Замените на ваш токен
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# База данных товаров
PRODUCTS = {
    '1': {'name': '📱 Смартфон', 'price': 25000, 'emoji': '📱'},
    '2': {'name': '💻 Ноутбук', 'price': 50000, 'emoji': '💻'},
    '3': {'name': '🎧 Наушники', 'price': 5000, 'emoji': '🎧'},
    '4': {'name': '📟 Планшет', 'price': 30000, 'emoji': '📟'},
    '5': {'name': '⌚ Умные часы', 'price': 15000, 'emoji': '⌚'},
    '6': {'name': '🖨️ Принтер', 'price': 12000, 'emoji': '🖨️'},
}

# Хранилище данных пользователей
user_data = {}


class UserCart:
    def __init__(self):
        self.items = {}  # {product_id: quantity}
        self.state = 'main'  # main, waiting_quantity, waiting_name

    def add_item(self, product_id, quantity):
        if product_id in self.items:
            self.items[product_id] += quantity
        else:
            self.items[product_id] = quantity

    def clear(self):
        self.items.clear()

    def get_cart_text(self):
        if not self.items:
            return "🛒 *Корзина пуста*"

        text = "🛒 *Ваша корзина:*\n\n"
        total = 0

        for product_id, quantity in self.items.items():
            product = PRODUCTS[product_id]
            item_total = product['price'] * quantity
            text += f"{product['emoji']} *{product['name']}*\n"
            text += f"   └ Кол-во: {quantity} шт.\n"
            text += f"   └ Цена: {product['price']} руб. × {quantity} = *{item_total} руб.*\n\n"
            total += item_total

        text += f"💰 *Итого: {total} руб.*"
        return text


def save_order_to_csv(user_id, customer_name):
    """Сохранение заказа в CSV файл"""
    cart = user_data[user_id]['cart']

    # Подготавливаем данные для CSV
    order_data = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), customer_name]

    # Добавляем товары и количества
    for product_id, quantity in cart.items.items():
        product_name = PRODUCTS[product_id]['name']
        order_data.extend([product_name, str(quantity)])

    # Записываем в CSV
    with open('orders.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(order_data)


def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения через Telegram API"""
    conn = http.client.HTTPSConnection("api.telegram.org")

    message_data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }

    if reply_markup:
        message_data['reply_markup'] = json.dumps(reply_markup)

    headers = {'Content-Type': 'application/json'}
    conn.request("POST", f"/bot{BOT_TOKEN}/sendMessage",
                 json.dumps(message_data), headers)

    response = conn.getresponse()
    conn.close()
    return response.status == 200


def get_updates(offset=None):
    """Получение обновлений от Telegram"""
    conn = http.client.HTTPSConnection("api.telegram.org")

    url = f"/bot{BOT_TOKEN}/getUpdates"
    if offset:
        url += f"?offset={offset}&timeout=30"

    conn.request("GET", url)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    conn.close()

    return json.loads(data)


def create_main_menu():
    """Создание главного меню"""
    return {
        'keyboard': [
            ['📋 Каталог товаров', '🛒 Корзина'],
            ['📝 Оформить заказ', '🗑️ Очистить корзину'],
            ['ℹ️ Помощь']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }


def create_products_keyboard():
    """Создание клавиатуры для каталога товаров"""
    keyboard = []
    row = []

    for i, (product_id, product) in enumerate(PRODUCTS.items()):
        button = {
            'text': f"{product['emoji']} {product['name']}",
            'callback_data': f"product_{product_id}"
        }
        row.append(button)

        # Создаем ряды по 2 кнопки
        if len(row) == 2 or i == len(PRODUCTS) - 1:
            keyboard.append(row)
            row = []

    # Добавляем кнопку возврата
    keyboard.append([{'text': '🔙 Назад', 'callback_data': 'back_to_main'}])

    return {'inline_keyboard': keyboard}


def create_cart_keyboard():
    """Создание клавиатуры для корзины"""
    return {
        'inline_keyboard': [
            [
                {'text': '🛒 Добавить товары', 'callback_data': 'add_more'},
                {'text': '📝 Оформить заказ', 'callback_data': 'start_order'}
            ],
            [
                {'text': '🗑️ Очистить корзину', 'callback_data': 'clear_cart'},
                {'text': '🔙 В главное меню', 'callback_data': 'back_to_main'}
            ]
        ]
    }


def create_quantity_keyboard(product_id):
    """Создание клавиатуры для выбора количества"""
    return {
        'inline_keyboard': [
            [
                {'text': '1 шт.', 'callback_data': f'qty_{product_id}_1'},
                {'text': '2 шт.', 'callback_data': f'qty_{product_id}_2'},
                {'text': '3 шт.', 'callback_data': f'qty_{product_id}_3'}
            ],
            [
                {'text': '5 шт.', 'callback_data': f'qty_{product_id}_5'},
                {'text': '10 шт.', 'callback_data': f'qty_{product_id}_10'},
                {'text': 'Другое количество', 'callback_data': f'custom_qty_{product_id}'}
            ],
            [
                {'text': '🔙 Назад к каталогу', 'callback_data': 'back_to_products'}
            ]
        ]
    }


def create_back_keyboard():
    """Создание простой кнопки назад"""
    return {
        'inline_keyboard': [
            [{'text': '🔙 Назад', 'callback_data': 'back_to_main'}]
        ]
    }


def handle_message(chat_id, text, message_id=None):
    """Обработка текстовых сообщений"""
    if chat_id not in user_data:
        user_data[chat_id] = {'cart': UserCart()}

    cart = user_data[chat_id]['cart']

    if cart.state == 'waiting_quantity':
        try:
            quantity = int(text)
            if quantity > 0:
                product_id = user_data[chat_id].get('selected_product')
                if product_id:
                    cart.add_item(product_id, quantity)
                    cart.state = 'main'
                    product_name = PRODUCTS[product_id]['name']
                    send_message(chat_id,
                                 f"✅ *Товар добавлен в корзину!*\n\n"
                                 f"{PRODUCTS[product_id]['emoji']} *{product_name}*\n"
                                 f"📦 Количество: *{quantity} шт.*\n"
                                 f"💰 Сумма: *{PRODUCTS[product_id]['price'] * quantity} руб.*",
                                 create_main_menu())
            else:
                send_message(chat_id, "❌ Пожалуйста, введите положительное число")
        except ValueError:
            send_message(chat_id, "❌ Пожалуйста, введите корректное число")

    elif cart.state == 'waiting_name':
        if len(text.split()) >= 2:
            save_order_to_csv(chat_id, text)
            cart.clear()
            cart.state = 'main'
            send_message(chat_id,
                         f"🎉 *Заказ успешно оформлен!*\n\n"
                         f"👤 Заказчик: *{text}*\n"
                         f"📋 Данные сохранены в файл orders.csv\n"
                         f"⏰ Дата: *{datetime.now().strftime('%d.%m.%Y %H:%M')}*\n\n"
                         f"🛍️ Для нового заказа используйте кнопку '📋 Каталог товаров'",
                         create_main_menu())
        else:
            send_message(chat_id, "❌ Пожалуйста, введите Имя и Фамилию через пробел")

    elif text == '📋 Каталог товаров':
        send_message(chat_id,
                     "🏪 *Каталог товаров*\n\n"
                     "Выберите товар для добавления в корзину:",
                     create_products_keyboard())

    elif text == '🛒 Корзина':
        cart_text = cart.get_cart_text()
        if cart.items:
            send_message(chat_id, cart_text, create_cart_keyboard())
        else:
            send_message(chat_id, cart_text, create_main_menu())

    elif text == '📝 Оформить заказ':
        if cart.items:
            cart.state = 'waiting_name'
            send_message(chat_id,
                         "📝 *Оформление заказа*\n\n"
                         "Пожалуйста, введите ваше *Имя и Фамилию*:",
                         create_back_keyboard())
        else:
            send_message(chat_id, "❌ Корзина пуста! Сначала добавьте товары.", create_main_menu())

    elif text == '🗑️ Очистить корзину':
        cart.clear()
        cart.state = 'main'
        send_message(chat_id, "🗑️ *Корзина очищена*", create_main_menu())

    elif text == 'ℹ️ Помощь':
        send_message(chat_id,
                     "🤖 *Помощь по боту*\n\n"
                     "*Как пользоваться:*\n"
                     "1. 📋 *Каталог товаров* - выбрать товар\n"
                     "2. 🛒 *Корзина* - посмотреть корзину\n"
                     "3. 📝 *Оформить заказ* - завершить покупки\n\n"
                     "*Функции:*\n"
                     "• Добавление товаров в корзину\n"
                     "• Указание количества\n"
                     "• Просмотр суммы заказа\n"
                     "• Автосохранение в Excel\n\n"
                     "Просто используйте кнопки меню ниже! 👇",
                     create_main_menu())

    elif text.startswith('/'):
        handle_command(chat_id, text)

    else:
        send_message(chat_id,
                     "🤖 *Добро пожаловать в магазин!*\n\n"
                     "Используйте кнопки меню для навигации:",
                     create_main_menu())


def handle_command(chat_id, command):
    """Обработка команд"""
    if command == '/start':
        send_message(chat_id,
                     "🛍️ *Добро пожаловать в магазин электроники!*\n\n"
                     "Здесь вы можете заказать:\n"
                     "📱 Смартфоны • 💻 Ноутбуки • 🎧 Наушники\n"
                     "📟 Планшеты • ⌚ Часы • и многое другое!\n\n"
                     "Используйте кнопки меню ниже 👇",
                     create_main_menu())

    elif command == '/help':
        handle_message(chat_id, 'ℹ️ Помощь')


def handle_callback(chat_id, callback_data, message_id):
    """Обработка callback кнопок"""
    if chat_id not in user_data:
        user_data[chat_id] = {'cart': UserCart()}

    cart = user_data[chat_id]['cart']

    if callback_data.startswith('product_'):
        product_id = callback_data.split('_')[1]
        if product_id in PRODUCTS:
            product = PRODUCTS[product_id]
            send_message(chat_id,
                         f"🛒 *Добавление в корзину*\n\n"
                         f"{product['emoji']} *{product['name']}*\n"
                         f"💰 Цена: *{product['price']} руб.*\n\n"
                         "Выберите количество:",
                         create_quantity_keyboard(product_id))

    elif callback_data.startswith('qty_'):
        # Обработка предустановленных количеств
        parts = callback_data.split('_')
        product_id = parts[1]
        quantity = int(parts[2])

        if product_id in PRODUCTS:
            cart.add_item(product_id, quantity)
            product = PRODUCTS[product_id]
            send_message(chat_id,
                         f"✅ *Товар добавлен в корзину!*\n\n"
                         f"{product['emoji']} *{product['name']}*\n"
                         f"📦 Количество: *{quantity} шт.*\n"
                         f"💰 Сумма: *{product['price'] * quantity} руб.*",
                         create_main_menu())

    elif callback_data.startswith('custom_qty_'):
        product_id = callback_data.split('_')[2]
        if product_id in PRODUCTS:
            user_data[chat_id]['selected_product'] = product_id
            cart.state = 'waiting_quantity'
            product = PRODUCTS[product_id]
            send_message(chat_id,
                         f"📦 *Введите количество*\n\n"
                         f"{product['emoji']} *{product['name']}*\n"
                         f"💰 Цена: *{product['price']} руб.*\n\n"
                         "Введите число:")

    elif callback_data == 'clear_cart':
        cart.clear()
        cart.state = 'main'
        send_message(chat_id, "🗑️ *Корзина очищена*", create_main_menu())

    elif callback_data == 'start_order':
        if cart.items:
            cart.state = 'waiting_name'
            send_message(chat_id,
                         "📝 *Оформление заказа*\n\n"
                         "Пожалуйста, введите ваше *Имя и Фамилию*:",
                         create_back_keyboard())
        else:
            send_message(chat_id, "❌ Корзина пуста!", create_main_menu())

    elif callback_data == 'add_more':
        send_message(chat_id,
                     "🏪 *Каталог товаров*\n\n"
                     "Выберите товар для добавления в корзину:",
                     create_products_keyboard())

    elif callback_data == 'back_to_main':
        cart.state = 'main'
        send_message(chat_id, "🔙 *Главное меню*", create_main_menu())

    elif callback_data == 'back_to_products':
        send_message(chat_id,
                     "🏪 *Каталог товаров*\n\n"
                     "Выберите товар для добавления в корзину:",
                     create_products_keyboard())


def main():
    """Основной цикл бота"""
    print("🤖 Бот запущен...")
    print("🎨 Дизайн кнопок активирован!")
    last_update_id = None

    # Создаем CSV файл с заголовками
    try:
        with open('orders.csv', 'x', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Дата', 'Имя Фамилия', 'Товар_1', 'Количество_1', 'Товар_2', 'Количество_2'])
        print("📊 Файл orders.csv создан")
    except FileExistsError:
        print("📊 Файл orders.csv уже существует")

    while True:
        try:
            updates = get_updates(last_update_id)

            if updates.get('ok'):
                for update in updates['result']:
                    last_update_id = update['update_id'] + 1

                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        text = message.get('text', '')

                        if text:
                            handle_message(chat_id, text, message.get('message_id'))

                    elif 'callback_query' in update:
                        callback = update['callback_query']
                        chat_id = callback['message']['chat']['id']
                        callback_data = callback['data']
                        message_id = callback['message']['message_id']

                        handle_callback(chat_id, callback_data, message_id)

            time.sleep(1)

        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
