const API_URL = "https://bsz-app.onrender.com";

// Глобальные переменные сессии
let currentTabNum = null;
let currentUserRole = null;

// 1. ФУНКЦИЯ АВТОРИЗАЦИИ (ВХОД)
async function handleLogin() {
    const tabNumInput = document.getElementById("login-tab").value.trim();
    const passwordInput = document.getElementById("login-pass").value.trim();
    const errorBlock = document.getElementById("login-error");

    if (!tabNumInput || !passwordInput) {
        errorBlock.innerText = "Заполните все поля!";
        errorBlock.style.display = "block";
        return;
    }

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tab_num: tabNumInput, password: passwordInput })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Ошибка авторизации");
        }

        const user = await response.json();
        
        // Сохраняем данные пользователя
        currentTabNum = user.tab_num;
        currentUserRole = user.role;
    
        // --- ФИНАЛЬНАЯ И КРАСИВАЯ СМЕНА ЭКРАНОВ ---
        const loginScreen = document.getElementById("auth-block"); // ТВОЙ ИСТИННЫЙ ID
        const mainApp = document.getElementById("main-app");
        const managerBtn = document.getElementById("manager-btn");
        const userNameDiv = document.getElementById("user-name");

        // Скрываем экран логина
        if (loginScreen) {
            loginScreen.style.display = "none";
        }
        // Показываем главное приложение
        if (mainApp) {
            mainApp.style.display = "block";
        }

        // Выводим имя пользователя
        if (userNameDiv) {
            userNameDiv.innerText = user.name;
        }

        // Показываем кнопку руководителя, если вошел шеф
        if (managerBtn) {
            if (user.role === 'manager') {
                managerBtn.style.display = "inline-block";
            } else {
                managerBtn.style.display = "none";
            }
        }
        

        // По умолчанию загружаем первую вкладку (Расчетный листок)
        switchTab('salary-tab');

    } catch (err) {
        // 1. Выводим НАСТОЯЩУЮ причину в консоль, чтобы мы её увидели
        console.error("РЕНДЕР ИЛИ БЭКЕНД ВЕРНУЛ ОШИБКУ:", err);

        // 2. Ищем блок ошибки, но проверяем, существует ли он
        const errorBlock = document.getElementById("login-error");
        if (errorBlock) {
            errorBlock.innerText = err.message;
            errorBlock.style.display = "block";
        } else {
            // 3. Если блока в HTML нет, просто выводим окно на экран
            alert("Ошибка авторизации: " + err.message);
        }
    }
}


// 2. ВЫХОД ИЗ СИСТЕМЫ
function handleLogout() {
    currentTabNum = null;
    currentUserRole = null;
    document.getElementById("login-tab").value = "";  
    document.getElementById("login-pass").value = ""; 
    document.getElementById("main-app").style.display = "none"; 
    document.getElementById("login-screen").style.display = "block";
    if(document.getElementById("login-error")) {
        document.getElementById("login-error").style.display = "none";
    }
}

// 3. ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК
function switchTab(tabId) {
    // Скрываем все вкладки
    const tabs = document.querySelectorAll(".tab-content");
    tabs.forEach(tab => tab.style.display = "none");

    // Снимаем активный класс со всех кнопок
    const buttons = document.querySelectorAll(".tab-btn");
    buttons.forEach(btn => btn.classList.remove("active"));

    // Показываем нужную вкладку
    document.getElementById(tabId).style.display = "block";
    
    // Подсвечиваем нужную кнопку (находим по onclick атрибуту)
    buttons.forEach(btn => {
        if (btn.getAttribute("onclick").includes(tabId)) {
            btn.classList.add("active");
        }
    });

    // Автоматически подгружаем данные в зависимости от открытой вкладки
    if (tabId === 'vacation-tab') {
        loadVacationInfo();
    } else if (tabId === 'manager-tab') {
        loadManagerPanel();
    }
}

// 4. ЗАГРУЗКА РАСЧЕТНОГО ЛИСТКА
async function loadSalarySlip() {
    const month = document.getElementById("salary-month").value;
    const infoDiv = document.getElementById("salary-info");

    try {
        // Передаем через Query параметры (?tab_num=...&month=...) как настроено в FastAPI
        const response = await fetch(`${API_URL}/salary/slip?tab_num=${currentTabNum}&month=${month}`);
        
        if (!response.ok) {
            throw new Error("Данные за этот месяц отсутствуют");
        }

        const data = await response.json();
        infoDiv.innerHTML = `
            <p><strong>Оклад:</strong> ${data.salary} руб.</p>
            <p><strong>Премия:</strong> ${data.bonus} руб.</p>
            <p><strong>Налог (НДФЛ):</strong> ${data.tax} руб.</p>
            <hr>
            <p style="font-size: 1.2em; color: #2c3e50;"><strong>Итого к выдаче:</strong> ${data.total} руб.</p>
        `;
    } catch (err) {
        infoDiv.innerHTML = `<p style="color: red;">${err.message}</p>`;
    }
}

