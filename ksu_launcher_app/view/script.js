// Tab Switching Logic
const navBtns = document.querySelectorAll('.nav-btn');
const screens = document.querySelectorAll('.screen');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.target;

        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        screens.forEach(s => {
            s.classList.remove('active');
            if (s.id === target) s.classList.add('active');
        });
    });
});

// RAM Slider logic
const ramSlider = document.getElementById('ram-slider');
const ramValue = document.getElementById('ram-value');

ramSlider.addEventListener('input', (e) => {
    const val = e.target.value;
    ramValue.textContent = `${val} MB`;
    eel.save_settings({ ram: parseInt(val) });
});

//// Window controls - кнопки "закрыть" и "свернуть" в интерфейсе
//document.getElementById('close-btn').addEventListener('click', () => {
//    window.close(); // Or eel.close_app()
//});
//
//document.getElementById('minimize-btn').addEventListener('click', () => {
//    eel.minimize_window();
//});

// Play logic
const playBtn = document.getElementById('play-btn');
const statusText = document.getElementById('status-text');
const progressBar = document.getElementById('progress-bar');
const loginOverlay = document.getElementById('login-overlay');

let modpackName = 'KsuSerVer Season 2';
//let gameVersion = '1.21.1';

// Custom dropdown logic
function initCustomSelect() {
    const wrapper = document.getElementById('custom-version-select');
    if (!wrapper) return;
    const select = wrapper.querySelector('.custom-select');
    const trigger = wrapper.querySelector('.custom-select-trigger');
    const triggerText = wrapper.querySelector('.custom-select-text');
    const optionsContainer = wrapper.querySelector('.custom-options');

    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        select.classList.toggle('open');
    });
    document.addEventListener('click', () => select.classList.remove('open'));

    wrapper._setOptions = function(versions, savedVersion) {
        optionsContainer.innerHTML = '';
        versions.forEach((version, i) => {
            const opt = document.createElement('div');
            opt.className = 'custom-option';
            opt.textContent = `${version.name} (${version.minecraft_version})`;
            opt.dataset.value = version.name;
            if (version.name === savedVersion || i === 0) {
                opt.classList.add('selected');
                triggerText.textContent = opt.textContent;
                modpackName = version.name;
            }
            opt.addEventListener('click', (e) => {
                e.stopPropagation();
                optionsContainer.querySelectorAll('.custom-option').forEach(o => o.classList.remove('selected'));
                opt.classList.add('selected');
                triggerText.textContent = opt.textContent;
                modpackName = version.name;
                eel.save_settings({ selected_version: version.name });
                select.classList.remove('open');
                add_log(`Версия выбрана: ${version.name}`);
            });
            optionsContainer.appendChild(opt);
        });
    };
    wrapper._setLoading = function(text) {
        triggerText.textContent = text;
        optionsContainer.innerHTML = '';
    };
}

playBtn.addEventListener('click', async () => {
    if (playBtn.classList.contains('disabled')) return;
    // Check if logged in - отключил, чтобы работала кнопка скипа логина (режим оффлайн)
//    const settings = await eel.get_settings()();
//    if (!settings.username || !settings.password) {
//        showLogin();
//        return;
//    }
    playBtn.classList.add('disabled');
    playBtn.style.opacity = '0.5';
    statusText.textContent = "Инициализация...";
    progressBar.style.width = '5%';
    // Start installation/launch process
    eel.start_launch(modpackName);
});

// Login UI handlers
function showLogin() {
    loginOverlay.classList.remove('hidden');
}

const loginBtn = document.getElementById('login-btn');
loginBtn.addEventListener('click', async () => {
    const email = document.getElementById('email-input').value;
    const pass = document.getElementById('pass-input').value;
    const totp = document.getElementById('totp-input') ? document.getElementById('totp-input').value : null;
    if (!email || !pass) {
        alert('Введите почту и пароль!');
        return;
    }
    loginBtn.textContent = 'Входим...';
    loginBtn.style.opacity = '0.5';
    add_log(`Попытка входа: ${email}`);
    const result = await eel.login(email, pass, totp)(); // If TOTP is visible/exists, pass it too
    if (result.success) {
        add_log(`Вход выполнен: ${result.username}`);
        loginOverlay.classList.add('hidden');
        statusText.textContent = `Привет, ${result.username}!`;
        loginBtn.textContent = 'ВОЙТИ';
        loginBtn.style.opacity = '1';
    } else {
        add_log(`Ошибка входа: ${result.error}`);
        alert(result.error);
        loginBtn.textContent = 'ВОЙТИ В АККАУНТ';
        loginBtn.style.opacity = '1';
    }
});

