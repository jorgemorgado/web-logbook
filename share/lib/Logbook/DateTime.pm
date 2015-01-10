#
# $Id$
#
# Logbook date & time functions.
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

package Logbook::DateTime;

use strict;
use integer;

use Carp;
use POSIX qw(mktime strftime);

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;

	# object defaults
	my $self = {
		calformat => 'eu',
		weeklabel => 'W'
	};

	bless $self, $class;

	if (@args == 1) { # positional args given
		$self->{calformat} = $_[1];
	} elsif (@args > 1) { # named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(calformat|weeklabel)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self;
}

# returns a date in the desired format
sub get_date {
	my $self = shift;

	strftime($_[0], localtime $_[1]);
}

# receives a timestamp (ts) and returns the first second of the ts's YEAR
sub get_first_second_of_year {
	my $self = shift;

	mktime(0, 0, 0, 1, 0, (localtime $_[0])[5], , , -1);
}

# receives a timestamp (ts) and returns the last second of the ts's YEAR
sub get_last_second_of_year {
	my $self = shift;

	mktime(59, 59, 23, 31, 11, (localtime $_[0])[5], , , -1);
}

# receives a timestamp (ts) and returns the first second of the ts's MONTH
sub get_first_second_of_month {
	my $self = shift;

	mktime(0, 0, 0, 1, (localtime $_[0])[4, 5], , , -1);
}

# receives a timestamp (ts) and returns the last second of the ts's MONTH
sub get_last_second_of_month {
	my $self = shift;
	my ($month, $year) = (localtime $_[0])[4, 5];
	my @m_day = $self->get_month_days($year);

	mktime(59, 59, 23, $m_day[$month], $month, $year, , , -1);
}

# receives a timestamp (ts) and returns the first second of the ts's WEEK
sub get_first_second_of_week {
	my $self = shift;
	my $wday = (localtime $_[0])[6];

	# week starts on Monday (day 0); Sunday should become day 6
	$wday = ($wday == 0 ? 6 : --$wday);

	$self->get_first_second_of_day($_[0] - ($wday * 86400));
}

# receives a timestamp (ts) and returns the last second of the ts's WEEK
sub get_last_second_of_week {
	my $self = shift;
	my $wday = (localtime $_[0])[6];

	# week ends on Sunday (day 6);
	$wday = ($wday == 0 ? 0 : 7 - $wday);

	$self->get_last_second_of_day($_[0] + ($wday * 86400));
}

# receives a timestamp (ts) and returns the first second of the ts's DAY
sub get_first_second_of_day($) {
	my $self = shift;

	mktime(0, 0, 0, (localtime $_[0])[3, 4, 5], , , -1);
}

# receives a timestamp (ts) and returns the last second of the ts's DAY
sub get_last_second_of_day($) {
	my $self = shift;

	mktime(59, 59, 23, (localtime $_[0])[3, 4, 5], , , -1);
}

# adjusts a timestamp to DST
sub adjust_dst {
	my $self = shift;

	(localtime $_[0])[8] > 0 ? -3600 : 0;
}

sub get_year {
	my $self = shift;

	(localtime $_[0])[5] + 1900;
}

sub get_month {
	my $self = shift;

	$self->get_date('%b %Y', $_[0]);
}

# get the week number as defined by ISO8601:1988
# (based on http://www.adsb.co.uk/date_and_time/week_numbers/isowknum.perl)
sub get_week {
	my $self = shift;
	my ($year, $day, $daynr) = (localtime $_[0])[5, 6, 7];

	$year += 1900;	# 4 digits year
	$daynr++;		# day number (1-366)
	$day = 7 if $day == 0;	# make Sunday the 7th day (week starts on Monday)

	my $start_day = $daynr - $day;
	my $week = $start_day / 7 + 1;	# simple week number (SWN)

	# adjusts the SWN - ISO8601:1988 defines week number as:
	# - weeks start on a Monday;
	# - week 1 of a given year is the one that includes the first Thursday of
	#   that year (or, equivalently, week 1 is the week that includes 4 January)
	$week = 0 if $start_day < 0;

	$start_day += 7 if $start_day % 7 < 0;
	my $first_sunday = $start_day % 7;	# first Sunday of the year

	$week++ if $first_sunday > 3;

	if ($week < 1) {
		# this falls on the last week of the previous year, which is either 52 or 53
		# to get here, $first_sunday is either 1, 2 or 3
		# - if 1 => the last week of the previous year is guaranteed to be week 52
		# - if 2 => depends on:
		#   a. this year is a leap year: if yes, the last week of the previous year
		#      was week 52
		#   b. if this year isn't a leap year, was the previous year a leap year?
		#      if not => the last week of the previous year was week 52
		#      if yes => the last week of the previous year was week 53
		# - if 3 => the last week of the previous year is guaranteed to be week 53
		if ($first_sunday == 1) {
			$week = 52;
		} elsif ($first_sunday == 2) {
			$week = $self->is_leap($year) ? 52 : ($self->is_leap($year -1) ? 53 : 52);
		} elsif ($first_sunday == 3) {
			$week = 53;
		} else {
			# TODO: maybe we should produce an error here?
			$week = 0;
		}

		$year--;

	} elsif ($week == 53 && !($self->is_leap($year) && $first_sunday == 5) && $first_sunday != 4) {
		# although rare, week 53 can happen
		$week = 1;
		$year++;
	}

	sprintf('%s%d, %d', $self->{weeklabel}, $week, $year);
}

sub get_day {
	my $self = shift;

	($self->{calformat} eq 'us' ?
		$self->get_date('%b %e, %Y', $_[0]) :
		$self->get_date('%e %b %Y', $_[0])
	);
}

# is a leap year? (year must be a 4 digit number)
sub is_leap {
	my $self = shift;

	($_[0] % 4 == 0) && (($_[0] % 100 != 0) || ($_[0] % 400 == 0));
}

# returns an array with the nr. of days for each month
sub get_month_days {
	my $self = shift;

	(31, $self->is_leap($_[0]) ? 28 : 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31);
}

sub is_date {
	my $self = shift;
	my ($sec, $min, $hour, $day, $mon, $year) = @_;
	my @m_day = $self->get_month_days($year);

	(1900 <  $year && $year <  2100 &&
			0 <  $mon  && $mon  <= 12 &&
			0 <  $day  && $day  <= $m_day[$mon - 1] &&
			0 <= $hour && $hour <  24 &&
			0 <= $min  && $min  <  60 &&
			0 <= $sec  && $sec  <  60);
}

sub date2ts {
	my $self = shift;
	my $ts;

	if ($self->is_date(@_)) {
		my ($sec, $min, $hour, $day, $mon, $year) = @_;

		$ts = mktime($sec, $min, $hour, $day, $mon - 1, $year - 1900, , , -1);
		$ts += $self->adjust_dst($ts);		# cares about DST
	}

	$ts;
}

1;

__END__
