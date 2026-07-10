import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Код автоматически возьмет секретную ссылку DATABASE_URL из настроек Render
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel

# 1. Модель таблицы в PostgreSQL
class EmployeeDB(Base):
    tablename = "employees"

    tab_num = Column(Integer, primary_key=True, index=True)
    password = Column(String)
    full_name = Column(String)
    position = Column(String)

# 2. Автоматически создаем таблицы в базе данных при запуске
Base.metadata.create_all(bind=engine)

# Функция-помощник для получения доступа к базе в запросах
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Березниковский содовый завод - API")

# Разрешаем сайту общаться с сервером без блокировок безопасности
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Симуляция защищенной базы данных сотрудников БСЗ
DB_EMPLOYEES = {
    "1024": {
        "tab_num": "1024",
        "full_name": "Иванов Петр Сергеевич",
        "position": "Машинист бульдозера 5 разряда",
        "shop": "Цех механизации и технологического транспорта",
        "vacation_days_left": 32,
        "salary_slips": {
            "2026-06": {
                "period": "Июнь 2026",
                "base_salary": 65000.00,
                "bonus_prod": 19500.00,
                "hazard_pay": 7800.00,  # Надбавка за вредность на БСЗ
                "night_shifts": 4200.00,
                "tax_ndfl": 12545.00,
                "prof_union": 965.00,
                "advance_paid": 35000.00
            },
            "2026-05": {
                "period": "Май 2026",
                "base_salary": 65000.00,
                "bonus_prod": 15000.00,
                "hazard_pay": 7800.00,
                "night_shifts": 2100.00,
                "tax_ndfl": 11687.00,
                "prof_union": 899.00,
                "advance_paid": 35000.00
            }
        },
        "vacations": [
            {"start": "2026-03-10", "end": "2026-03-24", "type": "Очередной", "status": "Утвержден"}
        ]
    }
}

class LoginRequest(BaseModel):
    tab_num: str
    password: str

class VacationRequest(BaseModel):
    tab_num: str
    start_date: str
    end_date: str
    vacation_type: str

@app.post("/api/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Ищем сотрудника в реальной базе данных по табельному номеру
    emp = db.query(EmployeeDB).filter(EmployeeDB.tab_num == data.tab_num).first()
    
    # Если сотрудник найден и пароль совпадает
    if emp and emp.password == data.password:
        return {
            "status": "success", 
            "token": f"token-{emp.tab_num}", 
            "full_name": emp.full_name, 
            "position": emp.position
        }
        
    raise HTTPException(status_code=401, detail="Неверный табельный номер или пароль")
# Временный маршрут для создания сотрудников через /docs
@app.post("/api/auth/register")
def register(data: LoginRequest, db: Session = Depends(get_db)):
    # Проверяем, нет ли уже такого пользователя
    existing = db.query(EmployeeDB).filter(EmployeeDB.tab_num == data.tab_num).first()
    if existing:
        return {"status": "error", "message": "Пользователь уже существует"}
        
    # Создаем нового сотрудника (можете вписать свои имя и должность по умолчанию)
    new_emp = EmployeeDB(
        tab_num=data.tab_num,
        password=data.password,
        full_name="Евгений Овчинников.", 
        position="Машинист бульдозера 7 разряда"
    )
    db.add(new_emp)
    db.commit() # Сохраняем в PostgreSQL насовсем!
    return {"status": "success", "message": "Сотрудник успешно добавлен в базу"}

@app.get("/api/salary/{tab_num}/{month}")
def get_salary_slip(tab_num: str, month: str):
    if tab_num not in DB_EMPLOYEES:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    slips = DB_EMPLOYEES[tab_num]["salary_slips"]
    if month not in slips:
        raise HTTPException(status_code=404, detail="Данные за этот месяц отсутствуют")
    
    slip = slips[month]
    total_earned = slip["base_salary"] + slip["bonus_prod"] + slip["hazard_pay"] + slip["night_shifts"]
    total_deductions = slip["tax_ndfl"] + slip["prof_union"]
    final_amount = total_earned - total_deductions - slip["advance_paid"]
    
    return {
        "period": slip["period"],
        "income": {
            "Оклад по тарифу": slip["base_salary"],
            "Премия за выполнение плана": slip["bonus_prod"],
            "Надбавка за вредные условия труда": slip["hazard_pay"],
            "Доплата за ночные смены": slip["night_shifts"]
        },
        "deductions": {
            "НДФЛ (13%)": slip["tax_ndfl"],
            "Профсоюзный взнос": slip["prof_union"]
        },
        "payouts": {"Выплачен аванс": slip["advance_paid"]},
        "totals": {"total_earned": total_earned, "total_deductions": total_deductions, "final_amount": final_amount}
    }

@app.get("/api/vacation/{tab_num}")
def get_vacation_info(tab_num: str):
    if tab_num not in DB_EMPLOYEES:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return {"vacation_days_left": DB_EMPLOYEES[tab_num]["vacation_days_left"], "history": DB_EMPLOYEES[tab_num]["vacations"]}

@app.post("/api/vacation/request")
def apply_vacation(req: VacationRequest):
    if req.tab_num not in DB_EMPLOYEES:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    new_vac = {"start": req.start_date, "end": req.end_date, "type": req.vacation_type, "status": "На согласовании у начальника цеха"}
    DB_EMPLOYEES[req.tab_num]["vacations"].append(new_vac)
    return {"status": "success"}