#!/usr/bin/perl -w
#
# $Id: export.cgi,v 1.4 2008/08/07 15:47:27 jorge Exp jorge $
#
# Web logbook export page.
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
use Text::CSV;

my ($cfg, $log, $cgi, $lb);
my ($book, $frm);
my ($scripts, $styles);

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
	dbdir => $book->{dir},
	archive => $cgi->{archive}
);

# cgi fields
$cgi->set_var('approot',				# application root directory
	$cfg->{approot});
$cgi->set_var('charset',				# character set
	$cfg->{charset});
$cgi->set_var('calformat',			# calendar date format 
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

# logbook scripts
push @$scripts,
	"$cgi->{approot}/script/strftime.js",
	"$cgi->{approot}/script/common.js";

# initial form values
$frm = {
	#action => '',			# default action is 'no action'
	file => $cgi->param('file') || filename(),
	format => $cgi->param('format') || 'wlb',
	sep => $cgi->param('sep') || 'comma'
};

# build the file formats list...
my @formats = qw(wlb csv xml);
my $formats = {
	$formats[0] => $cgi->str(132),
	$formats[1] => $cgi->str(133),
	$formats[2] => $cgi->str(134)
};
# ...and respective MIME types
my $types = {
	$formats[1] => 'text/csv',
	$formats[2] => 'application/xml'
};

# field separator (delimiter)
my $sepchar = {
	comma => ',',
	tab => "\t",
	colon => ':',
	semicolon => ';',
	pipe => '|'
};
my @separators = qw(comma tab colon semicolon pipe);
my $separators = {
	comma => sprintf('%s (%s)', $cgi->str(136), $sepchar->{comma}),
	tab => $cgi->str(137),
	colon => sprintf('%s (%s)', $cgi->str(138), $sepchar->{colon}),
	semicolon => sprintf('%s (%s)', $cgi->str(139), $sepchar->{semicolon}),
	pipe => sprintf('%s (%s)', $cgi->str(140), $sepchar->{pipe})
};

# process the action if any
if ($cgi->param('action')) {
	# search action
	if ($cgi->param('action') eq 'export') {
		if ($cgi->param('search')) {
			# export from a search
			$frm->{case} = $cgi->param('case') if $cgi->param('case');
			$frm->{andor} = $cgi->param('andor') if $cgi->param('andor');

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
				} elsif (/^user$/) {
					$crit->{$_} = [ 2, '"%s"=~/'.$lb->escape_criteria($crit->{$_}).'/i' ];
				} elsif (/^subject$/) {
					$crit->{$_} = [ 3, '"%s"=~/'.$lb->escape_criteria($crit->{$_}).'/i' ];
					chop($crit->{$_}[1]) if $frm->{case};
				} elsif (/^desc$/) {
					$crit->{$_} = [ 4, '"%s"=~/'.$lb->escape_criteria($crit->{$_}).'/i' ];
					chop($crit->{$_}[1]) if $frm->{case};
				} elsif (/^attach$/) {
					$crit->{$_} = [ 5, '%d'.($crit->{$_} == 1 ? '>' : '==').'0' ];
				}
			}

			if ($sdate && $edate && $sdate > $edate) {
				swap(\$frm->{sdate}, \$frm->{edate});
				#$log->add($log->{WARNING}, $cgi->str(73));
			}

			# get logbook entries
			$lb->search_extended($crit, $frm->{andor});

		} else {
			# export all entries from current logbook or archive
			$lb->fetchall;
		}

		if ($#{$lb->{set}} == -1) {
			# no records found
			$log->add($log->{NOTICE}, $cgi->str(76));
		} else {
			# export logbook
			print
				$cgi->header({
					-charset => $cgi->{charset},
					-type => $types->{$frm->{format}} || 'application/octet-stream',
					-attachment => "$frm->{file}.$frm->{format}"
				});

			my $exp = $cgi->sort_expr(0, '', '0|1');

			if ($frm->{format} eq 'csv') {
				export_csv($sepchar->{$frm->{sep}}, sort { eval $exp } @{$lb->{set}});
			} elsif ($frm->{format} eq 'xml') {
				export_xml(sort { eval $exp } @{$lb->{set}});
			} else {
				export_csv('', sort { eval $exp } @{$lb->{set}});
			}

			exit 0;
		}

	} elsif ($cgi->param('action') eq 'search') {
		$frm->{search} = 1;
		$frm->{user} = $cgi->param('user');
		$frm->{sdate} = $cgi->param('sdate');
		$frm->{edate} = $cgi->param('edate');
		$frm->{subject} = $cgi->param('subject');
		$frm->{desc} = $cgi->param('desc');
		$frm->{case} = $cgi->param('case');
		$frm->{andor} = $cgi->param('andor');
	}
}

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => "setInterval('displaytime()', 1000);".
			"setfocus(document.forms['form'].elements['file']);",
	}),

	# page header
	$cgi->caption(sprintf($cgi->str(123), $book->{title})),
	$cgi->hr({ -class => 'line' }),

	# export form
	$cgi->start_form({
		-name => 'form',
		-method => 'POST',
		-onsubmit => sprintf("return checkRequired(this.file, '%s');", $cgi->str(125))
	}),

	# page content
	$cgi->start_content;

