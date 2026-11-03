#!/usr/bin/env python3
"""build.py <config.json> <agreement-body.html> <out_dir>
מייצר את 4 קובצי דף החתימה (Code.gs, index.html, agreement-body.html, appsscript.json)
מהתבנית שבתיקייה template, לפי config. לא פורס ולא שולח."""
import json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REQ = ['TITLE','SHEET_NAME','FOLDER_NAME','OWNER_NAME','PROP_PREFIX','SIG_CLAUSE','LAWYER_FOCUS',
       'SUBTITLE_EN','FILE_PREFIX','MAIL_SUBJECT','MAIL_BODY','FOOTER','OWNER_EMAIL','SENDER_NAME','SIGN_OFF']
def main(cfg_p, body_p, out):
    cfg = json.load(open(cfg_p, encoding='utf-8'))
    miss = [k for k in REQ if not cfg.get(k)]
    if miss: sys.exit('חסרים שדות בקונפיג: ' + ', '.join(miss))
    body = open(body_p, encoding='utf-8').read().strip()
    if '[להשלים]' in body: print('אזהרה: בגוף ההסכם יש [להשלים]. מותר לבדיקה עצמית בלבד, לא לשליחה.')
    if not re.search(r'סעיף\s*' + re.escape(cfg['SIG_CLAUSE']) + r'|^<p>' + re.escape(cfg['SIG_CLAUSE']) + r'\.', body, re.M):
        print(f"אזהרה: לא נמצא בגוף ההסכם סעיף {cfg['SIG_CLAUSE']} (חתימה דיגיטלית). בדוק את SIG_CLAUSE.")
    os.makedirs(out, exist_ok=True)
    js = lambda s: s.replace('\\', '\\\\').replace("'", "\\'")
    for name in ['Code.gs', 'index.html']:
        t = open(os.path.join(HERE, 'template', name), encoding='utf-8').read()
        for k in REQ:
            t = t.replace('{{%s}}' % k, js(cfg[k]) if name == 'Code.gs' else cfg[k])
        t = t.replace('{{BODY}}', body)
        left = re.findall(r'\{\{\w+\}\}', t)
        if left: sys.exit(f'{name}: נשארו משתנים {left}')
        open(os.path.join(out, name), 'w', encoding='utf-8').write(t)
    shutil.copy(os.path.join(HERE, 'template', 'appsscript.json'), out)
    open(os.path.join(out, 'agreement-body.html'), 'w', encoding='utf-8').write(body + '\n')
    print('נוצרו 4 קבצים ב-' + out)
if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
