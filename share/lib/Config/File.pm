#
# $Id: File.pm,v 1.1 2008/07/13 23:30:43 jorge Exp jorge $
#
# Configuration file.
#
# Copyright 2004-2007, Jorge Morgado. All rights reserved.
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

package Config::File;

use strict;

use Carp;

# global variables
use vars qw($VERSION);
$VERSION = '1.1';

sub new {
	my ($class, @args) = @_;

	# object defaults
	my $self = { file => '' };

	bless $self, $class;

	if (@args == 1) {	# positional args given
		$self->{file} = $_[1];
	} elsif (@args > 1) {	# named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(file)$/) {
				$self->{$1} = $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self->init if $self->{file};

	$self;
}

sub init {
	my $self = shift;
	my $file = shift || $self->{file};

	if ($file) {
		open(FH, $file) || croak "Failed to open config file $file. $!";

		my @lines = <FH>;

		_parse(0, \@lines, \%$self);

		close FH;
	} else {
		croak 'Config file was not provided';
	}
}

# private methods (used internally)
sub _parse {
	my ($start, $lines, $what) = @_;
	my $token_nl = 0;	# new line
	my $option;

	for (my $n = $start; $n < scalar @{$lines}; $n++) {
		my ($line, $value);

		next if $lines->[$n] =~ /^\s*($|#)/;	# skip blank/comments
		$line = (split /\s\#/, $lines->[$n])[0];	# remove inline comments
		$line =~ s/^\s+|\s+$//g;	# line trim

		if ($token_nl) {
			$value = $line;
		} elsif ($line =~ /^}/) {
			return $n;
		} elsif (($option, $value) = ($line =~ /^\s*(\S+)\s*(.*)/)) {
			$option = lc($option);	# lowercase directive
			$option =~ s/-/_/;	# dash -> underscore
		} else {
			croak sprintf('Config file syntax error (line %d): %s', $n + 1, $line);
		}

		if ($value =~ /^{$/) {
			$n = _parse($n + 1, \@$lines, \%{$what->{$option}});
		} else {
			# BUG: the parser fails if a multiline directive has more than 2 lines
			$value = $1 if (my $nl = ($value =~ /(.*)(\s+\\\s*$)/));
			$value =~ s/^["'](.*?)["']$/$1/;	# unquote value

			if ($nl) {
				$what->{$option} .= ' '._translate($value);
			} else {
				$what->{$option} = _translate($value);
			}

			$token_nl = $nl;
		}
	}
}

sub _translate {
	my $value = shift;

	$value = 1 if $value =~ /^(yes|true)$/i;	# yes, true => 1
	$value = 0 if $value =~ /^(no|false)$/i;	# no, false => 0

	$value;
}

1;

__END__
