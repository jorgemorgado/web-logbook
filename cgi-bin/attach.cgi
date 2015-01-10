#!/usr/bin/perl -w
#
# $Id: attach.cgi,v 1.4 2008/07/13 22:54:58 jorge Exp jorge $
#
# Web logbook attachments management.
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

use Util qw(is_empty);
use Config::File;
use Log::Simple;
use Logbook::CGI;
use Logbook::DB;

use File::Basename;

my ($cfg, $log, $cgi, $lb);
my ($book, $frm);
my ($scripts, $styles);
my ($attsize, $attid, $attinfo);

# prototypes
sub find_type($);

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
	id => $cgi->{id}.'_attach',
	dbdir => $book->{dir},
	attdir => $cfg->{attach}->{dir},
	archive => $cgi->{archive}
);

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

# logbook scripts
push @$scripts,
	"$cgi->{approot}/script/strftime.js",
	"$cgi->{approot}/script/common.js";

# maximum upload size (in Mb)
$attsize = $cfg->{attach}->{size} || 2;
$CGI::POST_MAX = 1024 * 1024 * $attsize;

# attach ID will prefix all uploads for this logbook entry
$attid = $cgi->param('attid') || 0;

# initial form values
$frm = {
	action => 'add',		# default action
	file => undef,
	type => 'binary',
	nr => undef
};

# create upload directory if doesn't exist
if (!(-d $lb->{attdir} || mkdir($lb->{attdir}, 0755))) {
	$log->add($log->{WARNING}, sprintf($cgi->str(9), $lb->{attdir}));

# check for a valid attach ID
} elsif (!$attid) {
	$log->add($log->{WARNING}, sprintf($cgi->str(10), $ENV{'HTTP_REFERER'}));

# process the action if any
} elsif ($cgi->param('action')) {
	# add action
	if ($cgi->param('action') eq 'add') {
		if ($cgi->param('file')) {
			# evaluate received data file - check whether the file transfer could be
			# incorrectly locked (if client didn't close the transmission with STOP)
			if ($cgi->cgi_error) {
				$log->add($log->{ERROR}, sprintf($cgi->str(11), $cgi->cgi_error));

			} else {
				my $fh = $cgi->param('file');	# file handle to the received file
				$frm->{fid} = $$;
				$frm->{file} = basename($fh);

				if (open(FH, sprintf('>%s/%s_%d_%s', $lb->{attdir}, $attid, $frm->{fid}, $frm->{file}))) {
					my $buffer;

					# read and store the data (always assumes it's a binary file)
					while (read($fh, $buffer, 1024)) {
						print FH $buffer;
					}

					close(FH);

					# find file's type
					$frm->{type} = $cgi->param('type') || 'binary';
					$frm->{type} = find_type($frm->{file}) if $frm->{type} eq 'binary';

					$lb->insert([
						$lb->{attdir},
						$attid,
						$frm->{fid},
						$frm->{file},
						$frm->{type}
					]);
				} else {
					# can we write to upload directory?
					$log->add($log->{WARNING}, sprintf($cgi->str(12), $lb->{attdir}, $!));
				}
			}
		} else {
			$log->add($log->{WARNING}, $cgi->str(13));
		}

	# edit action
	} elsif ($cgi->param('action') eq 'edit') {
		if ($cgi->param('file')) {
			# find file's type
			$frm->{type} = $cgi->param('type') || 'binary';
			$frm->{type} = find_type($cgi->param('file')) if $frm->{type} eq 'binary';

			$lb->update_fields($cgi->param('nr'), { 5 => $frm->{type} });

			# resets values for the new form add
			$frm->{type} = 'binary';
		} else {
			$frm->{action} = 'edit';
			$frm->{nr} = $cgi->param('nr');

			($frm->{file}, $frm->{type}) = ($lb->fetch($frm->{nr}))[3, 4];
		}

	# delete action
	} elsif ($cgi->param('action') eq 'delete') {
		($frm->{fid}, $frm->{file}) = ($lb->fetch($cgi->param('nr')))[2, 3];

		if (unlink(sprintf('%s/%s_%d_%s', $lb->{attdir}, $attid, $frm->{fid}, $frm->{file}))) {
			$lb->delete($cgi->param('nr'));
		} else {
			$log->add($log->{WARNING}, sprintf($cgi->str(14), $frm->{file}, $!));
		}

		# resets values for the new form add
		$frm->{file} = undef;
	} 
}

