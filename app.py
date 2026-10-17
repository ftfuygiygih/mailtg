from flask import Flask, request, render_template_string
import smtplib
from email.mime.text import MIMEText
import itertools
import time
import threading
import random
import requests

app = Flask(__name__)

# --- Настройки Telegram ---
TELEGRAM_BOT_TOKEN = '8793490491:AAH1aXRS3k9xzbouVQBIP-UjwWYD5jPeJ1U' 
TELEGRAM_CHAT_ID = '8705859046'            

def send_telegram_message(text):
    if TELEGRAM_BOT_TOKEN == 'ТВОЙ_ТОКЕН_ОТ_BOTFATHER' or TELEGRAM_CHAT_ID == 'ТВОЙ_CHAT_ID':
        print("⚠️ Telegram уведомление не отправлено: не настроен токен или chat_id.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

# Веб-панель (Без поля "Отправители", так как они читаются из файла)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Панель рассылки eChat</title>
    <style>
        body { background-color: #121212; color: #ffffff; font-family: sans-serif; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 8px; }
        label { display: block; margin-top: 15px; font-weight: bold; color: #bb86fc; }
        input, textarea { width: 100%; box-sizing: border-box; background: #2c2c2c; color: #fff; border: 1px solid #444; padding: 10px; border-radius: 4px; margin-top: 5px; }
        button { background: #bb86fc; color: #000; border: none; padding: 12px 20px; margin-top: 20px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%; }
        button:hover { background: #9b68e6; }
        .success { color: #03dac6; margin-top: 20px; font-weight: bold; text-align: center; }
        .error { color: #cf6679; margin-top: 20px; font-weight: bold; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Система рассылки кодов</h2>
        {% if message %}
            <div class="success">{{ message }}</div>
        {% endif %}
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <label>Мастер-пароль (пин-код):</label>
            <input type="password" name="pincode" required placeholder="Введите пароль для запуска">

            <label>Кому отправляем:</label>
            <div style="font-size: 12px; color: #aaa;">Формат: один email на строку</div>
            <textarea name="targets" rows="4" required placeholder="user1@gmail.com&#10;user2@yandex.ru"></textarea>

            <label>Тема письма:</label>
            <input type="text" name="subject" required value="Код авторизации в eChat">

            <label>Текст письма:</label>
            <div style="font-size: 12px; color: #aaa;">Используйте <b>{code}</b> чтобы вставить сгенерированный код.</div>
            <textarea name="body" rows="4" required placeholder="Твой код подтверждения: {code}"></textarea>

            <label>Интервал между отправками (в секундах):</label>
            <input type="number" name="delay" value="5" min="1" required>

            <button type="submit">Запустить рассылку</button>
        </form>
    </div>
</body>
</html>
"""

def mailer_worker(senders_list, targets_list, subject, body_template, delay):
    sender_pool = itertools.cycle(senders_list)
    success_count = 0
    error_count = 0
    
    send_telegram_message(f"🚀 <b>Начата новая сессия рассылки</b>\nВсего адресов в очереди: {len(targets_list)}")

    for target in targets_list:
        current = next(sender_pool)
        unique_code = str(random.randint(100000, 999999))
        final_body = body_template.replace("{code}", unique_code)
        
        msg = MIMEText(final_body)
        msg["Subject"] = subject
        msg["From"] = current["email"]
        msg["To"] = target
        
                try:
            # Используем SMTP_SSL и порт 465
            with smtplib.SMTP_SSL("smtp.firstmail.ltd", 465) as server:
                server.login(current["email"], current["password"])
                server.send_message(msg)

            
            print(f"✅ Отправлено: {target} (код: {unique_code})")
            success_count += 1
            send_telegram_message(f"✅ Письмо успешно ушло на <b>{target}</b>\nС ящика: <code>{current['email']}</code>\nКод: {unique_code}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки на {target}: {e}")
            error_count += 1
            send_telegram_message(f"❌ Ошибка при отправке на <b>{target}</b>\nС ящика: <code>{current['email']}</code>\nПричина: {e}")
        
        time.sleep(delay)
        
    report_msg = (
        "📊 <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно отправлено: <b>{success_count}</b>\n"
        f"❌ Ошибок: <b>{error_count}</b>"
    )
    send_telegram_message(report_msg)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. Проверяем пин-код
        user_pincode = request.form.get('pincode', '')
        if user_pincode != '1234':  # ЗАМЕНИ НА СВОЙ ПИН-КОД!
            return render_template_string(HTML_TEMPLATE, error="❌ Неверный пин-код!")

        # 2. Читаем отправителей из файла senders.txt
        senders_list = []
        try:
            with open('senders.txt', 'r', encoding='utf-8') as f:
                raw_senders = f.read().strip().split('\n')
                
            for line in raw_senders:
                if ':' in line:
                    email, pwd = line.split(':', 1)
                    senders_list.append({"email": email.strip(), "password": pwd.strip()})
        except FileNotFoundError:
            return render_template_string(HTML_TEMPLATE, error="❌ Ошибка: файл senders.txt не найден рядом со скриптом!")

        if not senders_list:
            return render_template_string(HTML_TEMPLATE, error="❌ В файле senders.txt нет корректных аккаунтов (формат почта:пароль)")

        # 3. Собираем остальные данные из формы
        raw_targets = request.form.get('targets', '').strip().split('\n')
        subject = request.form.get('subject', 'Уведомление')
        body = request.form.get('body', '')
        delay = int(request.form.get('delay', 5))
        
        targets_list = [t.strip() for t in raw_targets if t.strip()]

        if targets_list:
            thread = threading.Thread(
                target=mailer_worker, 
                args=(senders_list, targets_list, subject, body, delay)
            )
            thread.start()
            
            return render_template_string(HTML_TEMPLATE, message="🚀 Рассылка запущена! Чекни Telegram.")

    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
