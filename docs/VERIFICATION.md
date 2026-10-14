# PWA и локальный ИИ — 27 сентября 2026

- Django: 49 тестов прошли; проверены публичные снимки без чужого аккаунта, запрет приватных страниц в пакете, manifest, service worker, перенос сравнения ответов на клиент.
- Пять Node-проверок прошли, включая изоляцию локальных и персональных черновиков и ограничение готового кода в учебных подсказках.
- IAB: скачано 586 ресурсов, страницы и материалы открываются из готового пакета.
- При остановленном web и runner: «Сумма трёх чисел» принята (3/3), решение сохранено на устройстве и восстановлено после reload, локальный разбор открыт.
- При остановленном web и runner: OpenCV создал изображение 256×192; неправильный результат задания отвергнут локально.
- Qwen Coder 1.5B реально загружена и выполнила два диалога об ошибках Python; второй при остановленном Django. Qwen3 0.6B также реально отвечала при остановленном сервере.
- Whisper tiny загрузилась в браузере; повторная подготовка модели успешна без работающего Django. Живая диктовка с микрофона и качество русской озвучки ещё не проверены.
- Настоящая установка приложения в ОС не выполнялась; кнопка и install prompt доступны в браузере. Проверки не охватывают все мобильные устройства и не являются бенчмарком всех моделей.

Ниже — история более ранних проверок.

---

# Исполнение Python в браузере — 27 сентября 2026

По умолчанию `EXECUTION_MODE=browser`. Контейнер runner остановлен; работает только web.
Браузер: Codex IAB на macOS. Pyodide 314.0.7 / Python 3.14.2, OpenCV 4.11.0.86.

- Девять проверок `/static/tests/browser-runtime.html` прошли: input/print, исключение, пошаговая трасса, лимит вывода, остановка бесконечного цикла, запуск после остановки, создание изображения OpenCV, пакет тестов изображений, блокировка запроса к API аккаунтов из Worker.
- Реальный интерфейс визуализатора: вывод, переменные, граф объектов.
- После остановки runner: «Сумма трёх чисел» принята, все три теста зелёные.
- После остановки runner: «Оттенки серого» создала и отобразила PNG 256×192, три учебных теста пройдены, прогресс сохранён с execution_source=browser.
- Django: 47 тестов прошли. Запуск с EXECUTION_MODE=server сохраняет проверки старого режима; новые тесты явно включают browser и проверяют отсутствие серверного исполнения, сравнение вывода, источник результата, CSRF, авторизацию, CSP и отключение старых маршрутов.
- Четыре существующих Node-проверки интерфейса прошли.

Ограничения: проверено в указанном браузере, не во всех мобильных устройствах. Клиентский результат можно подделать; это самопроверка, а не независимая контрольная работа. Не все 134 задачи повторно прогнаны в WASM. Предыдущие проверки полного курса ниже относятся к серверному режиму. Версии OpenCV в WASM и серверном режиме различаются.

---

# Проверки сборки — 27 сентября 2026

Проверено на macOS arm64, Docker Engine29.8.0 после обновления пользователем.
Веб, runner и среда ученика — Docker-образы на Python3.14.7.
Локальная установка доступна по http://localhost:8042/.

## Выполнено

| Проверка | Фактический результат |
|---|---|
| Сборка worker + Compose web/runner | Успешно; оба сервиса healthy |
| Django tests внутри web на Python3.14.7 | 24 passed |
| Runner tests + реальный control-plane с Docker socket | 13 passed, 26 секунд |
| Эталоны OpenCV в отдельных контейнерах | 24/24 совпадений пикселей |
| HTTP: вход, CSRF, рекурсивная трасса, верное/неверное решение | Успешно (`scripts/verify_live.py`) |
| HTTP: все8задач по3изображения | Приняты; отсутствие output.png отклоняется |
| JS: renderer, image UI, черновики разных пользователей | 3 regression-скрипта проходят |
| `manage.py check` | Ошибок нет |
| `makemigrations --check --dry-run` | No changes detected |
| Полный импорт | 15 уроков,134 задачи,1302 тестовые пары; повторный импорт сохраняет прогресс |
| Backup SQLite | integrity_check=ok; пользователи и решения присутствуют |
| Конфигурация Compose с HTTPS override | `config --quiet` успешно |
| `git diff --check` | Ошибок пробелов нет |

## Реальный пользовательский путь в браузере

Создан и введён демонстрационный ученик. Решение задачи «Сумма трёх чисел»
принято на всех трёх тестах. Пошаговый запуск показывает переменные a,b,c
и ответ11. Пример «разные имена одного объекта» проходит23шага, отображает
списки и стрелки связей; ошибок JavaScript в журнале нет.