// Кнопка скипа логина (режим оффлайн)
const loginSkipBtn = document.getElementById('login-skip-btn');
loginSkipBtn.addEventListener('click', async () => {
    const result = await eel.skip_login()();
    add_log(`Тестовый вход`);
    loginOverlay.classList.add('hidden');
    statusText.textContent = `Привет, ${result.username}!`;
});

// Expose functions to Python
eel.expose(update_status);
function update_status(text, progress = null) {
    if (text) {
        add_log(`[STATUS] ${text}`);
        statusText.style.opacity = '0';
        setTimeout(() => {
            statusText.textContent = text;
            statusText.style.opacity = '1';

            // Re-enable button on error or final step
            const lowerText = text.toLowerCase();
            if (lowerText.includes("ошибка") || text.includes("Запустите") || text.includes("Запуск")) {
                playBtn.classList.remove('disabled');
                playBtn.style.opacity = '1';
            }
        }, 150);
    }
    if (progress !== null) {
        progressBar.style.width = `${progress}%`;
        if (progress >= 100) {
            playBtn.classList.remove('disabled');
            playBtn.style.opacity = '1';
        }
    }
}

eel.expose(add_log);
function add_log(text) {
    const logContainer = document.getElementById('status-log');
    if (!logContainer) return;
    const logLine = document.createElement('div');
    logLine.className = 'log-line';
    const time = new Date().toLocaleTimeString();
    logLine.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-text">${text}</span>`;
    logContainer.appendChild(logLine);
    logContainer.scrollTop = logContainer.scrollHeight;
    if (logContainer.childNodes.length > 50) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// Initial load
async function init() {
    const settings = await eel.get_settings()();
    if (settings.ram) {
        ramSlider.value = settings.ram;
        ramValue.textContent = `${settings.ram} MB`;
    }
    const pathInput = document.getElementById('current-path');
    if (settings.path) {
        pathInput.value = settings.path;
    }
    const installMethodWrapper = document.getElementById('custom-install-method-select');
    if (installMethodWrapper && settings.install_method) {
        installMethodWrapper._setValue(settings.install_method);
    }
    loadVersions(settings); // Pre-load versions in background
    //    eel.get_versions_list()(); - заменено строкой выше
    // Save manually edited path
    pathInput.onchange = () => {
        const newPath = pathInput.value.trim();
        if (newPath) {
            eel.save_settings({ path: newPath });
            add_log(`Путь вручную изменен на: ${newPath}`);
        }
    };
    // Delay autologin slightly to ensure stable connection
    setTimeout(async () => {
        if (settings.username && settings.password) {
            update_status("Авто-логин...", 80);
            add_log("Попытка автологина...");
            const result = await eel.login(settings.username, settings.password)();
            if (result.success) {
                add_log(`Автологин успешен: ${result.username}`);
                onLoginSuccess(result.username);
            } else {
                add_log(`Автологин не удался: ${result.error}`);
                update_status("");
                showLogin();
            }
        } else {
            showLogin();
        }
    }, 1000);
}

document.getElementById('browse-btn').addEventListener('click', async () => {
    const path = await eel.pick_folder()();
    if (path) {
        document.getElementById('current-path').value = path;
        eel.save_settings({ path: path });
        add_log(`Путь изменен через обзор: ${path}`);
    }
});

// Update Modpack Button
const updateBtn = document.getElementById('update-btn');
if (updateBtn) {
    updateBtn.addEventListener('click', () => {
        if (updateBtn.classList.contains('disabled')) return;
        updateBtn.classList.add('disabled');
        updateBtn.textContent = "ЗАГРУЗКА...";
        add_log("Запуск принудительного обновления модпака...");
        eel.update_modpack(modpackName);
        // Reset button after some time or via a status check
        // For now, we'll let the user wait for the status text to finish
        setTimeout(() => {
            updateBtn.classList.remove('disabled');
            updateBtn.textContent = "УСТАНОВИТЬ ОБНОВЛЕНИЕ";
        }, 10000); // 10s cooldown/buffer
    });
}

// Logout Logic
const logoutModal = document.getElementById('logout-modal');
const logoutBtn = document.getElementById('logout-btn');
const confirmLogout = document.getElementById('confirm-logout');
const cancelLogout = document.getElementById('cancel-logout');

logoutBtn.addEventListener('click', () => {
    logoutModal.classList.remove('hidden');
});

cancelLogout.addEventListener('click', () => {
    logoutModal.classList.add('hidden');
});

confirmLogout.addEventListener('click', async () => {
    logoutModal.classList.add('hidden');
    // Clear tokens from memory and file
    await eel.save_settings({ username: "", password: "" })();
    loginOverlay.classList.remove('hidden');
    statusText.textContent = "Войдите в аккаунт";
    // Reset inputs
    document.getElementById('email-input').value = "";
    document.getElementById('pass-input').value = "";
});

// External links
document.getElementById('reg-link').onclick = () => eel.open_url('https://account.ely.by/register');

// Modrinth Content Logic
let currentRPPage = 1;
let currentRPQuery = '';
let currentModrinthType = 'resourcepack'; // or 'shader'
const RP_LIMIT = 12;

const rpSearchInput = document.getElementById('rp-search-input');
const rpGrid = document.getElementById('rp-grid');
const rpPagination = document.getElementById('rp-pagination');
const subTabs = document.querySelectorAll('.sub-tab');

// Tab switching inside search screen
subTabs.forEach(tab => {
    tab.onclick = () => {
        if (tab.classList.contains('active')) return;

        subTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        currentModrinthType = tab.dataset.type;
        currentRPPage = 1;
        loadResourcePacks();
    };
});

// Debounce for search
let searchTimeout;
if (rpSearchInput) {
    rpSearchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentRPQuery = e.target.value;
            currentRPPage = 1;
            loadResourcePacks();
        }, 500);
    });
}

