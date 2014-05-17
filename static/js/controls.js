var xhr = null;
var setup_in_progress = false;

var source = new EventSource('/states');
source.addEventListener('message', function(e) {
	//console.log('data: ' + e.data);
	var result = JSON.parse(e.data);
	if (result.success) {
		for (i=0; i<result.states.length; i++) {
			var checkbox = document.getElementById(result.states[i].name);
			if (checkbox != undefined) {
				if (checkbox.checked != result.states[i].state) {
					//console.log('state changed: ' + result.states[i].name + ' > ' + result.states[i].state)
					checkbox.checked = result.states[i].state;
				}
			}
		}
	}
}, false);

function setup(name, action) {
	//console.log('set state: ' + name + ' ' + action)
	if (xhr != null) xhr.abort();
	xhr = getXMLHttpRequest();
	xhr.onreadystatechange = function() {
		if (xhr.readyState == 4 && (xhr.status == 200 || xhr.status == 0)) {
			var result = JSON.parse(xhr.responseText);
			//console.log('-> state: ' + result.name + ', ' + result.state);
			if (!result.success) {
				var checkbox = document.getElementById(result.name);
				checkbox.checked = result.state;
			}
		}
	}
	uri = '/exec/' + name + '/' + action;
	//console.log('-> uri: ' + uri);
	xhr.open('GET', uri, true);
	xhr.send(null);
}

function search(qry) {
	//console.log('set state: ' + name + ' ' + action)
	if (xhr != null) xhr.abort();
	xhr = getXMLHttpRequest();
	xhr.onreadystatechange = function() {
		if (xhr.readyState == 4 && (xhr.status == 200 || xhr.status == 0)) {
			var div = document.getElementById('result');
			div.innerHTML = xhr.responseText;
		}
	}
	uri = '/search/' + encodeURIComponent(qry);
	//console.log('-> uri: ' + uri);
	xhr.open('GET', uri, true);
	xhr.send(null);
}

function getXMLHttpRequest() {
	var xhr = null;
	if (window.XMLHttpRequest || window.ActiveXObject) {
		if (window.ActiveXObject) {
			try {
				xhr = new ActiveXObject("Msxml2.XMLHTTP");
			} catch(e) {
				xhr = new ActiveXObject("Microsoft.XMLHTTP");
			}
		} else {
			xhr = new XMLHttpRequest(); 
		}
	} else {
		alert("Votre navigateur ne supporte pas l'objet XMLHTTPRequest...");
		return null;
	}
	return xhr;
}