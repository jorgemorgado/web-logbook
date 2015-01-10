#
# $Id: CGI.pm,v 1.9 2008/07/13 23:36:59 jorge Exp jorge $
#
# Web logbook GUI related tasks. This class extends the CGI.pm module in a
# way that is very much adapted to the logbook GUI.
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

package Logbook::CGI;

use strict;

# base class
use base 'CGI';
our $AutoloadClass = 'CGI';

__PACKAGE__->nosticky(1);

use Carp;
use Util qw(trim is_empty char2hex swap);
use Data::Page;
use Lang;
use Logbook::DateTime;

# global variables
use vars qw($VERSION);
$VERSION = '1.2';

sub new {
	my ($class, @args) = @_;
	my $self = bless $class->SUPER::new, $class;

	# object defaults
	$self->{approot} = '/logbook';
	$self->{charset} = 'utf-8';
	$self->{daysnew} = 2;
	$self->{refresh} = 0;
	$self->{calformat} = 'eu';
	$self->{dateformat} = '%a %b %e %H:%M:%S %Y';
	$self->{entriesperpage} = 10;
	$self->{subject_maxlen} = 30;	# subject field maximum length

	bless $self, $class;

	# the relevant parameters that must be kept through all logbook pages
	my $keep = 'id|archive|lang|sort|dir|page|user|view';

	# builds a list with the relevant parameters that have been received
	$self->{params} = {};
	for ($self->param) {
		$self->{params}->{$_} = $self->param($_) if /^($keep)$/;
	}

	$self->{archive} = $self->{params}->{archive} || 0;
	$self->{view} = $self->{params}->{view} || 0;
	$self->{tabindex} = 0;
	$self->{menupopup} = 0;	# assume there is no popup menu
	$self->{total_entries} = 0;
	$self->{banner} = '';

	# The maximum fields length is calculated as follows:
	#
	# 1008 bytes is the maximum length of a hash row (key and associated values)
	# [ see BUGS AND WARNINGS on http://perldoc.perl.org/SDBM_File.html ]
	#
	#  4 bytes - hash key (estimated)
	# 10 bytes - timestamp (stored as string)
	# 10 bytes - user's nickname
	#  1 byte  - attach count (estimated)
	#  4 bytes - field separator (one byte per separator)
	#	 9 bytes - hash structure overhead? (i'm really guessing here)
	#
	# This sums to 38 bytes for all fields except the subject and description.
	# Because the subject is user defined (above), the description will be:
	$self->{desc_maxlen} = 1008 - $self->{subject_maxlen} - 38;

	# page object
	$self->{_page} = new Data::Page;
	$self->{params}->{page} = 1 unless $self->{params}->{page};

	# date/time object
	$self->{_datetime} = new Logbook::DateTime;

	$self;
}

# get the same parameters that have been passed to the page
# arg 0 - hash table with extra pairs to be added to the parameters list
# arg 1 - hash table with keys to exclude from the parameters list
sub get_params {
	my $self = shift;
	my $extra = shift;
	my $include = {};
	my $params = '';

	# make a copy of $extra to avoid modifying its original values
	@{$include}{keys %$extra} = values %$extra;

	# include these
	map {
		$include->{$_} = $self->{params}->{$_} unless defined $include->{$_}
	} keys %{$self->{params}};

	# make parameters list (string)
	map {
		$params .= sprintf('%s=%s&', $_, $self->escape_uri($include->{$_}))
	} keys %$include;

	chop $params;
	$params;
}

# set the tabindex
sub set_tabindex {
	my $self = shift;

	if ($_[0]) {
		$self->{tabindex} = $_[0];
	} else {
		$self->get_tabindex;
	}

	$self->{tabindex};
}

# get the next tab index
sub get_tabindex {
	my $self = shift;

	++$self->{tabindex};
}

# set properties in a 'smarter' way (takes the first value that is defined)
sub set_var {
	my $self = shift;
	my ($var, @values) = @_;

	for (@values) {
		if (defined $_) {
			$self->{$var} = $_;
			next;
		}
	}
}

# set language
sub set_language {
	my $self = shift;
	my $lang = shift;

	$self->{_lang} = new Lang(lc($self->{params}->{lang} || $lang));
}

# set banner
sub set_banner {
	my $self = shift;
	my ($list, $banners) = @_;

	unless (is_empty($list)) {
		for (split(',', $list)) {
			if (my $banner = $banners->{lc(trim($_))}) {
				$self->{banner} .= ' '.$banner;
			}
		}
	}
}

# reset the page marker (i.e., back to the first page)
sub reset_page {
	my $self = shift;

	$self->{params}->{page} = 1;
}

# returns a language string
sub str {
	my $self = shift;

	# always returns something to avoid errors
	$self->escapeHTML($self->{_lang}->{$_[0]}) || 'translate me!';
}

# builds and returns the logbook's search criteria (see search form)
sub get_criteria {
	my $self = shift;
	my $crit = {};

	if ($self->param('quicksearch')) {
		$crit->{user} = trim($self->param('quicksearch'));
		$crit->{subject} = $crit->{user};
		$crit->{desc} = $crit->{user};
	} else {
		$crit->{sdate} = trim($self->param('sdate')) if $self->param('sdate');
		$crit->{edate} = trim($self->param('edate')) if $self->param('edate');

		$crit->{user} = $self->param('user')
			if $self->param('user') && $self->param('user') ne '('.$self->str(59).')';

		$crit->{subject} = trim($self->param('subject'))
			if defined $self->param('subject');
  
		$crit->{desc} = trim($self->param('desc')) if defined $self->param('desc');

		$crit->{attach} = $self->param('attach') if $self->param('attach');
	}

	$crit;
}