// Подгрузка ресурспаков с модринта
async function loadResourcePacks() {
    if (!rpGrid) return;
    add_log(`Загрузка ${currentModrinthType === 'shader' ? 'шейдеров' : 'ресурспаков'}...`);
    rpGrid.innerHTML = '<div class="status-msg">Синхронизация базы Modrinth...</div>';
    rpPagination.innerHTML = '';
//    gameVersion = '1.21.1'; // динамическая подгрузка версий
//    const versions = await eel.get_versions_list()();
//    for (let i = 0; i < versions.length; i++) {
//        if (versions[i].name === modpackName) {
//            gameVersion = versions[i].minecraft_version;
//            break;
//        }
//    }
    // Fetch from backend
    const result = await eel.search_modrinth(currentRPQuery, modpackName, currentModrinthType, currentRPPage)();
    if (result.error) {
        rpGrid.innerHTML = `<div class="status-msg" style="color: #ef4444;">Ошибка: ${result.error}</div>`;
        return;
    }
    renderRPPagination(result.total_hits || 0);
    if (!result.hits || result.hits.length === 0) {
        rpGrid.innerHTML = '<div class="status-msg">Ничего не найдено :(</div>';
        return;
    }
    renderRPCards(result.hits);
}

// Карточки модринта
function renderRPCards(hits) {
    rpGrid.innerHTML = '';
    hits.forEach(hit => {
        const card = document.createElement('div');
        card.className = 'rp-card glass';
        // Smarter download formatting
        let downloads = hit.downloads;
        if (downloads >= 1000000) {
            downloads = (downloads / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
        } else if (downloads >= 1000) {
            downloads = (downloads / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
        }
        card.innerHTML = `
            <img src="${hit.icon_url || 'https://placehold.co/400x400?text=No+Icon'}" class="rp-thumb" alt="${hit.title}">
            <div class="rp-info">
                <h3 title="${hit.title}">${hit.title}</h3>
                <p title="${hit.description}">${hit.description}</p>
            </div>
            <div class="rp-meta">
                <span title="Скачиваний">📥 ${downloads}</span>
                <button class="primary-btn install-btn" data-id="${hit.project_id}" style="padding: 8px 15px; font-size: 0.7rem;">Установить</button>
            </div>
        `;
        const installBtn = card.querySelector('.install-btn');
        installBtn.onclick = async () => {
            installBtn.textContent = '...';
            installBtn.classList.add('disabled');
            const folder = currentModrinthType === 'shader' ? 'shaderpacks' : 'resourcepacks'; // Determine target folder
            const res = await eel.install_modrinth(hit.project_id, modpackName, folder)();
            if (res.success) {
                installBtn.textContent = 'ГОТОВО!';
                installBtn.style.background = '#22c55e';
                add_log(`${currentModrinthType === 'shader' ? 'Шейдер' : 'Пак'} установлен: ${res.filename}`);
            } else {
                installBtn.textContent = 'ОШИБКА';
                installBtn.style.background = '#ef4444';
                add_log(`Ошибка: ${res.error}`);
                setTimeout(() => {
                    installBtn.textContent = 'Установить';
                    installBtn.style.background = '';
                    installBtn.classList.remove('disabled');
                }, 2000);
            }
        };
        rpGrid.appendChild(card);
    });
}

function renderRPPagination(totalHits) {
    rpPagination.innerHTML = '';
    const totalPages = Math.min(Math.ceil(totalHits / RP_LIMIT), 20); // Cap at 20 pages for stability
    if (totalPages <= 1) return;
    const maxVisible = 5;
    let startPage = Math.max(1, currentRPPage - 2);
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement('button');
        btn.className = `page-btn ${i === currentRPPage ? 'active' : ''}`;
        btn.textContent = i;
        btn.onclick = () => {
            if (currentRPPage === i) return;
            currentRPPage = i;
            loadResourcePacks();
            // Scroll content to top
            document.querySelector('.content').scrollTop = 0;
        };
        rpPagination.appendChild(btn);
    }
}

// Trigger load on screen switch
navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.getAttribute('data-target') === 'rp-screen') {
            loadResourcePacks();
        }
    });
});

