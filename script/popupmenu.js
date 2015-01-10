// Title: Popup-Menu
// URL: http://www.morgado.ch ; http://web-logbook.sourceforge.net
// Version: 1.0
// Date: 21-07-2008 (dd-mm-yyyy)
// Note: Permission given to use this script in ANY kind of applications if
//    header lines are left unchanged.

var overmenupup = false;

function hideMenu(e) {
	var menupup = document.getElementById('menupup');

	if (!overmenupup && menupup.style.display == 'block')
		menupup.style.display='none';

	// always return true or any mouse down event might be 'compromised'
	return true;
}

function showMenu(e) {
	var menupup = document.getElementById('menupup');

	if (menupup.style.display == 'none') {
		menupup.style.top = 2 * document.getElementById('menutup').offsetTop + 4 + 'px';
		menupup.style.left = document.getElementById('menutup').offsetLeft + 'px';

		menupup.style.display='block';
	}

	return true;
}

// TODO: ideally, the background colors should be obtained from the css to
// avoid having style definitions in more than one place. To be fixed...
function overOption(obj_target) {
	with (obj_target)
		style.backgroundColor = '#cfcfcf';
}

function outOption(obj_target) {
	with (obj_target)
		style.backgroundColor = '#ffffff';
}

document.onmousedown = hideMenu;