# get attachments list for this record
$lb->search({ 2 => $attid });

$attinfo = $cgi->attach_info($#{$lb->{set}} + 1);

# build the file types list
my @types = ('binary', sort keys %{$cfg->{types}});
my $types;

for (@types) {
	if (/^binary$/) {
		$types->{'binary'} = $cgi->str(15);
	} else {
		$types->{$_} = sprintf('%s (%s)',
			$cfg->{types}->{$_}->{description},
			$cfg->{types}->{$_}->{type}
		);
	}
}

print
	# page start
	$cgi->start_doc({
		-title => $book->{title},
		-scripts => $scripts,
		-styles => $styles,
		-onload => "setInterval('displaytime()', 1000);".
			"setfocus(document.forms['form'].elements['file']);".
			"changeLabel(opener.document.getElementById('attinfo'),'($attinfo)');",
	}),

	# page header
	$cgi->caption(
		-title => sprintf($cgi->str(16), $book->{title})
	),
	$cgi->hr({ -class => 'line' }),

	# attachment form
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
		$cgi->td({ -colspan => 4 },
			($frm->{action} eq 'edit' ?
				$cgi->hidden('file', $frm->{file}).	# replaces dummyfile (disabled)
				$cgi->input({
					-name => 'dummyfile',
					-size => 37,
					-value => $frm->{file},
					-disabled => 1,
					-class => 'input',
					-tabindex => $cgi->get_tabindex
				}) :
				$cgi->filefield({
					-name => 'file',
					-size => 26,
					-class => 'input',
					-tabindex => $cgi->get_tabindex
				})
			),
			'&nbsp;',
			$cgi->submit({ -value => $cgi->str(28), -tabindex => $cgi->get_tabindex }),
			$cgi->br,
			$cgi->note(sprintf($cgi->str(17), $attsize)),
			$cgi->br,
			$cgi->str(18).
			$cgi->br.
			$cgi->popup_menu({
				-name => 'type',
				-values => \@types,
				-default => $frm->{type},
				-labels => \%$types,
				-tabindex => $cgi->get_tabindex
			}),
			$cgi->form_hidden({
				-action => $frm->{action},
				-nr => $frm->{nr},
				-attid => $attid
			})
		)
	);

# attachment list
if ($#{$lb->{set}} > -1) {
	my $exp = $cgi->sort_expr(4, 'a', '-');
	my $i = 0;

	print
		# sort buttons
		$cgi->Tr(
			$cgi->td(
				$cgi->sort_buttons('attach.cgi?%s', 4, { attid => $attid })),
			$cgi->td({ -colspan => 3 },
				$cgi->sort_buttons('attach.cgi?%s', 5, { attid => $attid }))
		);

	# attachment entries dump starts
	for (sort { eval $exp } @{$lb->{set}}) {
		print
			$cgi->Tr({ -class => $i++ % 2 ? 'odd' : 'even' },
				$cgi->td([ $_->[4], $_->[5] ]).
				$cgi->action_buttons('attach.cgi?%s', $_->[0], { attid => $attid })
			);
	}
}

print
	# page end
	$cgi->end_content,
	$cgi->end_form,
	$cgi->end_doc;

exit 0;

# return the file's content type or 'binary' if not found
sub find_type($) {
	my $filename = shift;

	my $file_ext = (split /\./, $filename)[-1];

	if (!is_empty($file_ext)) {
		$file_ext = lc($file_ext);

		my @types = sort keys %{$cfg->{types}};
		my $types;

		for (@types) {
			my @extensions = split(/ /, lc($cfg->{types}->{$_}->{extension}));

			for my $i (@extensions) {
				return $_ if ($file_ext eq $i);
			}
		}
	}

	# if file type can't be found, assumes binary type (application/octet-stream)
	return 'binary';
}
