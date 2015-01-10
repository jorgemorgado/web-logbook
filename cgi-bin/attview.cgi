#!/usr/bin/perl -w
#
# $Id: attview.cgi,v 1.6 2008/07/13 22:56:35 jorge Exp jorge $
#
# Web logbook attachments viewer.
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

my ($cfg, $log, $cgi, $lb);
my ($book);
my ($scripts, $styles);
my ($sort, $dir);

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

# file view/download
if ($cgi->param('nr')) {
	my $nr = $cgi->param('nr');
	my ($path, $lid, $fid, $name, $type) = $lb->fetch($nr);

	$path .= ".$cgi->{archive}" if $cgi->{archive};

	if (open FILE, (my $file = sprintf '%s/%d_%d_%s', $path, $lid, $fid, $name)) {
		$type = $cfg->{types}->{$type}->{type} ?
			lc($cfg->{types}->{$type}->{type}) :
			'application/octet-stream';

		print
			$cgi->header({
				-charset => $cgi->{charset},
				-type => $type,
				-content_length => (-s $file),
				-attachment => $cgi->param('action') && $cgi->param('action') eq 'view' ? undef : $name		# provides the real file name to the browser
			});

		while (<FILE>) {
			print $_;
		}

		close FILE;

		exit 0;

	} else {
		$log->add($log->{ERROR}, sprintf($cgi->str(19), $name, $!));
	}
}

# this helps to keep the sort field and direction from and to the previous page
if (defined $cgi->param('psort')) {
	$sort = $cgi->param('psort');
} elsif (defined $cgi->{params}->{sort}) {
	$sort = $cgi->{params}->{sort};
	delete $cgi->{params}->{sort};
}
if (defined $cgi->param('pdir')) {
	$dir = $cgi->param('pdir');
} elsif (defined $cgi->{params}->{dir}) {
	$dir = $cgi->{params}->{dir};
	delete $cgi->{params}->{dir};
}

# attachment list view
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
		-menus => [ 'back' ],
		-langs => $cfg->{lang},
		-params => { sort => $sort, dir => $dir }
	}),
	$cgi->caption({
		-title => sprintf($cgi->str(20), $book->{title})
	}),

	# page content
	$cgi->start_content;

# show messages if any
print
	$cgi->Tr(
		$cgi->td({ -colspan => 3 }, $cgi->notify($log->getlevel, $log->getall))
	) if $log->gettotal;

if (my $attid = $cgi->param('attid')) {
	# get attachments list for this record
	$lb->search({ 2 => $attid });

	# attachment list
	if ($#{$lb->{set}} > -1) {
		my $exp = $cgi->sort_expr(4, 'a', '-');
		my $i = 0;

		print
			$cgi->section($cgi->str(64), 3),

			# table header
			$cgi->Tr(
				$cgi->th({ -align => 'left' }, $cgi->str(21)),
				$cgi->th({ -align => 'left', -colspan => 2 }, $cgi->str(51)),
			),

			# sort buttons
			$cgi->Tr(
				$cgi->td({ -bgcolor => '#ffffff' },
					$cgi->sort_buttons('attview.cgi?%s', 4, {
						attid => $attid,
						psort => $sort,
						pdir => $dir
					})),
				$cgi->td({ -bgcolor => '#ffffff', -colspan => 2 },
					$cgi->sort_buttons('attview.cgi?%s', 5, {
						attid => $attid,
						psort => $sort,
						pdir => $dir
					}))
			);

		# attachment entries dump starts
		for (sort { eval $exp } @{$lb->{set}}) {
			print
				$cgi->Tr({ -class => $i++ % 2 ? 'odd' : 'even' },
					$cgi->td([
						# file name
						$cgi->a({
							-href => 'attview.cgi?'.
								$cgi->get_params({ attid => $attid, nr => $_->[0] })
							},
							$_->[4]
						).' '.

						# view online button opens in a new window
						($cfg->{types}->{$_->[5]}->{viewonline} ?
							$cgi->a({
								-target => '_blank',
								-href => 'attview.cgi?'.
									$cgi->get_params({
										attid => $attid, nr => $_->[0], action => 'view'
									})
								}, $cgi->img('glasses.gif', 19, 9, $cgi->str(56))
							) : ''
						),

						# file's type and type's description
						$_->[5],
						sprintf('%s (%s)',
							$cfg->{types}->{$_->[5]}->{description} || $cgi->str(22),
							$cfg->{types}->{$_->[5]}->{type} || 'application/octet-stream'
						)
					])
				);
		}
	}
}

print
	# page end
	$cgi->end_content,
	$cgi->end_doc;

exit 0;