В разделе OpenCV введён код cvtColor, показан серый PNG. Через системный
выбор файла загружено другое изображение127×95; stdout подтвердил его размер,
результат появился в браузере. Отправка на проверку приняла все три учебных
изображения, сохранив прогресс. Преподаватель создал задание для student_demo
и увидел статус «Решено». Эти две локальные учётные записи и демонстрационное
назначение остаются в локальной базе; их нет в переносимом архиве исходников.

## Границы проверенного

- Проверена нативная сборка arm64. Сборка amd64 предусмотрена Dockerfile и
  бинарными зависимостями, но на отдельном x86-сервере не выполнялась.
- Публичный домен, выпуск TLS-сертификата и нагрузочное тестирование не
  выполнялись. HTTPS-конфигурация подготовлена; нужен домен нового сервера.
- Для локального HTTP `check --deploy` выдаёт ожидаемые предупреждения о
  HTTPS/cookie/HSTS. При проверке с secure-cookie и redirect остаются только
  предупреждения о включении HSTS для всех поддоменов и preload; эти политики
  не включены автоматически. Это не сообщение о существующем публичном HTTPS.
- Все 134 страницы задач и 15 уроков отрендерены в тестах. Авторские решения
  базы знаний проверены на всех 1302 тестовых парах: 269 вариантов, 2625 запусков,
  0 ошибок, Python 3.14.7 внутри контейнера. Это проверка доступных тестов,
  а не доказательство для всех возможных входов.
- Материалы публичного архива отличаются от действующего сайта; подробности
  в PROVENANCE.md. Закрытые базы, чужие аккаунты и внешний OAuth не копировались.

## Исправленные при интеграции проблемы

Обновлены устаревшие Django API и миграции, восстановлены7несвязанных задач,
включены CSRF/контроль доступа/общие квоты. Устранён обход квот через суффикс URL.
Исправлено отображение пользовательских строк в визуализаторе без HTML-инъекции.
В runner отдельно установлен docker-cli; управляющий сервис реально проверен
через HTTP и Docker socket. Веб-сервис подключён к отдельной frontend-сети,
поскольку internal-only сеть не публиковала порт. Необязательный control socket
Gunicorn отключён для работы с readonly-корнем контейнера.

## База знаний и повторная проверка после правок

- `knowledge/verification.json`: 134 задачи, 269 вариантов, 2625 успешных запусков;
  SHA256 фиксирует конкретные проверенные статьи, Python 3.14.7.
- `scripts/verify_image_knowledge.py`: 8 задач, 16 вариантов, 48 совпадений пикселей.
- `knowledge/review-edge-cases.json`: отдельный аудит 9 статей, 197 архивных и
  47 дополнительных проверок. Проверялись точные десятичные значения,
  одиночные узлы и цепочки родства из 1200 узлов.
- 24 Django-теста прошли в итоговой сборке; проверены запрет чужого доступа,
  отсутствие выдачи до успешной сдачи, независимость OpenCV, XSS-экранирование,
  запрет получения JSON через static, private/no-store, псевдонимы задач.
- Черновики разделены по пользователю и задаче; старые общие черновики не читаются.
- Итоговый `scripts/verify_live.py` повторно прошёл: рекурсивная трасса, верный и
  неверный ответ, 24 проверки всех 8 изображений, PNG-превью, отсутствие output.png.
- В браузере «МКАД»: закрытый разбор → сдача всех 6 тестов → появление ссылки →
  рекомендуемый вариант, альтернатива и собственное решение. OpenCV cvtColor:
  цветное исходное изображение и серый результат показаны рядом.

Графика визуализатора проверена на общих ссылках двух переменных на список,
отдельном равном списке, Unicode, tuple, set, nested dict, объекте класса,
рекурсивном стеке fact(3), переходах до конца и обратном направлении. Проверены
ZeroDivisionError и подсветка строки. После исправления переполнения граф не
растягивает страницу (viewport и scrollWidth 1280, нет NaN в SVG-путях).
Домашняя страница проверена при ширине 390px без горизонтального переполнения.
Иллюстрация «Шнурки» загрузилась в оригинальном размере 243×225.

## Преподаватели и регистрация по приглашению

