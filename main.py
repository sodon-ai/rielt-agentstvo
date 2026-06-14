from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import uuid
import shutil
from datetime import datetime
from typing import Optional
import re

app = FastAPI(title="Риэлторское агентство by Гаун")

# Создаём папки
os.makedirs("static/uploads/photos", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище данных
users = {}
properties = []
messages = []  # Активные сообщения {id, username, text, time, photo}
deleted_messages = []  # Корзина для админа {id, username, text, time, photo, deleted_by, deleted_at}
notifications = []
transactions = []
current_user = None
message_counter = 1

# Инициализация админа
users["admin"] = {"password": "admin123", "role": "admin", "name": "Администратор", "email": "", "notifications": []}


def is_valid_email(email: str) -> bool:
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9_.+-]+@(mail\.ru|gmail\.com)$'
    return re.match(pattern, email) is not None


def get_base_html(content: str, user=None, error=None, success=None):
    user_html = ""
    if user:
        unread_count = len([n for n in notifications if n["to_user"] == user["username"] and not n.get("read", False)])
        notif_badge = f'<span style="background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; margin-left: 5px;">{unread_count}</span>' if unread_count > 0 else ''

        user_html = f'''
            <span>👤 {user["name"]} ({user["role"]})</span>
            <a href="/profile" class="btn">📋 Профиль{notif_badge}</a>
            <a href="/logout" class="btn">Выйти</a>
        '''
    else:
        user_html = '''
            <a href="/login" class="btn">Вход</a>
            <a href="/register" class="btn">Регистрация</a>
        '''

    error_html = f'<div class="error">{error}</div>' if error else ''
    success_html = f'<div class="success">{success}</div>' if success else ''

    return f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Риэлторское агентство by Гаун</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f7fa;
            color: #2c3e50;
        }}
        :root {{
            --light-blue: #6ec8e6;
            --medium-blue: #4ab0d0;
            --dark-blue: #2c7aa0;
            --bg-blue: #e0f2f8;
        }}
        header {{
            background: white;
            box-shadow: 0 2px 15px rgba(0,0,0,0.08);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .top-banner {{
            background: var(--light-blue);
            padding: 8px 0;
            text-align: center;
            font-size: 13px;
            color: #1a4d66;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 25px;
        }}
        .header-main {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .logo-area {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .logo-icon {{
            background: var(--light-blue);
            width: 55px;
            height: 55px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            color: white;
        }}
        .logo-text h1 {{ font-size: 18px; color: #1a4d66; }}
        .logo-text h2 {{ font-size: 22px; color: var(--dark-blue); }}
        .slogan {{ font-size: 13px; color: var(--medium-blue); }}
        nav ul {{
            display: flex;
            list-style: none;
            gap: 25px;
            flex-wrap: wrap;
        }}
        nav a {{
            text-decoration: none;
            color: #2c3e50;
            font-weight: 600;
            transition: 0.3s;
            padding: 8px 12px;
            border-radius: 8px;
        }}
        nav a:hover {{
            background: var(--bg-blue);
            color: var(--dark-blue);
        }}
        .user-info {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .btn {{
            background: var(--light-blue);
            padding: 8px 20px;
            border-radius: 25px;
            text-decoration: none;
            color: #1a4d66;
            font-weight: bold;
            border: none;
            cursor: pointer;
            display: inline-block;
        }}
        .btn:hover {{ background: var(--medium-blue); }}
        .btn-red {{
            background: #ff6b6b;
            color: white;
        }}
        .btn-red:hover {{ background: #ff5252; }}
        .hero {{
            background: linear-gradient(120deg, var(--bg-blue) 0%, white 80%);
            padding: 50px 0;
            text-align: center;
        }}
        .hero h1 {{ font-size: 42px; color: #1a5d7a; }}
        .services-block {{
            background: white;
            padding: 50px 0;
            border-bottom: 1px solid #d4e8f0;
        }}
        .services-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}
        .service-box {{
            background: #fafeff;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border-left: 4px solid var(--light-blue);
        }}
        .service-box h3 {{
            color: var(--dark-blue);
            font-size: 22px;
            margin-bottom: 15px;
        }}
        .service-box ul {{
            list-style: none;
            padding-left: 0;
        }}
        .service-box li {{
            padding: 8px 0 8px 25px;
            position: relative;
        }}
        .service-box li:before {{
            content: "•";
            color: var(--light-blue);
            font-size: 18px;
            position: absolute;
            left: 5px;
        }}
        .about-section {{
            background: #f9fdfe;
            padding: 50px 0;
            border-top: 1px solid #d4e8f0;
            border-bottom: 1px solid #d4e8f0;
        }}
        .about-section h2 {{
            font-size: 32px;
            color: #1a5d7a;
            margin-bottom: 25px;
        }}
        .about-section h3 {{
            font-size: 26px;
            color: var(--dark-blue);
            margin: 30px 0 15px 0;
        }}
        .about-section p {{
            font-size: 16px;
            line-height: 1.7;
            color: #3a5a72;
            margin-bottom: 18px;
        }}
        .about-list {{
            list-style: none;
            padding-left: 0;
        }}
        .about-list li {{
            padding: 10px 0 10px 28px;
            position: relative;
            font-size: 16px;
            line-height: 1.5;
            color: #3a5a72;
        }}
        .about-list li:before {{
            content: "•";
            color: var(--light-blue);
            font-size: 22px;
            position: absolute;
            left: 5px;
            top: 8px;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
            padding: 40px 0;
        }}
        .property-card {{
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-left: 4px solid var(--light-blue);
            transition: 0.2s;
        }}
        .property-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.12); }}
        .property-card h3 {{ color: var(--dark-blue); margin-bottom: 10px; }}
        .property-actions {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        .delete-btn {{
            background: #ff6b6b;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 8px;
            cursor: pointer;
        }}
        .rent-btn {{
            background: #4caf50;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 8px;
            cursor: pointer;
        }}
        .buy-btn {{
            background: var(--light-blue);
            color: #1a4d66;
            border: none;
            padding: 8px 15px;
            border-radius: 8px;
            cursor: pointer;
        }}
        .delete-msg-btn {{
            background: #ff6b6b;
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }}
        .form-group {{
            margin-bottom: 15px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        .form-group input, .form-group textarea, .form-group select {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .chat-messages {{
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 12px;
            padding: 15px;
            background: #f9f9f9;
            margin-bottom: 15px;
        }}
        .message {{
            margin-bottom: 15px;
            padding: 10px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            position: relative;
        }}
        .message-user {{ font-weight: bold; color: var(--dark-blue); }}
        .message-time {{ font-size: 11px; color: #999; margin-left: 10px; }}
        .message-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .message-actions {{
            display: flex;
            gap: 5px;
        }}
        .media-preview {{
            max-width: 200px;
            max-height: 150px;
            margin-top: 10px;
            border-radius: 8px;
        }}
        .chat-input-area {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .chat-input-area textarea {{
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .file-inputs {{
            margin-top: 10px;
        }}
        .file-inputs input {{
            padding: 8px;
        }}
        .error {{
            color: red;
            background: #ffe0e0;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
        }}
        .success {{
            color: green;
            background: #e0ffe0;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
        }}
        .notification {{
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 10px;
            border-left: 4px solid var(--light-blue);
        }}
        .transaction-item, .user-item {{
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 10px;
            border-left: 4px solid var(--light-blue);
        }}
        .info-section {{
            background: white;
            border-radius: 24px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        .info-section h2 {{
            color: #1a5d7a;
            margin-bottom: 20px;
        }}
        .deleted-message {{
            background: #fff3f0;
            border-left: 4px solid #ff6b6b;
            opacity: 0.8;
        }}
        footer {{
            background: #1e3a47;
            color: #cbdce6;
            padding: 30px 0;
            text-align: center;
            margin-top: 40px;
        }}
        @media (max-width: 768px) {{
            .header-main {{ flex-direction: column; text-align: center; }}
            nav ul {{ justify-content: center; }}
        }}
    </style>
</head>
<body>
<header>
    <div class="top-banner">🏡 Лянтор | Ваш надёжный партнёр в мире недвижимости</div>
    <div class="container header-main">
        <div class="logo-area">
            <div class="logo-icon">🏢</div>
            <div class="logo-text">
                <h1>РИЭЛТОРСКОЕ АГЕНТСТВО</h1>
                <h2>BY ГАУН</h2>
                <div class="slogan">МЕСТО, ГДЕ ВЫ СТАНЕТЕ СОБОЙ</div>
            </div>
        </div>
        <nav>
            <ul>
                <li><a href="/">Главная</a></li>
                <li><a href="/buy">Покупка квартиры</a></li>
                <li><a href="/sell">Продажа</a></li>
                <li><a href="/info">Сведения</a></li>
                <li><a href="/chat">Переписка</a></li>
                <li><a href="/contacts">Контакты</a></li>
            </ul>
        </nav>
        <div class="user-info">
            {user_html}
        </div>
    </div>
</header>
<main>
    {error_html}
    {success_html}
    {content}
</main>
<footer>
    <div class="container">
        <p>© 2025 Риэлторское агентство by Гаун | Лянтор</p>
    </div>
</footer>
</body>
</html>
'''


# Главная страница
@app.get("/", response_class=HTMLResponse)
async def index():
    global current_user

    cards_html = ""
    for p in properties[-6:]:
        cards_html += f'''
        <div class="property-card">
            <h3>{p["title"]}</h3>
            <p><strong>📍 Локация:</strong> {p["location"]}</p>
            <p><strong>💰 Цена:</strong> {p["price"]} ₽</p>
            <p><strong>📐 Площадь:</strong> {p["area"]} м²</p>
            <p><strong>🏗️ Этаж:</strong> {p["floor"]} / {p["total_floors"]}</p>
            <p><strong>👤 Продавец:</strong> {p["seller_name"]}</p>
        '''
        if current_user and current_user["role"] == "admin":
            cards_html += f'<form action="/delete_property/{p["id"]}" method="post"><button type="submit" class="delete-btn">Удалить</button></form>'
        cards_html += '</div>'

    if not properties:
        cards_html = '<p>Пока нет объявлений. Станьте продавцом и добавьте первое!</p>'

    content = f'''
    <section class="hero">
        <div class="container">
            <h1>Ваша недвижимость — наша профессиональная забота</h1>
            <p>Поможем купить, продать или выкупить жильё в Лянторе</p>
        </div>
    </section>

    <section class="services-block">
        <div class="container">
            <h2 style="text-align: center; color: #1a5d7a; margin-bottom: 20px;">Наши услуги</h2>
            <p style="text-align: center; color: #4a627a; margin-bottom: 10px;">Риэлторская компания / Наши услуги</p>

            <div class="services-grid">
                <div class="service-box">
                    <h3>🏠 Риэлторские услуги</h3>
                    <ul>
                        <li>Купить недвижимость</li>
                        <li>Продать недвижимость</li>
                        <li>Обмен квартир в Лянторе</li>
                        <li>Анализ стоимости объекта недвижимости</li>
                        <li>Срочный выкуп недвижимости</li>
                        <li>Помощь в получении кредита</li>
                    </ul>
                    <a href="/buy" class="btn" style="margin-top: 15px; display: inline-block;">Подробнее →</a>
                </div>

                <div class="service-box">
                    <h3>⚡ Срочный выкуп недвижимости</h3>
                    <p><strong>Агентство «by Гаун» выкупит Вашу:</strong></p>
                    <ul>
                        <li>комнату, долю в квартире</li>
                        <li>квартиру (даже требующую ремонта, с обременением)</li>
                        <li>новостройку на любой стадии строительства</li>
                    </ul>
                    <a href="/sell" class="btn" style="margin-top: 15px; display: inline-block;">Подробнее →</a>
                </div>
            </div>
        </div>
    </section>

    <section class="about-section">
        <div class="container">
            <h2>Риэлторское агентство</h2>
            <p><strong>В чем суть работы риэлторского агентства?</strong> Это помощь клиенту в подборе и продаже недвижимости. Если вы не сталкиваетесь с рынком недвижимости каждый день, то вам довольно сложно ориентироваться в адекватности цен, разнообразии планировок и даже в удачности месторасположения объекта. Работа риэлторского агентства заточена под то, чтобы помочь клиенту купить или продать свою недвижимость и сделать это максимально выгодно и комфортно.</p>

            <h3>Агентство недвижимости г. Лянтора</h3>
            <p>Работа риэлторского агентства заточена под то, чтобы помочь клиенту купить или продать свою недвижимость и сделать это максимально выгодно и комфортно.</p>
            <p>Чтобы любая сделка прошла безопасно на всех этапах, при выборе риэлторского агентства нужно учитывать такой важный фактор как репутация компании. Обращаясь в Агентство «by Гаун», можно быть уверенным в том, что ваши задачи будут решать профессионалы рынка услуг в сфере недвижимости, работающие по высоким стандартам качества Российском Гильдии Риэлторов.</p>

            <h3>Услуги риэлторского агентства в Лянторе</h3>
            <ul class="about-list">
                <li><strong>Качественный подбор недвижимости</strong> от квалифицированных специалистов, которые знают каждый дом в закрепленном районе.</li>
                <li><strong>Быстрая и выгодная продажа объекта.</strong> Риэлторское агентство всегда отстаивает интересы клиента и помогает продать недвижимость по максимально возможной цене в короткие сроки.</li>
                <li><strong>Юридические услуги.</strong> Сопровождение сделки купли-продажи и трепетное отношение к каждому документу, контроль всей цепочки от сбора документов до получения ключей или денег.</li>
            </ul>
        </div>
    </section>

    <section style="padding: 50px 0;">
        <div class="container">
            <h2 style="text-align: center; color: #1a5d7a;">Доступные объявления</h2>
            <div class="cards-grid">
                {cards_html}
            </div>
        </div>
    </section>
    '''

    return HTMLResponse(get_base_html(content, user=current_user))


# Страница "Сведения"
@app.get("/info", response_class=HTMLResponse)
async def info():
    global current_user, transactions, users

    transactions_html = ""
    if transactions:
        for t in transactions[-20:]:
            transactions_html += f'''
            <div class="transaction-item">
                <strong>📅 {t["date"]}</strong>
                <p>🏠 {t["property_title"]}</p>
                <p>💰 {t["price"]} ₽</p>
                <p>👤 Продавец: {t["seller"]} → 👤 Покупатель: {t["buyer"]}</p>
                <p>📝 Тип: {t["type"]}</p>
            </div>
            '''
    else:
        transactions_html = "<p>Пока нет завершённых сделок</p>"

    admin_html = ""
    if current_user and current_user["role"] == "admin":
        users_list_html = ""
        for username, data in users.items():
            users_list_html += f'''
            <div class="user-item">
                <strong>👤 {data["name"]}</strong> (@{username})
                <br>Роль: {data["role"]}
                <br>Почта: {data.get("email", "не указана")}
            </div>
            '''

        admin_html = f'''
        <div class="info-section">
            <h2>👥 Зарегистрированные пользователи</h2>
            <div style="max-height: 400px; overflow-y: auto;">
                {users_list_html}
            </div>
        </div>

        <div class="info-section">
            <h2>🗑️ Корзина (удалённые сообщения)</h2>
            <div style="max-height: 400px; overflow-y: auto;">
        '''

        if deleted_messages:
            for dm in deleted_messages[-30:]:
                admin_html += f'''
                <div class="deleted-message" style="padding: 10px; margin-bottom: 8px; background: #fff0f0; border-radius: 8px;">
                    <strong>🗑️ {dm["username"]}</strong> <small>{dm["time"]}</small>
                    <p style="margin: 5px 0;">{dm["text"]}</p>
                    {f'<img src="{dm["photo"]}" style="max-width: 100px; border-radius: 8px;">' if dm.get("photo") else ''}
                    <div style="font-size: 12px; color: #888; margin-top: 5px;">
                        Удалено: {dm["deleted_by"]} ({dm["deleted_at"]})
                    </div>
                </div>
                '''
        else:
            admin_html += "<p>Корзина пуста</p>"

        admin_html += '''
            </div>
        </div>
        '''

    content = f'''
    <section style="padding: 50px 0;">
        <div class="container">
            <h1 style="color: #1a5d7a; margin-bottom: 30px;">📊 Сведения о сделках</h1>

            <div class="info-section">
                <h2>📋 История покупок и продаж</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    {transactions_html}
                </div>
            </div>

            {admin_html}
        </div>
    </section>
    '''

    return HTMLResponse(get_base_html(content, user=current_user))


# Страница покупки
@app.get("/buy", response_class=HTMLResponse)
async def buy():
    global current_user

    cards_html = ""
    for p in properties:
        cards_html += f'''
        <div class="property-card">
            <h3>{p["title"]}</h3>
            <p><strong>📍 Локация:</strong> {p["location"]}</p>
            <p><strong>💰 Цена:</strong> {p["price"]} ₽</p>
            <p><strong>📐 Площадь:</strong> {p["area"]} м²</p>
            <p><strong>🏗️ Этаж:</strong> {p["floor"]} / {p["total_floors"]}</p>
            <p><strong>🏠 Тип строения:</strong> {p["building_type"]}</p>
            <p><strong>📝 Описание:</strong> {p["description"]}</p>
            <p><strong>👤 Продавец:</strong> {p["seller_name"]}</p>
            <div class="property-actions">
        '''

        if current_user:
            if current_user["role"] == "client":
                cards_html += f'''
                <form action="/buy_property/{p["id"]}" method="post" style="display: inline;">
                    <button type="submit" class="buy-btn">💰 Купить</button>
                </form>
                <form action="/rent_property/{p["id"]}" method="post" style="display: inline;">
                    <button type="submit" class="rent-btn">🔑 Арендовать</button>
                </form>
                '''
            elif current_user["role"] == "admin":
                cards_html += f'<form action="/delete_property/{p["id"]}" method="post" style="display: inline;"><button type="submit" class="delete-btn">Удалить объявление</button></form>'

        cards_html += '</div></div>'

    if not properties:
        cards_html = '<p>Нет доступных объявлений.</p>'

    content = f'''
    <section style="padding: 50px 0;">
        <div class="container">
            <h1 style="color: #1a5d7a; margin-bottom: 30px;">🏠 Квартиры и дома на продажу/аренду</h1>
            <div class="cards-grid">
                {cards_html}
            </div>
        </div>
    </section>
    '''

    return HTMLResponse(get_base_html(content, user=current_user))


# Покупка квартиры
@app.post("/buy_property/{prop_id}")
async def buy_property(prop_id: int):
    global current_user, properties, notifications, transactions

    if not current_user or current_user["role"] != "client":
        return RedirectResponse("/login?error=Только клиенты могут покупать", status_code=303)

    prop = next((p for p in properties if p["id"] == prop_id), None)
    if not prop:
        return RedirectResponse("/buy?error=Объявление не найдено", status_code=303)

    transactions.append({
        "buyer": current_user["name"],
        "seller": prop["seller_name"],
        "property_title": prop["title"],
        "price": prop["price"],
        "type": "Покупка",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })

    notifications.append({
        "to_user": prop["seller_username"],
        "message": f"🏠 КЛИЕНТ {current_user['name']} КУПИЛ вашу недвижимость: {prop['title']} за {prop['price']} ₽",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "type": "sale",
        "property_id": prop_id,
        "read": False
    })

    properties = [p for p in properties if p["id"] != prop_id]
    return RedirectResponse("/buy?success=Поздравляем с покупкой! Продавец получил уведомление", status_code=303)


# Аренда квартиры
@app.post("/rent_property/{prop_id}")
async def rent_property(prop_id: int):
    global current_user, properties, notifications, transactions

    if not current_user or current_user["role"] != "client":
        return RedirectResponse("/login?error=Только клиенты могут арендовать", status_code=303)

    prop = next((p for p in properties if p["id"] == prop_id), None)
    if not prop:
        return RedirectResponse("/buy?error=Объявление не найдено", status_code=303)

    transactions.append({
        "buyer": current_user["name"],
        "seller": prop["seller_name"],
        "property_title": prop["title"],
        "price": prop["price"],
        "type": "Аренда",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })

    notifications.append({
        "to_user": prop["seller_username"],
        "message": f"🔑 КЛИЕНТ {current_user['name']} АРЕНДОВАЛ вашу недвижимость: {prop['title']}",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "type": "rent",
        "property_id": prop_id,
        "read": False
    })

    properties = [p for p in properties if p["id"] != prop_id]
    return RedirectResponse("/buy?success=Поздравляем с арендой! Продавец получил уведомление", status_code=303)


# Личный кабинет
@app.get("/profile", response_class=HTMLResponse)
async def profile(error: str = None, success: str = None):
    global current_user, notifications, users

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    for n in notifications:
        if n["to_user"] == current_user["username"]:
            n["read"] = True

    user_notifications = [n for n in notifications if n["to_user"] == current_user["username"]]
    notif_html = ""
    for n in user_notifications:
        notif_html += f'''
        <div class="notification">
            <strong>{n["date"]}</strong>
            <p>{n["message"]}</p>
        </div>
        '''

    if not user_notifications:
        notif_html = "<p>У вас пока нет уведомлений</p>"

    user_email = users[current_user["username"]].get("email", "")

    content = f'''
    <section style="padding: 50px 0;">
        <div class="container">
            <div style="background: white; border-radius: 24px; padding: 40px; box-shadow: 0 8px 20px rgba(0,0,0,0.05);">
                <h1 style="color: #1a5d7a;">📋 Личный кабинет</h1>

                <div style="margin: 30px 0; padding: 20px; background: var(--bg-blue); border-radius: 16px;">
                    <p><strong>👤 Имя:</strong> {current_user["name"]}</p>
                    <p><strong>🔑 Роль:</strong> {current_user["role"]}</p>
                    <p><strong>📧 Email:</strong> {user_email if user_email else "Не указан"}</p>
                </div>

                <form action="/update_email" method="post" style="margin-bottom: 40px;">
                    <div class="form-group">
                        <label>Привязать почту (@mail.ru или @gmail.com)</label>
                        <div style="display: flex; gap: 10px;">
                            <input type="email" name="email" placeholder="example@mail.ru" value="{user_email}" style="flex: 1;">
                            <button type="submit" class="btn">Сохранить</button>
                        </div>
                        <small>Почта нужна для получения уведомлений о покупках и аренде</small>
                    </div>
                </form>

                <h2 style="color: #1a5d7a; margin: 30px 0 20px;">🔔 Уведомления</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    {notif_html}
                </div>
            </div>
        </div>
    </section>
    '''

    return HTMLResponse(get_base_html(content, user=current_user, error=error, success=success))


# Обновление email
@app.post("/update_email")
async def update_email(email: str = Form(...)):
    global current_user, users

    if not current_user:
        return RedirectResponse("/login", status_code=303)

    if email and not is_valid_email(email):
        return RedirectResponse("/profile?error=Неверный формат почты. Поддерживается только @mail.ru или @gmail.com",
                                status_code=303)

    users[current_user["username"]]["email"] = email
    return RedirectResponse("/profile?success=Почта успешно обновлена", status_code=303)


# Страница продажи
@app.get("/sell", response_class=HTMLResponse)
async def sell():
    global current_user

    if current_user and (current_user["role"] == "seller" or current_user["role"] == "admin"):
        content = '''
        <section style="padding: 50px 0;">
            <div class="container">
                <h1 style="color: #1a5d7a; margin-bottom: 30px;">📝 Добавить объявление о продаже</h1>
                <form action="/add_property" method="post" style="max-width: 600px; background: white; padding: 30px; border-radius: 20px;">
                    <div class="form-group">
                        <label>Название объекта</label>
                        <input type="text" name="title" required>
                    </div>
                    <div class="form-group">
                        <label>Локация (район/улица)</label>
                        <input type="text" name="location" required>
                    </div>
                    <div class="form-group">
                        <label>Цена (₽)</label>
                        <input type="number" name="price" required>
                    </div>
                    <div class="form-group">
                        <label>Площадь (м²)</label>
                        <input type="number" step="0.1" name="area" required>
                    </div>
                    <div class="form-group">
                        <label>Этаж</label>
                        <input type="number" name="floor" required>
                    </div>
                    <div class="form-group">
                        <label>Всего этажей в доме</label>
                        <input type="number" name="total_floors" required>
                    </div>
                    <div class="form-group">
                        <label>Тип строения</label>
                        <select name="building_type">
                            <option>Кирпичный</option>
                            <option>Панельный</option>
                            <option>Монолитный</option>
                            <option>Деревянный</option>
                            <option>Блочный</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Описание</label>
                        <textarea name="description" rows="4"></textarea>
                    </div>
                    <button type="submit" class="btn">Опубликовать объявление</button>
                </form>
            </div>
        </section>
        '''
    else:
        content = '''
        <section style="padding: 50px 0;">
            <div class="container">
                <div style="background: white; padding: 30px; border-radius: 20px; text-align: center;">
                    <p style="color: red;">⚠️ Только продавцы и администраторы могут добавлять объявления.</p>
                    <p><a href="/register">Зарегистрируйтесь как продавец</a></p>
                </div>
            </div>
        </section>
        '''

    return HTMLResponse(get_base_html(content, user=current_user))


# Страница чата (с возможностью удаления сообщений)
@app.get("/chat", response_class=HTMLResponse)
async def chat():
    global current_user, messages

    messages_html = ""
    for msg in messages[-50:]:
        delete_button = ''
        if current_user:
            # Пользователь может удалить своё сообщение, админ — любое
            if current_user["role"] == "admin" or current_user["name"] == msg["username"]:
                delete_button = f'''
                <form action="/delete_message/{msg["id"]}" method="post" style="display: inline;">
                    <button type="submit" class="delete-msg-btn" onclick="return confirm('Удалить сообщение?')">🗑️</button>
                </form>
                '''

        messages_html += f'''
        <div class="message">
            <div class="message-header">
                <div>
                    <span class="message-user">{msg["username"]}</span>
                    <span class="message-time">{msg["time"]}</span>
                </div>
                <div class="message-actions">
                    {delete_button}
                </div>
            </div>
            <p>{msg["text"]}</p>
        '''
        if msg.get("photo"):
            messages_html += f'<img src="{msg["photo"]}" class="media-preview">'
        messages_html += '</div>'

    if not messages:
        messages_html = '<p style="text-align: center; color: #999;">Пока нет сообщений. Будьте первым!</p>'

    chat_form = ''
    if current_user:
        chat_form = '''
        <form action="/send_message" method="post" enctype="multipart/form-data">
            <div class="chat-input-area">
                <textarea name="message_text" rows="2" placeholder="Ваше сообщение..." required></textarea>
            </div>
            <div class="file-inputs">
                <input type="file" name="photo" accept="image/*" placeholder="Фото">
            </div>
            <button type="submit" class="btn" style="margin-top: 10px;">Отправить</button>
        </form>
        '''
    else:
        chat_form = '<p><a href="/login">Войдите</a>, чтобы участвовать в переписке</p>'

    content = f'''
    <section style="padding: 50px 0;">
        <div class="container">
            <h1 style="color: #1a5d7a; margin-bottom: 20px;">💬 Общая переписка</h1>
            <div class="chat-messages" id="chatMessages">
                {messages_html}
            </div>
            {chat_form}
        </div>
    </section>
    <script>
        function loadMessages() {{
            fetch('/get_messages')
                .then(res => res.json())
                .then(data => {{
                    const container = document.getElementById('chatMessages');
                    if (data.html) {{
                        container.innerHTML = data.html;
                        container.scrollTop = container.scrollHeight;
                    }}
                }});
        }}
        setInterval(loadMessages, 3000);
        loadMessages();
    </script>
    '''

    return HTMLResponse(get_base_html(content, user=current_user))


# Удаление сообщения
@app.post("/delete_message/{msg_id}")
async def delete_message(msg_id: int):
    global current_user, messages, deleted_messages

    if not current_user:
        return RedirectResponse("/login?error=Авторизуйтесь", status_code=303)

    # Находим сообщение
    msg = next((m for m in messages if m["id"] == msg_id), None)
    if not msg:
        return RedirectResponse("/chat?error=Сообщение не найдено", status_code=303)

    # Проверяем права: админ может всё, обычный пользователь — только свои
    if current_user["role"] != "admin" and current_user["name"] != msg["username"]:
        return RedirectResponse("/chat?error=Нельзя удалить чужое сообщение", status_code=303)

    # Переносим в корзину (только для админа, для сохранения истории)
    deleted_messages.append({
        "id": msg["id"],
        "username": msg["username"],
        "text": msg["text"],
        "time": msg["time"],
        "photo": msg.get("photo"),
        "deleted_by": current_user["name"],
        "deleted_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })

    # Удаляем из активных сообщений
    messages = [m for m in messages if m["id"] != msg_id]

    return RedirectResponse("/chat?success=Сообщение удалено", status_code=303)


# Страница контактов
@app.get("/contacts", response_class=HTMLResponse)
async def contacts():
    content = '''
    <section style="padding: 50px 0;">
        <div class="container">
            <div style="background: white; border-radius: 24px; padding: 40px; box-shadow: 0 8px 20px rgba(0,0,0,0.05);">
                <h1 style="color: #1a5d7a;">📬 Наши контакты</h1>
                <div style="background: #f0f9ff; padding: 22px; border-radius: 16px; margin: 25px 0;">
                    <p><strong>📍 Адрес:</strong> г. Лянтор, Лянторский Нефтяной техникум</p>
                    <p><strong>📧 Email:</strong> artemgaun104@gmail.com</p>
                </div>
                <div style="border-radius: 20px; overflow: hidden;">
                    <iframe src="https://yandex.ru/map-widget/v1/?ll=72.1579%2C61.6229&z=17&pt=72.1589,61.6230&what=here%3A1&lang=ru_RU" style="width:100%; height:380px; border:0;"></iframe>
                </div>
            </div>
        </div>
    </section>
    '''
    return HTMLResponse(get_base_html(content, user=current_user))


# Страница входа
@app.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    content = f'''
    <section style="padding: 50px 0;">
        <div class="container">
            <div style="max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 20px;">
                <h2 style="color: #1a5d7a;">Вход в аккаунт</h2>
                <form action="/login" method="post">
                    <div class="form-group">
                        <label>Логин</label>
                        <input type="text" name="username" required>
                    </div>
                    <div class="form-group">
                        <label>Пароль</label>
                        <input type="password" name="password" required>
                    </div>
                    <button type="submit" class="btn">Войти</button>
                </form>
                <p style="margin-top: 15px;">Нет аккаунта? <a href="/register">Зарегистрируйтесь</a></p>
            </div>
        </div>
    </section>
    '''
    return HTMLResponse(get_base_html(content, user=current_user, error=error))


@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    global current_user
    if username in users and users[username]["password"] == password:
        current_user = {"username": username, "role": users[username]["role"], "name": users[username]["name"]}
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/login?error=Неверный логин или пароль", status_code=303)


@app.get("/logout")
async def logout():
    global current_user
    current_user = None
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(error: str = None):
    content = f'''
    <section style="padding: 50px 0;">
        <div class="container">
            <div style="max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 20px;">
                <h2 style="color: #1a5d7a;">Регистрация</h2>
                <form action="/register" method="post">
                    <div class="form-group">
                        <label>Имя</label>
                        <input type="text" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Логин</label>
                        <input type="text" name="username" required>
                    </div>
                    <div class="form-group">
                        <label>Пароль</label>
                        <input type="password" name="password" required>
                    </div>
                    <div class="form-group">
                        <label>Роль</label>
                        <select name="role">
                            <option value="client">Клиент (просмотр квартир, покупка, аренда)</option>
                            <option value="seller">Продавец (добавление объявлений)</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">Зарегистрироваться</button>
                </form>
                <p style="margin-top: 15px;">Уже есть аккаунт? <a href="/login">Войдите</a></p>
            </div>
        </div>
    </section>
    '''
    return HTMLResponse(get_base_html(content, user=current_user, error=error))


@app.post("/register")
async def register_post(name: str = Form(...), username: str = Form(...), password: str = Form(...),
                        role: str = Form(...)):
    if username in users:
        return RedirectResponse("/register?error=Пользователь уже существует", status_code=303)
    users[username] = {"password": password, "role": role, "name": name, "email": "", "notifications": []}
    return RedirectResponse("/login", status_code=303)


@app.post("/add_property")
async def add_property(
        title: str = Form(...),
        location: str = Form(...),
        price: int = Form(...),
        area: float = Form(...),
        floor: int = Form(...),
        total_floors: int = Form(...),
        building_type: str = Form(...),
        description: str = Form("")
):
    global current_user, properties
    if not current_user or current_user["role"] not in ["seller", "admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    prop = {
        "id": len(properties) + 1,
        "title": title,
        "location": location,
        "price": price,
        "area": area,
        "floor": floor,
        "total_floors": total_floors,
        "building_type": building_type,
        "description": description,
        "seller_name": current_user["name"],
        "seller_username": current_user["username"]
    }
    properties.append(prop)
    return RedirectResponse("/buy", status_code=303)


@app.post("/delete_property/{prop_id}")
async def delete_property(prop_id: int):
    global current_user, properties
    if not current_user or current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только для администратора")

    properties = [p for p in properties if p["id"] != prop_id]
    return RedirectResponse("/buy", status_code=303)


@app.post("/send_message")
async def send_message(
        message_text: str = Form(...),
        photo: Optional[UploadFile] = File(None)
):
    global current_user, messages, message_counter

    if not current_user:
        raise HTTPException(status_code=403, detail="Авторизуйтесь")

    msg = {
        "id": message_counter,
        "username": current_user["name"],
        "text": message_text,
        "time": datetime.now().strftime("%H:%M:%S"),
        "photo": None
    }
    message_counter += 1

    if photo and photo.filename and photo.filename != "":
        ext = photo.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        path = f"static/uploads/photos/{filename}"
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        msg["photo"] = f"/{path}"

    messages.append(msg)
    return RedirectResponse("/chat", status_code=303)


@app.get("/get_messages")
async def get_messages():
    global current_user, messages

    html = ""
    for msg in messages[-50:]:
        delete_button = ''
        if current_user:
            if current_user["role"] == "admin" or current_user["name"] == msg["username"]:
                delete_button = f'''
                <form action="/delete_message/{msg["id"]}" method="post" style="display: inline;">
                    <button type="submit" class="delete-msg-btn" onclick="return confirm('Удалить сообщение?')">🗑️</button>
                </form>
                '''

        html += f'''
        <div class="message">
            <div class="message-header">
                <div>
                    <span class="message-user">{msg["username"]}</span>
                    <span class="message-time">{msg["time"]}</span>
                </div>
                <div class="message-actions">
                    {delete_button}
                </div>
            </div>
            <p>{msg["text"]}</p>
        '''
        if msg.get("photo"):
            html += f'<img src="{msg["photo"]}" class="media-preview">'
        html += '</div>'

    if not messages:
        html = '<p style="text-align: center; color: #999;">Пока нет сообщений. Будьте первым!</p>'

    return {"html": html}


if __name__ == "__main__":
    import socket


    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print("✅ САЙТ ЗАПУЩЕН!")
    print("=" * 60)
    print("\n📱 Доступ на этом компьютере:")
    print("   → http://127.0.0.1:8000")
    print(f"\n📱 Доступ с других устройств (локальная сеть):")
    print(f"   → http://{local_ip}:8000")
    print("\n🔑 Тестовый аккаунт: admin / admin123")
    print("\n💬 Новое в чате:")
    print("   • Кнопка 🗑️ для удаления своих сообщений")
    print("   • Админ может удалять любые сообщения")
    print("   • Удалённые сообщения видны админу в 'Сведениях' → 'Корзина'")
    print("   • Убрана загрузка аудио и видео (только текст и фото)")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)