function onLoginSuccess(username) {
    statusText.textContent = `Привет, ${username}!`;
    update_status("Готов к запуску", 0);
    add_log(`Вход выполнен: ${username}`);
}

// Загрузка версий при старте
async function loadVersions(settings) {
    const wrapper = document.getElementById('custom-version-select');
    if (!wrapper) return;
    try {
        const versions = await eel.get_versions_list()();
        if (!versions || versions.length === 0) {
            wrapper._setLoading('Нет версий');
            return;
        }
        const savedVersion = settings.selected_version || null;
        wrapper._setOptions(versions, savedVersion);
        console.log(`Loaded ${versions.length} versions`);
    } catch (error) {
        console.error('Ошибка загрузки версий:', error);
        wrapper._setLoading('Ошибка загрузки');
    }
}

// Custom dropdown logic for installation method
function initInstallMethodSelect() {
    const wrapper = document.getElementById('custom-install-method-select');
    if (!wrapper) return;
    const select = wrapper.querySelector('.custom-select');
    const trigger = wrapper.querySelector('.custom-select-trigger');
    const triggerText = wrapper.querySelector('.custom-select-text');
    const optionsContainer = wrapper.querySelector('.custom-options');

    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        select.classList.toggle('open');
    });
    document.addEventListener('click', () => select.classList.remove('open'));

    const options = optionsContainer.querySelectorAll('.custom-option');
    options.forEach(opt => {
        opt.addEventListener('click', (e) => {
            e.stopPropagation();
            options.forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            triggerText.textContent = opt.textContent;
            const value = opt.dataset.value;
            eel.save_settings({ install_method: value });
            select.classList.remove('open');
            add_log(`Способ установки изменен на: ${opt.textContent}`);
        });
    });

    wrapper._setValue = function(value) {
        const opt = Array.from(options).find(o => o.dataset.value === value);
        if (opt) {
            options.forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            triggerText.textContent = opt.textContent;
        }
    };
}

