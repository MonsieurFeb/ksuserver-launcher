import os
import uuid
import requests
import json
import shutil
import threading
import zipfile
import subprocess
import sys
import webbrowser
import time
import tkinter as tk
from tkinter import filedialog
import gdown
import minecraft_launcher_lib
from nbt import nbt
import csv
import urllib.request
import math

VERSIONS_URL = 'https://docs.google.com/spreadsheets/d/1rW6vIDIhrlXweWmcSU3eNVbSrhQjxs346XdkWJlaNUw/export?format=csv'
AUTHLIB_URL = "https://authserver.ely.by"

class LauncherAPI:
    def __init__(self):
        # Global fix: Always use the root of C: to avoid Cyrillic/Admin issues in AppData
        self.minecraft_dir = "C:\\.ksulauncher"
        # Ensure directories exist
        os.makedirs(self.minecraft_dir, exist_ok=True)
        self.versions_data = []
        self.selected_version = None
        self.current_user = None
        self.USER_MODS_FILE = "user_mods.json"
        # Файлы конфигурации
        self.settings_file = os.path.join(self.minecraft_dir, "ksuserver_settings.json")
        self.versions_file = os.path.join(self.minecraft_dir, "ksuserver_versions.json")
        self.authlib_injector = self.resource_path("authlib-injector-1.2.7.jar")
        self.settings = self.load_settings()
        if not os.path.exists(self.settings_file):
            self.save_settings(self.settings)


    # Сохранение и загрузка конфигурационных файлов лаунчера
    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {"path": self.minecraft_dir, "ram": 4096}


    def save_settings(self, new_settings):
        self.settings.update(new_settings)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2)


    def load_versions_file(self, file):
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}


    def save_versions_file(self, vary, new_value, file):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(new_value, f, indent=2)


    # Вход через Ely.by или без него
    def login(self, username, password, totp=None):
        auth_pass = f"{password}:{totp}" if totp else password
        payload = {"username": username, "password": auth_pass, "requestUser": True}
        try:
            response = requests.post("https://authserver.ely.by/auth/authenticate", json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.current_user = {
                    "username": data["selectedProfile"]["name"],
                    "uuid": data["selectedProfile"]["id"],
                    "access_token": data["accessToken"]
                }
                self.save_settings({"username": username, "password": password})
                return {"success": True, "username": self.current_user["username"]}
            else:
                try: err_msg = response.json().get("errorMessage", "Ошибка входа")
                except: err_msg = "Ошибка сервера"
                return {"success": False, "error": err_msg}
        except Exception as e:
            return {"success": False, "error": str(e)}


    def logout(self):
        self.save_settings({"username": "", "password": ""})
        self.current_user = None
        return True


    def skip_login(self):
        return {"success": True, "username": "TestUser"}


    # Загрузка модпаков и модлоадеров
    def _download_modpack(self, info, game_dir, report_callback):
        if not info['id_archive']:
            return
        mods_dir = os.path.join(game_dir, "mods")
        path_text = game_dir
        output = os.path.join(path_text, "archive.zip")
        report_callback("Загрузка модов...", 60)
        gdown.download(id=info['id_archive'], output=output, quiet=True)
        if os.path.exists(output):
            report_callback("Распаковка...", 75)
            if os.path.exists(mods_dir):
                shutil.rmtree(mods_dir)
            with zipfile.ZipFile(output, 'r') as zip_ref:
                zip_ref.extractall(path_text)
            os.remove(output)


    def _download_modloader(self, info, game_dir, report_callback):
        path_text = game_dir
        output = os.path.join(path_text, "archive1.zip")
        report_callback("Загрузка модлоадера...", 40)
        gdown.download(id=info['modloader-id'], output=output, quiet=True)
        if os.path.exists(output):
            report_callback("Распаковка...", 50)
            with zipfile.ZipFile(output, 'r') as zip_ref:
                zip_ref.extractall(path_text)
            os.remove(output)


    # Основной метод установки и запуска. Поддерживает быстрый запуск
    def download_and_launch(self, version_name, report_callback, force_update=False):
        try:
            info = {}
            for v in self.versions_data:
                if version_name == v.get('name'):
                    info = v; break
            if not info:
                report_callback(f"Ошибка: Версия не найдена", 0)
                return
            game_dir = os.path.abspath(self.settings.get("path", self.minecraft_dir))+"\\"+info['name']
            loader = minecraft_launcher_lib.mod_loader.get_mod_loader(info['modloader'])
            version_id = loader.get_installed_version(info['minecraft_version'], info['modloader_version'])
            version_path = os.path.join(game_dir, "versions", version_id)
            # 1. Minecraft & Runtime (with Retry Logic for [Errno 13] Permission denied)
            if not os.path.exists(version_path) or force_update:
                report_callback("Установка Minecraft...", 10)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        minecraft_launcher_lib.install.install_minecraft_version(info['minecraft_version'], game_dir)
                        # If success, break the retry loop
                        break
                    except PermissionError as pe:
                        if attempt < max_retries - 1:
                            report_callback(f"Ожидание доступа (попытка {attempt+1}/{max_retries})...", 20)
                            time.sleep(1.5) # Wait for antivirus/system lock
                        else:
                            # Final failure suggest fix
                            err_msg = str(pe)
                            if "Permission denied" in err_msg or "WinError 5" in err_msg:
                                report_callback("ОШИБКА ДОСТУПА: Попробуйте сменить папку игры в Настройках на путь без русских букв (например, C:\\Games\\Ksu).", 0)
                                return
                            raise pe
            # 2. Install modloader (Smart Start Skip)
                if info['modloader-id']:
                    self._download_modloader(info, game_dir, report_callback)
                else:
                    report_callback("Установка загрузчика...", 40)
                    dummy_opts = minecraft_launcher_lib.utils.generate_test_options()
                    try:
                        vm = minecraft_launcher_lib.command.get_minecraft_command(info['minecraft_version'], game_dir, dummy_opts)
                        java_path = vm[0]
                    except: java_path = "java"
                    loader.install(info['minecraft_version'], game_dir, loader_version=info['modloader_version'], java=java_path)
                # Servers list — only on first install
                # try:
                #     report_callback("Загрузка списка серверов...", 75)
                #     servers_dat_path = os.path.join(game_dir, "servers.dat")
                #     gdown.download(id="1ojv4-e3R_RA8r2Ngrxg57bT2wac-dHq0", output=servers_dat_path, quiet=True)
                # except Exception:
                #     pass
            else:
                report_callback("Найден готовый клиент...", 40)
            # 3. Modpack (Smart Start Skip)
            mods_dir = os.path.join(game_dir, "mods")
            if not os.path.exists(mods_dir) or not os.listdir(mods_dir) or force_update:
                self._download_modpack(info, game_dir, report_callback)
            else:
                report_callback("Клиент готов...", 80)
            # 4. Servers entry
            if info['serv_entry']:
                self.add_server_to_list(game_dir, version_name, info['serv_entry'])
                report_callback("Загрузка серверов...", 90)
            # 5. Launch
            report_callback("Запуск игры!", 100)
            options = {
                "username": self.current_user["username"] if self.current_user else "TestUser",
                "uuid": self.current_user["uuid"] if self.current_user else str(uuid.uuid4()),
                "token": self.current_user["access_token"] if self.current_user else "token",
                "jvmArguments": [f"-javaagent:{self.authlib_injector}={AUTHLIB_URL}", "-Dauthlibinjector.noLogFile", f"-Xmx{self.settings.get('ram', 4096)}M"] if self.current_user else []
            }
            # Формирование команды запуска майна
            # warning указывает на то что переменная может быть не проинициализирована
            cmd = minecraft_launcher_lib.command.get_minecraft_command(version_id, game_dir, options)
            proc = subprocess.Popen(cmd, cwd=game_dir, creationflags=subprocess.CREATE_NO_WINDOW)
            threading.Thread(target=lambda: proc.wait(), daemon=True).start()
        except Exception as e:
            report_callback(f"Ошибка: {str(e)}", 0)


    # Выбор папки с игрой
    def pick_folder(self):
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        path = filedialog.askdirectory(initialdir=self.minecraft_dir)
        root.destroy()
        return path.replace("/", "\\") if path else None


    def open_url(self, url):
        webbrowser.open(url)


    def search_modrinth(self, query, version_name, project_type, page=1, limit=12):
        try:
            info = {}
            for v in self.versions_data:
                if version_name == v.get('name'):
                    info = v; break
            version = info['minecraft_version']
            offset = (page - 1) * limit
            # Optimized version check
            search_version = version
            if version.count('.') > 1:
                search_version = '.'.join(version.split('.')[:2])
            headers = {"User-Agent": "KsuLauncher/0.1.1"}
            # project_type can be 'resourcepack' or 'shader'
            base_url = "https://api.modrinth.com/v2/search"
            facets = f'[["project_type:{project_type}"],["versions:{version}"]]'
            url = f"{base_url}?query={query}&facets={facets}&offset={offset}&limit={limit}&index=downloads"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                return {"hits": [], "total_hits": 0, "error": f"Ошибка Modrinth: {res.status_code}"}
            data = res.json()
            # Final fallback: try base version if 0 results
            if data.get('total_hits', 0) == 0 and search_version != version:
                facets_base = f'[["project_type:{project_type}"],["versions:{search_version}"]]'
                url_base = f"{base_url}?query={query}&facets={facets_base}&offset={offset}&limit={limit}&index=downloads"
                res = requests.get(url_base, headers=headers, timeout=10)
                data = res.json()
            return data
        except Exception as e:
            return {"hits": [], "total_hits": 0, "error": f"сбой сети"}


    def install_modrinth_project(self, project_id, version_name, folder_name):
        try:
            info = {}
            for v in self.versions_data:
                if version_name == v.get('name'):
                    info = v; break
            version = info['minecraft_version']
            headers = {"User-Agent": "KsuLauncher/0.1.1"}
            # Find compatible versions
            url = f"https://api.modrinth.com/v2/project/{project_id}/version?game_versions=[\"{version}\"]"
            res = requests.get(url, headers=headers, timeout=10)
            versions = res.json()
            if not versions:
                return {"success": False, "error": "Нет совместимых версий"}
            lat = versions[0]
            file_info = next((f for f in lat['files'] if f['primary']), lat['files'][0])
            dl_url = file_info['url']
            fname = file_info['filename']
            # Target folder (resourcepacks or shaderpacks)
            game_dir = self.settings.get("path", self.minecraft_dir)+"\\"+info['name']
            target_dir = os.path.join(game_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)
            # Download
            dest = os.path.join(target_dir, fname)
            r = requests.get(dl_url, stream=True, timeout=15)
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return {"success": True, "filename": fname}
        except Exception as e:
            return {"success": False, "error": str(e)}


    # Фича добавления сервера в servers.dat
    def add_server_to_list(self, minecraft_dir: str, server_name: str, server_ip: str):
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


    # ====== MOD MANAGEMENT ======
    def _get_mods_dir(self, version_name):
        game_dir = self.settings.get("path", self.minecraft_dir)+"\\"+version_name
        return os.path.join(game_dir, "mods")


    def _load_user_mods_registry(self, version_name):
        """Returns a set of filenames that were added by the user."""
        registry_path = os.path.join(self.minecraft_dir, self.USER_MODS_FILE)+"\\"+version_name
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except: pass
        return set()


    def _save_user_mods_registry(self, version_name, registry: set):
        registry_path = os.path.join(self.minecraft_dir, self.USER_MODS_FILE)+"\\"+version_name
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(list(registry), f, indent=2)


    def get_mods_list(self, version_name):
        """Returns list of {name, filename, is_user_mod} for all .jar files in mods dir."""
        mods_dir = self._get_mods_dir(version_name)
        user_mods = self._load_user_mods_registry(version_name)
        result = []
        if not os.path.exists(mods_dir):
            return result
        actual_jars = set()
        for fname in sorted(os.listdir(mods_dir)):
            if fname.lower().endswith('.jar'):
                actual_jars.add(fname)
                result.append({
                    'name': fname.replace('.jar', '').replace('-', ' ').replace('_', ' '),
                    'filename': fname,
                    'is_user_mod': fname in user_mods
                })
        # Auto-clean stale entries from user_mods registry
        stale = user_mods - actual_jars
        if stale:
            self._save_user_mods_registry(user_mods - stale, version_name)
        return result


    def add_user_mod(self, src_path, version_name):
        """Copy a .jar file to the mods folder and register it as a user mod."""
        try:
            if not src_path or not src_path.lower().endswith('.jar'):
                return {'success': False, 'error': 'Только .jar файлы!'}
            mods_dir = self._get_mods_dir(version_name)
            os.makedirs(mods_dir, exist_ok=True)
            fname = os.path.basename(src_path)
            dest = os.path.join(mods_dir, fname)
            shutil.copy2(src_path, dest)
            registry = self._load_user_mods_registry(version_name)
            registry.add(fname)
            self._save_user_mods_registry(registry, version_name)
            return {'success': True, 'filename': fname}
        except Exception as e:
            return {'success': False, 'error': str(e)}


    def delete_user_mod(self, filename, version_name):
        """Delete a user-added mod from the mods folder."""
        try:
            registry = self._load_user_mods_registry(version_name)
            if filename not in registry:
                return {'success': False, 'error': 'Нельзя удалить мод из модпака'}
            mods_dir = self._get_mods_dir(version_name)
            path = os.path.join(mods_dir, filename)
            if os.path.exists(path):
                os.remove(path)
            registry.discard(filename)
            self._save_user_mods_registry(registry, version_name)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


    def pick_jar_file(self, version_name):
        """Open file dialog to pick a .jar file."""
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            initialdir=self._get_mods_dir(version_name),
            filetypes=[("JAR files", "*.jar")]
        )
        root.destroy()
        return path.replace("/", "\\") if path else None


    # Для работы authlib-injector в пакете
    def resource_path(self, relative_path):
        """Возвращает абсолютный путь к файлу, учитывая режим работы (exe или скрипт)."""
        try:
            # PyInstaller создает временную папку _MEIPASS и сохраняет ее путь в атрибуте sys._MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            # Если программа запущена как обычный скрипт, а не как exe, используем текущую директорию
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


    # def on_version_selected(self, version_id):
    #     """Обработка выбора версии на Python стороне"""
    #     print(f"Выбрана версия: {version_id}")
    #     return f"Выбрана версия {version_id}"


    # Получение списка версий с облака или из сохранённого файла конфигурации
    def get_versions_list(self):
        try:
            with urllib.request.urlopen(VERSIONS_URL) as response:
                content = response.read().decode('utf-8')
                csv_reader = csv.reader(content.splitlines())
                data = list(csv_reader)
                flag = True
                for row in data:
                    if flag:
                        flag = False
                    else:
                        v_info = {
                            'name': str(row[0]),
                            'modloader': row[1] if self.notnaV(row[1]) else 'neoforge',
                            'minecraft_version': row[2] if self.notnaV(row[2]) else '1.21.1',
                            'modloader_version': row[3] if self.notnaV(row[3]) else '21.1.221',
                            'id_archive': row[4] if self.notnaV(row[4]) else '',
                            'serv_entry': row[5] if self.notnaV(row[5]) else '',
                            'modloader-id': row[6] if self.notnaV(row[6]) else ''
                        }
                        self.versions_data.append(v_info)
                self.save_versions_file({}, self.versions_data, self.versions_file)
            return self.versions_data
        except:
            return self.load_versions_file(self.versions_file)


    def notnaV(self, value):
        """Аналог pd.notna() для одного значения"""
        if value is None:
            return False
        if isinstance(value, float) and math.isnan(value):
            return False
        if isinstance(value, (str, bytes)) and value == '':
            return False
        return True