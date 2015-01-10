#!/usr/bin/perl -w
#
# $Id: trends.cgi,v 1.6 2008/07/22 23:45:54 jorge Exp jorge $
#
# Web logbook trends (statistics) functions.
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
my ($users);
my ($top, $stat, @avg);

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
	dbdir => $book->{dir},
	archive => $cgi->{archive}
);

# cgi fields
$cgi->set_var('approot',		# application root directory
	$cfg->{approot});
$cgi->set_var('charset',		# character set
	$cfg->{charset});
$cgi->set_var('dateformat',	# date format
	$book->{dateformat}, $cfg->{dateformat});
$cgi->set_var('calformat',		# calendar date format
	$book->{calformat}, $cfg->{calformat});

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

# initial form values
$frm = {
	#action => '',			# default action is 'no action'
	sdate => undef,
	edate => undef,
	limit => 10
};

# process the action if any
if ($cgi->param('action')) {
	# action submit
	if ($cgi->param('action') eq 'submit') {
		$frm->{limit} = $cgi->param('limit') if $cgi->param('limit');

		my ($sdate, $edate);
		my $crit = $cgi->get_criteria;
		for (keys %$crit) {
			$frm->{$_} = $crit->{$_};

			if (/^sdate$/) {
				$sdate = $cgi->date2ts($crit->{$_});
				$crit->{$_} = [ 1, '%d>='.$sdate ];
			} elsif (/^edate$/) {
				$edate = $cgi->date2ts($crit->{$_});
				$crit->{$_} = [ 1, '%d<='.$edate ];
			}
		}

		if ($sdate && $edate && $sdate > $edate) {
			swap(\$frm->{sdate}, \$frm->{edate});
			$log->add($log->{WARNING}, $cgi->str(73));
		}

		# get logbook entries list
		$lb->search_extended($crit);

		if ($#{$lb->{set}} == -1) {
			$log->add($log->{NOTICE}, $cgi->str(76));

		} else {
			# lets rock the trends...
			my $exp = $cgi->sort_expr(0, 'd', '0|1');

			for (sort { eval $exp } @{$lb->{set}}) {
				# subject, user and attachment tops
				$top->{subject}->{$_->[3]}++;
				$top->{user}->{$users->{$_->[2]}}++;
				$top->{attcnt}->{$cgi->attach_info($_->[5])}++;

				# statistics
				if ($_->[5]) {
					$stat->{with_attach}++;	# total entries with attachments
					$stat->{total_attach} += $_->[5];	# total attachments
				}
				$stat->{active_users}->{$_->[2]} = 1;	# total active users

				# oldest entry
				if ($stat->{oldest}) {
					$stat->{oldest} = $_->[1] if $_->[1] < $stat->{oldest};
				} else {
					$stat->{oldest} = $_->[1];
				}

				# newest entry
				if ($stat->{newest}) {
					$stat->{newest} = $_->[1] if $_->[1] > $stat->{newest};
				} else {
					$stat->{newest} = $_->[1];
				}
			}
			$stat->{recs} = $#{$lb->{set}} + 1;		# total records

			# trends timeline
			$stat->{period} = $stat->{newest} - $stat->{oldest};

			# averages
			push @avg, [ $cgi->str(77), $stat->{recs} / ($stat->{period} / 900) ]
				if $stat->{period} > 3600;	# 1 hour
			push @avg, [ $cgi->str(78), $stat->{recs} / ($stat->{period} / 3600) ]
				if $stat->{period} > 86400;	# 1 day
			push @avg, [ $cgi->str(79), $stat->{recs} / ($stat->{period} / 86400) ]
				if $stat->{period} > 604800;	# 1 week
			push @avg, [ $cgi->str(80), $stat->{recs} / ($stat->{period} / 604800) ]
				if $stat->{period} > 2628003;	# ~1 month (30.4167 days)
			push @avg, [ $cgi->str(81), $stat->{recs} / ($stat->{period} / 2628003) ]
				if $stat->{period} > 31536000;	# 1 year (365 days)
			push @avg, [ $cgi->str(82), $stat->{recs} / ($stat->{period} / 31536000) ]
				if $stat->{period} >= 31536000;	# > 1 year
		}
	}
}

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => "setInterval('displaytime()', 1000);".
			"setfocus(document.forms['form'].elements['sdate']);",
	}),

	# page header
	$cgi->menu({
		-menus => [ qw(search browse back) ],
		-langs => $cfg->{lang},
  }),
	$cgi->caption(
		-title => sprintf($cgi->str($cgi->{archive} ? 84 : 83), $book->{title})
	),

	# page content
	$cgi->start_form({ -name => 'form', -method => 'POST' }),
	$cgi->start_content,

	# trends period form
	$cgi->section($cgi->str(85).($cgi->{archive} ? sprintf(' (%s)', $cgi->get_date($cgi->{archive})) : ''), 2),
	$cgi->Tr({ -class => 'nowrap' }, [
		# table header
		$cgi->th({ -align => 'left', -nowrap => 'nowrap', -colspan => 2 },
			$cgi->str(58), $cgi->img('clock.gif', 16, 16, $cgi->str(58))
		),

		# input form
		$cgi->td({ -valign => 'top', -nowrap => 'nowrap', -colspan => 2 },
			# from: date
			$cgi->note($cgi->str(65).':'),
			$cgi->date({ -name => 'sdate', -value => $frm->{sdate} })
		),

		$cgi->td({ -valign => 'top', -nowrap => 'nowrap', -colspan => 2 },
			# to: date
			$cgi->note($cgi->str(66).':'),
			$cgi->date({ -name => 'edate', -value => $frm->{edate} })
		),

		$cgi->td({ -valign => 'top', -nowrap => 'nowrap', -colspan => 2 },
			# limit
			$cgi->br,
			sprintf($cgi->str(86),
				$cgi->popup_menu({
					-name => 'limit',
					-values => [ 10, 50, 100 ],
					-default => $frm->{limit}
				})
			)
		),

		# form buttons
		$cgi->td({ -colspan => 2 },
			$cgi->br,
			$cgi->submit({ -value => $cgi->str(113) }),
			$cgi->reset({ -value => $cgi->str(29) }),
			$cgi->form_hidden({ -action => 'submit' })
		)
	]);

