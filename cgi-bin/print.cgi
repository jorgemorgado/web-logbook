#!/usr/bin/perl -w
#
# $Id: print.cgi,v 1.3 2008/08/08 22:25:14 jorge Exp jorge $
#
# Web logbook print view.
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
my ($params);

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
$cgi->set_var('title',			# logbook title
	$book->{title});

# page language
$cgi->set_language($book->{lang} || $cfg->{lang}->{default});

# builds parameters list
map { $params->{$_} = $cgi->param($_) if $cgi->param($_) } $cgi->param;

print
	# page start
	$cgi->header({ -charset => $cgi->{charset} }),
	$cgi->doc_type({
		-dtd => [
			'-//W3C//DTD XHTML 1.0 Frameset//EN',
			'http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd'
		]
	}),
	$cgi->html({
			-xmlns => 'http://www.w3.org/1999/xhtml',
			-lang => 'en-US',
			'xml:lang' => 'en-US'
		},
		$cgi->head(
			$cgi->title($cgi->{title}),
			$cgi->Link({
				-rel => 'stylesheet',
				-type => 'text/css',
				-href => "$cgi->{approot}/css/ie6_fix.css"
			})
		),
		$cgi->frameset({ -rows => '45, *' }, [
			$cgi->frame({
				-title => $cgi->str(41),
				-src => 'print_top.cgi?'.$cgi->get_params,
				-name => 'top',
				-scrolling => 'no',
				-noresize => 'noresize',
				-frameborder => 0
			}).
			$cgi->frame({
				-title => $cgi->{title},
				-src => 'print_bottom.cgi?'.$cgi->get_params($params),
				-name => 'bottom',
				-frameborder => 0
			})
		])
	);

exit 0;
