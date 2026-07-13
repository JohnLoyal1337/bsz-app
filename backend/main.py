from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Личный кабинет БСЗ")

# --- ИСПРАВЛЕННЫЙ БЛОК CORS ---
app.add_middleware(
    CORSMiddleware,  # ТУТ ТЕПЕРЬ ЗАПЯТАЯ ВМЕСТО СКОБКИ
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PYDANTIC МОДЕЛИ ДЛЯ ВАЛИДАЦИИ ЗАПРОСОВ ---
class LoginModel(BaseModel):
    tab_num: str
    password: str

class TabNumModel(BaseModel):
    tab_num: str

class VacationRequestModel(BaseModel):
    tab_num: str
    request_type: str
    start_date: str
    end_date: str

class ActionRequestModel(BaseModel):
    request_id: int
    manager_tab_num: str

# --- ВРЕМЕННАЯ БАЗА ДАННЫХ (Имитация до подключения PostgreSQL) ---
DB_EMPLOYEES = {
    "1024": {
        "name": "Иванов Иван Иванович",
        "role": "worker", # Может быть 'worker' или 'manager'
        "password": "123",
        "vacation_days_left": 28,
        "vacations": [
            {"id": 1, "request_type": "Очередной отпуск", "start_date": "2026-05-10", "end_date": "2026-05-24", "status": "Утвержден"}
        ],
        "salary_slips": {
            "2026-05": {"salary": "85000", "bonus": "15000", "tax": "13000", "total": "87000"}
        }
    },
    "777": {
        "name": "Петров Петр Петрович (Начальник цеха)",
        "role": "manager",
        "password": "321",
        "vacation_days_left": 14,
        "vacations": [],
        "salary_slips": {}
    }
}

# Общий список заявок для панели руководителя (глобальный счетчик ID)
vacation_requests_counter = 1
ALL_VACATION_REQUESTS = []

# --- РОУТЫ / ЭНДПОИНТЫ ---

# 1. Авторизация
@app.post("/auth/login")
def login(data: LoginModel):
    if data.tab_num not in DB_EMPLOYEES or DB_EMPLOYEES[data.tab_num]["password"] != data.password:
        raise HTTPException(status_code=401, detail="Неверный табельный номер или пароль")
    
    user = DB_EMPLOYEES[data.tab_num]
    return {"tab_num": data.tab_num, "name": user["name"], "role": user["role"]}

# 2. Получение расчетного листка (GET, так как просто забираем данные)
@app.get("/salary/slip")
def get_salary_slip(tab_num: str, month: str):
    if tab_num not in DB_EMPLOYEES:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    slips = DB_EMPLOYEES[tab_num]["salary_slips"]
    if month not in slips:
        raise HTTPException(status_code=404, detail="Данные за этот месяц не найдены")
        
    return slips[month]

# 3. Получение истории отпусков (POST с телом Body, как просил твой Swagger)
@app.post("/vacation/info")
def get_vacation_info(data: TabNumModel):
    if data.tab_num not in DB_EMPLOYEES:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    user = DB_EMPLOYEES[data.tab_num]
    return {
        "vacation_days_left": user["vacation_days_left"],
        "history": user["vacations"]
    }

# 4. Отправка заявления на отпуск/отгул
from datetime import datetime # Обязательно проверь, что этот импорт есть вверху файла

@app.post("/vacation/approve/{request_id}")
async def approve_vacation(request_id: int):
    # 1. Находим заявку в базе
    vacation_request = db.query(Vacation).filter(Vacation.id == request_id).first()
    
    if not vacation_request:
        return {"error": "Заявление не найдено"}, 404
        
    # Меняем статус
    vacation_request.status = "Утвержден"
    
    # Приводим тип к нижнему регистру для безопасной проверки
    req_type = vacation_request.request_type.lower() if vacation_request.request_type else ""
    
    # 2. ЕСЛИ это очередной отпуск (в любом регистре), уменьшаем баланс
    if "очередной" in req_type or req_type == "отпуск":
        try:
            # Безопасно переводим строки в даты для расчёта, если они сохранены как текст
            if isinstance(vacation_request.start_date, str):
                start_dt = datetime.strptime(vacation_request.start_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(vacation_request.end_date, "%Y-%m-%d").date()
            else:
                start_dt = vacation_request.start_date
                end_dt = vacation_request.end_date

            # Считаем количество дней
            days = (end_dt - start_dt).days + 1
            
            # Находим сотрудника (приводим к строке/числу в зависимости от типа в твоей базе)
            user = db.query(User).filter(User.tab_num == str(vacation_request.tab_num)).first()
            
            if user:
                # Вычитаем дни из его личного баланса
                user.vacation_days_left -= days
                print(f"Успешно списано {days} дн. у сотрудника {user.tab_num}")
            else:
                print(f"Предупреждение: Пользователь с табельным {vacation_request.tab_num} не найден")
                
        except Exception as e:
            print(f"Ошибка при подсчете дней отпуска: {e}")
            # Если даты не распарсились, статус всё равно обновится, но база не упадёт
            
    db.commit()
    return {"message": "Заявление успешно утверждено, изменения сохранены"}

# 5. Получение списка всех заявок для руководителя
@app.get("/manager/requests")
def get_manager_requests(manager_tab_num: str):
    if manager_tab_num not in DB_EMPLOYEES or DB_EMPLOYEES[manager_tab_num]["role"] != "manager":
        raise HTTPException(status_code=403, detail="Доступ запрещен. Вы не руководитель")
    return ALL_VACATION_REQUESTS

# 6. Утверждение заявки шефом
@app.post("/manager/approve")
def approve_request(data: ActionRequestModel):
    if data.manager_tab_num not in DB_EMPLOYEES or DB_EMPLOYEES[data.manager_tab_num]["role"] != "manager":
        raise HTTPException(status_code=403, detail="Доступ запрещен")
        
    for req in ALL_VACATION_REQUESTS:
        if req["id"] == data.request_id:
            req["status"] = "Утвержден"
            # Обновляем статус и в истории самого работника
            worker_tab = req["tab_num"]
            for w_req in DB_EMPLOYEES[worker_tab]["vacations"]:
                if w_req["id"] == data.request_id:
                    w_req["status"] = "Утвержден"
            return {"status": "success"}
            
    raise HTTPException(status_code=404, detail="Заявка не найдена")