#!/usr/bin/perl -w
#
# $Id$
#
# Group nodes page.
#
# Copyright 2008, Jorge Morgado. All rights reserved.
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
use Log::Simple;
use Logbook::CGI;
use Logbook::DB;
use Logbook::DateTime;

my ($cfg, $log, $cgi, $lb, $dt);
my ($book);
# TODO: under test -- start
#my ($scripts, $styles);
# TODO: under test -- end
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

$dt = new Logbook::DateTime;

# cgi fields
$cgi->set_var('approot',				# application root directory
	$cfg->{approot});
$cgi->set_var('charset',				# character set
	$cfg->{charset});
$cgi->set_var('dateformat',			# date format
	$book->{dateformat}, $cfg->{dateformat});
$cgi->set_var('daysnew',				# display new entries
	$book->{daysnew}, $cfg->{daysnew});
$cgi->set_var('calendar',				# calendar date format
	$book->{calformat}, $cfg->{calformat});
$cgi->set_var('refresh',				# page reload interval
	$book->{refresh}, $cfg->{refresh});
$cgi->set_var('entriesperpage',	# maxium entries per page
	$book->{entriesperpage}, $cfg->{entriesperpage});

# page language
$cgi->set_language($book->{lang} || $cfg->{lang}->{default});

# get logbook entries list
my $exp = $cgi->sort_expr(0, 'd', '0|1');

# header
print $cgi->header;

if (defined $cgi->param('idParent')) {
	my $idParent = $cgi->param('idParent');

	# first, obtains the 'base' record we will use as the group criteria
	my $base;
	($base->{date},
	 $base->{user},
	 $base->{subject},
	 $base->{desc},
	 $base->{attinfo}) = $lb->fetch($cgi->param('nr'));

	if ($base->{date} > 0) {
		# found, so lets search all records that respect this criteria
		my $crit = {};

		if ($cgi->{view} == 2) {	# group by day
			$crit->{sdate} = [1,'%d>='.$dt->get_first_second_of_day($base->{date}) ];
			$crit->{edate} = [1,'%d<='.$dt->get_last_second_of_day($base->{date}) ];
		} elsif ($cgi->{view} == 3) {	# group by week
			$crit->{sdate} = [1,'%d>='.$dt->get_first_second_of_week($base->{date}) ];
			$crit->{edate} = [1,'%d<='.$dt->get_last_second_of_week($base->{date}) ];
		} elsif ($cgi->{view} == 4) {	# group by month
			$crit->{sdate} = [1,'%d>='.$dt->get_first_second_of_month($base->{date})];
			$crit->{edate} = [1,'%d<='.$dt->get_last_second_of_month($base->{date}) ];
		} elsif ($cgi->{view} == 5) {	# group by year
			$crit->{sdate} = [1,'%d>='.$dt->get_first_second_of_year($base->{date}) ];
			$crit->{edate} = [1,'%d<='.$dt->get_last_second_of_year($base->{date}) ];
		} elsif ($cgi->{view} == 6) {	# group by user
			$crit->{user} = [ 2, '"%s"=~/'.$lb->escape_criteria($base->{user}).'/i' ];
		} else {	# group by subject (default)
			$crit->{subject} = [ 3, '"%s"=~/^'.$lb->escape_criteria($base->{subject}).'$/i' ];
		}

		# get logbook entries list
		$lb->search_extended($crit);

		# at least one record should exist so it should never get here but...
		$log->add($log->{ERROR}, $cgi->str(76)) if $#{$lb->{set}} == -1;
	} else {
		# found no records which shouldn't happen either but again, just in case...
		$log->add($log->{ERROR}, $cgi->str(76));
	} 

	if ($log->gettotal) {
		# show messages if any
		print
			$cgi->table({ -width => '100%' },
				$cgi->Tr(
					$cgi->td($cgi->notify($log->getlevel, $log->getall))
				)
			);
	} else {
		print
			$cgi->start_li,
			$cgi->start_table({ -width => '100%' }),

			# logbook entries dump starts
			$cgi->view_default('index.cgi?%s',
				$lb->{users},
				!$cgi->{archive},
				sort { eval $exp } @{$lb->{set}}
			),

			# show page buttons
			$cgi->page_buttons("javascript:nodeRefresh('%s',".($idParent + 1).");").

			$cgi->end_table,
			$cgi->end_li;
	}
}

exit 0;