# for recent entries, it returns the 'new' label; for older ones, returns blank
sub is_new {
	my $self = shift;
	my $ts = shift;

	$ts > time - (86400 * $self->{daysnew}) ?
		$self->img('new.gif', 25, 9, $self->str(63)) : '';
}

# start document
# $title - a string with the logbook title
# $scripts - an optional array reference with javascript pages (.js)
# $styles - an optional array reference with CSS pages (.css)
sub start_doc {
	my $self = shift;
	my ($title, $scripts, $styles, $onload) =
		CGI::Util::rearrange(['TITLE', 'SCRIPTS', 'STYLES', 'ONLOAD'], @_);

	$self->header({
		-charset => $self->{charset}
	}),
	$self->start_html({
		-encoding => $self->{charset},
		-title => $title,
		-script => [
			"var approot = '$self->{approot}';",	# global vars must appear first
# TODO: under test - start
			"var dateformat = '".$self->{dateformat}."';",
#			"var currenttime = '".(scalar localtime)."';",
			"var currenttime = ".(time * 1000).";",	# current time since epoch in ms
# TODO: under test - start
			map { { -src => $_ } } @$scripts
		],
		-style => [ map { { -src => $_ } } @$styles ],
		-onload => $onload || 'return true;',
		-head => $self->Link({
				-rel => 'shortcut icon',
				-href => "$self->{approot}/favicon.ico"
			}).
			# TODO: meta tag for content-type should be removed somewhere in the
			# future as recent versions of CGI.pm automatically add this tag
			# beased on the -encoding key (above). Keeping this will result in
			# the http-equiv meta tag being displayed twice.
			$self->meta({
				'http-equiv' => 'Content-Type',
				-content => "text/html; charset=$self->{charset}"
			}).
			$self->meta({
				'http-equiv' => 'Content-Script-Type',
				-content => 'text/javascript'
			}).
			$self->meta({
				'http-equiv' => 'Content-Style-Type',
				-content => 'text/css'
			}).
			($self->{refresh} ? $self->meta({
				'http-equiv' => 'refresh',
				-content => $self->{refresh}
			}) : '')
	}),
	$self->div({ -class => 'body' });
}

# end document
sub end_doc {
	my $self = shift;

	$self->end_html;
}

# top menu
sub menu {
	my $self = shift;
	my ($menus, $books, $langs, $params) =
		CGI::Util::rearrange(['MENUS', 'BOOKS', 'LANGS', 'PARAMS'], @_);
	my @result;

	# top bar menu
	push @result,
		$self->div({ -id => 'menu' },
			$self->table({ -bgcolor => '#ffffff', -width => '100%' },
				$self->Tr(
					$self->td({ -align => 'left', -class => 'left' },
						$self->menu_options($menus, $params)
					),
					$self->td({ -align => 'right', -class => 'right' },
						($books ? $self->sel_book($books) : ''),
						'&nbsp;',
						($langs ? $self->sel_lang($langs) : '')
					)
				)
			)
		);

	# popup menu
	push @result,
		$self->menu_popup_options($menus, $params) if $self->{menupopup};

	@result;
}

# document header (title and banner if defined)
# $title - a string with the logbook title
# $banner - an optional string with a page banner
sub caption {
	my $self = shift;
	my ($title) =
		CGI::Util::rearrange(['TITLE'], @_);

	# title with book's name and banner
	$self->div({ -id => 'title' },
		$self->table({ -width => '100%' },
			$self->Tr(
				$self->td({ -align => 'left', -class => 'left' },
					$self->div({ -class => 'heading' }, $title),
					$self->div({ -class => 'smalltext' },
# TODO: under test
#						$self->span({ -id => 'servertime' }, '&nbsp;')
# TODO: under test
						$self->span({ -id => 'servertime' }, $self->get_date(time))
					)
				),
				$self->td({ -align => 'right', -class => 'right' }, $self->{banner})
			)
		)
	);
}

# start document body
sub start_content {
	my $self = shift;

	$self->start_div({ -id => 'content' }),
	$self->start_table({ -width => '100%' });
}

# end document body
sub end_content {
	my $self = shift;

	$self->end_table,
	$self->end_div;
}

# document section
# $title - section title
# $colspan - how many columns should the section title span
sub section {
	my $self = shift;
	my ($title, $colspan) =
		CGI::Util::rearrange(['TITLE', 'COLSPAN'], @_);

	$colspan = $colspan || ($self->{archive} ? 4 : 6);

	$self->Tr({ -class => 'section' },
		$self->td({ -colspan => $colspan }, $title)
	);
}

# document's footer
sub footer {
	my $self = shift;
	my $footnote = shift;

	$self->hr({ -class => 'line' }),
	$self->note($footnote || 'Web Logbook');
}

# small text note
# $text - text string
sub note {
	my $self = shift;
	my ($note) =
		CGI::Util::rearrange(['NOTE'], @_);

	$self->div({ -class => 'smalltext' }, $note);
}

