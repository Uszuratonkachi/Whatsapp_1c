import requests
import json
import time
from datetime import datetime, timedelta, timezone
from requests.auth import HTTPBasicAuth

# Ваши данные для Green API
instance_id = "7103953253"
token = "6466530a17e046de97d6177312cc2b46828a0d225e0948eca2"
green_api_url = f"https://api.green-api.com/waInstance{instance_id}/SendMessage/{token}"

# Ссылка на Google Форму
google_form_link = "https://docs.google.com/forms/d/e/1FAIpQLSdyDlEhpX6oafzYpbszq-kg4gnH3g8y2K7zZLoE7R7hR59pNA/viewform?usp=sf_link"

# Шаблон сообщения
message_template = (
    "Добрый день! \n\n"
    "Пожалуйста, посетите и оцените наш товар по следующей ссылке: \n\n"
    f"{google_form_link}\n\n"
    "(Чтобы ссылка стала активной, напишите нам любое сообщение.)"
)

# Функция для преобразования номера телефона в формат Казахстана
def convert_to_kazakh_format(phone_number):
    if phone_number.startswith("8"):
        return "7" + phone_number[1:]
    elif phone_number.startswith("+7"):
        return phone_number[2:]
    return phone_number

# Функция для отправки сообщения через Green API
def send_message(phone_number, message):
    payload = {
        "chatId": f"{phone_number}@c.us",
        "message": message
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(green_api_url, data=json.dumps(payload), headers=headers)
    return response.json()

# Храним отправленные номера и дату отправки
sent_messages = {}
last_cleanup_date = None

def fetch_and_send_messages():
    global last_cleanup_date
    now = datetime.now(timezone.utc) + timedelta(hours=5)

    # Очищаем список, если день изменился
    if last_cleanup_date is None or last_cleanup_date.date() != now.date():
        sent_messages.clear()  # Очищаем словарь
        last_cleanup_date = now  # Обновляем дату последней очистки

    four_days_ago = now - timedelta(days=4)
    three_days_ago = now - timedelta(days=3)
    four_days_ago_str = four_days_ago.strftime('%Y%m%d')
    three_days_ago_str = three_days_ago.strftime('%Y%m%d')

    # Получаем данные с сайта
    url = f"https://asiamebel.itsg.kz/ERP_WORK/hs/wzexch/getOrderInfo?StartDate={four_days_ago_str}&EndDate={three_days_ago_str}"
    auth = HTTPBasicAuth('wzexch', 'XO5qazon')

    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json().get("body", [])
    except requests.RequestException as e:
        print(f"Ошибка при запросе данных: {e}")
        return

    # Создаем множество уникальных номеров телефонов
    unique_phone_numbers = set()

    if isinstance(data, list):
        for order in data:
            order_date = order.get("Дата", "")
            if four_days_ago_str <= order_date <= three_days_ago_str:
                contact_info = order.get("Контрагент_КонтактнаяИнформацияКонтрагент", [])
                for contact in contact_info:
                    if contact.get("Вид") == "Телефон контрагента":
                        phone_number = contact.get("Представление")
                        if not phone_number:
                            print("Пустой номер телефона, пропускаем.")
                            continue

                        kazakh_phone_number = convert_to_kazakh_format(phone_number)
                        unique_phone_numbers.add(kazakh_phone_number)

    else:
        print("Ответ не является списком. Ответ:")
        print(data)
        return

    # Отправляем сообщения только уникальным номерам
    today_str = now.strftime('%Y-%m-%d')
    for phone_number in unique_phone_numbers:
        if (phone_number in sent_messages and
                sent_messages[phone_number] == today_str):
            print(f"Сообщение уже отправлено на {phone_number} сегодня.")
            continue

        response = send_message(phone_number, message_template)
        if response.get("sent") == True:
            print(f"Сообщение отправлено на {phone_number}")
            sent_messages[phone_number] = today_str

# Бесконечный цикл для проверки времени
while True:
    current_time = datetime.now(timezone.utc) + timedelta(hours=5)

    if current_time.hour == 10 and current_time.minute == 22:
        fetch_and_send_messages()
        time.sleep(3660)
    else:
        time.sleep(60)
