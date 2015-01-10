#!/usr/bin/perl -w
#
# $Id: print_top.cgi,v 1.2 2008/08/08 22:26:40 jorge Exp jorge $
#
# Web logbook print view (top frame).
#
# Copyright 2007, Jorge Morgado. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# You should view this file with a tab stop of 2. Vim and Emacs should
# detect and adjust this automatically. On vi type ':set tabstop=2'.
#

use 5.003;
use strict;

use lib '../share/lib';

use Config::File;
use Logbook::CGI;

my ($cfg, $cgi);
my ($book);
my ($scripts, $styles);

# config file object
$cfg = new Config::File('../share/etc/logbook.cfg');

# logbook cgi object
$cgi = new Logbook::CGI;

# logbook id (from config file)
$cgi->set_var('id', lc($cgi->param('id') || $cfg->{logbook}->{default}));

# shortcut (reference) to the selected logbook configuration
$book = \%{$cfg->{logbook}->{$cgi->{id}}};

# cgi fields
$cgi->set_var('approot',		# application root directory
	$cfg->{approot});
$cgi->set_var('charset',		# character set
	$cfg->{charset});

# page language
$cgi->set_language($book->{lang} || $cfg->{lang}->{default});

# logbook cascade style sheet
if (my $style = $book->{style} || $cfg->{style}) {
	push @$styles, "$cgi->{approot}/css/$style";
}
push @$styles, "$cgi->{approot}/css/ie6_fix.css";

# logbook scripts
push @$scripts,
	"$cgi->{approot}/script/strftime.js",
	"$cgi->{approot}/script/common.js";

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles
	}),

	# page header
	$cgi->menu({
		-menus => [ qw(printpage close) ]
	}),

	# page end
	$cgi->end_doc;

exit 0;
