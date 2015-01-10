#!/usr/bin/perl -w
#
# $Id: print_bottom.cgi,v 1.4 2008/07/13 23:04:20 jorge Exp jorge $
#
# Web logbook print view (bottom frame).
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
use Logbook::DB;

my ($cfg, $cgi, $lb);
my ($book);
my ($scripts, $styles, $onload);
my ($users);
my ($params, $label);
my ($sort, $order, $expr);

# config file object
$cfg = new Config::File('../share/etc/logbook.cfg');

# loads the logbooks and users from the configuration file
map {
	$users->{$cfg->{user}->{$_}->{nick}} = $cfg->{user}->{$_}->{name}
} keys %{$cfg->{user}};

# logbook cgi object
$cgi = new Logbook::CGI;

# # logbook id (from config file)
$cgi->set_var('id', lc($cgi->param('id') || $cfg->{logbook}->{default}));

# shortcut (reference) to the selected logbook configuration
$book = \%{$cfg->{logbook}->{$cgi->{id}}};

# logbook object
$lb = new Logbook::DB(
	id => $cgi->{id},
	users => $users,
	dbdir => $book->{dir},
	attdir => $cfg->{attach}->{dir},
	archive => $cgi->{archive}
);

# cgi fields
$cgi->set_var('approot',				# application root directory
	$cfg->{approot});
$cgi->set_var('charset',				# character set
	$cfg->{charset});
$cgi->set_var('dateformat',			# date format
	$book->{dateformat}, $cfg->{dateformat});
$cgi->set_var('calformat',				# calendar date format
	$book->{calformat}, $cfg->{calformat});
$cgi->set_var('daysnew',				# logbook display new entries
	$book->{daysnew}, $cfg->{daysnew});
$cgi->set_var('entriesperpage',	# maxium entries per page
	$book->{entriesperpage}, $cfg->{entriesperpage});

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
	"$cgi->{approot}/script/common.js",
	"$cgi->{approot}/script/ajax.js",
	"$cgi->{approot}/script/treeview.js";

# this will determine if this script will make use of the view parameter
# (if received) or not; tipically, if printing the result of a search, the
# view will be discarded (searches do not supported groupped views since a
# search result is already a group on itself).
my $use_view;

$onload .= "setInterval('displaytime()', 1000);";

# process the action if any
if ($cgi->param('action')) {
	# search action
	if ($cgi->param('action') eq 'search') {
		$params->{action} = $cgi->param('action');
		$params->{case} = $cgi->param('case') if $cgi->param('case');
		$params->{andor} = $cgi->param('andor') if $cgi->param('andor');

		my $crit = $cgi->get_criteria;
		for (keys %$crit) {
			$params->{$_} = $cgi->escape_uri($crit->{$_});

			if (/^sdate$/) {
				$crit->{$_} = [ 1, '%d>='.$cgi->date2ts($crit->{$_}) ];
			} elsif (/^edate$/) {
				$crit->{$_} = [ 1, '%d<='.$cgi->date2ts($crit->{$_}) ];
			} elsif (/^user$/) {
				$crit->{$_} = [ 2, '"%s"=~/'.$lb->escape_criteria($crit->{$_}).'/i' ];
			} elsif (/^subject$/) {
				$crit->{$_} = [ 3, '"%s"=~/'.$lb->escape_criteria($crit->{$_}).'/i' ];
				chop($crit->{$_}[1]) if $params->{case};
			} elsif (/^desc$/) {
				$crit->{$_} = [ 4, '"%s"=~/'.$lb->escape_criteria($crit->{$_}).'/i' ];
				chop($crit->{$_}[1]) if $params->{case};
			} elsif (/^attach$/) {
				$crit->{$_} = [ 5, '%d'.($crit->{$_} == 1 ? '>' : '==').'0' ];
			}
		}

		# get logbook entries list (search)
		$lb->search_extended($crit, $params->{andor});

		$label = 32;
		$use_view = 0;

		($sort, $order, $expr) = (0, 'd', '0|1');
	}
} else {
	# get logbook entries list (all records)
	$lb->fetchall;

	$label = 31;
	$use_view = ($cgi->{view} > 1);

	# on-load actions
	$onload .= 'initTree();' if $cgi->{view} > 1;

	for ($cgi->{view}) {
		if (/^(2|3|4|5)$/) {	# group by day, week, month or year
			($sort, $order, $expr) = (1, 'd', '0|1');
		} elsif (/^6$/) {			# group by user
			($sort, $order, $expr) = (2, 'a', '-');
		} elsif (/^7$/) {	# group by subject
			($sort, $order, $expr) = (3, 'a', '-');
		} else {	# default view
			($sort, $order, $expr) = (0, 'd', '0|1');
		}
	}
}

$cgi->{total_entries} = $#{$lb->{set}} + 1;

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => $onload
	}),

	# page header
	$cgi->caption($book->{title}),

	# page content
	$cgi->start_content;

if ($cgi->{total_entries} > -1) {
  my $exp = $cgi->sort_expr($sort, $order, $expr);

	print
		# dump header
		$cgi->section(sprintf($cgi->str($label), $cgi->{total_entries})),

  	# sort buttons
		($use_view ?
			$cgi->Tr(
				$cgi->td({ -colspan => $cgi->{archive} ? 4 : 6 },
					$cgi->sort_buttons('index.cgi?%s', $sort)
				)
			)
			:
			$cgi->Tr(
				$cgi->td([
					$cgi->sort_buttons('print_bottom.cgi?%s', 1, $params),
					$cgi->sort_buttons('print_bottom.cgi?%s', 2, $params)
				]),
				$cgi->td({ -colspan => 2 },
					$cgi->sort_buttons('print_bottom.cgi?%s', 3, $params)
				)
			)
		),

		# logbook entries dump starts
		($use_view ?
			$cgi->dump(
				'print_bottom.cgi?%s',
				$lb->{users},
				0,
				sort { eval $exp } @{$lb->{set}}
			)
			:
			$cgi->view_default(
				'print_bottom.cgi?%s',
				$lb->{users},
				0,
				sort { eval $exp } @{$lb->{set}}
			)
		),

		# show page or expand/collapse buttons
		($use_view ?
			# expand/collapse buttons
			$cgi->expand_collapse_buttons
			:
			# page buttons
			$cgi->page_buttons('print_bottom.cgi?%s', $params)
		);
}

print
	# page end
	$cgi->end_content,
	$cgi->footer($cfg->{footnote}),
	$cgi->end_doc;

exit 0;
