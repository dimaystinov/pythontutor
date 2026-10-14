/* Send Django CSRF tokens only to same-origin, state-changing requests. */
(function ($) {
    $.ajaxPrefilter(function (options, original, xhr) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.type) && !options.crossDomain) {
            var token = document.querySelector('meta[name="csrf-token"]');
            if (token) xhr.setRequestHeader('X-CSRFToken', token.content);
        }
    });
})(jQuery);

$(function () {
    var menuOpen = true;
    try { menuOpen = localStorage.getItem('lesson-menu-open') !== 'no'; } catch (_) {}
    $('body').toggleClass('lesson-menu-hidden', !menuOpen);
    function syncMenuButton() {
        var sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        var visible = getComputedStyle(sidebar).display !== 'none';
        $('.sidebar-toggle').attr('aria-expanded', String(visible))
            .attr('aria-label', visible ? 'Скрыть меню уроков' : 'Показать меню уроков')
            .find('i').toggleClass('fa-angle-left', visible).toggleClass('fa-angle-right', !visible);
    }
    $('.sidebar-toggle').on('click', function () {
        var sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        var show = getComputedStyle(sidebar).display === 'none';
        $('body').toggleClass('lesson-menu-hidden', !show);
        try { localStorage.setItem('lesson-menu-open', show ? 'yes' : 'no'); } catch (_) {}
        syncMenuButton();
        window.dispatchEvent(new Event('resize'));
    });
    window.addEventListener('resize', syncMenuButton);
    syncMenuButton();
});
