// Title: Utilities
// URL: http://www.morgado.ch ; http://web-logbook.sourceforge.net
// Version: 1.2
// Date: 30-12-2007 (dd-mm-yyyy)
// Note: Permission given to use this script in ANY kind of applications if
//    header lines are left unchanged.

var serverdate = new Date(currenttime);

function is_defined(variable) {
    return (typeof(variable) != 'undefined');
}

function setfocus(obj_target) {
	if (is_defined(obj_target)) obj_target.focus();
}

function trim(str) {
	return str.replace(/^\s+|\s+$/g, '');
}

function is_empty(str) {
	return (str == null || trim(str) == '');
}

function displaytime() {
	serverdate.setSeconds(serverdate.getSeconds() + 1);

	document.getElementById("servertime").innerHTML = serverdate.strftime(dateformat);
}

// sprintf
// [ref: http://jan.moesen.nu/code/javascript/sprintf-and-printf-in-javascript/]
function sprintf() {
	// validate input parameters
	if (!arguments || arguments.length < 1 || !RegExp) return;

	var str = arguments[0];
	var re = /([^%]*)%('.|0|\x20)?(-)?(\d+)?(\.\d+)?(%|b|c|d|u|f|o|s|x|X)(.*)/;
	var a = b = [], numSubstitutions = 0, numMatches = 0;

	while (a = re.exec(str)) {
		var leftpart = a[1], pPad = a[2], pJustify = a[3], pMinLength = a[4];
		var pPrecision = a[5], pType = a[6], rightPart = a[7];

		//alert(a + '\n' + [a[0], leftpart, pPad, pJustify, pMinLength, pPrecision);

		numMatches++;
		if (pType == '%') {
			subst = '%';
		} else {
			if (++numSubstitutions >= arguments.length) {
				alert('Error! Not enough function arguments (' + (arguments.length - 1) + ', excluding the string)\nfor the number of substitution parameters in string (' + numSubstitutions + ' so far).');
			}

			var param = arguments[numSubstitutions];
			var pad = '';
			if (pPad && pPad.substr(0,1) == "'")
				pad = leftpart.substr(1,1);
		  else if (pPad)
				pad = pPad;

			var justifyRight = true;
			if (pJustify && pJustify == "-") justifyRight = false;
			var minLength = -1;
			if (pMinLength) minLength = parseInt(pMinLength);
			var precision = -1;
			if (pPrecision && pType == 'f') precision = parseInt(pPrecision.substring(1));

			var subst = param;
			if (pType == 'b') subst = parseInt(param).toString(2);
			else if (pType == 'c') subst = String.fromCharCode(parseInt(param));
			else if (pType == 'd') subst = parseInt(param) ? parseInt(param) : 0;
			else if (pType == 'u') subst = Math.abs(param);
			else if (pType == 'f') subst = (precision > -1) ? Math.round(parseFloat(param) * Math.pow(10, precision)) / Math.pow(10, precision): parseFloat(param);
			else if (pType == 'o') subst = parseInt(param).toString(8);
			else if (pType == 's') subst = param;
			else if (pType == 'x') subst = ('' + parseInt(param).toString(16)).toLowerCase();
			else if (pType == 'X') subst = ('' + parseInt(param).toString(16)).toUpperCase();
		}
		str = leftpart + subst + rightPart;
	}

	return str;
}

function windowOpen(url, title, width, height) {
	var obj_window = window.open(url, title, "width=" + width + ",height=" + height + ',toolbar=no,directories=no,scrollbars=yes,status=no,resizable=no,top=200,left=200,dependent=yes,alwaysRaised=yes');

	obj_window.opener = window;
	obj_window.focus();
}

function printPage() {
	parent.frames[1].focus();
	parent.frames[1].print();
}

function changeLabel(obj_target, value) {
	if (is_defined(obj_target)) obj_target.innerHTML = value;
}

function checkRequired(obj_target, alert_txt) {
	with (obj_target) {
		if (is_empty(value)) {
			if (is_defined(alert_txt)) alert(alert_txt);

			focus();
			return false;
		}
	}

	return true;
}

function checkMaxLength(obj_target, max_length, alert_txt) {
	with (obj_target) {
		if (value.length > max_length) {
			if (is_defined(alert_txt)) alert(alert_txt);

			focus();
			return false;
		}
	}

	return true;
}

function limitMaxLength(obj_target, max_length) {
	with (obj_target) {
		if (value.length > max_length) value = value.substring(0, max_length);
	}
}

function check_dropdown(obj_target, obj_def_idx, obj_block_idxs, alert_txt) {
	for (var i = 0; i < obj_block_idxs.length; i++) {
		with (obj_target) {
			if (selectedIndex == obj_block_idxs[i]) {
				if (is_defined(string, alert_txt) && alert_txt) alert(alert_txt);
				if (is_defined(object, obj_def_idx)) selectedIndex = obj_def_idx;

				focus();
				return false;
			}
		}
	}

	return true;
}

function switchId(obj_id, ids) {
	hideAllDivs(ids);
	showDiv(obj_id);
}

// show an element with a specified id
function showDiv(obj_id) {
	if (obj_id) setDiv(obj_id, 'block');
}

// hide an element with a specified id
function hideDiv(obj_id) {
	if (obj_id) setDiv(obj_id, 'none');
}

function hideAllDivs(obj_ids) {
	// hide each array element by id
	for (var i = 0; i < obj_ids.length; i++) {
		hideDiv(obj_ids[i]);
	}
}

// show/hide an element with a specified id
function setDiv(obj_id, status) {
	if (is_defined(obj_id)) {
		if (document.getElementById) {	// DOM3 = IE5, NS6
			document.getElementById(obj_id).style.display = status;
		} else {
			if (document.layers) {	// Netscape 4
				document.obj_id.display = status;
			} else {	// IE 4
				document.all.obj_id.style.display = status;
			}
		}
	}
}
