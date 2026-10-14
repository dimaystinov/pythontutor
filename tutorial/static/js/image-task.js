/* Local image lesson UI: learner output is always rendered as text or a PNG data URL. */
(function ($) {
    'use strict';
    var messages = {
        skipped: 'Не запускался.', ok: 'Выполнено.', accepted: 'Решение принято.', wrong_answer: 'Результат не совпадает с ожидаемым.',
        error: 'Решение требует исправления.', invalid_image: 'Программа не создала допустимое изображение output.png.',
        output_limited: 'Превышен лимит вывода. Уменьшите количество печатаемых данных.',
        realtime_limited: 'Превышено время выполнения.', time_limited: 'Превышено время выполнения.',
        unhandled_exception: 'Ошибка выполнения Python.', internal_error: 'Сервис выполнения временно недоступен.',
        unavailable: 'Сервис выполнения временно недоступен.', runner_unavailable: 'Сервис выполнения временно недоступен.'
    };
    function statusText(status) { return messages[status] || 'Программа завершилась с ошибкой.'; }
    function pngURL(value) {
        return typeof value === 'string' && /^iVBORw0KGgo[A-Za-z0-9+/]*={0,2}$/.test(value)
            ? 'data:image/png;base64,' + value : null;
    }
    // Small pure helpers are exposed for the Node regression test.
    window.ImageTaskUI = {statusText: statusText, pngURL: pngURL};

    $(function () {
        var root = document.getElementById('image-task');
        if (!root) return;
        var editor = ace.edit('image-code');
        editor.setOptions({mode: 'ace/mode/python', fontSize: 15, showPrintMargin: false});
        editor.textInput.getElement().setAttribute('aria-label', 'Код Python для обработки изображения');
        const draftKey='image-draft:'+window.TutorDevice?.owner()+':'+root.dataset.slug;
        try { const draft=localStorage.getItem(draftKey);if(draft!==null)editor.setValue(draft,-1); } catch(_){}
        editor.on('change',()=>{try{localStorage.setItem(draftKey,editor.getValue());}catch(_){}});
        var input = document.getElementById('image-input');
        var defaultInput = input.src;
        var uploaded = null;
        var previewURL = null;
        var imageVersion = 0;
        var busy = false;

        function status(text) { $('#image-status').text(text); }
        function error(text) { $('#image-error').text(text || '').prop('hidden', !text); }
        function clearOutput() {
            $('#image-output').removeAttr('src');
            $('#image-output-wrap, #image-download').prop('hidden', true);
            $('#image-download').removeAttr('href');
            $('#image-output-empty').prop('hidden', false).text('Результат пока не получен.');
        }
        function setBusy(value) {
            busy = value;
            $('#image-run, #image-submit, #image-upload, #image-reset').prop('disabled', value);
        }
        function resetInput() {
            imageVersion++;
            uploaded = null;
            $('#image-upload').val('');
            if (previewURL) URL.revokeObjectURL(previewURL);
            previewURL = null;
            input.src = defaultInput;
        }
        $('#image-reset').on('click', function () { resetInput(); error(''); status('Выбрано учебное изображение.'); });
        $('#image-upload').on('change', function () {
            var file = this.files[0];
            resetInput();
            if (!file) return;
            error('');
            if (!/^image\/(png|jpeg)$/.test(file.type) || file.size > 2 * 1024 * 1024) {
                error('Выберите PNG или JPEG размером не более 2 МБ.');
                return;
            }
            var version = imageVersion;
            var image = new Image();
            previewURL = URL.createObjectURL(file);
            image.onload = function () {
                if (version !== imageVersion) return;
                if (image.width * image.height > 4000000) {
                    resetInput(); error('Изображение должно содержать не более 4 млн пикселей.'); return;
                }
                uploaded = file;
                input.src = previewURL;
                status('Выбрано изображение: ' + file.name);
            };
            image.onerror = function () {
                if (version !== imageVersion) return;
                resetInput(); error('Не удалось прочитать изображение. Выберите другой файл.');
            };
            image.src = previewURL;
        });

        function request(url, data, done) {
            if (busy) return;
            setBusy(true);
            error('');
            var operation;
            if(window.BrowserPython){
                operation=$.Deferred(function(d){(async function(){
                    const slug=root.dataset.slug;
                    if(url===root.dataset.submitUrl)return window.BrowserPython.submit('image',slug,data.get('code'));
                    const blob=uploaded || await (await fetch(defaultInput)).blob();
                    const image=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(blob);});
                    return window.BrowserPython.run({code:data.get('code'),image});
                })().then(d.resolve,d.reject);}).promise();
            }else operation=$.ajax({url: url, method: 'POST', data: data, processData: false, contentType: false, dataType: 'json'});
            operation
                .done(done)
                .fail(function (xhr) {
                    status('Запрос не выполнен.');
                    error(xhr.responseJSON && xhr.responseJSON.error || 'Не удалось выполнить запрос. Повторите попытку; если сеанс истёк, войдите снова.');
                })
                .always(function () { setBusy(false); });
        }
        $('#image-run').on('click', function () {
            if (busy) return;
            clearOutput();
            $('#image-stdout').text('');
            status('Выполняем программу…');
            var data = new FormData();
            data.append('code', editor.getValue());
            if (uploaded) data.append('image', uploaded);
            request(root.dataset.runUrl, data, function (result) {
                $('#image-stdout').text(result.stdout || '');
                var details = result.stderr || '';
                if (result.exception) details += (details ? '\n' : '') + (result.exception.exception_msg || 'Ошибка Python');
                error(details);
                status(statusText(result.result));
                var url = pngURL(result.image);
                if (url) {
                    $('#image-output').attr('src', url);
                    $('#image-download').attr('href', url).prop('hidden', false);
                    $('#image-output-wrap').prop('hidden', false);
                    $('#image-output-empty').prop('hidden', true);
                } else if (result.result === 'ok') {
                    error('Изображение не получено. Сохраните результат в output.png.');
                }
            });
        });
        $('#image-submit').on('click', function () {
            if (busy) return;
            status('Проверяем на учебных тестах…');
            $('#image-test-results').empty();
            var data = new FormData();
            data.append('code', editor.getValue());
            request(root.dataset.submitUrl, data, function (result) {
                status(result.status === 'ok' || result.status === 'accepted' ? (result.storage_error?'Решение принято, но локальное сохранение недоступно.':result.local&&!result.synced?'Решение принято. Сохранено на устройстве.':'Решение принято. Прогресс сохранён.') : statusText(result.status));
                if (result.status === 'ok') $('#image-knowledge-unlock').prop('hidden', false);
                var list = $('<ol>');
                (result.tests || []).forEach(function (test) {
                    var verdict = typeof test === 'string' ? test : (test.status || test.result);
                    list.append($('<li>').text(statusText(verdict)).addClass(verdict === 'ok' ? 'text-success' : (verdict === 'skipped' ? 'text-muted' : 'text-danger')));
                });
                $('#image-test-results').append($('<h2 class="h4">').text('Результаты проверки'), list);
            });
        });
    });
})(jQuery);
