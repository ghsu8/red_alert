# Red Alert Desktop Notifier (Windows)

אפליקציית שולחן עבודה להצגת התראות פיקוד העורף בצד הימני של המסך.

## התקנה

### אפשרות 1: בעזרת Installer (מומלץ למשתמשים)

1. הורד את ה-installer: `RedAlert_Setup_1.0.0.exe`
2. הרץ את ה-installer
3. בחר מיקום התקנה
4. בחר אם ברצונך קיצור דרך בשולחן העבודה
5. סיים את ההתקנה
6. אפליקציה מוכנה להשימוש - הפעל מתוך קיצור הדרך או Start Menu

**לא נדרשת התקנה של Python או תלויות נוספות!**

### אפשרות 2: בעזרת Python (למפתחים)

1. וודא שיש לך Python 3.11+ מותקן.
2. התקן את התלויות:

```powershell
pip install -r requirements.txt
```

3. הרץ את האפליקציה:

```powershell
python main.py
```

## בניית Installer (עבור מפתחים)

כדי ליצור installer חדש:

1. הרץ את `build_installer.bat`
2. זה ייצור את קובץ ה-`.exe` הסטנדלון
3. התקן את NSIS מ-https://nsis.sourceforge.io
4. פתח `RedAlert_Installer.nsi` ב-NSIS
5. לחץ "Compile NSI Scripts"

לפרטים מלאים, ראה [BUILDING.md](BUILDING.md)

## יכולות מרכזיות

- הצגת פופאפ בצד ימין (Edge Notification) עם פינות מעוגלות.
- צבע התראה משתנה לפי סוג: טילים, כלי טיס, אירוע שהסתיים.
- ניתן לבחור צליל, שקט או קובץ מותאם אישית.
- תמיכה בסינון לפי אזור/עיר ונקודת יחס (POI) עם מרחק.
- מערכת אחסון הגדרות JSON ב-`%APPDATA%/RedAlert/config.json`.
- ריצה ברקע דרך System Tray.
- אפשרות הפעלה אוטומטית עם מערכת ההפעלה.

## אריזות (Packaging)

האפליקציה מוגדרת לעבודה עם `pyinstaller`:

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

אם ברצונך להיות בטוח שהאיקון יופיע, תוכל לספק קובץ `.ico` ולהכניס אותו ל-`TrayIcon`.
