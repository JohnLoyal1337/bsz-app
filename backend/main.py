from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Личный кабинет БСЗ")

# Настройка CORS, чтобы фронтенд с Vercel мог достучаться до бэкенда на Render
app.add_middleware(
    CORSMiddleware(
        allow_origins=["*"], # В будущем можно заменить на конкретный URL твоего фронтенда
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
@app.post("/vacation/request")
def create_vacation_request(data: VacationRequestModel):
    global vacation_requests_counter
    if data.tab_num not in DB_EMPLOYEES:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    new_request = {
        "id": vacation_requests_counter,
        "tab_num": data.tab_num,
        "name": DB_EMPLOYEES[data.tab_num]["name"],
        "request_type": data.request_type,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "status": "Ожидает рассмотрения"
    }
    
    # Добавляем и сотруднику в личную историю, и в общий список для шефа
    DB_EMPLOYEES[data.tab_num]["vacations"].append(new_request)
    ALL_VACATION_REQUESTS.append(new_request)
    
    vacation_requests_counter += 1
    return {"status": "success", "message": "Заявление успешно отправлено!"}

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