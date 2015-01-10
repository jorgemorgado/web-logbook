#
# $Id: Page.pm,v 1.2 2007/09/04 21:41:57 jorge Exp $
#
# Page functions.
#
# Based on the code of Data::Page from Leon Brocard.
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

package Data::Page;

use strict;

use Carp;

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;

	my $self= {
		entries_per_page => 10,
		current_page => 1
	};

	bless $self, $class;

	if (@args == 1) { # positional args given
		$self->{total_entries} = $_[1];
	} elsif (@args > 1) { # named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(entries_per_page|current_page|total_entries)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self;
}

sub entries_per_page {
	my $self = shift;

	if (@_) {
		if ($_[0] < 1) {
			carp 'Fewer than one entry per page';
		} else {
			$self->{entries_per_page} = $_[0];
		}
	}

	$self->{entries_per_page};
}

sub current_page {
	my $self = shift;

	if (@_) {
		$self->{current_page} = $_[0];
	} elsif (!defined $self->{current_page}) {
		$self->{current_page} =  $self->first_page;
	} elsif ($self->{current_page} < $self->first_page) {
		$self->{current_page} =  $self->first_page;
	} elsif ($self->{current_page} > $self->last_page) {
		$self->{current_page} =  $self->last_page;
	}

	$self->{current_page};
}
  
sub total_entries {
	my $self = shift;

	$self->{total_entries} = $_[0] if @_;
	$self->{total_entries};
}
  
sub entries_on_this_page {
	my $self = shift;
    
	$self->total_entries <= 0 ?
		0 :
		$self->last - $self->first + 1;
}

sub first_page {
	my $self = shift;

	1;
}

sub last_page {
	my $self = shift;

	my $pages = $self->total_entries / $self->entries_per_page;
	my $last_page = $pages == int $pages ? $pages : int($pages) + 1;

	$last_page = 1 if $last_page < 1;
	$last_page;
}

sub first {
	my $self = shift;

	$self->total_entries == 0 ?
		0 :
		(($self->current_page - 1) * $self->entries_per_page) + 1;
}

sub last {
	my $self = shift;

	$self->current_page == $self->last_page ?
		$self->total_entries :
		$self->current_page * $self->entries_per_page;
}

sub previous_page {
	my $self = shift;

	$self->current_page > 1 ?
		$self->current_page - 1 :
		undef;
}

sub next_page {
	my $self = shift;

	$self->current_page < $self->last_page ?
		$self->current_page + 1 :
		undef;
}

1;

__END__
