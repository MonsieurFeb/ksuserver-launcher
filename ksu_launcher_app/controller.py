import threading
import eel
from model import LauncherAPI

launcher = LauncherAPI()

@eel.expose
def login(username, password, totp=None):
    return launcher.login(username, password, totp)

@eel.expose
def skip_login():
    return launcher.skip_login()

@eel.expose
def get_settings():
    return launcher.load_settings()

@eel.expose
def save_settings(new_settings):
    launcher.save_settings(new_settings)

@eel.expose
def start_launch(version_name):
    def report(text, p):
        eel.update_status(text, p)()
    threading.Thread(target=launcher.download_and_launch, args=(version_name, report), daemon=True).start()

@eel.expose
def update_modpack(version_name):
    def report(text, p):
        eel.update_status(text, p)()
    threading.Thread(target=launcher.download_and_launch, args=(version_name, report, True), daemon=True).start()

@eel.expose
def pick_folder():
    return launcher.pick_folder()

@eel.expose
def open_url(url):
    launcher.open_url(url)

@eel.expose
def search_modrinth(query, version, project_type, page):
    return launcher.search_modrinth(query, version, project_type, page)

@eel.expose
def install_modrinth(project_id, version, folder_name):
    return launcher.install_modrinth_project(project_id, version, folder_name)

@eel.expose
def logout():
    return launcher.logout()

@eel.expose
def get_versions_list():
    return launcher.get_versions_list()

# @eel.expose
# def on_version_selected(version):
#     return launcher.on_version_selected(version)


# Initialize Eel with the web directory
eel.init(launcher.resource_path('view'))
print("KsuLauncher started. Port conflict protection enabled.")
# Robust startup logic to find a suitable browser
# Chrome and Edge are prioritized for standalone window mode.
# Default is the safe fallback.
for browser in ['chrome', 'msedge', 'edge', 'default']:
    try:
        print(f"Starting KsuLauncher in {browser} mode...")
        eel.start('index.html', size=(900, 700), port=0, mode=browser)
        # If eel.start returns, the window was closed normally. 
        # We exit the loop and the script.
        break
    except OSError:
        # This occurs ONLY if the browser executable is not found.
        print(f"{browser} not found, trying next option...")
        continue
    except SystemExit:
        # Standard Eel/Bottle closure behavior.
        break