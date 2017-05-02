
function toggle_children_visible(element) {
	var li = element.parentNode.parentNode;
	var link = li.querySelector('div a');
	var children_ul = li.querySelector('ul');
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

function toggle_artifact_visible(button_element, artifact_id, artifact_name, request_path) {
	console.log('toggle_artifact_visible', artifact_id, request_path, button_element);
	var li = button_element.parentNode.parentNode.parentNode;
	var artifact_loading_error_div = li.querySelector('.artifact-loading-error');
	var artifacts_div = li.querySelector('.artifacts');
	console.log('li:', li, artifact_loading_error_div);

	var artifact_element = document.getElementById('artifact-' + artifact_id);
	if (artifact_element) {
		if (artifact_element.style.display != 'none')
			hide_artifact(button_element, artifact_element);
		else
			show_artifact(button_element, artifact_element);
		return false;
	}

	var request = new XMLHttpRequest();
	request.open('GET', request_path);
	request.onload = function() {
		if (request.status == 200) {
			handle_loaded_artifact(button_element, artifacts_div, artifact_loading_error_div, artifact_id, artifact_name, request.responseText);
		} else {
			show_artifact_loading_error(
				artifact_name, artifact_loading_error_div, 'server returned: ' + request.status + ' ' + request.statusText);
		}
	};
	request.onerror = function() {
		show_artifact_loading_error(
			artifact_name, artifact_loading_error_div, 'server is unreachable ' + request.statusText);
	};
	request.send();
	return false;
}

function show_artifact_loading_error(artifact_name, error_div, error) {
	error_div.textContent = 'Failed to load artifact "' + artifact_name + '": ' + error;
	error_div.style.display = 'block';
}

function hide_artifact(button_element, artifact_element) {
	artifact_element.style.display = 'none';
	button_element.classList.remove('artifact-button-opened');
}

function show_artifact(button_element, artifact_element) {
	artifact_element.style.display = 'block';
	button_element.classList.add('artifact-button-opened');
}

function handle_loaded_artifact(button_element, artifacts_div, error_div, artifact_id, artifact_name, contents) {
	console.log('loaded artifact', contents);
	error_div.style.display = 'none';
	var artifact_element = make_artifact_element(artifact_id, artifact_name, contents);
	artifacts_div.appendChild(artifact_element);
	artifacts_div.style.display = 'block';
	button_element.classList.toggle('artifact-button-opened');
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
