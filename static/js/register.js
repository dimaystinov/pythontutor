$(function() {
	$('form').submit(function() {
		if($(this['password']).val() !== $(this['confirm_password']).val()) {
			alert('Пароли не совпадают... Пожалуйста, введите их снова.');

			$(this['password']).val('').focus();
			$(this['confirm_password']).val('');

			return false;
		}
	});
});
