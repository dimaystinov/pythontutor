function submit_solution(problem_name, code, callback) {
    if(window.BrowserPython){window.BrowserPython.submit('problem',problem_name,code).then(function(r){callback(true,r);},function(){callback(false);});return;}
	var req = $.ajax({url: '/tester/submit/', method: 'POST', dataType: 'json', data: {
		problem: problem_name,
		user_code: code
	}});

	req.done(function(res) {
		callback(true, res);
	});

	req.fail(function() {
		callback(false);
	});
}


var visualizer;

$(function() {
	var code = undefined;
	var stdin = $('#example_tests pre.input:first').text();
	var draftUserId = $('#visualizer').attr('data-draft-user-id') || 'local';
	var draftKey = draftUserId ? 'problem-draft:' + draftUserId + ':' + problem_name : null;

	var problem_saved = null;
	try { if (draftKey) problem_saved = JSON.parse(localStorage.getItem(draftKey)); } catch (error) { /* Storage may be unavailable or stale. */ }
	if(problem_saved !== null && problem_saved.solution !== undefined) {
		if(problem_saved.solution.code != '') {
			code = problem_saved.solution.code;
		}
		if(problem_saved.solution.stdin != '') {
			stdin = problem_saved.solution.stdin;
		}
	}


	visualizer = new Visualizer('#visualizer', code, stdin, {
		explain_mode: false
	});

	visualizer.focusCodeEditor();

	visualizer.on('change_code', function() {
		$('.submit_solution').toggle(visualizer.code.trim() != '');
	});


	setInterval(function() {
		if (!draftKey) return;
		try { localStorage.setItem(draftKey, JSON.stringify({
			solution: {
				code: visualizer.code,
				stdin: visualizer.stdin
			},
		})); } catch (error) { /* Editing works without browser storage. */ }
	}, 1000);


	$('.submit_solution').toggle(visualizer.code.trim() != '');

	$('.submit_solution button').click(function() {
		var test_rows = $('#example_tests > tbody > tr');
		$('#submission-status').removeClass('is-solved').text('Проверяем решение…');
        $('#submission-next-task').prop('hidden', true);

		var button = $(this);
		var initial_text = button.html();

		button.attr('disabled', true).html('<span class="glyphicon glyphicon-time"></span> Решение отправляется...');

		submit_solution(problem_name, visualizer.code, function(success, result) {

			button.attr('disabled', false).html(initial_text);

			if(!success) {
				$('#submission-status').text('Не удалось проверить решение. Повторите попытку; если сеанс истёк, войдите снова.');
				return;
			}

			$('#submission-status').toggleClass('is-solved', result.status === 'ok').text(result.status === 'ok' ? 'Правильное решение, поздравляем.' + (result.storage_error ? ' Не удалось сохранить прогресс на устройстве.' : '') : 'Неправильное решение. На одном из тестов ниже программа неправильно работает.');
            $('#submission-next-task').prop('hidden', result.status !== 'ok');
			$('#example_tests .test_result').show();
            $('#example_tests .test_output').toggle(Array.isArray(result.outputs));
            var testOutputs = result.outputs || [];
            if (result.status === 'ok') $('#knowledge-unlock').prop('hidden', false);

			$.each(result.tests, function(id, result) {
				test_rows[id] = $(test_rows[id]);

				var clazz, image, text;

				if(result == 'ok') {
					clazz = 'success';
					image = 'ok';
					text = 'правильно';
				} else if(result == 'skipped') {
					clazz = 'active';
					image = null;
					text = 'Не запускался';
				} else if(result == 'wrong_answer') {
					clazz = 'warning';
					image = 'error';
					text = 'неправильно';
				} else {
					clazz = 'danger';
					image = 'error';
					text = 'ошибка выполнения';
				}

				test_rows[id].addClass(clazz);
				test_rows[id].find('.test_output pre').text(testOutputs[id] || '');
                test_rows[id].find('.test_result').text(text);
                if(image)test_rows[id].find('.test_result').append($('<img>', {src:'/static/images/test_' + image + '.png?v=snakes5',alt:'',class:'test-snake'}));
			});
		});

		$('#example_tests tr').removeClass('success')
		                      .removeClass('warning')
		                      .removeClass('danger')
		                      .removeClass('active');

		$('#example_tests .test_result, #example_tests .test_output').hide();
        $('#example_tests .test_output pre').empty();
	});

	$('#example_tests .debug_me').click(function() {
		var row = $(this).parent();

		visualizer.stdin = row.find('pre.input').text();
		visualizer.run();

		var visualizer_top = $("#visualizer").offset().top - 65;
		if($('body').scrollTop() > visualizer_top) {
			$('body').animate({scrollTop: visualizer_top}, 500);
		}
	});


})
