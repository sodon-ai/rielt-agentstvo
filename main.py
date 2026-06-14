from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import uuid
import shutil
import json
from datetime import datetime
from typing import Optional
import re

app = FastAPI(title="Риэлторское агентство by Гаун")

# Создаём папки
os.makedirs("static/uploads/photos", exist_ok=True)
os.makedirs("data", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Файлы для хранения данных
DATA_FILES = {
    "users": "data/users.json",
    "properties": "data/properties.json",
    "messages": "data/messages.json",
    "notifications": "data/notifications.json",
    "transactions": "data/transactions.json",
    "deleted_messages": "data/deleted_messages.json"
}

# Инициализация
def init_data_files():
    for name, path in DATA_FILES.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                if name == "users":
                    json.dump([{
                        "id": 1,
                        "username": "admin",
                        "password": "admin123",
                        "name": "Администратор",
                        "role": "admin",
                        "email": "",
                        "is_active": True,
                        "created_at": datetime.now().isoformat()
                    }], f, ensure_ascii=False, indent=2)
                else:
                    json.dump([], f, ensure_ascii=False, indent=2)

init_data_files()

def load_data(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_next_id(data):
    return max([item["id"] for item in data]) + 1 if data else 1

def get_user_by_username(username):
    users = load_data(DATA_FILES["users"])
    for user in users:
        if user["username"] == username:
            return user
    return None

def create_user(username, password, name, role):
    users = load_data(DATA_FILES["users"])
    new_id = get_next_id(users)
    users.append({
        "id": new_id,
        "username": username,
        "password": password,
        "name": name,
        "role": role,
        "email": "",
        "is_active": True,
        "created_at": datetime.now().isoformat()
    })
    save_data(DATA_FILES["users"], users)

def update_user_email(username, email):
    users = load_data(DATA_FILES["users"])
    for user in users:
        if user["username"] == username:
            user["email"] = email
            break
    save_data(DATA_FILES["users"], users)

def get_all_users():
    return load_data(DATA_FILES["users"])

def get_all_properties():
    return load_data(DATA_FILES["properties"])

def add_property(title, location, price, area, floor, total_floors, building_type, description, seller_name, seller_username):
    properties = load_data(DATA_FILES["properties"])
    new_id = get_next_id(properties)
    properties.append({
        "id": new_id,
        "title": title,
        "location": location,
        "price": price,
        "area": area,
        "floor": floor,
        "total_floors": total_floors,
        "building_type": building_type,
        "description": description,
        "seller_name": seller_name,
        "seller_username": seller_username,
        "created_at": datetime.now().isoformat()
    })
    save_data(DATA_FILES["properties"], properties)

def delete_property_by_id(prop_id):
    properties = load_data(DATA_FILES["properties"])
    properties = [p for p in properties if p["id"] != prop_id]
    save_data(DATA_FILES["properties"], properties)

def get_all_messages():
    return load_data(DATA_FILES["messages"])

def add_message(username, text, time, photo):
    messages = load_data(DATA_FILES["messages"])
    new_id = get_next_id(messages)
    messages.append({
        "id": new_id,
        "username": username,
        "text": text,
        "time": time,
        "photo": photo
    })
    save_data(DATA_FILES["messages"], messages)

def delete_message_by_id(msg_id, deleted_by):
    messages = load_data(DATA_FILES["messages"])
    deleted_msgs = load_data(DATA_FILES["deleted_messages"])
    
    msg_to_delete = None
    for msg in messages:
        if msg["id"] == msg_id:
            msg_to_delete = msg
            break
    
    if msg_to_delete:
        new_id = get_next_id(deleted_msgs)
        deleted_msgs.append({
            "id": new_id,
            "username": msg_to_delete["username"],
            "text": msg_to_delete["text"],
            "time": msg_to_delete["time"],
            "photo": msg_to_delete.get("photo"),
            "deleted_by": deleted_by,
            "deleted_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        })
        save_data(DATA_FILES["deleted_messages"], deleted_msgs)
        messages = [m for m in messages if m["id"] != msg_id]
        save_data(DATA_FILES["messages"], messages)

def get_deleted_messages():
    return load_data(DATA_FILES["deleted_messages"])

def add_notification(to_user, message, date, type, property_id):
    notifications = load_data(DATA_FILES["notifications"])
    new_id = get_next_id(notifications)
    notifications.append({
        "id": new_id,
        "to_user": to_user,
        "message": message,
        "date": date,
        "type": type,
        "property_id": property_id,
        "read": False
    })
    save_data(DATA_FILES["notifications"], notifications)

def get_notifications_by_user(username):
    notifications = load_data(DATA_FILES["notifications"])
    return [n for n in notifications if n["to_user"] == username]

def mark_notifications_read(username):
    notifications = load_data(DATA_FILES["notifications"])
    for n in notifications:
        if n["to_user"] == username:
            n["read"] = True
    save_data(DATA_FILES["notifications"], notifications)

def add_transaction(buyer, seller, property_title, price, type, date):
    transactions = load_data(DATA_FILES["transactions"])
    new_id = get_next_id(transactions)
    transactions.append({
        "id": new_id,
        "buyer": buyer,
        "seller": seller,
        "property_title": property_title,
        "price": price,
        "type": type,
        "date": date
    })
    save_data(DATA_FILES["transactions"], transactions)

def get_all_transactions():
    return load_data(DATA_FILES["transactions"])

current_user = None

def is_valid_email(email):
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9_.+-]+@(mail\.ru|gmail\.com)$'
    return re.match(pattern, email) is not None

# HTML
def render_html(content, user=None, error=None, success=None):
    user_html = ""
    if user:
        notif_list = get_notifications_by_user(user["username"])
        unread = len([n for n in notif_list if not n.get("read")])
        badge = f'<span style="background:red;color:white;border-radius:50%;padding:2px 6px;font-size:12px;margin-left:5px;">{unread}</span>' if unread > 0 else ''
        user_html = f'<span>👤 {user["name"]} ({user["role"]})</span><a href="/profile" class="btn">📋 Профиль{badge}</a><a href="/logout" class="btn">Выйти</a>'
    else:
        user_html = '<a href="/login" class="btn">Вход</a><a href="/register" class="btn">Регистрация</a>'
    
    err_html = f'<div class="error">{error}</div>' if error else ''
    suc_html = f'<div class="success">{success}</div>' if success else ''
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Риэлторское агентство by Гаун</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;}}
        body{{font-family:Segoe UI, sans-serif;background:#f0f7fa;color:#2c3e50;}}
        :root{{--light-blue:#6ec8e6;--medium-blue:#4ab0d0;--dark-blue:#2c7aa0;}}
        header{{background:white;box-shadow:0 2px 15px rgba(0,0,0,0.08);position:sticky;top:0;}}
        .top-banner{{background:var(--light-blue);padding:8px 0;text-align:center;font-size:13px;color:#1a4d66;}}
        .container{{max-width:1200px;margin:0 auto;padding:0 25px;}}
        .header-main{{display:flex;justify-content:space-between;align-items:center;padding:20px 0;flex-wrap:wrap;gap:15px;}}
        .logo-area{{display:flex;align-items:center;gap:15px;}}
        .logo-icon{{background:var(--light-blue);width:55px;height:55px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;color:white;}}
        .logo-text h1{{font-size:18px;color:#1a4d66;}}
        .logo-text h2{{font-size:22px;color:var(--dark-blue);}}
        .slogan{{font-size:13px;color:var(--medium-blue);}}
        nav ul{{display:flex;list-style:none;gap:25px;}}
        nav a{{text-decoration:none;color:#2c3e50;font-weight:600;padding:8px 12px;border-radius:8px;}}
        nav a:hover{{background:#e0f2f8;color:var(--dark-blue);}}
        .user-info{{display:flex;gap:15px;align-items:center;}}
        .btn{{background:var(--light-blue);padding:8px 20px;border-radius:25px;text-decoration:none;color:#1a4d66;font-weight:bold;border:none;cursor:pointer;display:inline-block;}}
        .btn:hover{{background:var(--medium-blue);}}
        .hero{{background:linear-gradient(120deg,#e0f2f8 0%,white 80%);padding:50px 0;text-align:center;}}
        .hero h1{{font-size:42px;color:#1a5d7a;}}
        .services-block{{background:white;padding:50px 0;border-bottom:1px solid #d4e8f0;}}
        .services-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:30px;margin-top:30px;}}
        .service-box{{background:#fafeff;border-radius:16px;padding:25px;border-left:4px solid var(--light-blue);}}
        .service-box h3{{color:var(--dark-blue);font-size:22px;}}
        .service-box ul{{list-style:none;}}
        .service-box li{{padding:8px 0 8px 25px;position:relative;}}
        .service-box li:before{{content:"•";color:var(--light-blue);position:absolute;left:5px;}}
        .about-section{{background:#f9fdfe;padding:50px 0;border-top:1px solid #d4e8f0;border-bottom:1px solid #d4e8f0;}}
        .about-section h2{{font-size:32px;color:#1a5d7a;}}
        .about-section h3{{font-size:26px;color:var(--dark-blue);margin:30px 0 15px;}}
        .about-section p{{font-size:16px;line-height:1.7;color:#3a5a72;margin-bottom:18px;}}
        .about-list{{list-style:none;}}
        .about-list li{{padding:10px 0 10px 28px;position:relative;}}
        .about-list li:before{{content:"•";color:var(--light-blue);font-size:22px;position:absolute;left:5px;}}
        .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:25px;padding:40px 0;}}
        .property-card{{background:white;border-radius:16px;padding:20px;border-left:4px solid var(--light-blue);}}
        .property-card h3{{color:var(--dark-blue);}}
        .property-actions{{display:flex;gap:10px;margin-top:15px;}}
        .delete-btn{{background:#ff6b6b;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;}}
        .rent-btn{{background:#4caf50;color:white;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;}}
        .buy-btn{{background:var(--light-blue);color:#1a4d66;border:none;padding:8px 15px;border-radius:8px;cursor:pointer;}}
        .delete-msg-btn{{background:#ff6b6b;color:white;border:none;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:12px;}}
        .form-group{{margin-bottom:15px;}}
        .form-group label{{display:block;margin-bottom:5px;font-weight:bold;}}
        .form-group input,.form-group textarea,.form-group select{{width:100%;padding:10px;border:1px solid #ddd;border-radius:8px;}}
        .chat-messages{{height:400px;overflow-y:auto;border:1px solid #ddd;border-radius:12px;padding:15px;background:#f9f9f9;margin-bottom:15px;}}
        .message{{margin-bottom:15px;padding:10px;background:white;border-radius:10px;}}
        .message-user{{font-weight:bold;color:var(--dark-blue);}}
        .message-time{{font-size:11px;color:#999;margin-left:10px;}}
        .message-header{{display:flex;justify-content:space-between;margin-bottom:8px;}}
        .media-preview{{max-width:200px;max-height:150px;margin-top:10px;border-radius:8px;}}
        .chat-input-area{{display:flex;gap:10px;}}
        .chat-input-area textarea{{flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;}}
        .file-inputs{{margin-top:10px;}}
        .error{{color:red;background:#ffe0e0;padding:10px;border-radius:8px;margin-bottom:15px;}}
        .success{{color:green;background:#e0ffe0;padding:10px;border-radius:8px;margin-bottom:15px;}}
        .notification{{background:white;padding:12px;margin-bottom:10px;border-radius:10px;border-left:4px solid var(--light-blue);}}
        .transaction-item,.user-item,.deleted-item{{background:white;padding:12px;margin-bottom:10px;border-radius:10px;border-left:4px solid var(--light-blue);}}
        .deleted-item{{border-left-color:#ff6b6b;background:#fff8f0;}}
        .info-section{{background:white;border-radius:24px;padding:30px;margin-bottom:30px;}}
        .info-section h2{{color:#1a5d7a;margin-bottom:20px;}}
        footer{{background:#1e3a47;color:#cbdce6;padding:30px 0;text-align:center;}}
        @media (max-width:768px){{.header-main{{flex-direction:column;text-align:center;}}nav ul{{justify-content:center;}}}}
    </style>
</head>
<body>
<header>
    <div class="top-banner">🏡 Лянтор | Ваш надёжный партнёр в мире недвижимости</div>
    <div class="container header-main">
        <div class="logo-area">
            <div class="logo-icon">🏢</div>
            <div class="logo-text"><h1>РИЭЛТОРСКОЕ АГЕНТСТВО</h1><h2>BY ГАУН</h2><div class="slogan">МЕСТО, ГДЕ ВЫ СТАНЕТЕ СОБОЙ</div></div>
        </div>
        <nav><ul><li><a href="/">Главная</a></li><li><a href="/buy">Покупка квартиры</a></li><li><a href="/sell">Продажа</a></li><li><a href="/info">Сведения</a></li><li><a href="/chat">Переписка</a></li><li><a href="/contacts">Контакты</a></li></ul></nav>
        <div class="user-info">{user_html}</div>
    </div>
</header>
<main>{err_html}{suc_html}{content}</main>
<footer><div class="container"><p>© 2025 Риэлторское агентство by Гаун | Лянтор</p></div></footer>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def index():
    global current_user
    props = get_all_properties()
    cards = ""
    for p in props[-6:]:
        cards += f'<div class="property-card"><h3>{p["title"]}</h3><p><strong>📍 Локация:</strong> {p["location"]}</p><p><strong>💰 Цена:</strong> {p["price"]} ₽</p><p><strong>📐 Площадь:</strong> {p["area"]} м²</p><p><strong>🏗️ Этаж:</strong> {p["floor"]} / {p["total_floors"]}</p><p><strong>👤 Продавец:</strong> {p["seller_name"]}</p>'
        if current_user and current_user["role"] == "admin":
            cards += f'<form action="/delete_property/{p["id"]}" method="post"><button type="submit" class="delete-btn">Удалить</button></form>'
        cards += '</div>'
    if not props:
        cards = '<p>Пока нет объявлений. Станьте продавцом и добавьте первое!</p>'
    
    content = f'''<section class="hero"><div class="container"><h1>Ваша недвижимость — наша профессиональная забота</h1><p>Поможем купить, продать или выкупить жильё в Лянторе</p></div></section>
    <section class="services-block"><div class="container"><h2 style="text-align:center;color:#1a5d7a;">Наши услуги</h2><p style="text-align:center;">Риэлторская компания / Наши услуги</p>
    <div class="services-grid"><div class="service-box"><h3>🏠 Риэлторские услуги</h3><ul><li>Купить недвижимость</li><li>Продать недвижимость</li><li>Обмен квартир в Лянторе</li><li>Анализ стоимости объекта</li><li>Срочный выкуп недвижимости</li><li>Помощь в получении кредита</li></ul><a href="/buy" class="btn">Подробнее →</a></div>
    <div class="service-box"><h3>⚡ Срочный выкуп недвижимости</h3><p><strong>Агентство «by Гаун» выкупит Вашу:</strong></p><ul><li>комнату, долю в квартире</li><li>квартиру (даже требующую ремонта)</li><li>новостройку на любой стадии</li></ul><a href="/sell" class="btn">Подробнее →</a></div></div></div></section>
    <section class="about-section"><div class="container"><h2>Риэлторское агентство</h2><p><strong>В чем суть работы риэлторского агентства?</strong> Это помощь клиенту в подборе и продаже недвижимости. Если вы не сталкиваетесь с рынком недвижимости каждый день, то вам довольно сложно ориентироваться в адекватности цен, разнообразии планировок и даже в удачности месторасположения объекта.</p>
    <h3>Агентство недвижимости г. Лянтора</h3><p>Работа риэлторского агентства заточена под то, чтобы помочь клиенту купить или продать свою недвижимость и сделать это максимально выгодно и комфортно.</p>
    <p>Чтобы любая сделка прошла безопасно на всех этапах, при выборе риэлторского агентства нужно учитывать такой важный фактор как репутация компании. Обращаясь в Агентство «by Гаун», можно быть уверенным в том, что ваши задачи будут решать профессионалы рынка.</p>
    <h3>Услуги риэлторского агентства в Лянторе</h3><ul class="about-list"><li><strong>Качественный подбор недвижимости</strong> от квалифицированных специалистов</li><li><strong>Быстрая и выгодная продажа объекта</strong> по максимальной цене</li><li><strong>Юридические услуги</strong> – сопровождение сделки и контроль документов</li></ul></div></section>
    <section style="padding:50px 0;"><div class="container"><h2 style="text-align:center;">Доступные объявления</h2><div class="cards-grid">{cards}</div></div></section>'''
    return HTMLResponse(render_html(content, user=current_user))

@app.get("/buy", response_class=HTMLResponse)
async def buy():
    global current_user
    props = get_all_properties()
    cards = ""
    for p in props:
        cards += f'<div class="property-card"><h3>{p["title"]}</h3><p><strong>📍 Локация:</strong> {p["location"]}</p><p><strong>💰 Цена:</strong> {p["price"]} ₽</p><p><strong>📐 Площадь:</strong> {p["area"]} м²</p><p><strong>🏗️ Этаж:</strong> {p["floor"]} / {p["total_floors"]}</p><p><strong>🏠 Тип:</strong> {p["building_type"]}</p><p><strong>📝 Описание:</strong> {p["description"]}</p><p><strong>👤 Продавец:</strong> {p["seller_name"]}</p><div class="property-actions">'
        if current_user:
            if current_user["role"] == "client":
                cards += f'<form action="/buy_property/{p["id"]}" method="post"><button type="submit" class="buy-btn">💰 Купить</button></form><form action="/rent_property/{p["id"]}" method="post"><button type="submit" class="rent-btn">🔑 Арендовать</button></form>'
            elif current_user["role"] == "admin":
                cards += f'<form action="/delete_property/{p["id"]}" method="post"><button type="submit" class="delete-btn">Удалить</button></form>'
        cards += '</div></div>'
    if not props:
        cards = '<p>Нет доступных объявлений.</p>'
    content = f'<section style="padding:50px 0;"><div class="container"><h1 style="color:#1a5d7a;">🏠 Квартиры и дома на продажу/аренду</h1><div class="cards-grid">{cards}</div></div></section>'
    return HTMLResponse(render_html(content, user=current_user))

@app.post("/buy_property/{prop_id}")
async def buy_property(prop_id: int):
    global current_user
    if not current_user or current_user["role"] != "client":
        return RedirectResponse("/login?error=Только клиенты могут покупать", 303)
    props = get_all_properties()
    prop = next((p for p in props if p["id"] == prop_id), None)
    if not prop:
        return RedirectResponse("/buy?error=Объявление не найдено", 303)
    add_transaction(current_user["name"], prop["seller_name"], prop["title"], prop["price"], "Покупка", datetime.now().strftime("%d.%m.%Y %H:%M"))
    add_notification(prop["seller_username"], f"🏠 КЛИЕНТ {current_user['name']} КУПИЛ {prop['title']} за {prop['price']} ₽", datetime.now().strftime("%d.%m.%Y %H:%M"), "sale", prop_id)
    delete_property_by_id(prop_id)
    return RedirectResponse("/buy?success=Поздравляем с покупкой!", 303)

@app.post("/rent_property/{prop_id}")
async def rent_property(prop_id: int):
    global current_user
    if not current_user or current_user["role"] != "client":
        return RedirectResponse("/login?error=Только клиенты могут арендовать", 303)
    props = get_all_properties()
    prop = next((p for p in props if p["id"] == prop_id), None)
    if not prop:
        return RedirectResponse("/buy?error=Объявление не найдено", 303)
    add_transaction(current_user["name"], prop["seller_name"], prop["title"], prop["price"], "Аренда", datetime.now().strftime("%d.%m.%Y %H:%M"))
    add_notification(prop["seller_username"], f"🔑 КЛИЕНТ {current_user['name']} АРЕНДОВАЛ {prop['title']}", datetime.now().strftime("%d.%m.%Y %H:%M"), "rent", prop_id)
    delete_property_by_id(prop_id)
    return RedirectResponse("/buy?success=Поздравляем с арендой!", 303)

@app.get("/sell", response_class=HTMLResponse)
async def sell():
    global current_user
    if current_user and (current_user["role"] == "seller" or current_user["role"] == "admin"):
        content = '<section style="padding:50px 0;"><div class="container"><h1 style="color:#1a5d7a;">📝 Добавить объявление</h1><form action="/add_property" method="post" style="max-width:600px;background:white;padding:30px;border-radius:20px;"><div class="form-group"><label>Название</label><input type="text" name="title" required></div><div class="form-group"><label>Локация</label><input type="text" name="location" required></div><div class="form-group"><label>Цена (₽)</label><input type="number" name="price" required></div><div class="form-group"><label>Площадь (м²)</label><input type="number" step="0.1" name="area" required></div><div class="form-group"><label>Этаж</label><input type="number" name="floor" required></div><div class="form-group"><label>Всего этажей</label><input type="number" name="total_floors" required></div><div class="form-group"><label>Тип строения</label><select name="building_type"><option>Кирпичный</option><option>Панельный</option><option>Монолитный</option><option>Деревянный</option><option>Блочный</option></select></div><div class="form-group"><label>Описание</label><textarea name="description" rows="4"></textarea></div><button type="submit" class="btn">Опубликовать</button></form></div></section>'
    else:
        content = '<section style="padding:50px 0;"><div class="container"><div style="background:white;padding:30px;border-radius:20px;text-align:center;"><p style="color:red;">⚠️ Только продавцы и администраторы могут добавлять объявления.</p><p><a href="/register">Зарегистрируйтесь как продавец</a></p></div></div></section>'
    return HTMLResponse(render_html(content, user=current_user))

@app.post("/add_property")
async def add_property_route(title: str = Form(...), location: str = Form(...), price: int = Form(...), area: float = Form(...), floor: int = Form(...), total_floors: int = Form(...), building_type: str = Form(...), description: str = Form("")):
    global current_user
    if not current_user or current_user["role"] not in ["seller", "admin"]:
        raise HTTPException(403, "Доступ запрещён")
    add_property(title, location, price, area, floor, total_floors, building_type, description, current_user["name"], current_user["username"])
    return RedirectResponse("/buy", 303)

@app.post("/delete_property/{prop_id}")
async def delete_property_route(prop_id: int):
    global current_user
    if not current_user or current_user["role"] != "admin":
        raise HTTPException(403, "Только для администратора")
    delete_property_by_id(prop_id)
    return RedirectResponse("/buy", 303)

@app.get("/chat", response_class=HTMLResponse)
async def chat():
    global current_user
    msgs = get_all_messages()
    html = ""
    for m in msgs[-50:]:
        btn = ''
        if current_user and (current_user["role"] == "admin" or current_user["name"] == m["username"]):
            btn = f'<form action="/delete_message/{m["id"]}" method="post" style="display:inline;"><button type="submit" class="delete-msg-btn" onclick="return confirm(\'Удалить?\')">🗑️</button></form>'
        html += f'<div class="message"><div class="message-header"><div><span class="message-user">{m["username"]}</span><span class="message-time">{m["time"]}</span></div><div>{btn}</div></div><p>{m["text"]}</p>'
        if m.get("photo"):
            html += f'<img src="{m["photo"]}" class="media-preview">'
        html += '</div>'
    if not msgs:
        html = '<p style="text-align:center;color:#999;">Пока нет сообщений</p>'
    form = '<form action="/send_message" method="post" enctype="multipart/form-data"><div class="chat-input-area"><textarea name="message_text" rows="2" placeholder="Ваше сообщение..." required></textarea></div><div class="file-inputs"><input type="file" name="photo" accept="image/*"></div><button type="submit" class="btn" style="margin-top:10px;">Отправить</button></form>' if current_user else '<p><a href="/login">Войдите</a>, чтобы писать в чат</p>'
    content = f'<section style="padding:50px 0;"><div class="container"><h1>💬 Общая переписка</h1><div class="chat-messages" id="chatMessages">{html}</div>{form}</div></section><script>function loadMessages(){{fetch("/get_messages").then(r=>r.json()).then(d=>{{const c=document.getElementById("chatMessages");if(d.html){{c.innerHTML=d.html;c.scrollTop=c.scrollHeight;}}}});}}setInterval(loadMessages,3000);loadMessages();</script>'
    return HTMLResponse(render_html(content, user=current_user))

@app.post("/send_message")
async def send_message_route(message_text: str = Form(...), photo: Optional[UploadFile] = File(None)):
    global current_user
    if not current_user:
        raise HTTPException(403, "Авторизуйтесь")
    path = None
    if photo and photo.filename:
        ext = photo.filename.split(".")[-1]
        name = f"{uuid.uuid4()}.{ext}"
        path = f"static/uploads/photos/{name}"
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        path = f"/{path}"
    add_message(current_user["name"], message_text, datetime.now().strftime("%H:%M:%S"), path)
    return RedirectResponse("/chat", 303)

@app.post("/delete_message/{msg_id}")
async def delete_message_route(msg_id: int):
    global current_user
    if not current_user:
        return RedirectResponse("/login?error=Авторизуйтесь", 303)
    msgs = get_all_messages()
    msg = next((m for m in msgs if m["id"] == msg_id), None)
    if not msg:
        return RedirectResponse("/chat?error=Сообщение не найдено", 303)
    if current_user["role"] != "admin" and current_user["name"] != msg["username"]:
        return RedirectResponse("/chat?error=Нельзя удалить чужое сообщение", 303)
    delete_message_by_id(msg_id, current_user["name"])
    return RedirectResponse("/chat?success=Сообщение удалено", 303)

@app.get("/get_messages")
async def get_messages():
    global current_user
    msgs = get_all_messages()
    html = ""
    for m in msgs[-50:]:
        btn = ''
        if current_user and (current_user["role"] == "admin" or current_user["name"] == m["username"]):
            btn = f'<form action="/delete_message/{m["id"]}" method="post" style="display:inline;"><button type="submit" class="delete-msg-btn" onclick="return confirm(\'Удалить?\')">🗑️</button></form>'
        html += f'<div class="message"><div class="message-header"><div><span class="message-user">{m["username"]}</span><span class="message-time">{m["time"]}</span></div><div>{btn}</div></div><p>{m["text"]}</p>'
        if m.get("photo"):
            html += f'<img src="{m["photo"]}" class="media-preview">'
        html += '</div>'
    if not msgs:
        html = '<p style="text-align:center;color:#999;">Пока нет сообщений</p>'
    return {"html": html}

@app.get("/info", response_class=HTMLResponse)
async def info():
    global current_user
    trans = get_all_transactions()
    trans_html = ""
    for t in trans[:20]:
        trans_html += f'<div class="transaction-item"><strong>📅 {t["date"]}</strong><p>🏠 {t["property_title"]}</p><p>💰 {t["price"]} ₽</p><p>👤 Продавец: {t["seller"]} → Покупатель: {t["buyer"]}</p><p>📝 Тип: {t["type"]}</p></div>'
    if not trans:
        trans_html = "<p>Пока нет завершённых сделок</p>"
    admin_html = ""
    if current_user and current_user["role"] == "admin":
        users_list = get_all_users()
        users_html = ""
        for u in users_list:
            users_html += f'<div class="user-item"><strong>👤 {u["name"]}</strong> (@{u["username"]})<br>Роль: {u["role"]}<br>Почта: {u.get("email","не указана")}</div>'
        deleted = get_deleted_messages()
        del_html = ""
        for d in deleted[:30]:
            del_html += f'<div class="deleted-item"><strong>🗑️ {d["username"]}</strong> <small>{d["time"]}</small><p>{d["text"]}</p>'
            if d.get("photo"):
                del_html += f'<img src="{d["photo"]}" style="max-width:100px;border-radius:8px;">'
            del_html += f'<div style="font-size:12px;">Удалено: {d["deleted_by"]} ({d["deleted_at"]})</div></div>'
        admin_html = f'<div class="info-section"><h2>👥 Зарегистрированные пользователи</h2><div>{users_html if users_html else "<p>Нет пользователей</p>"}</div></div><div class="info-section"><h2>🗑️ Корзина</h2><div>{del_html if deleted else "<p>Корзина пуста</p>"}</div></div>'
    content = f'<section style="padding:50px 0;"><div class="container"><h1 style="color:#1a5d7a;">📊 Сведения о сделках</h1><div class="info-section"><h2>📋 История покупок и продаж</h2><div>{trans_html}</div></div>{admin_html}</div></section>'
    return HTMLResponse(render_html(content, user=current_user))

@app.get("/contacts", response_class=HTMLResponse)
async def contacts():
    content = '<section style="padding:50px 0;"><div class="container"><div style="background:white;border-radius:24px;padding:40px;"><h1 style="color:#1a5d7a;">📬 Наши контакты</h1><div style="background:#f0f9ff;padding:22px;border-radius:16px;margin:25px 0;"><p><strong>📍 Адрес:</strong> г. Лянтор, Лянторский Нефтяной техникум</p><p><strong>📧 Email:</strong> artemgaun104@gmail.com</p></div><div style="border-radius:20px;overflow:hidden;"><iframe src="https://yandex.ru/map-widget/v1/?ll=72.1579%2C61.6229&z=17&pt=72.1589,61.6230&what=here%3A1&lang=ru_RU" style="width:100%;height:380px;border:0;"></iframe></div></div></div></section>'
    return HTMLResponse(render_html(content, user=current_user))

@app.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    err = f'<div class="error">{error}</div>' if error else ''
    content = f'<section style="padding:50px 0;"><div class="container"><div style="max-width:400px;margin:0 auto;background:white;padding:30px;border-radius:20px;"><h2 style="color:#1a5d7a;">Вход</h2>{err}<form action="/login" method="post"><div class="form-group"><label>Логин</label><input type="text" name="username" required></div><div class="form-group"><label>Пароль</label><input type="password" name="password" required></div><button type="submit" class="btn">Войти</button></form><p style="margin-top:15px;"><a href="/register">Зарегистрироваться</a></p></div></div></section>'
    return HTMLResponse(render_html(content, user=current_user, error=error))

@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    global current_user
    user = get_user_by_username(username)
    if user and user["password"] == password and user["is_active"]:
        current_user = {"username": user["username"], "role": user["role"], "name": user["name"]}
        return RedirectResponse("/", 303)
    return RedirectResponse("/login?error=Неверный логин или пароль", 303)

@app.get("/logout")
async def logout():
    global current_user
    current_user = None
    return RedirectResponse("/", 303)

@app.get("/register", response_class=HTMLResponse)
async def register_page(error: str = None):
    err = f'<div class="error">{error}</div>' if error else ''
    content = f'<section style="padding:50px 0;"><div class="container"><div style="max-width:400px;margin:0 auto;background:white;padding:30px;border-radius:20px;"><h2 style="color:#1a5d7a;">Регистрация</h2>{err}<form action="/register" method="post"><div class="form-group"><label>Имя</label><input type="text" name="name" required></div><div class="form-group"><label>Логин</label><input type="text" name="username" required></div><div class="form-group"><label>Пароль</label><input type="password" name="password" required></div><div class="form-group"><label>Роль</label><select name="role"><option value="client">Клиент</option><option value="seller">Продавец</option></select></div><button type="submit" class="btn">Зарегистрироваться</button></form><p style="margin-top:15px;"><a href="/login">Уже есть аккаунт?</a></p></div></div></section>'
    return HTMLResponse(render_html(content, user=current_user, error=error))

@app.post("/register")
async def register_post(name: str = Form(...), username: str = Form(...), password: str = Form(...), role: str = Form(...)):
    if get_user_by_username(username):
        return RedirectResponse("/register?error=Пользователь уже существует", 303)
    create_user(username, password, name, role)
    return RedirectResponse("/login", 303)

@app.get("/profile", response_class=HTMLResponse)
async def profile(error: str = None, success: str = None):
    global current_user
    if not current_user:
        return RedirectResponse("/login", 303)
    mark_notifications_read(current_user["username"])
    notif_list = get_notifications_by_user(current_user["username"])
    notif_html = ""
    for n in notif_list:
        notif_html += f'<div class="notification"><strong>{n["date"]}</strong><p>{n["message"]}</p></div>'
    if not notif_html:
        notif_html = "<p>У вас пока нет уведомлений</p>"
    user = get_user_by_username(current_user["username"])
    email = user.get("email", "") if user else ""
    content = f'<section style="padding:50px 0;"><div class="container"><div style="background:white;border-radius:24px;padding:40px;"><h1 style="color:#1a5d7a;">📋 Личный кабинет</h1><div style="margin:30px 0;padding:20px;background:#e0f2f8;border-radius:16px;"><p><strong>👤 Имя:</strong> {current_user["name"]}</p><p><strong>🔑 Роль:</strong> {current_user["role"]}</p><p><strong>📧 Email:</strong> {email if email else "Не указан"}</p></div><form action="/update_email" method="post"><div class="form-group"><label>Привязать почту (@mail.ru или @gmail.com)</label><div style="display:flex;gap:10px;"><input type="email" name="email" placeholder="example@mail.ru" value="{email}" style="flex:1;"><button type="submit" class="btn">Сохранить</button></div></div></form><h2 style="color:#1a5d7a;margin:30px 0 20px;">🔔 Уведомления</h2><div>{notif_html}</div></div></div></section>'
    return HTMLResponse(render_html(content, user=current_user, error=error, success=success))

@app.post("/update_email")
async def update_email(email: str = Form(...)):
    global current_user
    if not current_user:
        return RedirectResponse("/login", 303)
    if email and not is_valid_email(email):
        return RedirectResponse("/profile?error=Неверный формат почты. Поддерживается @mail.ru или @gmail.com", 303)
    update_user_email(current_user["username"], email)
    return RedirectResponse("/profile?success=Почта обновлена", 303)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("✅ САЙТ ЗАПУЩЕН!")
    print("🌐 Открой в браузере: http://127.0.0.1:8000")
    print("="*60)
    print("\n🔑 Тестовый аккаунт: admin / admin123")
    print("\n💾 Все данные сохраняются в папке data/")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