sub sel_book {
	my $self = shift;
	my $books = shift;
	my (@values , %labels);
	my ($escape, @result);

	# process configuration directives
	$books->{active} =~ s/\s+//g;	# strip whitespaces
	$books->{active} = lc($books->{active});

	for (split ',', $books->{active}) {
		# active books
		push @values, $_;

		# labels for active books
		$labels{$_} = $books->{$_}->{title} || $_;
	}

	# books selection menu
	push @result, $self->start_form({ -class => 'form', -method => 'POST' });

	# turn off HTML escapes
	$escape = $self->autoEscape(undef);	# hack(?) supported by CGI.pm

	push @result,
		$self->popup_menu({
			-name => 'id',
			-class => 'obj',
			-values => \@values,
			-labels => \%labels,
			-default => $self->{id},
			-tabindex => $self->get_tabindex
		});

	# restores original value
	$self->autoEscape($escape);

	push @result,
		$self->input({
			-class => 'obj',
			-type => 'image',
			-src => "$self->{approot}/images/submit.gif",
			-value => $self->str(71),
			-alt => $self->str(71),
			-title => $self->str(71),
			-tabindex => $self->get_tabindex
		}),
		$self->hidden('lang', $self->{_lang}->{lang}),
		$self->hidden('view', $self->{view}),
		$self->end_form;

	join "\n", @result;
}

sub sel_lang {
	my $self = shift;
	my $langs = shift;
	my (@values, %labels, %attrs);
	my ($escape, @result);
	my $flags = '';

	# process configuration directives
	$langs->{active} =~ s/\s+//g;	# strip whitespaces
	$langs->{active} = lc($langs->{active});

	for (split ',', $langs->{active}) {
		# active languages
		push @values, $_;

		# labels for active languages
		$labels{$_} = $langs->{$_}->{name} || $_;

		# attributes are used to show the flags next to the languages
		$attrs{$_} = { id => $_ };

		#ÊCSS for language flags
		$flags .= "\n#$_:before { content: url($self->{approot}/images/flags/$_.gif); padding-left: 0.1em; padding-right: 0.2em; }";
	}

	# languages selection menu
	push @result,
		$self->start_form({ -class => 'form', -method => 'POST' }),
		$self->style({ -type => 'text/css' }, $flags);

	# turn off HTML escapes
	$escape = $self->autoEscape(undef);	# hack(?) supported by CGI.pm

	push @result,
		$self->popup_menu({
			-name => 'lang',
			-class => 'lang',
			-values => \@values,
			-labels => \%labels,
			-attributes => \%attrs,
			-default => $langs->{default},
			-tabindex => $self->get_tabindex,
			#-onchange => 'selectLang(this);'
		});

	# restores original value
	$self->autoEscape($escape);

	push @result,
		$self->input({
			-class => 'obj',
			-type => 'image',
			-src => "$self->{approot}/images/submit.gif",
			-value => $self->str(72),
			-alt => $self->str(72),
			-title => $self->str(72),
			-tabindex => $self->get_tabindex
		}),
		$self->form_hidden({
			-user => $self->{params}->{user},
			-lang => ''	# excludes lang from the hidden values
		}),
		$self->end_form;

	join "\n", @result;
}

sub sel_view {
	my $self = shift;
	my $view = {
		0 => $self->str(142),	# standard
		1 => $self->str(143),	# group by
		2 => $self->str(144),	# - day
		3 => $self->str(145),	# - week 
		4 => $self->str(146),	# - month
		5 => $self->str(147),	# - year
		6 => $self->str(148),	# - user
		7 => $self->str(149),	# - subject
	};

	$self->start_form({
		-class => 'form',
		-method => 'POST',
		-onsubmit => "return check_dropdown(this.view,0,[1],'".$self->str(155)."');"
	}).
	$self->popup_menu({
		-name => 'view',
		-class => 'obj',
		-values => [ sort keys %$view ],
		-labels => \%$view,
		-default => $self->{view},
		-tabindex => $self->get_tabindex
	}).
	$self->form_hidden({
		-action => 'view',
		-user => $self->{params}->{user},
		-view => '',	# excludes view from the hidden values
		-tabindex => $self->get_tabindex
	}).
	$self->submit({
		-class => 'obj',
		-value => $self->str(151),
		-tabindex => $self->get_tabindex
	}).
	$self->end_form;
}

