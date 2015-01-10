// Title: Web-lobook tree view
// URL: http://www.morgado.ch ; http://web-logbook.sourceforge.net
// Version: 1.0
// Date: 24-07-2008 (dd-mm-yyyy)
// Note: Permission given to use this script in ANY kind of applications if
//    header lines are left unchanged. Some parts of this code was based on
//    the 'Static folder tree' from Alf Magne Kalleland of DTHMLGoodies.com

var imgFolder = approot + '/images/';	// path to images
var imgPlus = 'plus.gif';
var imgMinus = 'minus.gif';

var ajaxRequestFile = approot + '/cgi-bin/groupnodes.cgi';
var ajaxObjectArray = new Array();

// get the parameters/values from the given URL query string
// returns an associative array in the form param[name] => value
function getParams(query) {
	var aParams = new Array();

	query = query.substr(query.indexOf("#") + 1);
	query = query.substr(query.indexOf('?') + 1);

	var aQuery = query.split("&");
	for (var i = 0; i < aQuery.length; i++) {
		var aParam = aQuery[i].split("=");

		aParams[aParam[0]] = aParam[1];
	}

	return aParams;
}

function setParams(aParams) {
	var query = '';

	// cycles through all parameters to build an access query
	for (var param in aParams) {
		query += '&' + param + '=' + aParams[param];
	}

	return query.substr(query.indexOf('&') + 1);
}

function nodeRefresh(query, idInput) {
	var sParams, aParams = [];
	var firstLi, firstLabel;

	if (!document.getElementById('treeNode' + idInput)) return;
	thisNode = document.getElementById('treeNode' + idInput).getElementsByTagName('IMG')[0];

	var parentNode = thisNode.parentNode;
	var ul = parentNode.getElementsByTagName('UL')[0];

	// get logbook data
	if ((firstLi = ul.getElementsByTagName('LI')[0]) &&
			(firstLabel = firstLi.getElementsByTagName('LABEL')[0])) {
		sParams = firstLabel.getAttribute('TITLE');
		aParams = getParams(sParams);
	}

	// get logbook page to refresh
	var aQuery = getParams(query);
	if (aQuery['page']) aParams['page'] = aQuery['page'];

	// execute AJAX function
	runAJAX(ul, idInput, aParams);
}

function nodeShowHide(event, idInput) {
	var sParams, aParams = [];
	var firstLi, firstA;

	if (idInput) {
		if (!document.getElementById('treeNode' + idInput)) return;
		thisNode = document.getElementById('treeNode' + idInput).getElementsByTagName('IMG')[0];
	} else {
		thisNode = this;
		if (this.tagName == 'A') thisNode = this.parentNode.getElementsByTagName('IMG')[0];
	}

	if (thisNode.style.visibility == 'hidden') return;

	var parentNode = thisNode.parentNode;
	if (!idInput) idInput = parentNode.id.replace(/[^0-9]/g,'');

	if (thisNode.src.indexOf(imgPlus) >= 0) {
		thisNode.src = thisNode.src.replace(imgPlus, imgMinus);
		var ul = parentNode.getElementsByTagName('UL')[0];
		ul.style.display = 'block';

		// get logbook data
		if ((firstLi = ul.getElementsByTagName('LI')[0]) &&
				(firstA = firstLi.getElementsByTagName('A')[0])) {
			sParams = firstA.getAttribute('HREF');
			aParams = getParams(sParams);
		}

		// execute AJAX function
		runAJAX(ul, idInput, aParams);
	} else {
		thisNode.src = thisNode.src.replace(imgMinus, imgPlus);
		parentNode.getElementsByTagName('UL')[0].style.display = 'none';
	}

	return false;
}

function runAJAX(ul, idInput, aParams) {
	// get the node's parent id
	aParams['idParent'] = idInput - 1;

	if (aParams['idParent'] && aParams['nr']) {
		ajaxObjectArray[ajaxObjectArray.length] = new sack();
		var ajaxIndex = ajaxObjectArray.length - 1;
		ajaxObjectArray[ajaxIndex].requestFile = ajaxRequestFile;

		// call-back function to execute by AJAX lib
		ajaxObjectArray[ajaxIndex].onCompletion = function() {
			getNodeDataFromServer(ajaxIndex, ul.id, aParams['idParent']);
		};

		// run AJAX
		ajaxObjectArray[ajaxIndex].runAJAX(setParams(aParams));
	}
}

function expandAll(idTree) {
	var aItems = document.getElementById(idTree).getElementsByTagName('LI');

	for (var i = 0; i < aItems.length; i++) {
		var aSubItems = aItems[i].getElementsByTagName('UL');

		if (aSubItems.length > 0 && aSubItems[0].style.display != 'block')
			nodeShowHide(false, aItems[i].id.replace(/[^0-9]/g, ''));
	}
}

function collapseAll(idTree) {
	var aItems = document.getElementById(idTree).getElementsByTagName('LI');

	for (var i = 0; i < aItems.length; i++) {
		var aSubItems = aItems[i].getElementsByTagName('UL');

		if (aSubItems.length > 0 && aSubItems[0].style.display == 'block')
			nodeShowHide(false, aItems[i].id.replace(/[^0-9]/g, ''));
	}
}

function getNodeDataFromServer(ajaxIndex, idUl, idParent) {
	document.getElementById(idUl).innerHTML = ajaxObjectArray[ajaxIndex].response;
	ajaxObjectArray[ajaxIndex] = false;
}

function initTree() {
	var idNode = 1;
	var cntTreeUl = 0;

	var tree = document.getElementById('tree');

	if (tree) {
		// get an array of all menu items
		var aItems = tree.getElementsByTagName('LI');

		for (var i = 0; i < aItems.length; i++) {
			var aSubItems = aItems[i].getElementsByTagName('UL');
			var img = document.createElement('IMG');

			img.src = imgFolder + imgPlus;
			img.onclick = nodeShowHide;

			if (aSubItems.length == 0)
				img.style.visibility = 'hidden';
			else
				aSubItems[0].id = 'tree_ul_' + cntTreeUl++;

			var aTag = aItems[i].getElementsByTagName('A')[0];

			aTag.onclick = nodeShowHide;
			aItems[i].insertBefore(img, aTag);

			if (!aItems[i].id)
				aItems[i].id = 'treeNode' + ++idNode;
		}
	}
}

window.onload = initTree;
