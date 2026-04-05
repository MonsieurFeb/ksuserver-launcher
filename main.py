import pandas as pd
import json
import os
import shutil
import threading
import zipfile
import gdown
import minecraft_launcher_lib
import subprocess
import sys
from nbt import nbt
import requests
import time
import webbrowser
import uuid

# Определение пути для ресурсов
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath("..")
    return os.path.join(base_path, relative_path)

def download_authlib_injector():
    """Автоматически скачивает authlib-injector если его нет"""
    authlib_path = resource_path("../authlib-injector-1.2.7.jar")

    if os.path.exists(authlib_path):
        print(f"authlib-injector найден: {authlib_path}")
        return authlib_path

    print("authlib-injector не найден. Скачиваю...")

    # URL для скачивания (прямая ссылка на GitHub)
    urls = [
        "https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.7/authlib-injector-1.2.7.jar",
        "https://mirror.ghproxy.com/https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.7/authlib-injector-1.2.7.jar",
        "https://ghproxy.net/https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.7/authlib-injector-1.2.7.jar"
    ]

    for url in urls:
        try:
            print(f"Попытка скачать с {url}")
            response = requests.get(url, timeout=30, stream=True)
            if response.status_code == 200:
                with open(authlib_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"authlib-injector успешно скачан: {authlib_path}")
                return authlib_path
        except Exception as e:
            print(f"Ошибка скачивания с {url}: {e}")
            continue

    print("Не удалось скачать authlib-injector")
    print("Скачайте вручную: https://github.com/yushijinhun/authlib-injector/releases")
    return None

import customtkinter as ctk
from tkinter import filedialog, END, StringVar

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Для фоновых изображений установите Pillow: pip install Pillow")

df = pd.DataFrame()
df_loaded = False
versions_data = {}

AUTH_URL = "https://authserver.ely.by/auth/authenticate"
AUTHLIB_URL = "https://authserver.ely.by"

base_dir = os.path.dirname(resource_path(".."))
SETTINGS_FILE = os.path.join(base_dir, "../ksuserver_settings.json")
CACHE_FILE = os.path.join(base_dir, "../versions_cache.json")
CACHE_DURATION = 86400

def load_versions_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if time.time() - cache.get('timestamp', 0) < CACHE_DURATION:
                    return cache.get('versions', []), cache.get('data', {})
        except:
            pass
    return None, None

def save_versions_cache(versions, data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time(), 'versions': versions, 'data': data}, f)
    except:
        pass

