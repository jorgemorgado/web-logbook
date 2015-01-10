#
# $Id: DB.pm,v 1.2 2008/07/20 00:15:22 jorge Exp jorge $
#
# Web logbook DB related tasks.
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

package Logbook::DB;

use strict;

# base class
use base 'DB::PersHash';

use Carp;
use Util qw(swap);

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;
	my $self = bless $class->SUPER::new, $class;

	# object defaults
	$self->{dbdir} = 'db';
	$self->{attdir} = 'attach';	# attachments directory

	bless $self, $class;

	if (@args == 1) {	# positional args given
		$self->{id} = $_[1];
	} elsif (@args > 1) {	# named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(id|dbdir|users|attdir|archive)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	# set logbook's database path + name
	$self->{db} = sprintf('../share/%s/%s', $self->{dbdir}, $self->{id});

	# are we browsing archives?
	$self->{db} .= sprintf('.%s', $self->{archive}) if $self->{archive};

	# set attachments upload directory
	$self->{attdir} = sprintf('../share/%s/%s', $self->{attdir}, $self->{id});

	$self->dbopen;

	$self;
}

# get attachments
sub attach_get {
	my $self = shift;
	my $gid = shift;

	(DB::PersHash->new("$self->{db}_attach"))->search({ 2 => $gid });
}

# move attachments
sub attach_move {
	my $self = shift;
	my $gid = shift;
	my @recs = @_;
	my $ret = 1;

	my $db = new DB::PersHash("$self->{db}_attach");

	for (0..$#recs) {
		my $old = sprintf('%s/%s_%d_%s', $recs[$_][1], $recs[$_][2], $recs[$_][3], $recs[$_][4]);
		my $new = sprintf('%s/%s_%d_%s', $recs[$_][1], $gid, $recs[$_][3], $recs[$_][4]);

		if (rename $old, $new) {
			$db->update_fields($recs[$_][0], { 2 => $gid });
		} else {
			$ret = 0;
		}
	}

	$ret;
}

# delete attachments
sub attach_del {
	my $self = shift;
	my $gid = shift;
	my $ret = 1;

	my $db = new DB::PersHash("$self->{db}_attach");

	my @recs = $db->search({ 2 => $gid });

	for (@recs) {
		my $file = sprintf('%s/%s_%d_%s', $_->[1], $_->[2], $_->[3], $_->[4]);

		if (unlink $file) {
			$db->delete($_->[0]);
		} else {
			$ret = 0;
		}
	}

	$ret;
}

sub make_archive {
	my $self = shift;
	my $ret;

	# 1st archive the main database
	if (my $ts = $self->archive()) {
		$ret = sprintf('%s.%s', $self->{db}, $ts);

		my $db = new DB::PersHash("$self->{db}_attach");

		# 2nd the attachment database & 3rd the attachment upload directory
		rename "$self->{attdir}_attach", "$self->{attdir}_attach.$ts"
			if $db->archive($ts);
	}

	$ret;
}

1;

__END__
