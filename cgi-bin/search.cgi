#!/usr/bin/perl -w
#
# $Id: search.cgi,v 1.7 2008/07/13 23:06:16 jorge Exp jorge $
#
# Web logbook search page.
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

use Util qw(swap);
use Config::File;
use Log::Simple;
use Logbook::CGI;
use Logbook::DB;

my ($cfg, $log, $cgi, $lb);
my ($book, $frm);
my ($scripts, $styles);
my ($users, $attach);
my ($params);

# config file object
$cfg = new Config::File('../share/etc/logbook.cfg');

# simple log (event) object
$log = new Log::Simple(3);

# loads the logbooks and users from the configuration file
map {
	$users->{$cfg->{user}->{$_}->{nick}} = $cfg->{user}->{$_}->{name}
} keys %{$cfg->{user}};

# logbook cgi object
$cgi = new Logbook::CGI;

# logbook id (from config file)
$cgi->set_var('id', lc($cgi->param('id') || $cfg->{logbook}->{default}));

# shortcut (reference) to the selected logbook configuration
$book = \%{$cfg->{logbook}->{$cgi->{id}}};

# logbook object
$lb = new Logbook::DB(
	id => $cgi->{id},
	users => $users,
	dbdir => $book->{dir},
	archive => $cgi->{archive}
);

# cgi fields
$cgi->set_var('approot',				# application root directory
	$cfg->{approot});
$cgi->set_var('charset',				# character set
	$cfg->{charset});
$cgi->set_var('dateformat',			# date format
	$book->{dateformat}, $cfg->{dateformat});
$cgi->set_var('daysnew',				# display new entries
	$book->{daysnew}, $cfg->{daysnew});
$cgi->set_var('calformat',				# calendar date format
	$book->{calformat}, $cfg->{calformat});
$cgi->set_var('entriesperpage',	# maxium entries per page
	$book->{entriesperpage}, $cfg->{entriesperpage});

# page language
$cgi->set_language($book->{lang} || $cfg->{lang}->{default});

# logbook's banner
$cgi->set_banner($book->{banner}, $cfg->{banner});

# logbook cascade style sheet
if (my $style = $book->{style} || $cfg->{style}) {
	push @$styles, "$cgi->{approot}/css/$style";
}

# logbook scripts
push @$scripts,
	"$cgi->{approot}/script/calendar_$cgi->{calformat}.js",
	"$cgi->{approot}/script/strftime.js",
	"$cgi->{approot}/script/common.js",
	"$cgi->{approot}/script/popupmenu.js";

# adds the blank user (no user) to the list
$users->{'('.$cgi->str(59).')'} = '';

# initial form values
$frm = {
	#action => '',			# default action is 'no action'
	users => $users,
	user => $cgi->param('user') || undef,
	sdate => undef,
	edate => undef,
	subject => '',
	desc => ''
};

# attachments search criteria
$attach = {
	0 => $cgi->str(34),
	1 => $cgi->str(35),
	2 => $cgi->str(36)
};

# extra parameters
$params = {};

