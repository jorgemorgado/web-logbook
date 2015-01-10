#
# $Id: Simple.pm,v 1.1 2007/09/04 21:12:06 jorge Exp $
#
# Simple logging.
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

package Log::Simple;

use strict;

# base class
use base 'Log';

use Carp;

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;
	my $self = bless $class->SUPER::new(@args), $class;

	# object defaults
	$self->{msg} = ();

	bless $self, $class;

  $self;
}

# insert a new log message in the list
sub add {
	my $self = shift;
	my $level = shift;
	my @msg = @_;

	# only logs if the log level is more severe than the trace level
	if ($level <= $self->{trace}) {
		$self->{level} = $level if ($level >= 0 && $level < $self->{level});

		push @{$self->{msg}}, @msg;
	}
}

# last log message
sub getlast {
	my $self = shift;

	$self->{msg}[-1];
}

# all log messages
sub getall {
	my $self = shift;

	@{$self->{msg}};
}

# total of log messages
sub gettotal {
	my $self = shift;

	(1 + $#{$self->{msg}});
}

# most severe (highest) level of all log messages
sub getlevel {
	my $self = shift;

	$self->{level};
}

1;

__END__
