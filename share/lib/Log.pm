#
# $Id: Log.pm,v 1.2 2007/09/04 21:43:26 jorge Exp $
#
# Log functions.
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

package Log;

use strict;

use Carp;

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;

	# object defaults
	my $self = {
		ERROR => 0,
		WARNING => 1,
		NOTICE => 2,
		INFO => 3,
		DEBUG => 4,
		levels => {
			0 => 'ERROR',
			1 => 'WARNING',
			2 => 'NOTICE',
			3 => 'INFO',
			4 => 'DEBUG'
		},
		level => 4,		# stores the current level (with DEBUG being the less severe)
		trace	=> 2		# up to which severity level log entries will be catched
	};

	bless $self, $class;

	if (@args == 1) { # positional args given
		$self->{trace} = $_[1];
	} elsif (@args > 1) { # named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(trace)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self;
}

sub increase {
	my $self = shift;

	$self->{trace}++ if $self->{trace} < 4;
	$self->{trace};
}

sub decrease {
	my $self = shift;

	$self->{trace}-- if $self->{trace} > 0;
	$self->{trace};
}

1;

__END__
