#!/usr/bin/env python3
"""deploy.py <out_dir> [--script-id ID] [--deployment-id ID] [--title T] [--description D] [--dry-run]
פורס את 4 הקבצים שמייצר build.py ל-Apps Script דרך ה-API, ומחזיר קישור /exec.
  בלי --script-id ובלי קובץ מצב: יוצר פרויקט, גרסה ודיפלוימנט Web app חדשים.
  עם --script-id או עם קובץ מצב (.deploy.json ב-out_dir): מעלה את הקבצים, יוצר גרסה
  ומעדכן את אותו דיפלוימנט. הקישור לא משתנה.
טוקן OAuth נקרא ממשתנה הסביבה APPS_SCRIPT_TOKEN, או מפלט של פקודה ב-APPS_SCRIPT_TOKEN_CMD.
הטוקן לא מודפס ולא נשמר. נדרשים הסקופים script.projects ו-script.deployments."""
import argparse, json, os, shlex, subprocess, sys, urllib.error, urllib.request

BASE = os.environ.get('APPS_SCRIPT_API_BASE', 'https://script.googleapis.com/v1')
FILES = [('Code', 'Code.gs', 'SERVER_JS'), ('index', 'index.html', 'HTML'),
         ('agreement-body', 'agreement-body.html', 'HTML'), ('appsscript', 'appsscript.json', 'JSON')]
STATE = '.deploy.json'


def token():
    t = os.environ.get('APPS_SCRIPT_TOKEN', '').strip()
    cmd = os.environ.get('APPS_SCRIPT_TOKEN_CMD', '').strip()
    if not t and cmd:
        t = subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=True).stdout.strip()
    if not t:
        sys.exit('חסר טוקן. הגדר APPS_SCRIPT_TOKEN או APPS_SCRIPT_TOKEN_CMD (פקודה שמדפיסה access token). אל תדביק אותו בצ\'אט.')
    return t


class Api:
    def __init__(self, dry):
        self.dry, self.tok = dry, None

    def call(self, method, path, body=None):
        if self.dry:
            print(f'[dry-run] {method} {BASE}{path}' + (f' ({len(json.dumps(body))} בתים)' if body else ''))
            return {}
        self.tok = self.tok or token()
        req = urllib.request.Request(BASE + path, method=method,
                                     data=json.dumps(body).encode('utf-8') if body is not None else None,
                                     headers={'Authorization': 'Bearer ' + self.tok,
                                              'Content-Type': 'application/json; charset=utf-8'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8') or '{}')
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')
            hint = ''
            if e.code == 403 and 'Apps Script API' in msg:
                hint = '\nהפעל את Apps Script API ב-script.google.com/home/usersettings ונסה שוב.'
            sys.exit(f'שגיאת API {e.code} ב-{method} {path}:\n{msg}{hint}')


def load_files(out):
    miss = [f for _, f, _ in FILES if not os.path.isfile(os.path.join(out, f))]
    if miss:
        sys.exit('חסרים קבצים ב-' + out + ': ' + ', '.join(miss) + '. הרץ קודם build.py.')
    files = [{'name': n, 'type': t, 'source': open(os.path.join(out, f), encoding='utf-8').read()}
             for n, f, t in FILES]
    man = json.loads(files[-1]['source'])
    wa = man.get('webapp', {})
    if wa.get('access') != 'ANYONE_ANONYMOUS' or wa.get('executeAs') != 'USER_DEPLOYING':
        sys.exit('ב-appsscript.json חייב להיות webapp: access=ANYONE_ANONYMOUS, executeAs=USER_DEPLOYING.')
    return files


def exec_url(dep_id):
    return f'https://script.google.com/macros/s/{dep_id}/exec'


def find_web_deployment(api, script_id):
    """הדיפלוימנט המנוהל הראשון עם גרסה (לא ה-HEAD) ועם נקודת כניסה של Web app."""
    for d in api.call('GET', f'/projects/{script_id}/deployments').get('deployments', []):
        if d.get('deploymentConfig', {}).get('versionNumber') and \
           any('webApp' in e for e in d.get('entryPoints', [])):
            return d['deploymentId']
    return None


def main():
    ap = argparse.ArgumentParser(description='פריסה ל-Apps Script')
    ap.add_argument('out_dir')
    ap.add_argument('--script-id')
    ap.add_argument('--deployment-id')
    ap.add_argument('--title', default='הסכם לחתימה')
    ap.add_argument('--description', default='')
    ap.add_argument('--dry-run', action='store_true', help='מדפיס את הקריאות בלי לשלוח')
    a = ap.parse_args()

    files = load_files(a.out_dir)
    state_p = os.path.join(a.out_dir, STATE)
    state = json.load(open(state_p)) if os.path.isfile(state_p) else {}
    script_id = a.script_id or state.get('scriptId')
    dep_id = a.deployment_id or (state.get('deploymentId') if script_id == state.get('scriptId') else None)
    api = Api(a.dry_run)

    created = not script_id
    if created:
        script_id = api.call('POST', '/projects', {'title': a.title}).get('scriptId', 'SCRIPT_ID')
        print('נוצר פרויקט', script_id)
    api.call('PUT', f'/projects/{script_id}/content', {'files': files})
    ver = api.call('POST', f'/projects/{script_id}/versions',
                   {'description': a.description or 'deploy.py'}).get('versionNumber', 'N')
    cfg = {'versionNumber': ver, 'manifestFileName': 'appsscript', 'description': a.description or 'deploy.py'}

    if not dep_id and not created:
        dep_id = find_web_deployment(api, script_id)
    if dep_id:
        api.call('PUT', f'/projects/{script_id}/deployments/{dep_id}',
                 {'deploymentConfig': dict(cfg, scriptId=script_id)})
        print(f'עודכן דיפלוימנט {dep_id} לגרסה {ver}. הקישור לא השתנה.')
    else:
        dep_id = api.call('POST', f'/projects/{script_id}/deployments', cfg).get('deploymentId', 'DEPLOYMENT_ID')
        print(f'נוצר דיפלוימנט {dep_id} לגרסה {ver}.')

    if not a.dry_run:
        json.dump({'scriptId': script_id, 'deploymentId': dep_id}, open(state_p, 'w'))
    print('\nקישור:', exec_url(dep_id))
    print('editor:  https://script.google.com/d/%s/edit' % script_id)
    print('\nעוד לא גמור:')
    print(' 1. פריסה ראשונה מחזירה 403 עד שהבעלים מריץ פונקציה ציבורית אחת בעורך (doGet) ומאשר הרשאות.')
    print(' 2. חתום בעצמך ובדוק 4 דברים: PNG, PDF, שורה בגיליון ומייל. רק אז זה עובד (SKILL.md, שלב 5).')


if __name__ == '__main__':
    main()
