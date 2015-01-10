#
# $Id: CSV.pm,v 1.2 2008/08/09 15:18:56 jorge Exp jorge $
#
# CSV module.
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

package Text::CSV;

use strict;

use Carp;

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;

	# object defaults
	my $self = {
		fh => undef,
		buf => '',

		# control chars
		sep => ',',		# separator (delimiter)
		str => '"',		# string fields should be enclosed into this (quoted)
		eol => "\n",	# end of line

		is_eof => 0,
		is_dublequote => 0
	};

	bless $self, $class;

	if (@args == 1) {	# positional args given
		$self->{sep} = $_[1];
	} elsif (@args > 1) {	# named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(fh|sep)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

  $self;
}

sub escape {
	my $self = shift;
	my $val = shift;

	$val =~ s/$self->{str}/$self->{str}$self->{str}/g;
	$val;
}

sub quote {
	my $self = shift;

	$self->{str}.$self->escape($_[0]).$self->{str};
}

sub set_row {
	my $self = shift;

	join($self->{sep}, @_).$self->{eol};
}

# TODO: this is a very simple parser and needs a lot more testing
sub get_col {
	my $self = shift;
	my $col = '';
	my $mode = '';
	my @modes = ();

	my $append = sub {
		# don't append if it's a blank and we aren't in string mode with empty $col
		$col .= $_[0] unless $_[0] eq ' ' && $mode ne 'str' && $col eq '';
	};

	while (1) {
		# read next char to buffer; terminate if found end-of-file
		unless (read($self->{fh}, $self->{buf}, 1)) {
			$self->{is_eof} = 1;
			last;
		}

		# detect double quotes and make sure they are added to the result
		if ($self->{buf} eq $self->{str}) {
			if ($self->{is_dublequote}) {
				$self->{is_dublequote} = 0;

				&$append($self->{str});
			} else {
				$self->{is_dublequote} = 1;
			}
		} else {
			$self->{is_dublequote} = 0;
		}

		# if in string mode
		if ($mode eq 'str') {
			if ($self->{buf} eq $self->{str}) {
				$mode = (shift @modes) || '';
			} else {
				&$append($self->{buf});
			}

		# if found a quote, enter string mode
		} elsif ($self->{buf} eq $self->{str}) {
			push @modes, $mode;
			$mode = 'str';

		# if found found a delimiter or end-of-line
		} elsif ($self->{buf} eq $self->{sep} || $self->{buf} eq $self->{eol}) {
			last;

		# otherwise just append whatever it found
		} else {
			&$append($self->{buf});
		}
	}

	$col;
}

sub get_row {
	my $self = shift;
	my @cols = ();

	return undef if $self->{is_eof};

	while (1) {
		my $col = $self->get_col();

		last if $self->{is_eof};
		push @cols, $col;
		last if $self->{buf} eq $self->{eol};
	}

	\@cols;
}

1;

__END__
