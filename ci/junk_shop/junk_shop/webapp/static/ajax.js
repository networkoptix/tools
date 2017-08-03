
function toggle_children_visible(link, run_id, children_load_request_path) {
	var li = link.parentNode.parentNode;
	var children_ul = li.querySelector('ul');
	if ( link.classList.contains('run-lazy-children-loading') )
	{
		var ajax_loading_error_div = li.querySelector('.ajax-loading-error');
		load_run_children(link, children_ul, ajax_loading_error_div, run_id, children_load_request_path);
	}
	if ( children_ul.style.display == 'none' ) {
		children_ul.style.display = 'block';
		link.classList.remove('run-collapsed');
		link.classList.add('run-expanded');
	}
	else {
		children_ul.style.display = 'none';
		link.classList.add('run-collapsed');
		link.classList.remove('run-expanded');
	}
	return false;
}


function load_run_children(link, children_ul, ajax_loading_error_div, run_id, children_load_request_path)
{
	run_ajax_request(children_load_request_path, ajax_loading_error_div,
		'Failed to load children for run ' + run_id, function(responseText) {
		handle_loaded_run_children(link, children_ul, ajax_loading_error_div, responseText);
	});
}

function handle_loaded_run_children(link, children_ul, ajax_loading_error_div, contents)
{
	ajax_loading_error_div.style.display = 'none';
	link.classList.remove('run-lazy-children-loading');
	children_ul.innerHTML = contents;
}


function toggle_artifact_visible(button_link, artifact_id, artifact_name, request_path) {
	var button_span = button_link.parentNode;
	var li = button_span.parentNode.parentNode.parentNode;
	var ajax_loading_error_div = li.querySelector('.ajax-loading-error');
	var artifacts_div = li.querySelector('.artifacts');

	var artifact_element = document.getElementById('artifact-' + artifact_id);
	if (artifact_element) {
		if (artifact_element.style.display != 'none')
			hide_artifact(button_link, artifact_element);
		else
			show_artifact(button_link, artifact_element);
		return false;
	}

	button_link.classList.add('artifact-link-loading');
	run_ajax_request(request_path, ajax_loading_error_div, 'Failed to load artifact "' + artifact_name + '"', function(responseText){
			handle_loaded_artifact(button_link, artifacts_div, ajax_loading_error_div, artifact_id, artifact_name, responseText);
	});

	return false;
}

function run_ajax_request(request_path, ajax_loading_error_div, error_message, on_success)
{
	var request = new XMLHttpRequest();
	request.open('GET', request_path);
	request.onload = function() {
		if (request.status == 200)
			on_success(request.responseText);
		else
			show_ajax_loading_error(ajax_loading_error_div,
				error_message + ': server returned: ' + request.status + ' ' + request.statusText);
	};
	request.onerror = function() {
		show_ajax_loading_error(ajax_loading_error_div, error_message + ': server is unreachable ' + request.statusText);
	};
	request.send();
}

function show_ajax_loading_error(error_div, error_message) {
	error_div.textContent = error_message;
	error_div.style.display = 'block';
}

function hide_artifact(button_link, artifact_element) {
	var button_span = button_link.parentNode;
	artifact_element.style.display = 'none';
	button_span.classList.remove('artifact-button-opened');
}

function show_artifact(button_link, artifact_element) {
	var button_span = button_link.parentNode;
	artifact_element.style.display = 'block';
	button_span.classList.add('artifact-button-opened');
}

function handle_loaded_artifact(button_link, artifacts_div, error_div, artifact_id, artifact_name, contents) {
	var button_span = button_link.parentNode;
	error_div.style.display = 'none';
	var artifact_element = make_artifact_element(artifact_id, artifact_name, contents);
	artifacts_div.appendChild(artifact_element);
	artifacts_div.style.display = 'block';
	button_link.classList.remove('artifact-link-loading');
	button_span.classList.toggle('artifact-button-opened');
}

function make_artifact_element(artifact_id, artifact_name, contents) {
	var fieldset = document.createElement('fieldset');
	fieldset.id = 'artifact-' + artifact_id;
	fieldset.classList.add('artifact');

	var legend =  document.createElement('legend');
	legend.textContent = artifact_name;
	fieldset.appendChild(legend);

	var div = document.createElement('div');
	div.textContent = contents;
	fieldset.appendChild(div);

	return fieldset;
}
