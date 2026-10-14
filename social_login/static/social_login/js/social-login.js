function social_login(url) {
	var popup_width = 800;
	var popup_height = 600;

	var left = (screen.width / 2) - (popup_width / 2);
	var top = (screen.height / 2) - (popup_height / 2);

	var appearance = 'width=' + popup_width + ',height=' + popup_height + ',top=' + top + ',left=' + left;
	window.open(url, '', appearance);

	window.oauthlogin_done = function(error_text) {
		if(error_text === undefined) {
			var continue_url = $('.login_form input[name="next"]').val();
			if(continue_url == '') {
				continue_url = '/';
			}
			location.href = continue_url;
		} else {
			alert('OAuth login error: ' + error_text + '. Please, try another provider.');
		}
	}
}
