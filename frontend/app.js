const API_URL = "https://bsz-app.onrender.com";
let currentTabNum = "";
let isMasked = false;
let currentSalaryData = null;

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active-content'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active-content');
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    if (tabId === 'vacation-tab') { 
        loadVacationInfo(); 
    }
    if (tabId === 'manager-tab') {
    loadManagerRequests();
    // Загрузка всех заявок для шефа
async function loadManagerRequests() {
    try {
        const response = await fetch(${API_URL}/requests/all);
        const data = await response.json();
        const tbody = document.getElementById("table-manager-requests").getElementsByTagName('tbody')[0];
        tbody.innerHTML = "";
        
        data.forEach(r => {
            let row = tbody.insertRow();
            row.insertCell(0).innerText = r.tab_num;
            row.insertCell(1).innerText = r.request_type;
            row.insertCell(2).innerText = ${r.start_date} по ${r.end_date};
            row.insertCell(3).innerText = r.status;
            
            let actionsCell = row.insertCell(4);
            if (r.status === "Ожидает рассмотрения") {
                actionsCell.innerHTML = 
                    <button onclick="updateStatus(${r.id}, 'Утвержден')" style="background: green; color: white;">Утвердить</button>
                    <button onclick="updateStatus(${r.id}, 'Отклонен')" style="background: red; color: white;">Отклонить</button>
                ;
            } else {
                actionsCell.innerText = "Решение принято";
            }
        });
    } catch (err) {
        console.error(err);
    }
}

// Отправка решения (Утвердить/Отклонить) на бэкенд
async function updateStatus(reqId, status) {
    try {
        await fetch(${API_URL}/requests/update-status?req_id=${reqId}&new_status=${encodeURIComponent(status)}, {
            method: 'POST'
        });
        alert(Заявка ${status.toLowerCase()}а!);
        loadManagerRequests(); // Обновляем таблицу
    } catch (err) {
        alert("Не удалось изменить статус");
    }
}
}
}

// Замените вашу функцию handleLogin на эту:
async function handleLogin() {
    const tabNum = document.getElementById("login-tab").value;
    const password = document.getElementById("login-pass").value;
    try {
        const response = await fetch(${API_URL}/api/auth/login, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tab_num: tabNum, password: password })
        });
        if (!response.ok) throw new Error("Неверный табельный номер или пароль");
        const data = await response.json();
        currentTabNum = tabNum;
        
        document.getElementById("auth-block").style.display = "none";
        document.getElementById("main-app").style.display = "block";
        document.getElementById("user-name").innerText = data.full_name;
        document.getElementById("user-position").innerText = data.position;

        // ПРОВЕРКА РОЛИ: если зашел начальник
        if (data.role === 'manager') {
            document.getElementById("manager-btn").style.display = "inline-block";
        }

        loadSalarySlip();
    } catch (err) {
        alert(err.message);
    }
}

async function loadSalarySlip() {
    try {
        const month = document.getElementById("salary-month-select").value;
        const response = await fetch(`${API_URL}/salary/${currentTabNum}/${month}`);
        if (!response.ok) throw new Error("Ошибка загрузки квитка");
        currentSalaryData = await response.json();
        renderSalary();
    } catch (err) {
        console.error(err);
    }
}

function renderSalary() {
    if (!currentSalaryData) return;
    const finalAmt = document.getElementById("final-amount-val");
    finalAmt.innerText = `${currentSalaryData.totals.final_amount.toFixed(2)} руб.`;
    
    if (isMasked) finalAmt.classList.add("hidden-money");
    else finalAmt.classList.remove("hidden-money");

    fillTable("table-income", currentSalaryData.income);
    fillTable("table-deductions", currentSalaryData.deductions);
}

function fillTable(tableId, data) {
    const tbody = document.getElementById(tableId).getElementsByTagName('tbody')[0];
    tbody.innerHTML = "";
    for (const [name, val] of Object.entries(data)) {
        let row = tbody.insertRow();
        row.insertCell(0).innerText = name;
        let cVal = row.insertCell(1);
        cVal.innerText = `${val.toFixed(2)} руб.`;
        if (isMasked) cVal.classList.add("hidden-money");
    }
}

function toggleSalaryVisibility() {
    isMasked = !isMasked;
    renderSalary();
}

async function loadVacationInfo() {
    try {
        const response = await fetch(`${API_URL}/vacation/${currentTabNum}`);
        const data = await response.json();
        document.getElementById("vacation-days-count").innerText = data.vacation_days_left;
        const tbody = document.getElementById("table-vacations").getElementsByTagName('tbody')[0];
        tbody.innerHTML = "";
        data.history.forEach(v => {
            let row = tbody.insertRow();
            row.insertCell(0).innerText = `${v.start} по ${v.end}`;
            row.insertCell(1).innerText = v.status;
        });
    } catch (err) {
        console.error(err);
    }
}

// Замените вашу функцию submitVacation на эту:
async function submitVacation() {
    const start = document.getElementById("vac-start").value;
    const end = document.getElementById("vac-end").value;
    const type = document.getElementById("vac-type").value;
    
    if (!start || !end) {
        alert("Выберите даты");
        return;
    }
    try {
        await fetch(${API_URL}/vacation/request, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                tab_num: parseInt(currentTabNum), 
                start_date: start, 
                end_date: end, 
                vacation_type: type 
            })
        });
        alert("Заявление отправлено начальнику цеха!");
        loadVacationInfo();
    } catch (err) {
        alert("Не удалось отправить заявление");
    }
}

function handleLogout() { 
    location.reload(); 
}