# XControlP · returning to version 1.0.02

This note describes a code rollback while keeping your data. It does not publish or install a release.

## Before you start

1. Close every XControlP window and stop the program.
2. Make a full copy of the current XControlP folder, including data created after the update. Keep it unchanged until the restored copy has been checked.
3. Create a separate clean copy of the previous code version. The verified 1.0.02 source is commit `6462e2bc0bbdeba4d69cf68913bc488063784b4d`:

   ```powershell
   git clone https://github.com/XThoughtLabs/XControlP.git XControlP-1.0.02-restore
   git -C XControlP-1.0.02-restore checkout --detach 6462e2bc0bbdeba4d69cf68913bc488063784b4d
   ```

   Use a different, empty folder name if that path already exists. Do not reset or overwrite the only updated copy.

## Restore and check data

Copy the data from the backup into the separate 1.0.02 folder, preserving its folder structure and **not replacing tracked program files**. User data includes `projects.json`, `translations.json`, `settings.json`, `day.db*`, `day.json`, `day-inbox/`, `day-plan-backups/`, `calendar.json`, `alerts.json`, `flags.json`, `proposals.json`, `ideas-history.json`, `ideas/`, `reports/`, `requests/`, `answers/`, and `research/`. `data.js` is generated at startup; let XControlP rebuild it. Keep `google-*.json` credentials only on your computer and copy them only if you need the calendar integration; never attach or send them.

Start XControlP from the separate restore folder. Confirm **Settings → Updates** shows `1.0.02`, then open a project, the day plan, and a report. Keep both the updated folder and its backup until these checks pass. Do not delete data created after the update: the tested 1.0.02 copy could read the synthetic project, settings, proposal, report, and day-plan data created by the candidate. Real user data and integrations were not tested here.

If the restored version cannot read the current data, stop using that copy. Keep both folders, restore a working copy from the pre-update backup, and save the post-update folder for later data recovery. Do not copy `day.db` manually while either application is running.

---

# Возврат XControlP к версии 1.0.02

Эта памятка описывает возврат к прежнему коду с сохранением данных. Она не публикует и не устанавливает выпуск.

## Перед началом

1. Закройте все окна XControlP и остановите программу.
2. Сделайте полную копию текущей папки XControlP, включая данные, созданные после обновления. Не изменяйте её, пока не проверите восстановленную копию.
3. Создайте отдельную чистую копию прежней версии кода. Проверенный исходник 1.0.02 — коммит `6462e2bc0bbdeba4d69cf68913bc488063784b4d`:

   ```powershell
   git clone https://github.com/XThoughtLabs/XControlP.git XControlP-1.0.02-restore
   git -C XControlP-1.0.02-restore checkout --detach 6462e2bc0bbdeba4d69cf68913bc488063784b4d
   ```

   Если эта папка уже существует, выберите другое пустое имя. Не сбрасывайте Git и не перезаписывайте единственную обновлённую копию.

## Восстановление и проверка данных

Скопируйте данные из резервной копии в отдельную папку версии 1.0.02, сохранив структуру и **не заменяя отслеживаемые файлы программы**. К данным относятся `projects.json`, `translations.json`, `settings.json`, `day.db*`, `day.json`, `day-inbox/`, `day-plan-backups/`, `calendar.json`, `alerts.json`, `flags.json`, `proposals.json`, `ideas-history.json`, `ideas/`, `reports/`, `requests/`, `answers/` и `research/`. `data.js` создаётся при запуске; разрешите XControlP собрать его заново. Файлы учётных данных `google-*.json` храните только на своём компьютере и копируйте только при необходимости интеграции календаря; не прикладывайте и не отправляйте их.

Запустите XControlP из отдельной папки восстановления. Убедитесь, что в **Настройки → Обновления** указано `1.0.02`, затем откройте проект, План дня и отчёт. Сохраняйте обновлённую папку и её резервную копию, пока проверки не пройдут. В тесте версия 1.0.02 прочитала созданные кандидатом синтетические данные проекта, настроек, предложения, отчёта и плана дня. Настоящие данные пользователя и интеграции здесь не проверялись.

Если прежняя версия не читает текущие данные, остановитесь. Сохраните обе папки, восстановите рабочую копию из резервной копии до обновления, а папку после обновления оставьте для дальнейшего извлечения данных. Не копируйте `day.db` вручную, пока запущено любое из приложений.

---

# החזרת XControlP לגרסה 1.0.02

ההנחיות האלה מחזירות את קוד התוכנה תוך שמירה על הנתונים. הן אינן מפרסמות או מתקינות גרסה.

## לפני שמתחילים

1. סגרו את כל חלונות XControlP והפסיקו את התוכנה.
2. צרו עותק מלא של תיקיית XControlP הנוכחית, כולל נתונים שנוצרו אחרי העדכון. השאירו אותו ללא שינוי עד לבדיקת העותק המשוחזר.
3. צרו עותק נקי ונפרד של קוד הגרסה הקודמת. המקור שנבדק עבור 1.0.02 הוא commit `6462e2bc0bbdeba4d69cf68913bc488063784b4d`:

   ```powershell
   git clone https://github.com/XThoughtLabs/XControlP.git XControlP-1.0.02-restore
   git -C XControlP-1.0.02-restore checkout --detach 6462e2bc0bbdeba4d69cf68913bc488063784b4d
   ```

   אם התיקייה הזאת כבר קיימת, בחרו שם אחר לתיקייה ריקה. אל תאפסו את Git ואל תדרסו את העותק המעודכן היחיד.

## שחזור ובדיקת נתונים

העתיקו את הנתונים מהגיבוי לתיקיית 1.0.02 הנפרדת, תוך שמירה על מבנה התיקיות ו**בלי להחליף קובצי תוכנה שנמצאים במעקב Git**. הנתונים כוללים `projects.json`, `translations.json`, `settings.json`, `day.db*`, `day.json`, `day-inbox/`, `day-plan-backups/`, `calendar.json`, `alerts.json`, `flags.json`, `proposals.json`, `ideas-history.json`, `ideas/`, `reports/`, `requests/`, `answers/` ו-`research/`. `data.js` נוצר מחדש בעת ההפעלה; תנו ל-XControlP לבנות אותו. שמרו קובצי הרשאות `google-*.json` רק במחשב שלכם והעתיקו אותם רק אם דרושה לכם אינטגרציית היומן; לעולם אל תצרפו או תשלחו אותם.

הפעילו את XControlP מתוך תיקיית השחזור הנפרדת. ודאו שב**הגדרות ← עדכונים** מופיעה `1.0.02`, ואז פתחו פרויקט, את תוכנית היום ודוח. שמרו את התיקייה המעודכנת ואת הגיבוי שלה עד שהבדיקות יצליחו. בבדיקה, גרסה 1.0.02 קראה נתונים סינתטיים של פרויקט, הגדרות, הצעה, דוח ותוכנית יום שנוצרו על ידי המועמד. נתוני משתמש אמיתיים ואינטגרציות לא נבדקו.

אם הגרסה הקודמת אינה קוראת את הנתונים הנוכחיים, עצרו. שמרו את שתי התיקיות, שחזרו עותק עובד מהגיבוי שלפני העדכון והשאירו את התיקייה שאחריו לצורך חילוץ נתונים בהמשך. אל תעתיקו `day.db` ידנית בזמן שאחת מהתוכנות פועלת.
