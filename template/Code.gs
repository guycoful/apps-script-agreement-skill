/**
 * חתימה דיגיטלית על {{TITLE}}.
 * doGet מגיש את ההסכם + פאד חתימה. submitSignature שומר לגיליון, שומר PNG ב-Drive,
 * מייצר PDF חתום ושולח לשני הצדדים.
 */

var SHEET_NAME  = '{{SHEET_NAME}}';
var FOLDER_NAME = '{{FOLDER_NAME}}';
var OWNER_EMAIL = '{{OWNER_EMAIL}}';
var OWNER_NAME  = '{{OWNER_NAME}}';
var PROP_SHEET  = '{{PROP_PREFIX}}_SHEET_ID';
var PROP_FOLDER = '{{PROP_PREFIX}}_FOLDER_ID';
var TZ          = 'Asia/Jerusalem';

function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('{{TITLE}} · {{SENDER_NAME}}')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getFolder_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty(PROP_FOLDER);
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) {} }
  var it = DriveApp.getFoldersByName(FOLDER_NAME);
  var f = it.hasNext() ? it.next() : DriveApp.createFolder(FOLDER_NAME);
  props.setProperty(PROP_FOLDER, f.getId());
  return f;
}

function getSheet_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty(PROP_SHEET), ss = null;
  if (id) { try { ss = SpreadsheetApp.openById(id); } catch (e) { ss = null; } }
  if (!ss) {
    ss = SpreadsheetApp.create(SHEET_NAME);
    props.setProperty(PROP_SHEET, ss.getId());
    getFolder_().addFile(DriveApp.getFileById(ss.getId()));
  }
  var sh = ss.getSheets()[0];
  if (sh.getLastRow() === 0) {
    sh.appendRow(['חותמת זמן', 'שם מלא', 'ת.ז. / ח.פ.', 'טלפון', 'דוא״ל', 'כתובת',
                  'אישר תנאים', 'קישור לחתימה', 'קישור להסכם החתום', 'דפדפן']);
    sh.getRange(1, 1, 1, 10).setFontWeight('bold').setBackground('#f2f4f7');
    sh.setFrozenRows(1);
  }
  return sh;
}

