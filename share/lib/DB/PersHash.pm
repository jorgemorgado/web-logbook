#
# $Id: PersHash.pm,v 1.4 2008/08/23 20:21:15 jorge Exp jorge $
#
# Persistent Hash database.
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
# NB: the field separator is the character  (make it with Ctrl-V + Crtl-Y)
#
# You should view this file with a tab stop of 2. Vim and Emacs should
# detect and adjust this automatically. On vi type ':set tabstop=2'.
#

package DB::PersHash;

use strict;

use Carp;
use SDBM_File;
use Fcntl;

# global variables
use vars qw($VERSION);
$VERSION = '1.1';

sub new {
	my ($class, @args) = @_;

	# object defaults
	my $self = {
		db => undef,
		hash => undef,
		set => []
	};

	bless $self, $class;

	if (@args == 1) {	# positional args given
		$self->{db} = $_[1];
	} elsif (@args > 1) {	# named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(db)$/) {
				$self->{$1} = $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self->dbopen if $self->{db};

	$self;
}

sub DESTROY {
	my $self = shift;

	$self->dbclose;
}

# Associates the hash with the SDBM_File class
# Args: -
# Return: -
sub dbopen {
	my $self = shift;
	my $db = shift || $self->{db};

	if ($db) {
		tie %{$self->{hash}}, "SDBM_File", $db, O_RDWR|O_CREAT, 0644;	# tie hash
	} else {
		carp 'Database was not provided';
	}
}

sub dbclose {
	my $self = shift;

	untie %{$self->{hash}};
}

# Get record
# Args: record id
# Return: array reference of the record
sub fetch($) {
	my $self = shift;

	_get($self->{hash}->{$_[0]});
}

# Get all records
# Args: -
# Return: multidimensional array with all records
sub fetchall {
	my $self = shift;

	while (my ($key, $val) = each %{$self->{hash}}) {
		push @{$self->{set}}, [ $key, _get($val) ];
	}

	@{$self->{set}};
}

# First key in the hash
# Args: -
# Return: first key in the hash
sub firstkey {
	my $self = shift;

	# reset iterator
	keys %{$self->{hash}};

	(each %{$self->{hash}})[0];
}

# Next key in the hash
# Args: -
# Return: next key in the hash
sub nextkey {
	my $self = shift;

	(each %{$self->{hash}})[0];
}

# Last key (highest) in the hash
# Args: -
# Return: last key in the hash
sub lastkey {
	my $self = shift;
	my $pos = 0;

	while (my ($key, $val) = each %{$self->{hash}}) {
		$pos = $key if ($key > $pos);
	}

	$pos;
}

# Add record
# Args: array reference of record
# Return: id of the inserted record
sub insert($) {
	my $self = shift;
	my $key = $self->lastkey + 1;

	$self->update($key, $_[0]);

	$key;
}

# Modify record
# Args: record id, array reference of the record
# Return: -
sub update($$) {
	my $self = shift;

	$self->{hash}->{$_[0]} = _put($_[1]);
}

# Modify some fields of a record
# Args: record id, hash with pair field (nr -> value)
# Return: -
sub update_fields($$) {
	my $self = shift;
	my @fields = $self->fetch($_[0]);

	for (keys %{$_[1]}) {
		$fields[$_ - 1] = $_[1]->{$_};
	}

	$self->update($_[0], [ @fields ]);
}

# Delete record
# Args: record id
# Return: true on success; otherwise false
sub delete($) {
	my $self = shift;

	delete $self->{hash}->{$_[0]};
}

# Delete all records
# Args: -
# Return: -
sub clear {
	my $self = shift;

	%{$self->{hash}} = ();
}

# Returns the total number of records
# Args: -
# Return: number of elements in the hash
sub count {
	my $self = shift;

	scalar keys %{$self->{hash}};
}

# Verify that id exists
# Args: id to verify
# Return: true if exist; otherwise false
sub exists($) {
	my $self = shift;

	exists $self->{hash}->{$_[0]};
}

# Search records
# Args: search criteria (hash) in the form of 'field => search_value' pairs
# Return: multidimensional array with all records found
sub search($$) {
	my $self = shift;
	my $criteria = shift;

	ROW: while (my ($key, $val) = each %{$self->{hash}}) {
		my @row = $self->fetch($key);

		for (keys %$criteria) {
			next ROW if ($row[$_ - 1] !~ /$criteria->{$_}/);
		}

		# if we got up to here, then the criteria matches with this record
		push @{$self->{set}}, [ $key, _get($val) ];
	}

	@{$self->{set}};
}

# Advanced search records
# Args: search criteria (hash) in the form of 'key => [ field, op, val, case? ]'
# Return: multidimensional array with all records found
sub search_extended($$) {
	my $self = shift;
	my $criteria = shift;
	my $or = shift || 0;

	ROW: while (my ($key, $val) = each %{$self->{hash}}) {
		my @row = $self->fetch($key);
		my $match = 0;

		for (keys %$criteria) {
			# these must be escaped before the search
			$row[$criteria->{$_}->[0] - 1] =~ s/\\/\\\\/g;	# backslash (keep on top!)
			$row[$criteria->{$_}->[0] - 1] =~ s/(["\$\@])/\\$1/g;	# quote, dollar, at

			my $exp = sprintf($criteria->{$_}->[1], $row[$criteria->{$_}->[0] - 1]);

			if ($or) {
				last if ($match = eval($exp));
			} else {
				next ROW unless eval($exp);
			}
		}

		push @{$self->{set}}, [ $key, _get($val) ] if ($or && $match) || (!$or);
	}

	@{$self->{set}};
}

# Escapes a search criteria so that it can then be used in a regular
# expression (such as in search_extended(), above); if the criteria is
# prefixed with 'regexp:', assumes it is already a regular expression and
# only the prefix is removed.
# Args: search criteria
# Return: escaped search criteria
sub escape_criteria {
	my $self = shift;
	my $crit = shift;

	if ($crit =~ /^regexp:?/) {
		# if regular expression, remove prefix
		$crit =~ s/regexp:?(\s*)//;
	} else {
		# otherwise, escape those that will cause problems in the search
		$crit =~ s/\\/\\\\/g;				# keep this at the top!
		$crit =~ s/([\/^\$\@[\]*+?()|.])/\\$1/g;
		$crit =~ s/(\s+)/(\\s+)/g;	# keep this at the bottom!
	}

	# ugh! this is ugly but it is needed for sprintf on search_extended :(
	$crit =~ s/%/%%/g;

	$crit;
}

# Archives the current database
# Args: the archive timestamp (optional - calculated if not provided)
# Return: on success the timestamp of the archived database; undef otherwise
sub archive($) {
	my $self = shift;

	my $ts = $_[0] || time();
	my $old = $self->{db};
	my $new = sprintf('%s.%s', $old, $ts);

	return (
		rename("$old.pag", "$new.pag") &&
		rename("$old.dir", "$new.dir") ?
		$ts : undef
	);
}

# Dumps all records
# Args: -
# Return: -
sub dump {
	my $self = shift;

	foreach (keys %{$self->{hash}}) {
		my @row = $self->fetch($_);

		printf("%d -> %s\n", $_, join(', ', @row));
	}
}


# These are private methods (they can't be called outside)
sub _get($) {
	split //, $_[0];
}

sub _put($) {
	join '', @{$_[0]};
}

1;

__END__