def save_settings(path_input_text, username_input_text, password_input_text, version_text, theme_mode):
    data = {
        "path": path_input_text.get(),
        "username": username_input_text.get(),
        "password": password_input_text.get(),
        "version": version_text,
        "theme": theme_mode
    }
    try:
        with open(SETTINGS_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")

def load_settings(path_input_text, username_input_text, password_input_text, version_select_text):
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                path_input_text.set(data.get("path", ""))
                username_input_text.set(data.get("username", ""))
                password_input_text.set(data.get("password", ""))
                saved_version = data.get("version", "")
                if saved_version:
                    version_select_text.set(saved_version)
                return data.get("theme", "dark")
        except:
            pass
    return "dark"

def get_version_data(version_name):
    return versions_data.get(version_name, {})

def modpack(version_name, path_text, df_local):
    try:
        version_info = get_version_data(version_name)

        if version_info:
            id_archive = version_info.get('id_archive', '')
            if not id_archive:
                print("ID архива не найден")
                return False
        else:
            dfrow = df_local[df_local['name'] == version_name]
            if dfrow.empty:
                print(f"Версия '{version_name}' не найдена")
                return False

            if 'id_archive' in df_local.columns:
                id_archive = dfrow.iloc[0]['id_archive']
            elif len(df_local.columns) >= 5:
                id_archive = dfrow.iloc[0, 4]
            else:
                print("Не удалось найти ID архива")
                return False

        output = path_text + "\\archive.zip"

        print("Download modpack...")
        gdown.download(id=id_archive, output=output, quiet=False)

        if os.path.exists(output):
            if os.path.exists(path_text + "\\mods"):
                shutil.rmtree(path_text + "\\mods")
            print("Unpack...")
            with zipfile.ZipFile(output, 'r') as zip_ref:
                zip_ref.extractall(path_text)
            print("Ready!")
            os.remove(output)
            return True
        else:
            print("The archive was not downloaded.")
            return False
    except Exception as e:
        print(f"Ошибка установки модпака: {e}")
        return False

class TextRedirector(object):
    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        self.widget.insert(END, string)
        self.widget.see(END)

    def flush(self):
        pass

def add_server_to_list(minecraft_dir: str, server_name: str, server_ip: str):
    try:
        servers_dat = os.path.join(minecraft_dir, "servers.dat")
        if os.path.exists(servers_dat):
            with open(servers_dat, "rb") as f:
                data = nbt.NBTFile(buffer=f)
            servers_list = data["servers"]
            for server in servers_list.tags:
                if server["ip"].value == server_ip:
                    print(f"{server_name} (IP: {server_ip}) already in list")
                    return True
        else:
            data = nbt.NBTFile()
            data.name = "servers"
            data.tags.append(nbt.TAG_List(name="servers", type=nbt.TAG_Compound))
        servers_list = data["servers"]
        new_server = nbt.TAG_Compound()
        new_server.tags.append(nbt.TAG_String(name="name", value=server_name))
        new_server.tags.append(nbt.TAG_String(name="ip", value=f"{server_ip}"))
        new_server.tags.append(nbt.TAG_Byte(name="acceptTextures", value=1))
        servers_list.tags.append(new_server)

        with open(servers_dat, "wb") as f:
            data.write_file(buffer=f)
            return True
    except:
        print(f"Error adding server")
        return False

def authenticate_ely_by(username, password, totp_token=None, client_token=None):
    payload = {
        "username": username,
        "requestUser": True
    }

    if totp_token:
        payload["password"] = f"{password}:{totp_token}"
    else:
        payload["password"] = password

    if client_token is None:
        client_token = str(uuid.uuid4())

    payload["clientToken"] = client_token

    try:
        response = requests.post(
            AUTH_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Авторизация успешна! Привет, {data['selectedProfile']['name']}")
            return {
                "success": True,
                "username": data["selectedProfile"]["name"],
                "uuid": data["selectedProfile"]["id"],
                "access_token": data["accessToken"],
                "client_token": data["clientToken"]
            }

        elif response.status_code == 401:
            try:
                error_data = response.json()
                error_msg = error_data.get("errorMessage", "")
            except:
                error_msg = "Неверный email или пароль"

            if "two factor auth" in error_msg.lower():
                return {
                    "success": False,
                    "error": "2FA_REQUIRED",
                    "errorMessage": "Требуется код двухфакторной аутентификации"
                }
            else:
                return {
                    "success": False,
                    "error": "INVALID_CREDENTIALS",
                    "errorMessage": "Неверный email или пароль"
                }
        else:
            return {
                "success": False,
                "error": f"HTTP_{response.status_code}",
                "errorMessage": f"Ошибка сервера: {response.status_code}"
            }
    except Exception as e:
        return {"success": False, "error": "UNKNOWN", "errorMessage": f"Ошибка: {str(e)}"}

def main():
    global df, df_loaded, versions_data

    minecraft_process = None

    # Проверяем и скачиваем authlib-injector при запуске
    authlib_path = download_authlib_injector()
    if not authlib_path:
        print("ВНИМАНИЕ: Minecraft может не запуститься без authlib-injector!")

    def on_closing():
        save_settings(path_input_text, username_input_text, password_input_text,
                      version_select.get(), theme_switch.get())
        window.destroy()
        os._exit(0)

    def browse_folder():
        folder_path = filedialog.askdirectory(initialdir=minecraft_launcher_lib.utils.get_minecraft_directory()).replace("/", "\\")
        if folder_path:
            path_entry.delete(0, END)
            path_entry.insert(0, folder_path)
            path_input_text.set(folder_path)

    def open_register():
        webbrowser.open("https://ely.by/register")

    def open_forgot_password():
        webbrowser.open("https://ely.by/password/reset")

    def change_theme(choice):
        ctk.set_appearance_mode(choice)
        save_settings(path_input_text, username_input_text, password_input_text,
                      version_select.get(), choice)

    def install_task():
        if not df_loaded:
            print("Подождите, данные о версиях еще загружаются...")
            return
        threading.Thread(target=install, daemon=True).start()

    def install():
        global df
        try:
            minecraft_directory = path_entry.get()
            if minecraft_directory == "":
                minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()

            if df.empty:
                print("Ошибка: Данные о версиях не загружены")
                return

            selected_version = version_select.get()
            version_info = get_version_data(selected_version)

            if not version_info:
                dfrow = df[df['name'] == selected_version]
                if dfrow.empty:
                    print(f"Ошибка: Версия '{selected_version}' не найдена")
                    return

                row = dfrow.iloc[0]
                modloader = row['modloader'] if 'modloader' in df.columns else 'neoforge'
                minecraft_version = row['minecraft_version'] if 'minecraft_version' in df.columns else '1.21.1'
                modloader_version = row['modloader_version'] if 'modloader_version' in df.columns else '21.1.221'
            else:
                modloader = version_info.get('modloader', 'neoforge')
                minecraft_version = version_info.get('minecraft_version', '1.21.1')
                modloader_version = version_info.get('modloader_version', '21.1.221')

            print("Used path:")
            print(minecraft_directory)
            print(f"Modloader: {modloader}")
            print(f"Minecraft version: {minecraft_version}")
            print(f"Modloader version: {modloader_version}")

            loader = minecraft_launcher_lib.mod_loader.get_mod_loader(modloader)
            minecraft_launcher_lib.install.install_minecraft_version(minecraft_version, minecraft_directory, callback={"setStatus": print})
            command = minecraft_launcher_lib.command.get_minecraft_command(minecraft_version, minecraft_directory, minecraft_launcher_lib.utils.generate_test_options())
            loader.install(minecraft_version, minecraft_directory, loader_version=modloader_version, callback={"setStatus": print}, java=command[0])

            modpack(selected_version, path_input_text.get(), df)

            if version_info and version_info.get('serv_entry'):
                add_server_to_list(minecraft_directory, selected_version, version_info['serv_entry'])
            elif 'serv_entry' in df.columns:
                serv_entry = df[df['name'] == selected_version].iloc[0]['serv_entry']
                if serv_entry:
                    add_server_to_list(minecraft_directory, selected_version, serv_entry)

            launch()
        except Exception as e:
            print(f"Ошибка установки: {e}")

    def launch():
        nonlocal minecraft_process

        if not df_loaded:
            print("Подождите, данные о версиях еще загружаются...")
            return

        save_settings(path_input_text, username_input_text, password_input_text,
                      version_select.get(), theme_switch.get())

        username = username_entry.get().strip()
        password = password_entry.get()

        if not username or not password:
            print("Ошибка: Введите email и пароль Ely.by")
            return

        print("Авторизация через Ely.by...")

        auth_result = authenticate_ely_by(username, password)

        if auth_result.get("error") == "2FA_REQUIRED":
            print(auth_result["errorMessage"])

            totp_window = ctk.CTkToplevel(window)
            totp_window.title("Двухфакторная аутентификация")
            totp_window.geometry("400x200")
            totp_window.transient(window)
            totp_window.grab_set()

            ctk.CTkLabel(totp_window, text="Введите код из приложения-аутентификатора:",
                         font=label_font).pack(pady=20)

            totp_entry = ctk.CTkEntry(totp_window, width=200, font=entry_font)
            totp_entry.pack(pady=10)

            result = {"code": None}

            def submit_totp():
                result["code"] = totp_entry.get()
                totp_window.destroy()

            ctk.CTkButton(totp_window, text="Подтвердить", command=submit_totp,
                          fg_color=accent_color, corner_radius=10).pack(pady=10)

            totp_window.wait_window()

            if result["code"]:
                auth_result = authenticate_ely_by(username, password, result["code"])

        if not auth_result["success"]:
            print(f"Ошибка авторизации: {auth_result['errorMessage']}")
            return

        print(f"Успешная авторизация! Привет, {auth_result['username']}")

        try:
            selected_version = version_select.get()
            version_info = get_version_data(selected_version)

            if version_info:
                modloader = version_info.get('modloader', 'neoforge')
                modloader_version = version_info.get('modloader_version', '21.1.221')
            else:
                dfrow = df[df['name'] == selected_version]
                if dfrow.empty:
                    print(f"Ошибка: Версия '{selected_version}' не найдена")
                    return

                row = dfrow.iloc[0]
                modloader = row['modloader'] if 'modloader' in df.columns else 'neoforge'
                modloader_version = row['modloader_version'] if 'modloader_version' in df.columns else '21.1.221'
        except Exception as e:
            print(f"Ошибка получения данных о версии: {e}")
            return

        installed_version = modloader + "-" + modloader_version

        # Используем authlib_path из глобальной переменной
        authlib_injector_path = authlib_path

        if not authlib_injector_path or not os.path.exists(authlib_injector_path):
            print(f"ОШИБКА: authlib-injector не найден по пути: {authlib_injector_path}")
            print("Пожалуйста, скачайте файл вручную:")
            print("https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.7/authlib-injector-1.2.7.jar")
            print("И положите его в папку с лаунчером")
            return

        options = {
            "username": auth_result["username"],
            "uuid": auth_result["uuid"],
            "token": auth_result["access_token"],
            "jvmArguments": [
                f"-javaagent:{authlib_injector_path}={AUTHLIB_URL}",
                "-Dauthlibinjector.noLogFile",
                "-Xmx4G",
                "-Xms2G",
                "-XX:+UseG1GC",
                "-XX:+ParallelRefProcEnabled",
                "-XX:MaxGCPauseMillis=200"
            ]
        }

        minecraft_directory = path_entry.get()
        if minecraft_directory == "":
            minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()

        try:
            final_command = minecraft_launcher_lib.command.get_minecraft_command(installed_version, minecraft_directory, options)
            print("=" * 50)
            print("Запуск Minecraft...")
            print(f"Используется версия: {installed_version}")
            print(f"Путь: {minecraft_directory}")
            print("=" * 50)

            status_label.configure(text="🟢 Запуск Minecraft... Подождите...")

            minecraft_process = subprocess.Popen(final_command, cwd=minecraft_directory,
                                                 creationflags=subprocess.CREATE_NO_WINDOW)

            def monitor_minecraft():
                minecraft_process.wait()
                status_label.configure(text="✅ Minecraft закрыт")
                print("Minecraft был закрыт")

            threading.Thread(target=monitor_minecraft, daemon=True).start()
            window.iconify()

        except Exception as e:
            print(f"Ошибка запуска: {e}")
            status_label.configure(text="❌ Ошибка запуска")

    # СОЗДАНИЕ ОКНА
    window = ctk.CTk()
    window.title("KsuSerVer Launcher v0.0.1")
    window.protocol('WM_DELETE_WINDOW', on_closing)

    try:
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            window.iconbitmap(icon_path)
    except:
        pass

    window.geometry("700x680")
    window.minsize(700, 680)

    bg_color = "#1a1a2e"
    fg_color = "#ffffff"
    accent_color = "#3b82f6"

    if PIL_AVAILABLE:
        bg_image_path = resource_path("background.png")
        if os.path.exists(bg_image_path):
            try:
                img = Image.open(bg_image_path)
                img = img.resize((700, 680), Image.Resampling.LANCZOS)
                bg_image_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(700, 680))
                bg_label = ctk.CTkLabel(window, text="", image=bg_image_ctk)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                window.bg_image = bg_image_ctk
                print("Фоновое изображение загружено")
            except Exception as e:
                print(f"Ошибка загрузки фона: {e}")
                window.configure(fg_color=bg_color)
        else:
            window.configure(fg_color=bg_color)
    else:
        window.configure(fg_color=bg_color)

    title_font = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
    label_font = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
    entry_font = ctk.CTkFont(family="Segoe UI", size=11)
    button_font = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")

    path_input_text = StringVar()
    username_input_text = StringVar()
    password_input_text = StringVar()
    version_select_text = StringVar()

    saved_theme = load_settings(path_input_text, username_input_text, password_input_text, version_select_text)
    ctk.set_appearance_mode(saved_theme)

    theme_frame = ctk.CTkFrame(window, fg_color="transparent")
    theme_frame.pack(pady=(10, 0), padx=20, anchor="ne")

    theme_label = ctk.CTkLabel(theme_frame, text="🌓 Тема:", font=label_font, text_color=fg_color)
    theme_label.pack(side="left", padx=5)

    theme_switch = ctk.CTkOptionMenu(theme_frame, values=["dark", "light", "system"],
                                     command=change_theme, width=100, height=30,
                                     corner_radius=10, fg_color=accent_color,
                                     button_color=accent_color, button_hover_color="#60a5fa")
    theme_switch.pack(side="left")
    theme_switch.set(saved_theme)

    main_frame = ctk.CTkFrame(window, fg_color="transparent", corner_radius=0)
    main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    title_label = ctk.CTkLabel(main_frame, text="KsuSerVer Launcher", font=title_font,
                               text_color="#60a5fa", fg_color="transparent")
    title_label.pack(pady=(0, 15))

    status_label = ctk.CTkLabel(main_frame, text="⚪ Готов к запуску", font=label_font,
                                text_color="#888888", fg_color="transparent")
    status_label.pack(pady=(0, 10))

    card_frame = ctk.CTkFrame(main_frame, fg_color="#0f0f1a", corner_radius=15, border_width=1, border_color=accent_color)
    card_frame.pack(fill="x", pady=(0, 15), padx=10)

    path_label = ctk.CTkLabel(card_frame, text="Путь к игре:", font=label_font,
                              text_color=fg_color, fg_color="transparent")
    path_label.pack(anchor="w", pady=(15, 5), padx=15)

    path_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
    path_frame.pack(fill="x", pady=(0, 10), padx=15)

    path_entry = ctk.CTkEntry(path_frame, textvariable=path_input_text, font=entry_font,
                              height=35, corner_radius=10,
                              border_color=accent_color, fg_color="#2a2a4a")
    path_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)

    browse_btn = ctk.CTkButton(path_frame, text="📁", command=browse_folder,
                               width=50, height=35, corner_radius=10,
                               fg_color=accent_color, hover_color="#60a5fa",
                               font=button_font)
    browse_btn.pack(side="right")

    username_label = ctk.CTkLabel(card_frame, text="Email Ely.by:", font=label_font,
                                  text_color=fg_color, fg_color="transparent")
    username_label.pack(anchor="w", pady=(5, 5), padx=15)

    username_entry = ctk.CTkEntry(card_frame, textvariable=username_input_text, font=entry_font,
                                  height=35, corner_radius=10,
                                  border_color=accent_color, fg_color="#2a2a4a")
    username_entry.pack(fill="x", pady=(0, 10), padx=15)

    password_label = ctk.CTkLabel(card_frame, text="Пароль:", font=label_font,
                                  text_color=fg_color, fg_color="transparent")
    password_label.pack(anchor="w", pady=(5, 5), padx=15)

    password_entry = ctk.CTkEntry(card_frame, textvariable=password_input_text, font=entry_font,
                                  height=35, corner_radius=10, show="*",
                                  border_color=accent_color, fg_color="#2a2a4a")
    password_entry.pack(fill="x", pady=(0, 10), padx=15)

    auth_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
    auth_frame.pack(fill="x", pady=(0, 15), padx=15)

    register_btn = ctk.CTkButton(auth_frame, text="📝 Регистрация", command=open_register,
                                 width=120, height=28, corner_radius=10,
                                 fg_color="transparent", text_color=accent_color,
                                 hover_color="#2a2a4a", font=label_font)
    register_btn.pack(side="left", padx=(0, 8))

    forgot_btn = ctk.CTkButton(auth_frame, text="🔑 Забыли пароль?", command=open_forgot_password,
                               width=120, height=28, corner_radius=10,
                               fg_color="transparent", text_color=accent_color,
                               hover_color="#2a2a4a", font=label_font)
    forgot_btn.pack(side="left")

    version_card = ctk.CTkFrame(main_frame, fg_color="#0f0f1a", corner_radius=15, border_width=1, border_color=accent_color)
    version_card.pack(fill="x", pady=(0, 15), padx=10)

    version_label = ctk.CTkLabel(version_card, text="Версия:", font=label_font,
                                 text_color=fg_color, fg_color="transparent")
    version_label.pack(anchor="w", pady=(15, 5), padx=15)

    version_select = ctk.CTkComboBox(version_card, values=["Загрузка..."], font=entry_font,
                                     height=35, corner_radius=10,
                                     border_color=accent_color, fg_color="#2a2a4a",
                                     button_color=accent_color, button_hover_color="#60a5fa")
    version_select.pack(fill="x", pady=(0, 15), padx=15)
    version_select.set("Загрузка...")

    buttons_card = ctk.CTkFrame(main_frame, fg_color="#0f0f1a", corner_radius=15, border_width=1, border_color=accent_color)
    buttons_card.pack(fill="x", pady=(0, 15), padx=10)

    buttons_frame = ctk.CTkFrame(buttons_card, fg_color="transparent")
    buttons_frame.pack(fill="x", pady=15, padx=15)

    install_btn = ctk.CTkButton(buttons_frame, text="Установить", command=install_task,
                                height=38, corner_radius=10, font=button_font,
                                fg_color=accent_color, hover_color="#60a5fa")
    install_btn.pack(side="left", padx=(0, 15), fill="x", expand=True)

    launch_btn = ctk.CTkButton(buttons_frame, text="Запустить", command=launch,
                               height=38, corner_radius=10, font=button_font,
                               fg_color=accent_color, hover_color="#60a5fa")
    launch_btn.pack(side="right", padx=(15, 0), fill="x", expand=True)

    console_card = ctk.CTkFrame(main_frame, fg_color="#0f0f1a", corner_radius=15, border_width=1, border_color=accent_color)
    console_card.pack(fill="both", expand=True, padx=10)

    console_label = ctk.CTkLabel(console_card, text="Консоль", font=label_font,
                                 text_color=fg_color, fg_color="transparent")
    console_label.pack(anchor="w", pady=(10, 5), padx=15)

    from tkinter.scrolledtext import ScrolledText
    log_frame = ctk.CTkFrame(console_card, fg_color="#0a0a14", corner_radius=10)
    log_frame.pack(fill="both", expand=True, pady=(0, 15), padx=15)

    log_area = ScrolledText(log_frame, state='normal', height=5, bg="#0a0a14", fg="#0f0",
                            font=("Consolas", 8), relief="flat", highlightthickness=1,
                            highlightcolor=accent_color, highlightbackground=accent_color, bd=0)
    log_area.pack(fill="both", expand=True, padx=2, pady=2)

    sys.stdout = TextRedirector(log_area)

    info_label = ctk.CTkLabel(main_frame, text="ℹ️ После запуска Minecraft окно лаунчера свернется",
                              font=("Segoe UI", 9), text_color="#888888", fg_color="transparent")
    info_label.pack(pady=(10, 0))

    def load_versions_async():
        global df, df_loaded, versions_data
        try:
            cached_versions, cached_data = load_versions_cache()
            if cached_versions and cached_data:
                version_select.configure(values=cached_versions)
                if version_select_text.get() and version_select_text.get() in cached_versions:
                    version_select.set(version_select_text.get())
                else:
                    version_select.set(cached_versions[0])
                versions_data = cached_data
                print(f"Загружено {len(cached_versions)} версий из кэша")
                df = pd.DataFrame({'name': cached_versions})
                df_loaded = True
                return

            print("Загрузка списка версий...")
            url = 'https://docs.google.com/spreadsheets/d/1rW6vIDIhrlXweWmcSU3eNVbSrhQjxs346XdkWJlaNUw/export?format=csv'
            df_local = pd.read_csv(url)

            version_list_local = []
            for idx, row in df_local.iterrows():
                version_name = str(row.iloc[0])
                version_list_local.append(version_name)

                version_info = {}
                for col_idx, col_name in enumerate(df_local.columns):
                    value = row.iloc[col_idx]
                    if col_idx == 0:
                        version_info['name'] = value
                    elif col_idx == 1:
                        version_info['modloader'] = value if pd.notna(value) else 'neoforge'
                    elif col_idx == 2:
                        version_info['minecraft_version'] = value if pd.notna(value) else '1.21.1'
                    elif col_idx == 3:
                        version_info['modloader_version'] = value if pd.notna(value) else '21.1.221'
                    elif col_idx == 4:
                        version_info['id_archive'] = value if pd.notna(value) else ''
                    elif col_idx == 5:
                        version_info['serv_entry'] = value if pd.notna(value) else ''

                versions_data[version_name] = version_info

            save_versions_cache(version_list_local, versions_data)

            version_select.configure(values=version_list_local)
            if version_select_text.get() and version_select_text.get() in version_list_local:
                version_select.set(version_select_text.get())
            else:
                version_select.set(version_list_local[0])
            print(f"Загружено {len(version_list_local)} версий")

            df = pd.DataFrame([{'name': v} for v in version_list_local])
            df_loaded = True

        except Exception as e:
            print(f"Ошибка загрузки версий: {e}")
            version_select.configure(values=["Ошибка загрузки"])
            version_select.set("Ошибка загрузки")
            df_loaded = False

    threading.Thread(target=load_versions_async, daemon=True).start()

    window.mainloop()

if __name__ == "__main__":
    main()