27 сентября: добавлены StudyGroup и необязательная группа профиля; резервная
копия SQLite сделана до миграции. 33 Django-теста прошли в Docker/Python 3.14.7.
9 новых сценариев проверяют приглашение, отклонение неверного/закрытого кода,
неактивного преподавателя, сохранение кода при ошибке формы, регистрацию без кода,
явное присоединение существующего ученика, запрет самовольного перевода,
создание/отзыв приглашений, ручное добавление/редактирование, поиск,
CSRF и разграничение доступа между преподавателями в кабинете, админке,
профиле, статистике и OpenCV.

На работающем сервере: группа «Ученики Дмитрия» создана через браузер,
проверено копирование ссылки; enrollment_demo самостоятельно зарегистрирован
через HTTP-форму с CSRF, вошёл, увидел свою группу, вышел/вошёл повторно —
привязка сохранилась. Он появился в кабинете преподавателя. Существующий
student_demo зачислен в группу через форму Django. Тестовые аккаунты остаются
только в локальной базе, пароль нового демонстрационного ученика — в `.private`
вне проекта и переносимого архива.

## 2026-09-27 — AI tutor and speech

- Reference: assistant panel viewed in the user's Comet tab on zachet.app; implemented analogous sidebar, text/voice mode switch, expandable view, composer, quick prompts, attachment, dictation, copy/read-aloud controls. Python mascot is project-specific; this is not a claim of source-code or pixel-perfect parity.
- Browser: live electronic_watch draft read without saving/submitting it; real answer identified `/` versus `//`; private history survived reload. Desktop 911 px sidebar leaves editor visible. Mobile 390×844 panel fits viewport; expand/restore checked; no captured JavaScript errors.
- Live authenticated HTTP: Responses API returned relevant Russian answer; NVIDIA Chatterbox generated 574604-byte WAV at 24 kHz; NVIDIA Whisper transcribed that synthetic answer; history contains completed turn. No human microphone recording was taken for QA.
- Live image API: synthetic red PNG attached to OpenCV task; model correctly returned «Красная».
- Yandex speech endpoint timed out from local Docker; default changed to working NVIDIA synthesis. Yandex remains an optional provider. This deployment uses the owner's existing provider credentials, stored only in excluded .env.
- Automated: Django assistant coverage includes own-user history, request id deduplication, code snapshot, accepted-solution gate, image validation, CSRF/auth, quotas, provider errors, audio ownership, chunking/WAV and connection failure cleanup. Node audio test checks 44.1/48 kHz → 16 kHz conversion and bounded worklet messages; existing three UI regression scripts retained.
- Limits: browser microphone permission and physical speaker/microphone loop require user device verification. Voice is turn-based (pause → transcription → complete answer → synthesis), not simultaneous streaming speech. AI hints are prompt-governed; database editorial unlock is server-governed.

## 2026-09-27 — Integrated adaptive assistant workspace

Replaced fixed 414px floating card with a full-height workspace below navigation. Lesson/editor and assistant share the available width; removed the 900px lesson cap while open. Divider supports pointer drag and keyboard arrows/Home, saves width locally; narrow screens (<900px) show a full-width assistant with collapse back to the task. Desktop opens by default and remembers open/closed state per tab.

Browser verification: 1280×720 workspace fills available area; keyboard divider changed 42→44%, pointer drag changed to 50%; 390×844 chat fits below navigation, collapse/reopen works. Existing draft and chat history retained. Assistant Django tests: 11 passed. JavaScript syntax check passed.

Assistant navigation regression fix: removed the unconditional effective hide of the lesson menu by adding an explicit open state. Toggle derives visibility from rendered sidebar and synchronizes aria-expanded on layout changes. Browser reproduced false→false before fix; after fix opening displayed lesson/task links, clicking «Дележ яблок» navigated to /problems/apples/, and repeated open/close returned true→false. JavaScript syntax check passed.

Next-task navigation: added bottom link with destination title to ordinary and OpenCV task pages. Ordinary ordering follows lessons and problems, including next lesson when current lesson ends. Final task links back to the course list. Browser checked minimum → signum via «Следующая задача».

Lesson navigation now opens as a left column beside the task while the assistant remains on the right, replacing the temporary block above the task. Menu has independent overflow and a sticky top position. Verified in the user's minimum task tab: left column visible, collapse false, reopen true; no downward task displacement.

Manual menu preference: defaults open, localStorage stores explicit open/closed choice, assistant no longer independently collapses it. Browser verified collapsed state after reload and open state after navigating to another task.

Task manual-entry mode: capture handlers block paste shortcuts, paste/beforeinput, and text drag/drop only inside task code editors (ordinary and OpenCV). Browser verified blocked paste status and successful keyboard typing; QA typing undone. This is an interface restriction, not tamper-proof assessment security. Chat, stdin, playground and existing drafts remain available.
