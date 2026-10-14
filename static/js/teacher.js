'use strict';
document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-copy-invite]');
    if (!button) return;
    const input = document.getElementById(button.dataset.copyInvite);
    const status = document.getElementById('copy-status');
    try {
        await navigator.clipboard.writeText(input.value);
        status.textContent = 'Ссылка скопирована. Отправьте её ученикам.';
    } catch (_) {
        input.focus();
        input.select();
        status.textContent = 'Ссылка выделена. Скопируйте её сочетанием Ctrl+C или ⌘C.';
    }
});