# top bar menu
sub menu_options {
	my $self = shift;
	my $funcs = shift; 
	my $params = shift;
	my @result;

	$params = $self->get_params($params);

	for (@$funcs) {
		next if $self->{archive} && /^archive$/;

		if (/^(archive|browse|print|trends|sep)$/) {
			# all these options are grupped under the popup menu
			unless ($self->{menupopup}) {
				$self->{menupopup} = 1;

				push @result,
					$self->option(
						$self->u($self->str(141)).$self->small(' &#9660;'), '#', {
							id => 'menutup',
							onclick => 'this.blur();showMenu(event);'
						}
					);
			}
		} else {
			push @result, (
				/^mkarchive$/ ?
					$self->option($self->str(55), "archive.cgi?action=archive&$params") :
				/^search$/ ?
					$self->option($self->str(54), "search.cgi?$params") :
				/^printpage$/ ?
					$self->option($self->str(41), 'javascript:printPage()') :
				/^close$/ ?
					$self->option($self->str(42), 'javascript:window.parent.close()') :

				/^import$/ ?
					$self->option($self->img('import.gif', 24, 23, $self->str(121)),
						"javascript:windowOpen('import.cgi?$params','".
						$self->str(121).
						"',400,400);"
					) :
				/^export$/ ?
					$self->option($self->img('export.gif', 24, 23, $self->str(122)),
						"javascript:windowOpen('export.cgi?$params','".
						$self->str(122).
						"',400,400);"
					) :

				/^quicksearch$/ ?
					$self->start_form({
						-class => 'form',
						-method => 'POST',
						-action => 'search.cgi',
						-onsubmit => "if (is_empty(this.quicksearch.value)) { alert('".$self->str(115)."'); return false; } return true;"
					}).
					$self->input({
						-name => 'quicksearch',
						-class => 'obj',
						-type => 'text',
						-tabindex => $self->get_tabindex
					}).
					$self->form_hidden({
						-action => 'search',
						-andor => 1
					}).
					$self->submit({
						-class => 'obj',
						-value => $self->str(114),
						-tabindex => $self->get_tabindex
					}).
					$self->end_form :

				/^view$/ ?
					$self->sel_view :

					$self->option($self->str(44), "index.cgi?$params")	# back (at last)
			);
		}
	}

	join ' | ', @result;
}

# popup menu
sub menu_popup_options {
	my $self = shift;
	my $funcs = shift; 
	my $params = shift;
	my @result;

	$params = $self->get_params($params);

	push @result,
		$self->start_div({
			-id => 'menupup',
			-style => 'display:none;',
			-onmouseover => 'overmenupup=true;',
			-onmouseout => 'overmenupup=false;'
		}),
		$self->start_table({
			-width => '122',
			-cellspacing => '0',
			-cellpadding => '0',
			-border => '0'
		});

	for (@$funcs) {
		push @result, $self->Tr(
			/^archive$/ ?
				$self->popup_option($self->str(55), "archive.cgi?$params") :
			/^browse$/ ?
				$self->popup_option($self->str(40), "archive.cgi?action=browse&$params") :
			/^print$/ ?
				$self->popup_option($self->str(41), "javascript:windowOpen('print.cgi?$params','".$self->str(41)."',800,600);") :
			/^trends$/ ?
				$self->popup_option($self->str(74), "trends.cgi?$params") :
			/^sep$/ ?
				$self->popup_separator : next
		);
	}

	push @result,
		$self->end_table,
		$self->end_div;

	@result;
}

# top bar menu option with a html A tag (link)
# $name - option name
# $href - option location
# $props - extra properties to the option A tag
sub option {
	my $self = shift;
	my ($name, $href, $props) = @_;

	$props->{href} = $href;
	$props->{tabindex} = $self->get_tabindex;

	$self->a(\%$props, $name);
}

# popup menu option with a html A tag (link)
# $name - option name
# $href - option location
# $props - extra properties to the option A tag
sub popup_option {
	my $self = shift;

	$self->td({
		-class => 'option',
		-bgcolor => '#ffffff',
		-width => '120',
		-height => '12',
		-onmouseover => 'overOption(this)',
		-onmouseout => 'outOption(this)'
		}, $self->option(@_)
	);
}

# popup menu separator
sub popup_separator {
	my $self = shift;

	$self->td({
		-class => 'separator',
		-bgcolor => '#ffffff',
		-width => '120',
		-height => '2'
	});
}

sub date {
	my $self = shift;
	my ($name, $value, $tabindex) =
		CGI::Util::rearrange(['NAME', 'VALUE', 'TABINDEX'], @_);

	$tabindex = $self->set_tabindex($tabindex);

	$self->input({
		-name => $name,
		-size => 22,
		-value => $value || "",
		-tabindex => $tabindex
	}).
	'&nbsp;'.
	$self->a({
		-href => '#',
		-onclick => "$name.popup();",
		-tabindex => $self->get_tabindex
		},
		$self->img('cal.gif', 16, 16, $self->str(45))
	).
	$self->script({ -type => 'text/javascript' },
		"var $name = new calendar(document.forms['form'].elements['$name'],'".$self->{approot}."');".
		"$name.year_scroll = false;".
		"$name.time_comp = true;"
	);
}

sub users {
	my $self = shift;
	my ($name, $values, $default, $tabindex) =
		CGI::Util::rearrange(['NAME', 'VALUES', 'DEFAULT', 'TABINDEX'], @_);

	$tabindex = $self->set_tabindex($tabindex);

	$self->popup_menu({
		-name => $name,
		-id => $name,
		-values => [ sort keys %{$values} ],
		-default => $default,
		-override => 1,
		-tabindex => $tabindex
	});
}

sub subject {
	my $self = shift;
	my ($name, $value, $tabindex) =
		CGI::Util::rearrange(['NAME', 'VALUE', 'TABINDEX'], @_);

	$tabindex = $self->set_tabindex($tabindex);

	$self->input({
		-name => $name,
		-size => 30,
		-maxlength => $self->{subject_maxlen},
		-value => $value,
		-class => 'input',
		-tabindex => $tabindex,
		-onchange => "limitMaxLength(this,$self->{subject_maxlen});",
		-onkeydown => "limitMaxLength(this,$self->{subject_maxlen});",
		-onkeyup => "limitMaxLength(this,$self->{subject_maxlen});"
	}).
	'&nbsp;'.
	$self->a({
		-href => '#',
		-onclick => 'windowOpen("subject.cgi?'.$self->get_params({ dir => 'a' }).'","Subject",350,400);',
		-tabindex => $self->get_tabindex
		},
		$self->img('folder.gif', 16, 16, $self->str(46))
	);
}

