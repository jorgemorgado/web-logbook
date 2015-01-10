#
# $Id: Lang.pm,v 1.2 2007/09/04 21:42:28 jorge Exp $
#
# Language functions.
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

package Lang;

use strict;

use Carp;

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;

	my $self= {
		default => 'en',	# default language is English
		lang => undef
	};

	bless $self, $class;

	if (@args == 1) {	# positional args given
		$self->{lang} = $_[1];
	} elsif (@args > 1) {	# named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(lang)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self->init if $self->{lang};

	$self;
}

sub init {
	my $self = shift;
	my $lang = shift || $self->{lang} || $self->{default};

	if ($lang) {
		open(FH, "../share/lang/$lang.txt") || croak "Failed to open language file $lang.txt. $!";

		while (<FH>) {
			next if /^\s*($|\#)/;		# skip blank/comments
			chomp;
			if (my ($key, $value) = split(/\s+/, $_, 2)) {
				$self->{$key} = $value;
			}
		}

		close FH;
	} else {
		croak 'Language was not provided';
	}
}

sub str {
	my $self = shift;

	$self->{$_[0]};
}

1;

__END__
