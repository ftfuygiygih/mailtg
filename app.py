from flask import Flask, request, render_template_string
import smtplib
from email.mime.text import MIMEText
import itertools
import time
import threading
import random
import requests
import ssl  # Добавлен импорт ssl для обхода ошибки сертификатов

app = Flask(__name__)

# --- Настройки Telegram ---
TELEGRAM_BOT_TOKEN = '8793490491:AAH1aXRS3k9xzbouVQBIP-UjwWYD5jPeJ1U' 
TELEGRAM_CHAT_ID = '8705859046'   

def send_telegram_message(text):
    if TELEGRAM_BOT_TOKEN == 'ТВОЙ_ТОКЕН_ОТ_BOTFATHER' or TELEGRAM_CHAT_ID == 'ТВОЙ_CHAT_ID':
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def load_senders():
    """Функция для чтения почт из файла"""
    senders = []
    try:
        with open('senders.txt', 'r', encoding='utf-8') as f:
            for line in f.read().strip().split('\n'):
                if ':' in line:
                    email, pwd = line.split(':', 1)
                    senders.append({"email": email.strip(), "password": pwd.strip()})
    except FileNotFoundError:
        pass
    return senders

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
        input[type="text"], input[type="password"], input[type="number"], textarea { width: 100%; box-sizing: border-box; background: #2c2c2c; color: #fff; border: 1px solid #444; padding: 10px; border-radius: 4px; margin-top: 5px; }
        
        .controls { display: flex; gap: 10px; margin-top: 10px; align-items: center; flex-wrap: wrap; }
        .controls button { background: #333; color: #fff; border: 1px solid #555; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; margin: 0;}
        .controls button:hover { background: #444; }
        .controls input[type="number"] { width: 60px; padding: 6px; margin: 0; }
        
        .checkbox-list { background: #2c2c2c; padding: 15px; border-radius: 4px; margin-top: 10px; max-height: 150px; overflow-y: auto; border: 1px solid #444; }
        .checkbox-list label { display: flex; align-items: center; margin-top: 5px; font-weight: normal; color: #ddd; cursor: pointer; }
        .checkbox-list input[type="checkbox"] { width: auto; margin: 0 10px 0 0; cursor: pointer; transform: scale(1.2); }
        
        .btn-submit { background: #bb86fc; color: #000; border: none; padding: 12px 20px; margin-top: 25px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; }
        .btn-submit:hover { background: #9b68e6; }
        .success { color: #03dac6; margin-top: 20px; font-weight: bold; text-align: center; background: rgba(3, 218, 198, 0.1); padding: 10px; border-radius: 4px;}
        .error { color: #cf6679; margin-top: 20px; font-weight: bold; text-align: center; background: rgba(207, 102, 121, 0.1); padding: 10px; border-radius: 4px;}
    </style>
    <script>
        function selectAll(state) {
            document.querySelectorAll('input[name="selected_senders"]').forEach(cb => cb.checked = state);
        }
        function selectRandom() {
            selectAll(false);
            let checkboxes = Array.from(document.querySelectorAll('input[name="selected_senders"]'));
            let count = parseInt(document.getElementById('randomCount').value) || 1;
            
            for (let i = checkboxes.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [checkboxes[i], checkboxes[j]] = [checkboxes[j], checkboxes[i]];
            }
            for(let i=0; i < Math.min(count, checkboxes.length); i++) {
                checkboxes[i].checked = true;
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>Система рассылки eChat</h2>
        {% if message %}<div class="success">{{ message }}</div>{% endif %}
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        
        <form method="POST">
            <label>Мастер-пароль (пин-код):</label>
            <input type="password" name="pincode" required placeholder="Введите пароль для запуска">

            <label>Выберите отправителей (Найдено: {{ emails|length }}):</label>
            <div class="controls">
                <button type="button" onclick="selectAll(true)">Выбрать все</button>
                <button type="button" onclick="selectAll(false)">Снять все</button>
                <button type="button" onclick="selectRandom()">Рандомно:</button>
                <input type="number" id="randomCount" min="1" max="{{ emails|length }}" value="1"> шт.
            </div>
            
            <div class="checkbox-list">
                {% if emails %}
                    {% for email in emails %}
                    <label>
                        <input type="checkbox" name="selected_senders" value="{{ email }}" checked>
                        {{ email }}
                    </label>
                    {% endfor %}
                {% else %}
                    <div style="color:#cf6679;">Файл senders.txt пуст или не найден!</div>
                {% endif %}
            </div>

            <label>Кому отправляем (один email на строку):</label>
            <textarea name="targets" rows="4" required placeholder="user1@gmail.com&#10;user2@yandex.ru"></textarea>

            <label>Тема письма:</label>
            <input type="text" name="subject" required value="Код авторизации в eChat">

            <label>Текст письма:</label>
            <div style="font-size: 12px; color: #aaa;">Используйте <b>{code}</b> чтобы вставить сгенерированный код.</div>
            <textarea name="body" rows="4" required placeholder="Твой код подтверждения: {code}"></textarea>

            <label>Интервал между отправками (в секундах):</label>
            <input type="number" name="delay" value="5" min="1" required>

            <button type="submit" class="btn-submit">🚀 Запустить рассылку</button>
        </form>
    </div>
</body>
</html>
"""

def mailer_worker(senders_list, targets_list, subject, body_template, delay):
    sender_pool = itertools.cycle(senders_list)
    success_count = 0
    error_count = 0
    
    send_telegram_message(f"🚀 <b>Начата рассылка</b>\nОтправителей в работе: {len(senders_list)}\nПолучателей: {len(targets_list)}")

    for target in targets_list:
        current = next(sender_pool)
        unique_code = str(random.randint(100000, 999999))
        final_body = body_template.replace("{code}", unique_code)
        
        msg = MIMEText(final_body)
        msg["Subject"] = subject
        msg["From"] = current["email"]
        msg["To"] = target
        
        try:
            # Создаем контекст, игнорирующий ошибки SSL-сертификатов a-Shell
            context = ssl._create_unverified_context()
            with smtplib.SMTP("smtp.firstmail.ltd", 587) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(current["email"], current["password"])
                server.send_message(msg)
            
            print(f"✅ Отправлено: {target} (код: {unique_code})")
            success_count += 1
            send_telegram_message(f"✅ Ушло на <b>{target}</b>\nС ящика: <code>{current['email']}</code>\nКод: {unique_code}")
            
        except Exception as e:
            print(f"❌ Ошибка на {target}: {e}")
            error_count += 1
            send_telegram_message(f"❌ Ошибка отправки на <b>{target}</b>\nС ящика: <code>{current['email']}</code>\nПричина: {e}")
        
        time.sleep(delay)
        
    report_msg = (
        "📊 <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: <b>{success_count}</b>\n"
        f"❌ Ошибок: <b>{error_count}</b>"
    )
    send_telegram_message(report_msg)

@app.route('/', methods=['GET', 'POST'])
def index():
    all_senders = load_senders()
    emails_only = [s['email'] for s in all_senders]

    if request.method == 'POST':
        if request.form.get('pincode', '') != '1234':
            return render_template_string(HTML_TEMPLATE, error="❌ Неверный пин-код!", emails=emails_only)

        selected_emails = request.form.getlist('selected_senders')
        if not selected_emails:
            return render_template_string(HTML_TEMPLATE, error="❌ Вы не выбрали ни одного отправителя!", emails=emails_only)

        active_senders = [s for s in all_senders if s['email'] in selected_emails]

        raw_targets = request.form.get('targets', '').strip().split('\n')
        targets_list = [t.strip() for t in raw_targets if t.strip()]
        
        subject = request.form.get('subject', '')
        body = request.form.get('body', '')
        delay = int(request.form.get('delay', 5))

        if targets_list:
            thread = threading.Thread(
                target=mailer_worker, 
                args=(active_senders, targets_list, subject, body, delay)
            )
            thread.start()
            return render_template_string(HTML_TEMPLATE, message="🚀 Рассылка запущена! Чекни Telegram.", emails=emails_only)
        else:
            return render_template_string(HTML_TEMPLATE, error="❌ Нет получателей!", emails=emails_only)

    return render_template_string(HTML_TEMPLATE, emails=emails_only)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
