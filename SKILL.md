---
name: apps-script-agreement
description: Build a Hebrew (RTL) digital-signature page for an agreement on Google Apps Script. The page shows the agreement, a signer form and a signature pad. On submit it saves a signed PDF and the signature PNG to Drive, adds a row to a Sheet, and emails the PDF to the signer with a copy to you. Use when asked for "הסכם לחתימה", "דף חתימה", "הסכם ב-Apps Script", or an online signature on an agreement. Also deploys the page to Apps Script (create, update an existing deployment, return the /exec link) when asked to "פרוס", "העלה ל-Apps Script" or "עדכן את הקישור".
---

# הסכם לחתימה דיגיטלית ב-Apps Script

## מה הדף עושה
החותם פותח קישור. הוא רואה את ההסכם המלא, ומתחתיו טופס: שם, ת.ז. או ח.פ., טלפון, דוא"ל, כתובת, תיבת אישור ופאד חתימה.
`submitSignature` בשרת:
- שומר PNG של החתימה בתיקייה בדרייב.
- בונה PDF חתום עם פרטי הצדדים ובלוק החתימה.
- מוסיף שורה לגיליון.
- שולח את ה-PDF לחותם, עם עותק אליך.
התיקייה והגיליון נוצרים בהרצה הראשונה, והמזהים שלהם נשמרים ב-Script Properties.

## שלב 1: הנוסח, לפני כל קוד
1. כל תנאי חייב מקור: הבעלים, הצעה שאושרה, תמלול או מסמך. פרט חסר נכתב `[להשלים]`, ולא ממציאים.
2. גוף ההסכם נכתב בקובץ `agreement-body.html`: `<h2>` לכל סעיף, `<p>` עם מספור "1.1.", ו-`<ul>` או `<table>` לפי הצורך. בלי `<html>` ובלי סגנון. דוגמה: `examples/agreement-body.html`.
3. סעיפים שכדאי לבדוק בכל הסכם:
   - מי הצד המתקשר.
   - מחיר מדויק, "מחיר סופי, ללא תוספות".
   - מה כלול ומה לא כלול.
   - לוחות זמנים.
   - בעלות: מה שנבנה ללקוח שייך ללקוח, וכלים וידע כללי נשארים אצלך.
   - סודיות.
   - היעדר התחייבות לתוצאה.
   - שירותי צד שלישי.
   - חתימה דיגיטלית מחייבת.
   - דין חל.
   - שורה בסוף: "נוסח זה אינו מהווה ייעוץ משפטי".
4. לפני שמראים לבעלים, קוראים מנקודת המבט של הצד השני. האם יש סעיף שלא סוכם? האם משהו מחייב מעבר למה שנאמר?

## שלב 2: יצירת הקבצים
```bash
python3 build.py config.json agreement-body.html OUT_DIR
```
`config.json` מכיל 15 שדות. הדוגמה: `examples/config.json`.

| שדה | מה זה |
|---|---|
| TITLE | כותרת ההסכם |
| OWNER_NAME | השם המשפטי שלך, כפי שיופיע ב-PDF |
| OWNER_EMAIL | לכאן מגיע עותק של כל הסכם חתום, וגם הודעות שגיאה |
| SENDER_NAME, SIGN_OFF | שם השולח במייל, והחתימה בסוף המייל |
| SHEET_NAME, FOLDER_NAME | שמות ייחודיים לכל הסכם |
| PROP_PREFIX | באנגלית, ייחודי לכל הסכם |
| SIG_CLAUSE | מספר הסעיף של החתימה הדיגיטלית בגוף ההסכם |
| LAWYER_FOCUS | על מה עורך הדין צריך להסתכל, בשורה שבתחתית ה-PDF |
| SUBTITLE_EN, FILE_PREFIX, MAIL_SUBJECT, MAIL_BODY, FOOTER | טקסטים לכותרת המשנה, לשם קובץ ה-PDF, למייל ולתחתית הדף |