sub description {
	my $self = shift;
	my ($name, $value, $rows, $cols, $tabindex, $maxlength) =
		CGI::Util::rearrange(['NAME', ['DEFAULT', 'VALUE'], 'ROWS', ['COLS', 'COLUMNS'], 'TABINDEX', 'MAXLENGTH'], @_);

	$rows = 5 unless ($rows);
	$cols = 73 unless ($cols);

	$tabindex = $self->set_tabindex($tabindex);
	$maxlength = $maxlength || 0;

	$self->script({ -type => 'text/javascript' }, "
function setCharsLeft(obj) {
	var max = $maxlength;
	limitMaxLength(obj, max);

	var left, str;
	if ((left = max - obj.value.length) > 1)
		str = sprintf('" . $self->str(118) ."', left);
	else if (left)
		str = '".$self->str(119)."';
	else
		str = '".$self->str(120)."';

	changeLabel(document.getElementById('descinfo'), str);
}"),
	$self->textarea({
		-name => $name,
		-id => $name,
		-rows => $rows,
		-cols => $cols,
		-value => $value,
		-override => 1,
		-tabindex => $tabindex,
		-onfocus => 'this.rows=10;',
		-onchange => $maxlength ? 'setCharsLeft(this);' : 'return true;',
		-onkeydown => $maxlength ? 'setCharsLeft(this);' : 'return true;',
		-onkeyup => $maxlength ? 'setCharsLeft(this);' : 'return true;'
	}),
	($maxlength ?
		$self->br.
		$self->label(
			$name,
			'descinfo',
			sprintf($self->str(118), $maxlength - length($value))
		) : ''
	);
}

sub form_hidden {
	my $self = shift;
	my ($archive, $lang, $id, $page, $sort, $dir, $view, @other) =
		CGI::Util::rearrange(['ARCHIVE', 'LANG', 'ID', 'PAGE', 'SORT', 'DIR', 'VIEW'], @_);
	my @result;

	# these should be always present in every form (if defined)
	$archive = $self->{archive} unless defined $archive;
	$lang = $self->{_lang}->{lang} unless defined $lang;
	$id = $self->{params}->{id} unless defined $id;
	$page = $self->{params}->{page} unless defined $page;
	$sort = $self->{params}->{sort} unless defined $sort;
	$dir = $self->{params}->{dir} unless defined $dir;
	$view = $self->{params}->{view} unless defined $view;
	push @result, $self->hidden('archive', $archive) if $archive && !is_empty($archive);
	push @result, $self->hidden('lang', $lang) if $lang && !is_empty($lang);
	push @result, $self->hidden('id', $id) if $id && !is_empty($id);
	push @result, $self->hidden('page', $page) if $page && !is_empty($page);
	push @result, $self->hidden('sort', $sort) if $sort && !is_empty($sort);
	push @result, $self->hidden('dir', $dir) if $dir && !is_empty($dir);
	push @result, $self->hidden('view', $view) if $view && !is_empty($view);


	# other hidden form elements
	for (@other) {
		push @result,
			/(.*)=\"(.*)\"/ ? $self->hidden($1, $2) : $self->hidden($_, '');
	}

	join "\n", @result;
}

sub form_attach {
	my $self = shift;

	# attach id works like a session id but for attachments only; the id is
	# used to relate all submitted attachments with this logbook entry
	$self->hidden('attid', $_[1]).
	$self->button({
		-id => 'attbtn',
		-value => $_[0],
		-onclick => 'windowOpen("attach.cgi?'.$self->get_params({ attid => $_[1] }).'","Upload",400,400);',
		-tabindex => $self->get_tabindex
	});
}

# set the attach info label on the logbook page
sub attach_info {
	my $self = shift;
	my $count = shift || 0;

	$count == 0 ?
		$self->str(60) :
	$count == 1 ?
		$self->str(61) :
		sprintf($self->str(62), $count);
}

# returns the document's type using the same semantic as in CGI::start_html()
# (actually, most of the code here was taken - almost verbatim - from there)
sub doc_type {
	my $self = shift;
	my ($dtd, $encoding, $declare_xml) =
		CGI::Util::rearrange(['DTD', 'ENCODING'], @_);

	$encoding = $self->{charset} unless defined $encoding;

	my (@result, $xml_dtd);

	if ($dtd) {
		if (defined(ref($dtd)) and (ref($dtd) eq 'ARRAY')) {
			$dtd = $CGI::DEFAULT_DTD unless $dtd->[0] =~ m|^-//|;
		} else {
			$dtd = $CGI::DEFAULT_DTD unless $dtd =~ m|^-//|;
		}
	} else {
		$dtd = $CGI::XHTML ? $self->XHTML_DTD : $CGI::DEFAULT_DTD;
	}

	$xml_dtd++ if $dtd && ref($dtd) eq 'ARRAY' && $dtd->[0] =~ /\bXHTML\b/i;
	$xml_dtd++ if $dtd && ref($dtd) eq '' && $dtd =~ /\bXHTML\b/i;
	push @result, qq(<?xml version="1.0" encoding="$encoding"?>) if $xml_dtd && $declare_xml;

	if (ref($dtd) && ref($dtd) eq 'ARRAY') {
		push @result, qq(<!DOCTYPE html\n\tPUBLIC "$dtd->[0]"\n\t "$dtd->[1]">);
		$self->{DTD_PUBLIC_IDENTIFIER} = $dtd->[0];
	} else {
		push @result, qq(<!DOCTYPE html\n\tPUBLIC "$dtd">);
		$self->{DTD_PUBLIC_IDENTIFIER} = $dtd;
	}

	join "\n", @result;
}

sub start_div {
	my $self = shift;
	my ($id, $class, @other) =
		CGI::Util::rearrange(['ID', 'CLASS'], @_);

	$id = $id ? qq( id="$id") : '';
	$class = $class ? qq( class="$class") : '';
	my $other = @other ? " @other" : '';

	"<div$id$class$other>";
}

sub end_div {
	my $self = shift;

	'</div>';
}

sub hidden {
	my $self = shift;
	my ($name, $value) =
		CGI::Util::rearrange(['NAME', 'VALUE'], @_);

	($value ?
		$self->input({ -type => 'hidden', -name => $name, -value => $value }) : '');
}

sub label {
	my $self = shift;
	my ($for, $id, $value, $title, @other) =
		CGI::Util::rearrange(['FOR', 'ID', ['DEFAULT', 'VALUE'], 'TITLE'], @_);

	$value = $value ? $self->escapeHTML($value) : '';
	$title = $title ? qq/ title="$title"/ : '';
	my $other = @other ? " @other" : '';

	qq{<label for="$for" id="$id"$title$other>$value</label>}
}

# re-defines the image tag
# $name - image filename (under the logbook image directory)
# $width - width in pixels
# $height - height in pixels
# $title - alternative/title text
sub img {
	my $self = shift;
	my ($name, $width, $height, $title) =
		CGI::Util::rearrange(['NAME', 'WIDTH', 'HEIGHT', ['ALT', 'TITLE']], @_);

	$self->SUPER::img({
		-src => "$self->{approot}/images/$name",
		-border => 0,
		-width => $width,
		-height => $height,
		-alt => $title,
		-title => $title
	});
}

# returns a sort expression to be used when sorting an list of values
# $sort - default sort field if not already provided
# $dir - default sort direction if not already provided
# $exp - CSV string with the numeric fields in the sort ('-' if not to be used)
sub sort_expr {
	my $self = shift;
	my ($sort, $dir, $exp) = @_;
	my $op;

	# sort field (0=1st column; 1=2nd column; ...)
	$self->{params}->{sort} = $sort if is_empty($self->{params}->{sort});

	# sort direction (a=ascending; d=descending)
	$self->{params}->{dir} = $dir if is_empty($self->{params}->{dir});

	my ($left, $right) = ($self->{params}->{dir} eq 'a') ? ('a','b') : ('b','a');

	if ($self->{params}->{sort} =~ /^($exp)$/) {			# numeric fields
		$op = '<=>';
		$left = "\$".$left."->[$self->{params}->{sort}]";
		$right = "\$".$right."->[$self->{params}->{sort}]";
	} else {			# alphanumeric fields
		$op = 'cmp';
		$left = "lc(\$".$left."->[$self->{params}->{sort}])";
		$right = "lc(\$".$right."->[$self->{params}->{sort}])";
	}

	"$left $op $right";
}

# returns the sort buttons (takes care if any has been selected)
# $href - referer page
# $col - sort column
# $params - extra parameters for the sort buttons
sub sort_buttons {
	my $self = shift;
	my ($href, $col, $params) = @_;

	$params = {} unless $params;

	$self->a({
		-href =>
			sprintf(
				$href,
				$self->get_params({ sort => $col, dir => 'a', %$params })
			)
		},
		$self->img(
			$col == $self->{params}->{sort} && $self->{params}->{dir} eq 'a' ?
				'sort_up_sel.gif' : 'sort_up.gif', 10, 4, $self->str(47)
		)
	).
	$self->a({
		-href =>
			sprintf(
				$href,
				$self->get_params({ sort => $col, dir => 'd', %$params })
			)
		},
		$self->img(
			$col == $self->{params}->{sort} && $self->{params}->{dir} eq 'd' ?
				'sort_down_sel.gif' : 'sort_down.gif', 10, 4, $self->str(48)
		)
	);
}

# returns the action buttons
# $href - referer page
# $nr - entry number
# $params - extra parameters for the action buttons
sub action_buttons {
	my $self = shift;
	my ($href, $nr, $params) = @_;

	$params = {} unless $params;

	$self->td({ -width => '1%', -align => 'right' }, [
		$self->a({
			-href =>
				sprintf(
					$href,
					$self->get_params({ action => 'edit', nr => $nr, %$params })
				)
			},
			$self->img('edit.gif', 16, 16, $self->str(53))
		),
		$self->a({
			-href =>
				sprintf(
					$href,
					$self->get_params({ action => 'delete', nr => $nr, %$params })
				),
			-onclick => "return confirm('".$self->str(50)."')"
			},
			$self->img('trash.gif', 16, 16, $self->str(49))
		),
	]);
}

# returns the page buttons
# $href - referer page
# $nr - entry number
sub page_buttons {
	my $self = shift;
	my ($href, $params) = @_;
	my @result;

	# no buttons if no entries or only one page
	return '' if $self->{entriesperpage} <= 0 || $self->{_page}->last_page == 1;

	$params = {} unless $params;

	my $tol = 8;	# tolerance for page navigation buttons

	my $start = $self->{_page}->current_page - $tol <= 1 ?
		$self->{_page}->first_page : $self->{_page}->current_page - $tol;
	my $end = $self->{_page}->current_page + $tol >= $self->{_page}->last_page ?
		$self->{_page}->last_page : $self->{_page}->current_page + $tol;

	push @result,
		$self->a({
			-href =>
				sprintf(
					$href,
					$self->get_params({ page => $self->{_page}->current_page-1,%$params })
				)
			}, $self->img('prev2.gif', 16, 16, $self->str(111))
		) if $self->{_page}->current_page > $self->{_page}->first_page;

	push @result,
		'...' if $self->{_page}->current_page - $tol > 1;

	foreach my $p ($start .. $self->{_page}->current_page-1) {
		push @result,
			$self->a({
				-href => sprintf($href, $self->get_params({ page => $p, %$params }))
				}, $p
			);
	}

	push @result,
		$self->{_page}->current_page;

	foreach my $p ($self->{_page}->current_page+1 .. $end) {
		push @result,
			$self->a({
				-href => sprintf($href, $self->get_params({ page => $p, %$params }))
				}, $p
			);
	}

	push @result,
		'...' if $self->{_page}->current_page + $tol < $self->{_page}->last_page;

	push @result,
		$self->a({
			-href =>
				sprintf(
					$href,
					$self->get_params({ page => $self->{_page}->current_page+1,%$params })
				)
			}, $self->img('next2.gif', 16, 16, $self->str(112))
		) if $self->{_page}->current_page < $self->{_page}->last_page;

	$self->Tr(
		$self->td({
			-align => 'center',
			-colspan => $self->{archive} ? 4 : 6
			}, join '&nbsp;&nbsp;', @result)
	);
}

# returns the expand/collapse buttons for the group views
sub expand_collapse_buttons {
	my $self = shift;

	$self->Tr(
		$self->td({ -colspan => $self->{archive} ? 4 : 6 },
			$self->a({
				-href => '#',
				-onclick => "expandAll('tree'); return false"
				}, $self->str(152)).
				'&nbsp;&nbsp;'.
				$self->a({
				-href => '#',
				-onclick => "collapseAll('tree'); return false"
				}, $self->str(153))
			)
		);
}

# message notification (usually errors or warnings)
# $level - current level
# @msg - messages list
sub notify {
	my $self = shift;
	my ($level, @msg) = @_;

	# these have to map the same levels defined in the Log object
	my %levels = (
		0 => [ $self->str(106), 'stoplight_r.gif' ],	# error
		1 => [ $self->str(107), 'stoplight_y.gif' ],	# warning
		2 => [ $self->str(108), 'stoplight_y.gif' ],	# notice
		3 => [ $self->str(109), 'stoplight_g.gif' ],	# information
		4 => [ $self->str(110), 'stoplight_g.gif' ]		# debug
	);

	$self->table({ -class => 'notify' },
		$self->Tr(
			$self->td({ -align => 'center' },
				$self->img($levels{$level}->[1], 35, 63, $levels{$level}->[0])),
			$self->td({ -align => 'left' },
				map { sprintf('%s%s', $_, $self->br) } @msg)
		)
	),
	$self->br;
}

# dumps the logbook entries
# $href - referer page
# $users - users list
# $actions - show action buttons?
# @recs - logbook entries
sub dump {
	my $self = shift;
	my ($href, $users, $actions, @recs) = @_;

	if ($self->{view} > 1) {
		# group by view
		$self->view_groupby($href, @recs);
	} else {
		# default view
		$self->view_default($href, $users, $actions, @recs);
	}
}

# default view
sub view_default {
	my $self = shift;
	my ($href, $users, $actions, @recs) = @_;
	my @result;

	# entries per page
	$self->{_page}->current_page($self->{params}->{page});
	$self->{_page}->total_entries($#recs + 1);
	$self->{_page}->entries_per_page(
		$self->{entriesperpage} > 0 ?
			$self->{entriesperpage} : $self->{_page}->total_entries
	);

	# this label will be used by the treeview.js to get the page parameters
	push @result,
		$self->Tr(
			$self->td({ -colspan => $self->{archive} ? 4 : 6 },
				$self->label({
					-for => 'content',
					-id => 'treeview',
				})
			)
		) if $self->{view} > 1;

	# logbook entries dump starts
	for my $i ($self->{_page}->first - 1 .. $self->{_page}->last - 1) {
		my ($nr, $ts, $user, $subject, $desc, $attcnt) = @{$recs[$i]};

		push @result,
			$self->start_Tr({ -class => $i % 2 ? 'odd' : 'even' });

		push @result,
			$self->td({ -width => '20%', -nowrap => 'nowrap' },
				$self->get_date($ts).' '.$self->is_new($ts)
			),
			$self->td({ -width => '5%' },
				$self->label('user', "$user$nr", $user, $users->{$user})
			),
			$self->td({ -colspan => ($attcnt ? 1 : 2) },
				$self->escape_subject($subject).$self->br.$self->escape_desc($desc)
			);

		# show the clip if there are attachments
		push @result,
			$self->td({ -width => '1%', -align => 'right' },
				$self->a({
					-href => "attview.cgi?".$self->get_params({ attid => $nr })
					}, $self->img('attach.gif', 16, 16, $self->attach_info($attcnt)))
			) if $attcnt;

		# show the action buttons (edit, delete)
		push @result,
			$self->action_buttons($href, $nr) if $actions;

		push @result,
			$self->end_Tr;
	}

	join "\n", @result;
}

# group view
sub view_groupby {
	my $self = shift;
	my ($href, @recs) = @_;
	my @result;

	my ($nodes, $cnt, $curr);
	my $last = '';
	my $node = 1;

	# prepare the DateTime object with my own settings
	$self->{_datetime}->{calformat} = $self->{calformat};
	$self->{_datetime}->{weeklabel} = $self->str(150);

	# logbook entries dump starts
	for my $i (0 .. $#recs) {
		my ($nr, $ts, $user, $subject, $desc, $attcnt) = @{$recs[$i]};

		for ($self->{view}) {
			$curr = (
				/^2$/ ?	# group by day
					$self->{_datetime}->get_day($ts) :
				/^3$/ ? # group by week
					$self->{_datetime}->get_week($ts) :
				/^4$/ ?	# group by month
					$self->{_datetime}->get_month($ts) :
				/^5$/ ?	# group by year
					$self->{_datetime}->get_year($ts) :
				/^6$/ ?	# group by user or by subject (default)
					$user : $subject
			);
		}

		if ($curr ne $last) {
			# if group field has changed, create a new node
			$cnt = 1;
			$last = $curr;
			$nodes->{$node++} = [ $curr, $nr, $cnt ];
		} else {
			# otherwise just increase the node's records counter
			$nodes->{$node - 1}[2] = ++$cnt;
		}
	}

	# reset the node's counter
	$node = 1;

	push @result,
		$self->start_Tr,
		$self->start_td({ -colspan => 6 }),
		$self->start_ul({ -id => 'tree', -class => 'tree' });

	push @result,
		$self->li(
			$self->a({
				-class => 'treelink',
				-href => sprintf($href, $self->get_params),
				-id => 'node_'.$node,
				}, $nodes->{$_}[0]." (".$nodes->{$_}[2].")"
			),
			$self->ul([
				$self->li(
					$self->a({
						-class => 'treelink',
						-href => sprintf($href,
							$self->get_params({
								idParent => $node++,
								nr => $nodes->{$_}[1]
							})
						),
						-id => 'node_'.($node++),
						}, $self->str(154)
					)
				)
			])
		) for (sort keys %$nodes);

	push @result,
		$self->end_ul,
		$self->end_td,
		$self->end_Tr;

	join "\n", @result;
}

sub escape_subject {
	my $self = shift;
	my $subject = shift;

	# underlines the subject if not empty
	is_empty($subject) ? '' : $self->u($self->escapeHTML($subject));
}

sub escape_desc {
	my $self = shift;
	my $desc = shift;

	if ($desc) {
		# escape HTML special chars/tags
		$desc = $self->escapeHTML($desc);
		# line break
		$desc =~ s/\n/\n<br \/>/g;
		# urls are translated into real html tags
		$desc =~ s/(\w+):\/\/([a-zA-Z0-9_&:,;=+\-\.\/\?]+)(\s*)/<a href=\"$1:\/\/$2">$1:\/\/$2<\/a>$3/g;
	} else {
		$desc = '';
	}

	$desc;
}

# re-writes an URI to be HTML compliant (see RFC2396)
sub escape_uri {
	my $self = shift;
	my $uri = shift || '';

	$uri =~ s/([\s#\$%&\/:;<=>?\@[\\\]^`{|}~])/'%'.char2hex($1)/eg;
	$uri;
}

# timestamp -> date (in the desired format or format from configuration file)
sub get_date {
	my $self = shift;

	$self->{_datetime}->get_date($_[1] || $self->{dateformat}, $_[0]);
}

# timestamp -> date
sub ts2date {
	my $self = shift;

	$self->get_date(
		$_[0],
		$self->{calformat} eq 'us' ? '%m/%d/%Y %H:%M:%S' : '%d-%m-%Y %H:%M:%S'
	);
}

# date -> timestamp
sub date2ts {
	my $self = shift;
	my $date = shift;
	my $ts;

	if ($date =~ /(\d+)-(\d+)-(\d+)\s*(\d+):(\d+):(\d+)/ ||
		$date =~ /(\d+)\/(\d+)\/(\d+)\s*(\d+):(\d+):(\d+)/) {
		my ($day, $month, $year, $hour, $min, $sec) = ($1, $2, $3, $4, $5, $6);

		# swaps day and month if american format
		swap(\$day, \$month) if $self->{calformat} eq 'us';

		$ts = $self->{_datetime}->date2ts($sec, $min, $hour, $day, $month, $year);
	}

	# TODO: return some warning if date is invalid?
	$ts;
}

sub format_interval {
	my $self = shift;
	my $secs = shift;

	sprintf('%d %s, %d:%02d:%02d',
		int($secs / 86400),
		$self->str(75),
		int($secs / 3600) % 24,
		int($secs / 60) % 60,
		$secs % 60);
}

1;

__END__
