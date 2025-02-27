import subprocess
import sys
import os
import pystray
from PIL import Image
import webbrowser

# Set up log file in the same directory as the database
db_dir = os.path.join(os.path.expanduser("~"), ".social_poster")
os.makedirs(db_dir, exist_ok=True)
log_file = open(os.path.join(db_dir, "server.log"), "w")

# Start the web server from app.py
server_process = subprocess.Popen([sys.executable, "app.py"], stdout=log_file, stderr=log_file)

# System tray icon setup
def open_browser():
    webbrowser.open("http://localhost:5001")

def stop_server():
    server_process.terminate()

def exit_app():
    stop_server()
    icon.stop()

# Determine icon path (handles both development and bundled executable cases)
if getattr(sys, 'frozen', False):
    # Running as a bundled executable (via pyinstaller)
    icon_path = os.path.join(sys._MEIPASS, "icon.png")
else:
    # Running as a script
    icon_path = "icon.png"

# Define the system tray menu
menu = (
    pystray.MenuItem("Open in Browser", open_browser),
    pystray.MenuItem("Stop Server", stop_server),
    pystray.MenuItem("Exit", exit_app),
)

# Create and run the system tray icon
icon = pystray.Icon("Social Poster", Image.open(icon_path), "Social Poster", menu)
icon.run()