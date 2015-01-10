#!/usr/bin/perl -w
#
# $Id: archive.cgi,v 1.4 2008/07/22 23:42:25 jorge Exp jorge $
#
# Web logbook archive functions.
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
use Log::Simple;
use Logbook::CGI;
use Logbook::DB;

use File::Find;
use File::Basename;

my ($cfg, $log, $cgi, $lb);
my ($book, $frm);
my ($scripts, $styles);
my ($dbname, $dbsize, $dbcount, $dbatime, $dbmtime);
my ($archfile, $archdir, @archlist, $archfind);

# config file object
$cfg = new Config::File('../share/etc/logbook.cfg');

# simple log (event) object
$log = new Log::Simple(3);

# logbook cgi object
$cgi = new Logbook::CGI;

# logbook id (from config file)
$cgi->set_var('id', lc($cgi->param('id') || $cfg->{logbook}->{default}));

# shortcut (reference) to the selected logbook configuration
$book = \%{$cfg->{logbook}->{$cgi->{id}}};

# logbook object
$lb = new Logbook::DB(
	id => $cgi->{id},
	dbdir => $book->{dir}
);

# cgi fields
$cgi->set_var('approot',		# application root directory
	$cfg->{approot});
$cgi->set_var('dateformat',	# date format
	$book->{dateformat}, $cfg->{dateformat});

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
	"$cgi->{approot}/script/popupmenu.js",
	"$cgi->{approot}/script/strftime.js",
	"$cgi->{approot}/script/common.js";

# initial form values
$frm = {
	action => 'prompt'	# default action
};

# database info (name, size, total entries, ...)
$dbname = sprintf("%s.pag", $lb->{db});
($dbsize, $dbatime, $dbmtime) = (stat($dbname))[7, 8, 9 ];
$dbsize = ($dbsize / 10240) || 0;
$dbcount = $lb->count;

# process the action if any
if ($cgi->param('action')) {
	# archive action
	if (($frm->{action} = $cgi->param('action')) eq 'archive') {
		if (defined(my $dbarch = $lb->make_archive)) {
			$dbname = sprintf("%s.pag", $dbarch);
			$log->add($log->{INFO}, $cgi->str(67));
		} else {
			$log->add($log->{WARNING}, $cgi->str(68));
		}
	}
} else {
	my $maxentries = $book->{archive}->{maxentries} || 0;
	my $maxsize = $book->{archive}->{maxsize} || 0;

	# archive is not possible if logbook is empty
	if ($dbcount == 0) {
		$frm->{action} = 'archive';
		$log->add($log->{ERROR}, $cgi->str(69));

	} else {
		# warn if logbook has less entries than what is defined for an archive
		$log->add($log->{NOTICE}, sprintf($cgi->str(1), $dbcount, $maxentries))
			if $dbcount < $maxentries;

		# warn if logbook has less bytes than what is defined for an archive
		$log->add($log->{NOTICE}, sprintf($cgi->str(2), $dbsize, $maxsize))
			if $dbsize < $maxsize;
	}
}

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => "setInterval('displaytime()', 1000);",
	}),

	# page header
	$cgi->menu({
		-menus => $dbcount ?
			[ $frm->{action} eq 'prompt' ?
				qw(mkarchive search trends back) : qw(search trends back) ] :
			[ qw(back) ],
		-langs => $cfg->{lang},
	}),
	$cgi->caption({
		-title => sprintf($cgi->str(3), $book->{title})
	}),

	# page content
	$cgi->start_content,
	$cgi->section($cgi->str(4));

# logbook database information
print
	$cgi->Tr(
		$cgi->td(
			$cgi->br,
			$cgi->table({
				-border => 1,
				-width => '60%',
				-cellspacing => 0,
				-cellpadding => 3
				},
				$cgi->Tr({ -class => 'nowrap' }, [
					$cgi->td({ -align => 'left', -nowrap => 'nowrap' },
						[ $cgi->b(sprintf '%s:',$cgi->str(5)), $dbname ]),
					$cgi->td({ -align => 'left', -nowrap => 'nowrap' },
						[ $cgi->b(sprintf '%s:',$cgi->str(6)), sprintf '%.1fMb', $dbsize ]),
					$cgi->td({ -align => 'left', -nowrap => 'nowrap' },
						[ $cgi->b(sprintf '%s:',$cgi->str(7)), $dbcount ]),
					$cgi->td({ -align => 'left', -nowrap => 'nowrap' },
						[ $cgi->b(sprintf '%s:',$cgi->str(43)), $cgi->get_date($dbatime) ]),
					$cgi->td({ -align => 'left', -nowrap => 'nowrap' },
						[ $cgi->b(sprintf '%s:',$cgi->str(57)), $cgi->get_date($dbmtime) ]),
				])
			),
			$cgi->br
		)
	) if $frm->{action} =~ /^(archive|prompt|browse)$/;

# show messages if any
print
	$cgi->Tr(
		$cgi->td($cgi->notify($log->getlevel, $log->getall))
	) if $log->gettotal;

# find logbook archives
$archfile = basename($lb->{db}); 
$archdir = dirname($lb->{db});
$archfind = sub {
	push @archlist, $1 if /^$archfile\.(\d+)\.pag$/;
};
find($archfind, $archdir);

# archive list
if ($#archlist > -1) {
	print
		$cgi->section($cgi->str(8));

	# sort archives chronologically
	for (sort { $a <=> $b } @archlist) {
		print
			$cgi->Tr(
				$cgi->td(
					$cgi->a({
						-href => 'index.cgi?'.$cgi->get_params({ archive => $_ })
						}, sprintf('%s', $cgi->get_date($_))
					)
				)
			);
	}
}

print
	# page end
	$cgi->end_content,
	$cgi->footer($cfg->{footnote}),
	$cgi->end_doc;

exit 0;
