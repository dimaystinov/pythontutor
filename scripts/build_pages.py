#!/usr/bin/env python3
"""Compile the course into a standalone static site; Django is a build tool only."""
import argparse, json, os, re, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
p = argparse.ArgumentParser()
p.add_argument('--base', default='/pythontutor/')
p.add_argument('--output', default='dist/pages')
args = p.parse_args()
base = '/' + args.base.strip('/') + '/' if args.base.strip('/') else '/'
if not re.fullmatch(r'/[a-zA-Z0-9_/-]*', base):
    p.error('base must be a URL path')
out = (ROOT / args.output).resolve()
if out == ROOT or ROOT not in out.parents:
    p.error('output must be a subdirectory of the project')
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ.update(DJANGO_SETTINGS_MODULE='pythontutor.settings', SECRET_KEY='static-build-not-a-deployed-secret', DATABASE_PATH=tmp+'/build.sqlite3', EXECUTION_MODE='browser')
    import django
    django.setup()
    from django.core.management import call_command
    from django.test import RequestFactory
    from django.contrib.auth.models import AnonymousUser
    from django.urls import resolve
    from tutorial.views.pwa import download_manifest, public_page, manifest
    call_command('migrate', verbosity=0)
    call_command('seed_course', verbosity=0)
    rf = RequestFactory()
    def request(url):
        r = rf.get(url, HTTP_HOST='localhost'); r.user = AnonymousUser(); r.session = {}; r.pwa_offline = True
        return r
    package = json.loads(download_manifest(request('/')).content)
    def rewrite(text):
        # Only root-relative strings/HTML attributes. Never touch external URLs or Python division.
        text = text.replace('href="/"', 'href="'+base+'"').replace("location.href='/'", "location.href='"+base+"'").replace("scope:'/'", "scope:'"+base+"'")
        return re.sub(r'''(["'`])/(?!/)(?=(?:static/|lessons/|browser/|assistant/|pwa/|knowledge/|images/|visualizer/|tester/|accounts/|log_user_action/|sw\.js|manifest\.webmanifest|__pwa_))''', lambda m:m[1]+base, text).replace(base+base.lstrip('/'),base)
    def write(url, data):
        target = out / url.lstrip('/')
        if url.endswith('/'): target = target / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.encode() if isinstance(data,str) else data)
    for url in package['pages']:
        response = public_page(request('/pwa/page/?path='+url))
        assert response.status_code == 200, url
        html = response.content.decode()
        html = re.sub(r'<li><a class="original-teacher".*?</li>', '', html)
        html = re.sub(r'<a[^>]+href="/images/assignments/"[^>]*>.*?</a>', '', html)
        html = re.sub(r'<input[^>]+name="csrfmiddlewaretoken"[^>]*>', '', html)
        html = html.replace('Облачный режим отправляет их внешним ИИ-сервисам. ', '')
        html = html.replace('</head>', '<meta name="static-site" content="yes"></head>')
        if url == '/pwa/':
            html = html.replace('Облачный ИИ, регистрация и кабинет преподавателя требуют сети.', 'Все учебные функции работают на устройстве. Учётная запись не нужна.')
            html = html.replace('Локальные решения хранятся в этом браузере отдельно от учётной записи.', 'Решения, черновики и история помощника хранятся только в этом браузере.')
            html = html.replace('Локальные Qwen и голосовой ввод Whisper скачиваются отдельно в помощнике.', 'Qwen и Whisper подготавливаются один раз из пакетов GitHub в помощнике или настройках.')
            html = html.replace('резервную копию решений','резервную копию данных')
        write(url, rewrite(html))
    shutil.copytree(ROOT/'tutorial/static', out/'static', dirs_exist_ok=True, ignore=shutil.ignore_patterns('tests','__pycache__'))
    for path in (out/'static').rglob('*'):
        if path.is_file() and path.suffix in {'.js','.mjs','.css','.html'} and 'vendor' not in path.relative_to(out).parts:
            
            if path.name == 'worker.mjs': continue
            try: text = path.read_text()
            except UnicodeDecodeError: continue
            rewritten = rewrite(text)
            if path.name == 'app.js': rewritten = rewritten.replace("'"+base+"problems/'", "'/problems/'")
            path.write_text(rewritten)
    # Worker must have a JS extension and correct MIME type on a static host.
    bp = out/'static/js/browser-execution.js'
    bp.write_text(bp.read_text().replace(base+'browser/worker/',base+'static/browser/worker.mjs').replace("+'/');", "+'/index.json');"))
    resources = []
    for url in package['resources']:
        if url.startswith('/static/') or url in {'/browser/worker/','/manifest.webmanifest'}: continue
        match = resolve(url)
        response = match.func(request(url), *match.args, **match.kwargs)
        assert response.status_code == 200, url
        if url.startswith('/browser/tests/'):
            url += 'index.json'
        elif '/input/' in url:
            old = url; url += 'input.png'
            # Image inputs are binary resources, not directory index documents.
            for page in (out/'images').rglob('*.html'):
                page.write_text(page.read_text().replace(base+old.lstrip('/'),base+url.lstrip('/')))
        content = b''.join(response.streaming_content) if response.streaming else response.content
        write(url, content); resources.append(base+url.lstrip('/'))
    m = json.loads(manifest(request('/')).content)
    for key in ('id','start_url','scope'): m[key] = base+m[key].lstrip('/')
    for icon in m['icons']: icon['src'] = base+icon['src'].lstrip('/')
    write('/manifest.webmanifest',json.dumps(m,ensure_ascii=False))
    # Static PWA downloads ordinary pages; no server snapshot API exists.
    sw = rewrite((ROOT/'tutorial/static/pwa/sw.js').read_text())
    sw = sw.replace("url:'"+base+"pwa/page/?path='+encodeURIComponent(path)", 'url:path')
    sw = sw.replace(base+'pwa/download-manifest/',base+'pwa/download-manifest.json')
    sw = sw.replace("'tutor-pwa-meta-v1'",json.dumps('tutor-pages-meta-'+base))
    sw = sw.replace("'tutor-pwa-pack-'",json.dumps('tutor-pages-pack-'+base+'-'))
    write('/sw.js',sw)
    resources += [base+p.relative_to(out).as_posix() for p in (out/'static').rglob('*') if p.is_file()]
    resources.append(base+'manifest.webmanifest')
    write('/pwa/download-manifest.json',json.dumps({'version':'pages-v1.1.0','pages':[base+u.lstrip('/') for u in package['pages']], 'resources':sorted(set(resources))}))
    write('/.nojekyll','')
    write('/404.html','<!doctype html><meta charset="utf-8"><h1>Страница не найдена</h1><a href="'+base+'">К урокам</a>')
    print(f'Static site: {out}; {len(package["pages"])} pages, {len(resources)} resources; base={base}')
