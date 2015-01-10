#!/usr/bin/perl -w
#
# $Id: subject.cgi,v 1.5 2008/07/13 23:08:44 jorge Exp jorge $
#
# Web logbook subject functions.
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

use Util qw(trim is_empty);
use Config::File;
use Logbook::CGI;
use Logbook::DB;

my ($cfg, $cgi, $lb);
my ($book, $frm);
my ($scripts, $styles);
my ($anchor, $idx);

# config file object
$cfg = new Config::File('../share/etc/logbook.cfg');

# logbook cgi object
$cgi = new Logbook::CGI;

# logbook id (from config file)
$cgi->set_var('id', lc($cgi->param('id') || $cfg->{logbook}->{default}));

# shortcut (reference) to the selected logbook configuration
$book = \%{$cfg->{logbook}->{$cgi->{id}}};

# logbook object
$lb = new Logbook::DB(
	id => $cgi->{id}.'_subject',
	dbdir => $book->{dir}
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

# initial form values
$frm = {
	action => 'add',		# # default action is add new                            
	subject => '',
	nr => undef
};

# process the action if any
if ($cgi->param('action')) {
	# add action
	if ($cgi->param('action') eq 'add') {
		$lb->insert([ trim($cgi->param('subject')) ]) if validate();

	# edit action
	} elsif ($cgi->param('action') eq 'edit') {
		if ($cgi->param('subject')) {
			$lb->update($cgi->param('nr'), [ trim($cgi->param('subject')) ])
				if validate();
		} else {
			$frm->{nr} = $cgi->param('nr');
			$frm->{action} = 'edit';

			($frm->{subject}) = $lb->fetch($frm->{nr});
		}

	# delete action
	} elsif ($cgi->param('action') eq 'delete') {
		$lb->delete($cgi->param('nr'));
	}
}

# get subject entries list
$lb->fetchall;

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
	$cgi->caption(sprintf $cgi->str(52), $book->{title}),
	$cgi->hr({ -class => 'line' }),

	# subject form
	$cgi->start_form({
		-name => 'form',
		-method => 'POST',
		-onsubmit => "return ".
			sprintf("checkRequired(this.subject, '%s') && ",
				$cgi->str(23)).
			sprintf("checkMaxLength(this.subject, %d, '%s');",
				$cgi->{subject_maxlen}, $cgi->str(102))
	}),

	# page content
	$cgi->start_content,

	$cgi->Tr(
		$cgi->td({ -colspan => 3 },
			$cgi->input({
				-name => 'subject',
				-size => 30,
				-maxlength => $cgi->{subject_maxlen},
				-value => $frm->{subject},
				-class => 'input',
				-tabindex => $cgi->get_tabindex
			}),
			'&nbsp;',
			$cgi->form_hidden({
				-action => $frm->{action},
				-nr => $frm->{nr}
			}),
			$cgi->submit({
				-value => $cgi->str(28),
				-tabindex => $cgi->get_tabindex
			}),
			$cgi->script({ -type => 'text/javaScript' },
				"function copyTo(obj_target, value) {".
				"	obj_target.value = value;".
				"	window.close();".
				"}")
		)
	);

my $exp = $cgi->sort_expr(1, 'a', '-');

# subject list
if ($#{$lb->{set}} > -1) {
	# cycles records to build the 'alphabet' anchor menu
	for (sort { eval $exp } @{$lb->{set}}) {
		$idx = uc(substr($_->[1], 0, 1));	# first char uppercase

		# this tastes like a quick-hack but the idea is like this: if the first
		# char is not a letter, then it will be indexed as a digit (of course, this
		# isn't always true depending on the char and the archor might be broken)
		$idx = 0 if $idx !~ /[A-Z]/;

		# if this anchor doesn't exist yet
		unless ($anchor->{$idx}) {
			if ($idx) {
				$anchor->{$idx} = $cgi->a({ -href => "#$idx" }, $idx);
			} else {
				$anchor->{$idx} = $cgi->a({ -href => '#a0-9' }, '0-9');
				$idx = 'a0-9';
			}

			# also record the index in the list for later use
			$_->[$#{$_} + 1] = $idx;
		}
	}

	print
		$cgi->Tr([
			# 'alphabet' menu with anchor-links for existing entries
			$cgi->td({ -bgcolor => '#ffffff', -colspan => 3, -align => 'center' },
				map { $anchor->{$_} || "$_" } (0,'A'..'Z')
			),
			# sort buttons
			$cgi->td({ -bgcolor => '#ffffff', -colspan => 3 },
				$cgi->sort_buttons('subject.cgi?%s', 1))
		]);

	my $i = 0;

	# subject entries dump starts
	for (sort { eval $exp } @{$lb->{set}}) {
		print
			$cgi->Tr({ -class => $i++ % 2 ? 'odd' : 'even' },
				$cgi->td(
					$cgi->a({
						-id => ($_->[2] || "a$_->[0]"),
						-href => '#',
						-onclick => "copyTo(opener.document.forms['form'].elements['subject'],'".($_->[1])."')"
						}, $cgi->escapeHTML($_->[1])
					)
				),
				$cgi->action_buttons('subject.cgi?%s', $_->[0])
			)
	}
}

print
	# page end
	$cgi->end_content,
	$cgi->end_form,
	$cgi->end_doc;

exit 0;

# validate form's data
sub validate {
	!is_empty($cgi->param('subject'));
}
