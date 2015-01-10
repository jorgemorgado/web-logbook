#!/usr/bin/perl -w
#
# $Id: index.cgi,v 1.7 2008/07/13 23:10:06 jorge Exp jorge $
#
# Web logbook main page.
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

use Util qw(is_empty trim);
use Config::File;
use Log::Simple;
use Logbook::CGI;
use Logbook::DB;
use Mail::SMTP;

my ($cfg, $log, $cgi, $lb, $mail);
my ($book, $frm);
my ($scripts, $styles, $onload);
my ($users);

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
$cgi->set_var('daysnew',				# display new entries
	$book->{daysnew}, $cfg->{daysnew});
$cgi->set_var('calformat',				# calendar date format
	$book->{calformat}, $cfg->{calformat});
$cgi->set_var('refresh',				# page reload interval
	$book->{refresh}, $cfg->{refresh});
$cgi->set_var('entriesperpage',	# maxium entries per page
	$book->{entriesperpage}, $cfg->{entriesperpage});

# page language
$cgi->set_language($book->{lang} || $cfg->{lang}->{default});

# logbook's banner
$cgi->set_banner($book->{banner}, $cfg->{banner});

# merge specific logbook mail directives into the global ones
if (defined $book->{mail}->{active} && $book->{mail}->{active} && defined $book->{mail}) {
  map {
    $cfg->{mail}->{$_} = $book->{mail}->{$_}
  } keys %{$book->{mail}};
}

# logbook cascade style sheet
if (my $style = $book->{style} || $cfg->{style}) {
	push @$styles, "$cgi->{approot}/css/$style";
}

# logbook scripts
push @$scripts,
	"$cgi->{approot}/script/calendar_$cgi->{calformat}.js",
	"$cgi->{approot}/script/strftime.js",
	"$cgi->{approot}/script/common.js",
	"$cgi->{approot}/script/popupmenu.js",
	"$cgi->{approot}/script/ajax.js",
	"$cgi->{approot}/script/treeview.js";

# initial form values
$frm = {
	action => 'add',		# default action
	label => $cgi->str(24),
	users => $users,
	user => $cgi->param('user') || undef,
	nr => undef,
	date => undef,
	subject => '',
	desc => '',
	attid => sprintf('%d-%d', time, $$),
	attinfo => $cgi->attach_info(0)
};