// 5. ЗАГРУЗКА ИСТОРИИ ОТПУСКОВ (Решаем проблему ошибки 422!)
async function loadVacationInfo() {
    try {
        // Передаем tab_num строго в Body методом POST, как заложено в бэкенде
        const response = await fetch(`${API_URL}/vacation/info`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tab_num: currentTabNum.toString() })
        });

        if (!response.ok) throw new Error("Не удалось загрузить данные отпусков");

        const data = await response.json();

        // Обновляем остаток дней
        if (data.vacation_days_left !== undefined) {
            document.getElementById("vacation-days-count").innerText = data.vacation_days_left;
        }

        // Заполняем таблицу истории
        const tbody = document.querySelector("#table-vacations tbody");
        tbody.innerHTML = "";

        if (Array.isArray(data.history)) {
            data.history.forEach(r => {
                let row = tbody.insertRow();
                row.insertCell(0).innerText = `${r.request_type}: с ${r.start_date} по ${r.end_date}`;
                
                let statusCell = row.insertCell(1);
                statusCell.innerText = r.status;

                // Цвета для статусов
                if (r.status === 'Утвержден') statusCell.style.color = 'green';
                if (r.status === 'Ожидает рассмотрения') statusCell.style.color = 'orange';
                if (r.status === 'Отклонен') statusCell.style.color = 'red';
            });
        }
    } catch (err) {
        console.error("Ошибка:", err);
    }
}

// 6. ОТПРАВКА ЗАЯВЛЕНИЯ НА ОТПУСК / ОТГУЛ
async function submitVacation() {
    const type = document.getElementById("vacation-type").value;
    const start = document.getElementById("vacation-start").value;
    const end = document.getElementById("vacation-end").value;

    if (!start || !end) {
        alert("Выберите даты начала и окончания!");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/vacation/request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tab_num: currentTabNum.toString(),
                request_type: type,
                start_date: start,
                end_date: end
            })
        });

        if (!response.ok) throw new Error("Ошибка при отправке заявления");

        alert("Заявление отправлено начальнику цеха!");
        
        // Сразу обновляем таблицу истории, чтобы строчка появилась автоматически!
        loadVacationInfo();

    } catch (err) {
        alert(err.message);
    }
}

// 7. ЗАГРУЗКА ПАНЕЛИ РУКОВОДИТЕЛЯ
async function loadManagerPanel() {
    try {
        const response = await fetch(`${API_URL}/manager/requests?manager_tab_num=${currentTabNum}`);
        if (!response.ok) throw new Error("Ошибка доступа к панели");

        const requests = await response.json();
        const tbody = document.querySelector("#table-manager-requests tbody");
        tbody.innerHTML = "";

        requests.forEach(r => {
            let row = tbody.insertRow();
            row.insertCell(0).innerText = r.name;
            row.insertCell(1).innerText = `${r.request_type} (${r.start_date} - ${r.end_date})`;
            
            let actionCell = row.insertCell(2);
            if (r.status === 'Ожидает рассмотрения') {
                actionCell.innerHTML = `<button onclick="approveRequest(${r.id})" style="background-color: green; color: white; border: none; padding: 3px 8px; cursor: pointer; border-radius: 3px;">Утвердить</button>`;
            } else {
                actionCell.innerText = r.status;
                if (r.status === 'Утвержден') actionCell.style.color = 'green';
            }
        });
    } catch (err) {
        console.error(err);
    }
}

// 8. УТВЕРЖДЕНИЕ ЗАЯВКИ РУКОВОДИТЕЛЕМ
async function approveRequest(requestId) {
    try {
        const response = await fetch(`${API_URL}/manager/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                request_id: requestId,
                manager_tab_num: currentTabNum.toString()
            })
        });

        if (!response.ok) throw new Error("Не удалось утвердить заявку");

        alert("Заявка успешно утверждена!");
        loadManagerPanel(); // Перезагружаем панель шефа, чтобы обновился статус

    } catch (err) {
        alert(err.message);
    }
}