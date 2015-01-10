#
# $Id: Util.pm,v 1.3 2008/07/19 23:59:32 jorge Exp jorge $
#
# Util functions.
#
# Copyright 2003-2007, Jorge Morgado. All rights reserved.
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

package Util;

use strict;

# global variables
use vars qw($VERSION @ISA @EXPORT);
$VERSION = '1.1';

require Exporter;
@ISA = qw(Exporter);

@EXPORT = qw(
	swap
	trim
	is_empty
	is_numeric
	date2ts
	char2hex
);

sub swap($$) {
	my ($one, $two) = (shift, shift);

	($$one, $$two) = ($$two, $$one);
}

sub trim($) {
	my $s = shift;

	$s =~ s/(^\s+|\s+$)//g;
	$s;
}

# string is empty
sub is_empty($) {
	!defined($_[0]) || trim($_[0]) eq '';
}

# is a number (digits only)?
sub is_numeric($) {
	return ($_[0] =~ /^\d+$/);
}

# convert character to hexadecimal
sub char2hex($) {
	sprintf '%lx', ord $_[0];
}

1;

__END__