# process the action if any
if ($cgi->param('action')) {
	if ($cgi->param('action') eq 'add' || $cgi->param('action') eq 'save') {
		my $ts;

		# valid date (if not empty)
		$log->add($log->{ERROR}, $cgi->str(156))
			unless is_empty($cgi->param('date')) || ($ts = $cgi->date2ts($cgi->param('date')));

		# validate subject (can't be empty)
		$log->add($log->{WARNING}, $cgi->str(23))
			if is_empty($cgi->param('subject'));

		# check email settings -- must be done before showing warnings/errors
		check_mail();

		# if there are errors
		if ($log->gettotal) {
			$frm->{action} = $cgi->param('action');
			$frm->{nr} = $cgi->param('nr');
			$frm->{date} = $cgi->param('date');
			$frm->{subject} = $cgi->param('subject') || '';
			$frm->{desc} = $cgi->param('desc');

		} else {
			# timestamp is either what was entered or if undefined, takes 'now'
			$ts = $ts || time;

			send_mail(
				trim($cgi->param('subject')),
				"Time: ".scalar localtime ($ts)."\n".
				"User: ".$cgi->param('user')."\n\n".
				$cgi->param('desc')
			) if $cfg->{mail}->{active};

			# add action
			if ($cgi->param('action') eq 'add') {
				my @attlist = $lb->attach_get($cgi->param('attid'));

				my $nr = $lb->insert([
					$ts,
					$cgi->param('user'),
					trim($cgi->param('subject')),
					$cgi->param('desc'),
					($#attlist + 1)
				]);

				$lb->attach_move($nr, @attlist) if ($#attlist > -1);

				# when inserting a new entry the first page will always be displayed
				$cgi->reset_page;

			# edit action
			} elsif ($cgi->param('action') eq 'save') {
				if ($cgi->param('nr')) {
					my @attlist = $lb->attach_get($cgi->param('attid'));

					$lb->update($cgi->param('nr'), [
						$ts,
						$cgi->param('user'),
						trim($cgi->param('subject')),
						$cgi->param('desc'),
						($#attlist + 1)
					]);

					# make sure the same user remains selected
					$frm->{user} = $cgi->param('user');
				}
			}
		}

	} elsif ($cgi->param('action') eq 'edit') {
		if ($cgi->param('nr')) {
			$frm->{nr} = $cgi->param('nr');
			$frm->{action} = 'save';
			$frm->{label} = sprintf($cgi->str(70), $frm->{nr});

			($frm->{date},
			$frm->{user},
			$frm->{subject},
			$frm->{desc},
			$frm->{attinfo}) = $lb->fetch($frm->{nr});

			$frm->{date} = $cgi->ts2date($frm->{date});
			$frm->{attid} = $frm->{nr};
			$frm->{attinfo} = $cgi->attach_info($frm->{attinfo});
		}

	# delete action
	} elsif ($cgi->param('action') eq 'delete' && $cgi->param('nr')) {
		$lb->delete($cgi->param('nr')) if $lb->attach_del($cgi->param('nr'));
	}
}

# get logbook entries list
$lb->fetchall;

$cgi->{total_entries} = $#{$lb->{set}} + 1;

# on-load actions
$onload .= "setInterval('displaytime()', 1000);";
$onload .= 'initTree();' if $cgi->{view} > 1;
$onload .= "setfocus(document.forms['form'].elements['subject']);"
	unless $cgi->{archive};

print
	# page start
	$cgi->start_doc(
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => $onload
	),

	# page header
	$cgi->menu({
		-menus => [ $cgi->{total_entries} == 0 ?
			qw(browse) : qw(search print sep browse archive sep trends quicksearch view)
		],
		-langs => $cfg->{lang},
		-books => $cfg->{logbook}
	}),
	$cgi->caption({
		-title => $book->{title}
	});

print
	# form start (if not browsing an archive)
	$cgi->start_form({
		-name => 'form',
		-method => 'POST',
		-onsubmit => "return ".
			sprintf("checkRequired(this.subject, '%s') && ",
				$cgi->str(23)).
			sprintf("checkMaxLength(this.subject, %d, '%s') && ",
				$cgi->{subject_maxlen}, $cgi->str(102)).
			sprintf("checkMaxLength(this.desc, %d, '%s');",
				$cgi->{desc_maxlen}, $cgi->str(103))
	}) unless $cgi->{archive};

print
	# page content
	$cgi->start_content;

# add/edit form (if not browsing an archive)
print
	# add new entry / import
	$cgi->section(
		$cgi->table({ -cellspacing => 0, -cellpadding => 0 },
			$cgi->Tr({ -class => 'section' },
				$cgi->td($frm->{label}),
				$cgi->td({ -align => 'right' }, $cgi->menu_options([ 'import' ]))
			)
		)
	),
	$cgi->Tr({ -class => 'nowrap' }, [
		# table header
		$cgi->th({ -align => 'left', -nowrap => 'nowrap' }, [
			$cgi->str(58).' '.$cgi->img('clock.gif', 16, 16, $cgi->str(58)),
			$cgi->str(59).' '.$cgi->img('user.gif', 16, 16, $cgi->str(59))
		]).
		$cgi->th({ -align => 'left', -colspan => 4 },
			$cgi->str(25), ' / ', $cgi->str(26),
			$cgi->img('desc.gif', 16, 16, $cgi->str(25).' / '.$cgi->str(26))
		),

		# input form (date, user, subject, description)
		$cgi->td({ -valign => 'top', -nowrap => 'nowrap', -rowspan => 2 }, [
			$cgi->date({ -name => 'date', -value => $frm->{date} }).
			$cgi->br.
			$cgi->note($cgi->str(27)),
			$cgi->users({
				-name => 'user',
				-values => $frm->{users},
				-default => $frm->{user}
			})
		]).
		$cgi->td({ -valign => 'top', -colspan => 4 },
			$cgi->subject({ -name => 'subject', -value => $frm->{subject} }),
			$cgi->br,
			$cgi->description({
				-name => 'desc',
				-value => $frm->{desc},
				-maxlength => $cgi->{desc_maxlen}
			})
		),

		# form buttons
		$cgi->td({ -colspan => 4 },
			$cgi->submit({ -value => $cgi->str(28), -tabindex => $cgi->get_tabindex }),
			$cgi->reset({ -value => $cgi->str(29), -tabindex => $cgi->get_tabindex }),
			$cgi->form_attach($cgi->str(30), $frm->{attid}),
      $cgi->label('attbtn', 'attinfo', sprintf('(%s)', $frm->{attinfo}), $frm->{attinfo}),
			$cgi->form_hidden({
				-action => $frm->{action},
				-nr => $frm->{nr}
			})
		)
	]) unless $cgi->{archive};

if ($log->gettotal) {
	print
		$cgi->Tr(
			$cgi->td({ -colspan => 6 },
				$cgi->br,
				$cgi->notify($log->getlevel, $log->getall)
			)
		);
}

if ($cgi->{total_entries} > 0) {
	my ($sort, $order, $expr);

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

	my $exp = $cgi->sort_expr($sort, $order, $expr);

	print
		# dump header / export
		$cgi->section(
			$cgi->table({ -cellspacing => 0, -cellpadding => 0 },
				$cgi->Tr({ -class => 'section' },
					$cgi->td(sprintf($cgi->str(31), $cgi->{total_entries})),
					$cgi->td({ -align => 'right' }, $cgi->menu_options([ 'export' ]))
				)
			)
		),

		# sort buttons
		($cgi->{view} > 1 ?
			$cgi->Tr(
				$cgi->td({ -colspan => $cgi->{archive} ? 4 : 6 },
					$cgi->sort_buttons('index.cgi?%s', $sort)
				)
			)
			:
			$cgi->Tr(
				$cgi->td([
					$cgi->sort_buttons('index.cgi?%s', 1),
					$cgi->sort_buttons('index.cgi?%s', 2)
				]),
				$cgi->td({ -colspan => $cgi->{archive} ? 2 : 4 },
					$cgi->sort_buttons('index.cgi?%s', 3)
				)
			)
		),

		# logbook entries dump starts
		$cgi->dump(
			'index.cgi?%s',
			$lb->{users},
			!$cgi->{archive},
			sort { eval $exp } @{$lb->{set}}
		),

		# show page or expand/collapse buttons
		($cgi->{view} > 1 ?
			# expand/collapse buttons
			$cgi->expand_collapse_buttons
			:
			# page buttons
			$cgi->page_buttons('index.cgi?%s')
		);
}

print
	# content end
	$cgi->end_content;

print
	# form end (if not browsing an archive)
	$cgi->end_form unless $cgi->{archive};

print
	# page end
	$cgi->footer($cfg->{footnote}),
	$cgi->end_doc;

exit 0;

sub check_mail {
	if (defined($cfg->{mail}->{active}) && $cfg->{mail}->{active}) {
		# these are mandatory and will produce a notice event
		$log->add($log->{NOTICE}, sprintf($cgi->str(157), 'ClientName', 'Mail'))
			unless defined $cfg->{mail}->{clientname};
		$log->add($log->{NOTICE}, sprintf($cgi->str(157), 'ServerName', 'Mail'))
			unless defined $cfg->{mail}->{servername};
		$log->add($log->{NOTICE}, sprintf($cgi->str(157), 'FromAddress', 'Mail'))
			unless defined $cfg->{mail}->{fromaddress};
		$log->add($log->{NOTICE}, sprintf($cgi->str(157), 'ToAddress', 'Mail'))
			unless defined $cfg->{mail}->{toaddress};

		# these are optional, so defaults are assumed if not provided
		$cfg->{mail}->{serverport} = 25
			unless defined($cfg->{mail}->{serverport});
		$cfg->{mail}->{subjecttag} = "[Web-Logbook]"
			unless defined($cfg->{mail}->{subjecttag});
	} else {
		$cfg->{mail}->{active} = 0;
	}

	return $cfg->{mail}->{active};
}

sub send_mail {
	my $subject = shift;
	my $body = shift;

	# smtp mail object
	$mail = new Mail::SMTP(
		clientname => $cfg->{mail}->{clientname},
		servername => $cfg->{mail}->{servername},
		organization => $cfg->{mail}->{organization},
		from_address => $cfg->{mail}->{fromaddress},
		to_address => $cfg->{mail}->{toaddress},
		mailpfx => $cfg->{mail}->{subjecttag},
	);

	unless ($mail->send($subject, $body)) {
		warn "Mail Error $mail->{errmsg}\n";
	}
}
