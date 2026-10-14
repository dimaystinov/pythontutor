/* Task editors require manual input; stdin and assistant remain unrestricted. */
(function () {
    'use strict';
    const selector = '#visualizer .visualizer_prog_code, #image-code';
    function inCode(event) {
        return event.target instanceof Element && event.target.closest(selector);
    }
    function block(event) {
        if (!inCode(event)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const notice = document.getElementById('task-writing-notice');
        if (notice) notice.textContent = 'Вставка кода отключена. Напишите решение самостоятельно с клавиатуры.';
    }
    ['paste', 'drop', 'dragover', 'dragstart'].forEach(type => document.addEventListener(type, block, true));
    document.addEventListener('beforeinput', event => {
        if (/^insertFrom(Paste|Drop)/.test(event.inputType || '')) block(event);
    }, true);
    document.addEventListener('keydown', event => {
        if (((event.ctrlKey || event.metaKey) && event.code === 'KeyV') ||
            (event.shiftKey && event.key === 'Insert')) block(event);
    }, true);
})();