function esc_(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** גוף ההסכם + בלוק החתימה, כ-HTML מוכן להמרה ל-PDF. */
function buildSignedHtml_(d, stamp) {
  var body = HtmlService.createHtmlOutputFromFile('agreement-body').getContent();
  var css =
    'body{direction:rtl;text-align:right;font-family:Arial,"Noto Sans Hebrew",sans-serif;font-size:11pt;line-height:1.6;color:#16181d;margin:28px}' +
    'h1{font-size:18pt;text-align:center;margin:0 0 4px}' +
    '.sub{text-align:center;color:#666;font-size:9.5pt;margin:0 0 16px}' +
    'h2{font-size:12.5pt;margin:16pt 0 5pt;border-bottom:1px solid #d8dbe2;padding-bottom:3pt}' +
    'p{margin:3pt 0}ul{padding-right:16pt}' +
    'table{width:100%;border-collapse:collapse;margin-top:18pt}' +
    'td{border:1px solid #c9ced8;padding:8pt;vertical-align:top;font-size:10.5pt}' +
    '.sig{max-width:230px;max-height:90px}' +
    '.meta{color:#666;font-size:9pt;margin-top:14pt;border-top:1px solid #ddd;padding-top:6pt}' +
    '.note{color:#666;font-size:8.5pt;margin-top:10pt}';

  var parties =
    '<h2>פרטי הצדדים</h2>' +
    '<p><strong>צד א:</strong> ' + OWNER_NAME + ' · דוא״ל: ' + OWNER_EMAIL + '</p>' +
    '<p><strong>צד ב:</strong> ' + esc_(d.name) + ' · ת.ז. / ח.פ. ' + esc_(d.idnum) +
    ' · טלפון ' + esc_(d.phone) + ' · דוא״ל ' + esc_(d.email) +
    (d.address ? ' · כתובת ' + esc_(d.address) : '') + '</p>' +
    '<p>הצדדים ייקראו להלן יחד "הצדדים", וכל אחד מהם לחוד "צד".</p>';

  var sig =
    '<h2>ולראיה באו הצדדים על החתום</h2>' +
    '<table><tr>' +
    '<td><strong>צד ב</strong><br>' + esc_(d.name) + ', ת.ז. / ח.פ. ' + esc_(d.idnum) + '<br><br>' +
      '<img class="sig" src="' + d.signature + '"><br>תאריך: ' + stamp + '</td>' +
    '<td><strong>צד א</strong><br>' + OWNER_NAME + '<br><br><br>' +
      'נחתם דיגיטלית<br>תאריך: ' + stamp + '</td>' +
    '</tr></table>' +
    '<p class="meta">ההסכם נחתם דיגיטלית באמצעות טופס החתימה המקוון. ' +
    'החותם אישר במפורש שקרא את ההסכם ושחתימתו הדיגיטלית מחייבת כדין חתימה מקורית (סעיף {{SIG_CLAUSE}}). ' +
    'חותמת זמן: ' + stamp + '</p>' +
    '<p class="note">נוסח זה נועד להתקשרות מוקדמת ואינו מהווה ייעוץ משפטי. לפני התקשרות מסחרית מלאה, ' +
    'ובפרט בכל הנוגע ל{{LAWYER_FOCUS}}, מומלץ שעורך דין יעבור על הנוסח.</p>';

  return '<html><head><meta charset="utf-8"><style>' + css + '</style></head><body>' +
         '<h1>{{TITLE}}</h1>' +
         '<p class="sub">{{SUBTITLE_EN}} · נחתם ביום ' + stamp + '</p>' +
         parties + body + sig + '</body></html>';
}

function submitSignature(payload) {
  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch (e) { return { ok: false, error: 'המערכת עמוסה, נסה שוב' }; }
  try {
    var d = payload || {};
    if (!d.name || !d.idnum || !d.email || !d.signature || !d.agreed) {
      return { ok: false, error: 'חסרים פרטים' };
    }
    if (String(d.email).indexOf('@') < 1) return { ok: false, error: 'דוא״ל לא תקין' };
    if (String(d.signature).indexOf('data:image/png;base64,') !== 0) {
      return { ok: false, error: 'חתימה לא תקינה' };
    }

    var now = new Date();
    var stamp = Utilities.formatDate(now, TZ, 'dd/MM/yyyy HH:mm');
    var slug = String(d.name).replace(/[^֐-תa-zA-Z0-9]+/g, '-').substring(0, 40);
    var folder = getFolder_();

    var pngBytes = Utilities.base64Decode(String(d.signature).split(',')[1]);
    var pngFile = folder.createFile(
      Utilities.newBlob(pngBytes, 'image/png', 'חתימה-' + slug + '.png'));

    var html = buildSignedHtml_(d, stamp);
    var pdfBlob = Utilities.newBlob(html, 'text/html', 'x.html')
      .getAs('application/pdf')
      .setName('{{FILE_PREFIX}}-חתום-' + slug + '.pdf');
    var pdfFile = folder.createFile(pdfBlob);

    getSheet_().appendRow([stamp, d.name, "'" + d.idnum, "'" + (d.phone || ''), d.email,
                           d.address || '', 'כן', pngFile.getUrl(), pdfFile.getUrl(),
                           (d.ua || '').substring(0, 200)]);

    MailApp.sendEmail({
      to: d.email,
      cc: OWNER_EMAIL,
      replyTo: OWNER_EMAIL,
      name: '{{SENDER_NAME}}',
      subject: '{{MAIL_SUBJECT}}',
      htmlBody:
        '<div dir="rtl" style="font-family:Arial,sans-serif;line-height:1.7;font-size:15px">' +
        'היי ' + esc_(d.name) + ',<br><br>' +
        '{{MAIL_BODY}}<br><br>' +
        '{{SIGN_OFF}}</div>',
      attachments: [pdfBlob]
    });

    return { ok: true };
  } catch (err) {
    try {
      MailApp.sendEmail(OWNER_EMAIL, 'שגיאה בחתימת {{TITLE}}',
        String(err) + '\n\n' + JSON.stringify(payload && payload.name));
    } catch (e2) {}
    return { ok: false, error: 'שגיאה בשמירה' };
  } finally {
    lock.releaseLock();
  }
}