# show messages if any
print
	$cgi->Tr(
		$cgi->td($cgi->notify($log->getlevel, $log->getall))
	) if $log->gettotal;

print
	$cgi->Tr(
		$cgi->td(
			$cgi->input({
				-name => 'file',
				-size => 30,
				-maxlength => 30,
				-value => $frm->{file},
				-class => 'input'
			}),
			'&nbsp;',
			$cgi->submit({ -value => $cgi->str(122) }),
			$cgi->br,
			$cgi->br,
			$cgi->str(126),
			$cgi->br,

			# div ids for each format option
			$cgi->script({ -type => 'text/javascript' },
				"var ids = new Array(".join(',', map { "'$_'" } @formats).");"),
			$cgi->popup_menu({
				-name => 'format',
				-values => \@formats,
				-default => $frm->{format},
				-labels => \%$formats,
				-onchange => 'switchId(this.value, ids);',
				-onkeydown => 'switchId(this.value, ids);',
				-onkeyup => 'switchId(this.value, ids);'
			}),

			# div layers for each format option
			$cgi->div({ -id => 'wlb', -style => 'display:block;' }, ''),
			$cgi->div({ -id => 'csv', -style => 'display:none;' },
				$cgi->br,
				$cgi->str(135),
				$cgi->br,
				$cgi->radio_group({
					-name => 'sep',
					-values => \@separators,
					-default => $frm->{sep},
					-labels => \%$separators,
					-linebreak=>'true'
				})
			),
			$cgi->div({ -id => 'xml', -style => 'display:none;' }, ''),

			$cgi->form_hidden({
				-action => 'export',
				-search => $frm->{search},
				-user => $frm->{user},
				-sdate => $frm->{sdate},
				-edate => $frm->{edate},
				-subject => $frm->{subject},
				-desc => $frm->{desc},
				-case => $frm->{case},
				-andor => $frm->{andor}
			})
		)
	);

print
	# page end
	$cgi->end_content,
	$cgi->end_form,
	$cgi->end_doc;

exit 0;

# suggested filename
sub filename {
	# DISCUSSION: should this date be in the format YYYYMMDD? This would
	# correctly sort the exported files.
	my $date = $cgi->ts2date(time);

	$date =~ s/[\/\-:]//g;	# strips out /, - and :
	$date =~ s/\s+/_/g;			# space -> underscore

	sprintf('%s_%s', $cgi->{id}, $date);
}

# csv export
sub export_csv {
	my $sep = shift;
	my @recs = @_;

	# cvs object
	my $csv = new Text::CSV(sep => $sep);

	for (0..$#recs) {
		print $csv->set_row(
			$recs[$_][0],
			$recs[$_][1],
			$csv->quote($recs[$_][2]),	# user
			$csv->quote($recs[$_][3]),	# subject
			$csv->quote($recs[$_][4]),	# description
			$recs[$_][5]
		);
	}
}

# xml export (TODO: this is really limited - needs more work here)
sub export_xml {
	my @recs = @_;

	print <<XML;
<?xml version="1.0" encoding="$cgi->{charset}"?>
<weblogbook name="$cgi->{id}" calformat="$cgi->{calformat}" daysnew="$cgi->{daysnew}" entriesperpage="$cgi->{entriesperpage}">
	<title>$book->{title}</title>
	<field name="id" type="numeric">Id</field>
	<field name="ts" type="numeric">Timestamp</field>
	<field name="user" type="string">User</field>
	<field name="subj" type="string" maxlength="$cgi->{subject_maxlen}">Subject</field>
	<field name="desc" type="string" maxlength="$cgi->{desc_maxlen}">Description</field>
	<field name="attcnt" type="numeric">Attach Count</field>
XML

	for (0..$#recs) {
		print "\t<row>\n";
		printf("\t\t<id>%d</id>\n", $recs[$_][0]);
		printf("\t\t<ts>%d</ts>\n", $recs[$_][1]);
		printf("\t\t<user>%s</user>\n", $recs[$_][2]);
		printf("\t\t<subj>%s</subj>\n", $recs[$_][3]);
		printf("\t\t<desc>%s</desc>\n", $recs[$_][4]);
		printf("\t\t<attcnt>%d</attcnt>\n", $recs[$_][5]);
		print "\t</row>\n";
	}

	print "</weblogbook>";
}