# process the action if any
if ($cgi->param('action')) {
	# search action
	if ($cgi->param('action') eq 'search') {
		$params->{action} = 'search';
		$params->{case} = $cgi->param('case') if $cgi->param('case');
		$params->{andor} = $cgi->param('andor') if $cgi->param('andor');

		my ($sdate, $edate);
		my $crit = $cgi->get_criteria;
		for (keys %$crit) {
			$frm->{$_} = $crit->{$_};
			$params->{$_} = $cgi->escape_uri($crit->{$_});

			if (/^sdate$/) {
				$sdate = $cgi->date2ts($crit->{$_});
				$crit->{$_} = [ 1, '%d>='.$sdate ];
			} elsif (/^edate$/) {
				$edate = $cgi->date2ts($crit->{$_});
				$crit->{$_} = [ 1, '%d<='.$edate ];
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

		if ($sdate && $edate && $sdate > $edate) {
			swap(\$frm->{sdate}, \$frm->{edate});
			$log->add($log->{WARNING}, $cgi->str(73));
		}

		# get logbook entries list
		$lb->search_extended($crit, $params->{andor});

		$cgi->{total_entries} = $#{$lb->{set}} + 1;

		$log->add($log->{NOTICE}, $cgi->str(76)) unless $cgi->{total_entries} > 0;
	}

# no action - a new search is starting
} else {
	# this ensures the current user won't be pre-selected in the search form
	$frm->{user} = undef;

	# and this ensures the search results will always start on the first page
	$cgi->reset_page;
}

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => "setInterval('displaytime()', 1000);".
			"setfocus(document.forms['form'].elements['subject']);",
	}),

	# page header
	$cgi->menu({
		-menus => [ $cgi->{total_entries} == 0 ?
			qw(browse sep trends back) : qw(print sep browse sep trends back)
		],
		-langs => $cfg->{lang},
		-params => $params
  }),
	$cgi->caption(
		-title => sprintf($cgi->str($cgi->{archive} ? 37 : 33), $book->{title})
	),

	# page content
	$cgi->start_form({ -name => 'form', -method => 'POST' }),
	$cgi->start_content,

	# search form
	$cgi->section($cgi->str(38).($cgi->{archive} ? sprintf(' (%s)', $cgi->get_date($cgi->{archive})) : ''), 4),
	$cgi->Tr([
		# table header
		$cgi->th({ -align => 'left', -nowrap => 'nowrap' }, [
			$cgi->str(58).' '.$cgi->img('clock.gif', 16, 16, $cgi->str(58)),
			$cgi->str(59).' '.$cgi->img('user.gif', 16, 16, $cgi->str(59))
		]).
		$cgi->th({ -align => 'left', -colspan => 2 },
			$cgi->str(25), ' / ', $cgi->str(26),
			$cgi->img('desc.gif', 16, 16, $cgi->str(25).' / '.$cgi->str(26))
		),

		# input form (from: date, user, subject, description)
		$cgi->td({ -valign => 'top', -nowrap => 'nowrap' },
			$cgi->note($cgi->str(65).':'),
			$cgi->date({ -name => 'sdate', -value => $frm->{sdate}, -tabindex => 1 })
		).
		$cgi->td({ -valign => 'top', -rowspan => 5 },
			$cgi->users({
				-name => 'user',
				-values => $frm->{users},
				-default => $frm->{user},
				-tabindex => 5
			})
		).
		$cgi->td({ -valign => 'top', -rowspan => 2, -colspan => 2 },
			$cgi->subject({
				-name => 'subject',
				-value => $frm->{subject},
				-tabindex => 6
			}),
			$cgi->br,
			$cgi->description({
				-name => 'desc',
				-value => $frm->{desc},
				-tabindex => 8
			})
		),

		# input form (to: date)
		$cgi->td({ -valign => 'top', -nowrap => 'nowrap', -rowspan => 4 },
			$cgi->note($cgi->str(66).':'),
			$cgi->date({ -name => 'edate', -value => $frm->{edate}, -tabindex => 3 })
		),

		# case checkbox
		$cgi->td({ -colspan => 2 },
			$cgi->checkbox({
				-name => 'case',
				-label => $cgi->str(39),
				-tabindex => $cgi->set_tabindex(9)
			}),
		),

		# and/or radio buttons
		$cgi->td({ -colspan => 2 },
			$cgi->radio_group({
				-name => 'andor',
				-values => [ 0, 1 ],
				-labels => { 0 => $cgi->str(116), 1 => $cgi->str(117) },
				-linebreak => 0,
				-default => '',
				-tabindex => $cgi->get_tabindex
			})
		),

		# form buttons
		$cgi->td({ -colspan => 2 },
			$cgi->submit({
				-value => $cgi->str(54),
				-tabindex => $cgi->get_tabindex
			}),
			$cgi->reset({
				-value => $cgi->str(29),
				-tabindex => $cgi->get_tabindex
			}),
			$cgi->popup_menu({
				-name => 'attach',
				-values => [ sort keys %$attach ],
				-labels => \%{$attach},
				-tabindex => $cgi->get_tabindex
			}),
			$cgi->form_hidden({ -action => 'search' })
		)
	]);

if ($log->gettotal) {
	print
		$cgi->Tr(
			$cgi->td({ -colspan => 4 },
				$cgi->br,
				$cgi->notify($log->getlevel, $log->getall)
			)
		);

} elsif ($cgi->{total_entries} > 0) {
	my $exp = $cgi->sort_expr(0, 'd', '0|1');

	print
		# dump header / export
		$cgi->section(
			$cgi->table({ -cellspacing => 0, -cellpadding => 0 },
				$cgi->Tr({ -class => 'section' },
					$cgi->td(sprintf $cgi->str(32), $cgi->{total_entries}),
					$cgi->td({ -align => 'right' },
						$cgi->menu_options([ 'export' ], $params)
					)
				)
			)
		),

		# sort buttons
		$cgi->Tr(
			$cgi->td([
				$cgi->sort_buttons('search.cgi?%s', 1, $params),
				$cgi->sort_buttons('search.cgi?%s', 2, $params)
			]),
			$cgi->td({ -colspan => 2 },
				$cgi->sort_buttons('search.cgi?%s', 3, $params)
			)
		),

		# logbook entries dump starts
		$cgi->view_default(
			'search.cgi?%s',
			$lb->{users},
			0,
			sort { eval $exp } @{$lb->{set}}
		),

		# show page buttons
		$cgi->page_buttons('search.cgi?%s', $params);
}

print
	# page end
	$cgi->end_content,
	$cgi->end_form,
	$cgi->footer($cfg->{footnote}),
	$cgi->end_doc;

exit 0;
