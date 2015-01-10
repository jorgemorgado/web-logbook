#!/usr/bin/perl -w
#
# $Id: import.cgi,v 1.5 2008/08/08 22:11:29 jorge Exp jorge $
#
# Web logbook import page.
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

use Util qw(trim is_empty is_numeric);
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
);

# cgi fields
$cgi->set_var('approot',				# application root directory
	$cfg->{approot});
$cgi->set_var('charset',				# character set
	$cfg->{charset});

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
	format => $cgi->param('format') || 'wlb',
	sep => $cgi->param('sep') || 'comma'
};

# build the file formats list
my @formats = qw(wlb csv);
my $formats = {
	$formats[0] => $cgi->str(132),
  $formats[1] => $cgi->str(133)
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
	# import action
	if ($cgi->param('action') eq 'import') {
		if ($cgi->param('file')) {
			# evaluate received data file - check whether the file transfer could be
			# incorrectly locked (if client didn't close the transmission with STOP)
			if ($cgi->cgi_error) {
				$log->add($log->{ERROR}, sprintf($cgi->str(11), $cgi->cgi_error));

			} else {
				my $fh = $cgi->param('file');	# file handle to the received file
				my ($status, $recs);

				# which format to parse?
				($recs, $status) = parse(
					$fh, $frm->{format} eq 'wlb' ? '' : $sepchar->{$frm->{sep}}
				);

				# records are imported in the keys order (ascending)
				# (this is consistent with any export order)
				for my $i (sort { $a <=> $b } keys %$recs) {
					$lb->insert([ map { $recs->{$i}[$_] } (1..5) ]);
				}

				# if any successfully imported records
				$log->add($log->{INFO}, sprintf($cgi->str(128), $status->{good}))
					if $status->{good};

				# if there were some attachments
				$log->add($log->{NOTICE}, sprintf($cgi->str(129), $status->{attach}))
					if $status->{attach};

				# if failed to import
				unless (scalar %$recs) {
					# if all have failed
					$log->add($log->{ERROR}, $cgi->str(131));
				} elsif ($status->{bad}) {
					# if some have failed
					$log->add($log->{WARNING}, sprintf($cgi->str(130), $status->{bad}));
				}
			}
		} else {
			$log->add($log->{WARNING}, $cgi->str(13));
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
			"setfocus(document.forms['form'].elements['file']);",
	}),

	# page header
	$cgi->caption(sprintf($cgi->str(124), $book->{title})),
	$cgi->hr({ -class => 'line' }),

	# import form
	$cgi->start_multipart_form({
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
			$cgi->filefield({
				-name => 'file',
				-size => 20,
				-class => 'input'
			}),
			'&nbsp;',
			$cgi->submit({ -value => $cgi->str(121) }),
			$cgi->br,
			$cgi->note($cgi->str(127)),
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
				-onchange => 'javascript:switchId(this.value, ids);',
				-onkeydown => 'javascript:switchId(this.value, ids);',
				-onkeyup => 'javascript:switchId(this.value, ids);'
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

			$cgi->form_hidden({ -action => 'import' })
		),
	);

print
	# page end
	$cgi->end_content,
	$cgi->end_form,
	$cgi->end_doc;

exit 0;

sub parse {
	my $fh = shift;
	my $delim = shift;
	my $status = { good => 0, attach => 0, bad => 0 };
	my $recs;

	# cvs object
	my $csv = new Text::CSV(fh => $fh, sep => $delim);

	while (1) {
		my $row = $csv->get_row();

		last unless defined $row;

		if ($#{$row} > -1) {
			if (validate(@$row)) {
				$status->{good}++;
				$status->{attach} += $row->[5] if $row->[5];

				$recs->{$row->[0]} = $row;
			} else {
				$status->{bad}++;
			}
		}
	}

	($recs, $status);
}

# data validation
# also see index.cgi's validate() function
sub validate {
	# there are 6 fields
	scalar(@_) == 6 &&

	# these are numeric
	is_numeric($_[0]) &&	# id
	is_numeric($_[1]) &&	# timestamp
	is_numeric($_[5]) &&	# attach count

	# these aren't empty
	!is_empty($_[2]) &&	# user's nick name
	!is_empty($_[3]) &&	# subject
	!is_empty($_[4]) &&	# descrption

	# these aren't too long
	length($_[2]) <= 10	&& # user's nick name (10 bytes is a guess!!)
	length($_[3]) <= $cgi->{subject_maxlen} &&	# subject
	length($_[4]) <= $cgi->{desc_maxlen}	# description
}