// Обработчики событий
document.addEventListener('DOMContentLoaded', () => {
    initCustomSelect();
    initInstallMethodSelect();
});

init();

// ====== MODS SCREEN ======
let allMods = [];

async function loadMods() {
    const list = document.getElementById('mods-list');
    list.innerHTML = '<div class="status-msg">Загрузка модов...</div>';
    try {
        allMods = await eel.get_mods_list(modpackName)();
        renderMods(allMods);
    } catch(e) {
        list.innerHTML = '<div class="status-msg" style="color:#ef4444;">Ошибка загрузки</div>';
    }
}

function renderMods(mods) {
    const list = document.getElementById('mods-list');
    const query = document.getElementById('mods-search-input').value.toLowerCase();
    const filtered = mods.filter(m => m.name.toLowerCase().includes(query) || m.filename.toLowerCase().includes(query));

    if (filtered.length === 0) {
        list.innerHTML = '<div class="status-msg">Моды не найдены</div>';
        return;
    }

    list.innerHTML = '';
    filtered.forEach(mod => {
        const item = document.createElement('div');
        item.className = 'mod-item';
        item.innerHTML = `
            <div class="mod-icon">
                <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M20.5 11H19V7c0-1.1-.9-2-2-2h-4V3.5C13 2.12 11.88 1 10.5 1S8 2.12 8 3.5V5H4c-1.1 0-1.99.9-1.99 2v3.8H3.5c1.49 0 2.7 1.21 2.7 2.7s-1.21 2.7-2.7 2.7H2V20c0 1.1.9 2 2 2h3.8v-1.5c0-1.49 1.21-2.7 2.7-2.7s2.7 1.21 2.7 2.7V22H17c1.1 0 2-.9 2-2v-4h1.5c1.38 0 2.5-1.12 2.5-2.5S21.88 11 20.5 11z"/></svg>
            </div>
            <div class="mod-info">
                <div class="mod-name">${mod.name}</div>
                <div class="mod-filename">${mod.filename}</div>
            </div>
            ${mod.is_user_mod ? '<span class="mod-badge-user">МОЙ МОД</span>' : ''}
            ${mod.is_user_mod ? `<button class="mod-delete-btn" data-filename="${mod.filename}" title="Удалить">
                <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/></svg>
            </button>` : ''}
        `;

        if (mod.is_user_mod) {
            const delBtn = item.querySelector('.mod-delete-btn');
            delBtn.addEventListener('click', async () => {
                delBtn.innerHTML = '...'; delBtn.style.pointerEvents = 'none';
                const res = await eel.delete_user_mod(mod.filename, modpackName)();
                if (res.success) {
                    item.style.opacity = '0'; item.style.transform = 'translateX(20px)';
                    setTimeout(() => { item.remove(); add_log(`Мод удалён: ${mod.filename}`); }, 300);
                } else {
                    delBtn.innerHTML = '✕'; delBtn.style.pointerEvents = '';
                    add_log(`Ошибка: ${res.error}`);
                }
            });
        }
        list.appendChild(item);
    });
}

// Поиск по модам
document.getElementById('mods-search-input').addEventListener('input', () => renderMods(allMods));

// Добавить мод
document.getElementById('add-mod-btn').addEventListener('click', async () => {
    const path = await eel.pick_jar_file(modpackName)();
    if (!path) return;
    const btn = document.getElementById('add-mod-btn');
    btn.textContent = 'Копирование...'; btn.style.opacity = '0.6';
    const res = await eel.add_user_mod(path, modpackName)();
    btn.textContent = '+ Добавить мод'; btn.style.opacity = '1';
    if (res.success) {
        add_log(`Мод добавлен: ${res.filename}`);
        await loadMods();
    } else {
        add_log(`Ошибка: ${res.error}`);
    }
});

// Загружаем моды при переходе на вкладку
navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.getAttribute('data-target') === 'mods-screen') {
            loadMods();
        }
    });
});
