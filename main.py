#!/usr/bin/env python3
#pyinstaller --onefile --windowed --add-binary "authlib-injector-1.2.7.jar;." main.py - команда создания exe файла
import pandas as pd
import json
import os
import shutil
import threading
import zipfile
from tkinter import Tk, Label, Entry, Button, mainloop, StringVar, END, filedialog
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Combobox
import gdown
import minecraft_launcher_lib
import subprocess
import sys
from nbt import nbt
import requests

# versions = {
#     "KsuSerVer Season 2": ("neoforge", "1.21.1", "21.1.221", "")
# }

# servers = {
#     "KsuSerVer Season 2": ("KsuSerVer", "")
# }

# Фича сохранения полей в файл
SETTINGS_FILE = minecraft_launcher_lib.utils.get_minecraft_directory()+"\\ksuserver_settings.json"

# Фича сохранения полей в файл
def save_settings(path_input_text, username_input_text, password_input_text, version_select_text):
    """Сохраняет данные из полей ввода в JSON файл."""
    data = {
        "path": path_input_text.get(),
        "username": username_input_text.get(),
        "password": password_input_text.get(),
        "version": version_select_text
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)


# Фича сохранения полей в файл
def load_settings(path_input_text, username_input_text, password_input_text, version_select_text):
    """Загружает данные из JSON файла при запуске."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                data = json.load(f)
                path_input_text.set(data.get("path", ""))
                username_input_text.set(data.get("username", ""))
                password_input_text.set(data.get("password", ""))
                version_select_text.set(data.get("version", ""))
            except json.JSONDecodeError:
                pass  # Если файл поврежден, оставляем пустым


# Фича установки модпака
def modpack(version_select, path_input_text, df):
    # modloader, minecraft_version, modloader_version, id_archive = versions[version_select.get()]
    dfrow = df.loc[df['name'] == version_select.get()]
    name_m, modloader, minecraft_version, modloader_version, id_archive, serv_entry = tuple(dfrow.itertuples(index=False, name=None))[0]
    output = path_input_text.get()+"\\archive.zip"

    # Скачивание файла
    print("Download modpack...")
    gdown.download(id=id_archive, output=output, quiet=False)

    # Распаковка архива
    if os.path.exists(output):
        if os.path.exists(path_input_text.get()+"\\mods"):
            shutil.rmtree(path_input_text.get()+"\\mods")
        print("Unpack...")
        with zipfile.ZipFile(output, 'r') as zip_ref:
            zip_ref.extractall(path_input_text.get()) # Папка для распаковки
        print("Ready!")
        # Удаление архива после распаковки
        os.remove(output)
    else:
        print("The archive was not downloaded.")

# Фича консоль в окне
class TextRedirector(object):
    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        self.widget.insert(END, string)
        self.widget.see(END) # Автопрокрутка вниз

    def flush(self):
        pass


# Для работы authlib-injector в пакете
def resource_path(relative_path):
    """Возвращает абсолютный путь к файлу, учитывая режим работы (exe или скрипт)."""
    try:
        # PyInstaller создает временную папку _MEIPASS и сохраняет ее путь в атрибуте sys._MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Если программа запущена как обычный скрипт, а не как exe, используем текущую директорию
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Фича добавления сервера в servers.dat
def add_server_to_list(minecraft_dir: str, server_name: str, server_ip: str):
    try:
        servers_dat = os.path.join(minecraft_dir, "servers.dat")
        # Читаем существующий файл или создаем новый
        if os.path.exists(servers_dat):
            with open(servers_dat, "rb") as f:
                data = nbt.NBTFile(buffer=f)
            servers_list = data["servers"]
            # Проверяем, не добавлен ли уже такой сервер
            for server in servers_list.tags:
                if server["ip"].value == server_ip:
                    print(f"{server_name} (IP: {server_ip}) already in list")
                    return True
        else:
            data = nbt.NBTFile()
            data.name = "servers"
            data.tags.append(nbt.TAG_List(name="servers", type=nbt.TAG_Compound))
        # Получаем список серверов
        servers_list = data["servers"]
        # Создаем новую запись о сервере
        new_server = nbt.TAG_Compound()
        new_server.tags.append(nbt.TAG_String(name="name", value=server_name))
        new_server.tags.append(nbt.TAG_String(name="ip", value=f"{server_ip}"))
        new_server.tags.append(nbt.TAG_Byte(name="acceptTextures", value=1))
        # Добавляем в список
        servers_list.tags.append(new_server)

        with open(servers_dat, "wb") as f:
            data.write_file(buffer=f)
            return True
    except:
        print(f"Error adding server")
        return False


def main():
    # Событие закрытия окна
    def on_closing():
        window.destroy()
        os._exit(0) # жёсткий выход

    # Фича выбора директории
    def browse_folder():
        folder_path = filedialog.askdirectory(initialdir=minecraft_launcher_lib.utils.get_minecraft_directory()).replace("/", "\\")
        if folder_path:
            # Очищаем Entry и вставляем путь
            path_input.delete(0, END)
            path_input.insert(0, folder_path)
            path_input_text.set(folder_path)

    # Действие кнопки установки
    def install_task():
        threading.Thread(target=install, daemon=True).start() # daemon означает, что этот подпроцесс завершится, если будет закрыто основное окно

    def install():
        # Тестовые данные и лицензионный логин
        #minecraft_launcher_lib.install.install_minecraft_version(version_select.get(), minecraft_directory, callback=callback)
        #login_data = minecraft_launcher_lib.account.login_user(username_input.get(), password_input.get())
        #options = minecraft_launcher_lib.utils.generate_test_options()

        minecraft_directory = path_input.get()
        if path_input.get() == "":
            minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()

        # modloader, minecraft_version, modloader_version, id_archive = versions[version_select.get()]
        dfrow = df.loc[df['name'] == version_select.get()]
        name_m, modloader, minecraft_version, modloader_version, id_archive, serv_entry = tuple(dfrow.itertuples(index=False, name=None))[0]

        print("Used path:")
        print(minecraft_directory)

        loader = minecraft_launcher_lib.mod_loader.get_mod_loader(modloader)
        minecraft_launcher_lib.install.install_minecraft_version(minecraft_version, minecraft_directory, callback={"setStatus": print})
        command = minecraft_launcher_lib.command.get_minecraft_command(minecraft_version, minecraft_directory, minecraft_launcher_lib.utils.generate_test_options())
        loader.install(minecraft_version, minecraft_directory, loader_version=modloader_version, callback={"setStatus": print}, java=command[0])

        modpack(version_select, path_input_text, df)

        if serv_entry:
            add_server_to_list(minecraft_directory, name_m, serv_entry)

        launch()


    # Действие кнопки запуска
    def launch():
        save_settings(path_input_text, username_input_text, password_input_text, version_select.get())

        # modloader, minecraft_version, modloader_version, id_archive = versions[version_select.get()]
        dfrow = df.loc[df['name'] == version_select.get()]
        name_m, modloader, minecraft_version, modloader_version, id_archive, serv_entry = tuple(dfrow.itertuples(index=False, name=None))[0]

        #print(installed_version) # neoforge-21.1.222
        installed_version = modloader+"-"+modloader_version

        payload = {
            "username": username_input.get(),      # Email или никнейм
            "password": password_input.get(),      # Пароль, для двухфакторки "пароль:токен"
            "requestUser": True                    # Запрашиваем доп. информацию
            #"clientToken": client_token,          # Уникальный токен
        }

        # Отправляем запрос Ely.by (по-хорошему - сделать через OAuth)
        response = requests.post(
            "https://authserver.ely.by/auth/authenticate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        # Применение https://github.com/yushijinhun/authlib-injector
        authlib_injector_path = resource_path("authlib-injector-1.2.7.jar")
        elyby_api_url = "https://authserver.ely.by"

        # Обрабатываем ответ Ely.by
        if response.status_code == 200:
            data = response.json()
            options:minecraft_launcher_lib.types.MinecraftOptions = {
                "username": data["selectedProfile"]["name"],
                "uuid": data["selectedProfile"]["id"],
                "token": data["accessToken"],
                'jvmArguments': [
                    f"-javaagent:{authlib_injector_path}={elyby_api_url}",  # путь к authlib-injector
                    "-Dauthlibinjector.noLogFile"  # отключает создание лог-файла authlib-injector
                ]
            }
        # javaagent_argument = f"-javaagent:{authlib_injector_path}={elyby_api_url}"
        # final_command = [base_command[0], javaagent_argument] + base_command[1:]

        minecraft_directory = path_input.get()
        if path_input.get() == "":
            minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()

        # Формирование команды запуска майна
        # warning указывает на то что переменная может быть не проинициализирована
        final_command = minecraft_launcher_lib.command.get_minecraft_command(installed_version, minecraft_directory, options)
        window.withdraw()

        # cwd - переносит логи в рабочую папку, creationflags - убирает консольку во вложенном процессе
        subprocess.run(final_command, cwd=minecraft_directory, creationflags=subprocess.CREATE_NO_WINDOW)
        # sys.exit(0) # обычный выход
        os._exit(0) # жёсткий выход

    window = Tk()
    window.title("KsuSerVer Launcher v0.0.1")
    window.protocol('WM_DELETE_WINDOW', on_closing)

    # Фича сохранения полей в файл
    path_input_text = StringVar()
    username_input_text = StringVar()
    password_input_text = StringVar()
    version_select_text = StringVar()
    load_settings(path_input_text, username_input_text, password_input_text, version_select_text)

    # Разметка приложения
    Label(window, text="Path:").grid(row=0, column=0)
    path_input = Entry(window, textvariable=path_input_text, width=50)
    path_input.grid(row=0, column=1)
    Button(window, text="Выбрать папку", command=browse_folder).grid(row=0, column=2)
    Label(window, text="Username:").grid(row=1, column=0)
    username_input = Entry(window, textvariable=username_input_text, width=50)
    username_input.grid(row=1, column=1)
    Label(window, text="Password:").grid(row=2, column=0)
    password_input = Entry(window, textvariable=password_input_text, width=50)
    password_input.grid(row=2, column=1)

    # versions = minecraft_launcher_lib.utils.get_available_versions(minecraft_directory)
    version_list = []

    # Достаём список версий и актуальные модпаки по документу на диске
    url = 'https://docs.google.com/spreadsheets/d/1rW6vIDIhrlXweWmcSU3eNVbSrhQjxs346XdkWJlaNUw/export?format=csv'
    df = pd.read_csv(url)
    for i in df.itertuples():
        # version_list.append(i["id"])
        version_list.append(i[1])

    Label(window, text="Version:").grid(row=3, column=0)
    version_select = Combobox(window, values=version_list, width=47, state="readonly")
    version_select.grid(row=3, column=1)
    version_select.current(0)

    version_select.set(version_select_text.get())

    Button(window, text="Launch", command=launch).grid(row=3, column=2)
    Button(window, text="Install+Launch", command=install_task).grid(row=1, column=2)

    # Фича консоль в окне
    log_area = ScrolledText(window, state='normal', width=60, height=7)
    log_area.grid(row=4, column=0, columnspan=3)
    # Перенаправление stdout
    sys.stdout = TextRedirector(log_area)

    Label(window, text="Ctrl+C Ctrl+V работают только с английской раскладкой").grid(row=5, column=0, columnspan=3)
    Label(window, text="Если долго не грузит - попробуйте сервис на 3 буквы").grid(row=6, column=0, columnspan=3)

    mainloop()


if __name__ == "__main__":
    main()