if ($log->gettotal) {
	print
		$cgi->Tr(
			$cgi->td({ -colspan => 3 },
				$cgi->br, $cgi->notify($log->getlevel, $log->getall))
		);

} elsif ($#{$lb->{set}} > -1) {
	print
		# results header
		$cgi->section(sprintf($cgi->str(87), $stat->{recs}), 2),

		$cgi->Tr(
			$cgi->td({ -valign => 'top', -align => 'left', -width => '50%' }, [
				# totals & some stats
				$cgi->br.
				table_stats($stat, @avg),

				# top subjects
				$cgi->br.
				table_top(
					$top->{subject},
					$frm->{limit},
					$cgi->str(89).' '.$cgi->img('desc.gif', 16, 16, $cgi->str(89))
				),
			]),
		),

		$cgi->Tr(
			$cgi->td({ -valign => 'top', -align => 'left', -width => '50%' }, [
				# top users
				$cgi->br.
				table_top(
					$top->{user},
					$frm->{limit},
					$cgi->str(90).' '.$cgi->img('user.gif', 16, 16, $cgi->str(90))
				),

				# top attachments
				$cgi->br.
				table_top(
					$top->{attcnt},
					$frm->{limit},
					$cgi->str(91).' '.$cgi->img('attach.gif', 16, 16, $cgi->str(91))
				)
			])
		);
}

print
	# page end
	$cgi->end_content,
	$cgi->end_form,
	$cgi->footer($cfg->{footnote}),
	$cgi->end_doc;

exit 0;

sub table_stats {
	my ($table, @avg) = (shift, @_);
	my @result;

	$cgi->table({
		-width => '90%',
		-border => 1,
		-cellspacing => 0,
		-cellpadding => 3
		},
		# table header
		$cgi->Tr([
			$cgi->th({ -colspan => 2, -align => 'center' }, 
				$cgi->str(88).' '.$cgi->img('sum.gif', 11, 16, $cgi->str(88))
			),
			$cgi->th({ -align => 'left' }, $cgi->str(26)).
			$cgi->th({ -align => 'right' }, $cgi->str(92))
		]),

		# totals
		$cgi->Tr([
			$cgi->td({ -align => 'left' }, $cgi->str(93)).
			$cgi->td({ -align => 'right' }, $table->{recs}),

			$cgi->td({ -align => 'left' }, $cgi->str(94)).
			$cgi->td({ -align => 'right' }, $table->{with_attach} || 0),

			$cgi->td({ -align => 'left' }, $cgi->str(95)).
			$cgi->td({ -align => 'right' }, $table->{total_attach} || 0),

			$cgi->td({ -align => 'left' }, $cgi->str(96)).
			$cgi->td({ -align => 'right' }, scalar keys %{$table->{active_users}}),

			$cgi->td({ -align => 'left' }, $cgi->str(97)).
			$cgi->td({ -align => 'right' }, $cgi->ts2date($table->{oldest})),

			$cgi->td({ -align => 'left' }, $cgi->str(98)).
			$cgi->td({ -align => 'right' }, $cgi->ts2date($table->{newest})),

			$cgi->td({ -align => 'left' }, $cgi->str(100)).
			$cgi->td({ -align => 'right' }, $cgi->format_interval($table->{period}))
		]),

		# averages
		$cgi->Tr([
			map {
				$cgi->td({ -align => 'left' }, sprintf($cgi->str(101), $_->[0])).
				$cgi->td({ -align => 'right' }, sprintf('%.2f', $_->[1]))
			} (@avg)
		])
	);
}

sub table_top {
	my ($table, $limit, $title) = @_;
	my @result;
	my $pos = 1;

	my $values_descending = sub {
		$table->{$b} <=> $table->{$a};
	};

	push @result,
		$cgi->start_table({
			-width => '90%',
			-border => 1,
			-cellspacing => 0,
			-cellpadding => 3
			}),
			# table header
			$cgi->Tr([
				$cgi->th({ -colspan => 3, -align => 'center' }, $title),
				$cgi->th({ -width => '5%' }, $cgi->str(104)).
				$cgi->th({ -width => '90%' }, $cgi->str(92)).
				$cgi->th({ -width => '5%' }, $cgi->str(105))
			]);

	for (sort $values_descending (keys %$table) ) {
		push @result,
			# top results
			$cgi->Tr(
				$cgi->td({ -align => 'right' }, $pos++),
				$cgi->td({ -align => 'left' }, $_),
				$cgi->td({ -align => 'right' }, $table->{$_})
			);

		last if $pos > $limit;
	}

	push @result,
		$cgi->end_table;

	join("\n", @result);
}
