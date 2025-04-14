# File Backup Application

A smart and user-friendly desktop tool to back up folders with history tracking, built with Python and Tkinter.

---

## ✨ Features

- 📁 Add multiple source–destination folder pairs
- 💾 Automatically remembers previously used folders
- 🔄 Syncs and updates only changed or new files
- ✅ Visual progress bar with real-time status
- 🖱️ Clean GUI – simple drag-and-click operation

---

## 🚀 Getting Started

### 1. Clone this repository

```bash
git clone https://github.com/v-alan-m/file_backup_application.git
cd file_backup_application
```

## 🐍 Run the app (using Python)

python backup_app.py

## 🔨 Build a Standalone .exe file
### 1. Install PyInstaller
```bash
pip install pyinstaller
```
### 2. Build the .exe file
```bash
pyinstaller --onefile --add-data "history.json;." backup_app.py
```
- The .exe will appear in the dist/ folder
- Run backup_app.exe from there