הסקריפט עוצר אם חסר שדה או אם נשאר משתנה בקבצים. הוא מזהיר על `[להשלים]`, ועל סעיף חתימה שלא נמצא בגוף ההסכם.

## שלב 3: פריסה
דרך הסקריפט, בלי לגעת בעורך:
```bash
export APPS_SCRIPT_TOKEN_CMD="<פקודה שמדפיסה access token>"   # או APPS_SCRIPT_TOKEN. הטוקן לא עובר בצ'אט
python3 deploy.py OUT_DIR --title "שם ההסכם"
```
הסקריפט יוצר פרויקט, מעלה את 4 הקבצים, יוצר גרסה ופורס Web app (Execute as: Me, Who has access: Anyone). הפלט הוא קישור `/exec`, ו-`OUT_DIR/.deploy.json` שומר את המזהים. כדאי להריץ קודם עם `--dry-run`, שמדפיס את הקריאות בלי לשלוח.
דרישות: Apps Script API פעיל ב-script.google.com/home/usersettings, וטוקן עם הסקופים script.projects ו-script.deployments.

### עדכון אחרי שינוי
```bash
python3 build.py config.json agreement-body.html OUT_DIR
python3 deploy.py OUT_DIR
```
כשיש `.deploy.json` או `--script-id`, הסקריפט מעלה את הקבצים, יוצר גרסה חדשה ומעדכן את אותו דיפלוימנט. הקישור `/exec` נשאר. בפרויקט שנפרס ידנית: `--script-id ID`, ואם יש כמה דיפלוימנטים גם `--deployment-id ID`.

### פריסה ידנית (בלי API)
בעורך, ב-script.google.com:
1. פרויקט חדש. מדביקים את `Code.gs`.
2. מוסיפים 2 קובצי HTML, בשמות `index` ו-`agreement-body`, בלי סיומת.
3. ב-Project Settings מסמנים "Show appsscript.json", ומחליפים את התוכן.
4. בוחרים בפונקציה `doGet`, לוחצים Run ומאשרים הרשאות. פונקציות שנגמרות בקו תחתון, כמו `getFolder_`, לא מופיעות ברשימה.
5. Deploy, ואז New deployment. Type: Web app. Execute as: Me. Who has access: Anyone.

## מלכודות
| תקלה | סיבה | פתרון |
|---|---|---|
| 403 על קישור /exec חדש | הבעלים עוד לא אישר הרשאות | בעורך: Run על `doGet`, לאשר הרשאות, ולנסות שוב |
| שינוי נשמר ולא מופיע בקישור | שמירה לא משנה את /exec | `deploy.py` שוב, או Manage deployments, Edit, New version |
| קישור השתנה | נוצר דיפלוימנט חדש | לעדכן את הקיים: `deploy.py` עם `.deploy.json` |
| שגיאת API 403 על Apps Script API | ה-API כבוי בחשבון | להפעיל ב-script.google.com/home/usersettings |
| גוף ההסכם שונה בין התצוגה ל-PDF | הנוסח קיים ב-`index.html` וב-`agreement-body.html` | `build.py` מסנכרן. בעריכה ידנית לתקן בשניהם |

## שלב 5: בדיקה לפני שליחה
אחרי הפריסה חותמים בעצמך, עם המייל שלך, על הקישור `/exec`. בודקים 4 דברים:
- נוצר PNG.
- נוצר PDF קריא בעברית מימין לשמאל, עם כל הסעיפים.
- נוספה שורה בגיליון.
- הגיע מייל עם קובץ מצורף.
"עובד" רק אחרי הבדיקה הזו, לא כשהדף נטען ולא כשהסקריפט הדפיס קישור. אחרי הבדיקה מוחקים את שורת הבדיקה מהגיליון. לא שולחים את הקישור לחותם לפני האישור של הבעלים.
