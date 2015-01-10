#
# $Id: SMTP.pm,v 1.0 2012/01/01 23:04:00 jorge Exp $
#
# Language functions.
#
# Copyright 2012, Jorge Morgado. All rights reserved.
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

package Mail::SMTP;

use strict;

use Carp;
use Socket;

# global variables
use vars qw($VERSION);
$VERSION = '1.0';

sub new {
	my ($class, @args) = @_;

	# object defaults
	my $self = {
		clientname => undef,	# client fqdn
		servername => undef,	# server fqdn
		serverport => undef,	# server SMTP port

		from_address => 'noreply@your.domain.com',
		organization => 'Your Organization',
		to_address => undef,	# destination address

		mailpfx => undef,			# subject prefix (tag)
		mailer => "Perl Mailer 1.0 [en] (undef)",

		errmsg => undef,
		errcnt => 0,
	};

	bless $self, $class;

	if (@args == 1) {	# positional args given
		$self->{servername} = $_[1];
	} elsif (@args > 1) {	# named args given
		my %args = @args;

		for (keys %args) {
			if (/^-?(clientname|servername|organization|from_address|to_address|mailpfx)$/) {
				$self->{$1} = $args{$_} if $args{$_};
			} else {
				croak "Invalid property '$_' in class $class";
			}
		}
	}

	$self;
}

sub set_error {
	my $self = shift;
	my $errmsg = shift;

	$self->{errmsg} = $errmsg;
	$self->{errcnt} += 1;
}

sub connect {
	my $self = shift;
	my $ret = 0;

	my $proto = (getprotobyname('tcp'))[2];
	my $port = (getservbyname('smtp', 'tcp' ))[2] || $self->{serverport} || 25;

	if (my $addr_client = (gethostbyname($self->{clientname}))[4]) {
		my $client = pack('Sna4x8', AF_INET, 0, $addr_client);

		if (my $addr_server = (gethostbyname($self->{servername}))[4]) {
			my $server = pack('Sna4x8', AF_INET, $port, $addr_server);
	
			if (socket(S, AF_INET, SOCK_STREAM, $proto)) {
				if (bind(S, $client)) {
					if (connect(S, $server)) {
						my $fh = select(S);
						$| = 1;
						select($fh);
					
						if (eof(S)) {
							$self->set_error("(eof): socket is not opened");
						} else {
							$ret = 1;		# all ok
						}
					} else {
						$self->set_error("(connect): $!");
					}
				} else {
					$self->set_error("(bind): $!");
				}
			} else {
				$self->set_error("(socket): $!");
			}
		} else {
			$self->set_error("(gethostbyname server): $!");
		}
	} else {
		$self->set_error("(gethostbyname client): $!");
	}

	$ret;
}

sub disconnect {
	my $self = shift;

	close(S);
}

# expects to get a specific code from the remote server
sub socket_expect {
	my $self  = shift;
	my $expect = shift;
	my $ret = 0;

	# read what we got
	my $read = <S>;

	if ($read =~ /^$expect/) {
		$ret = 1;
	} else {
		$self->set_error("(read): expected '$expect' but got '$read'");
		close S;
	}

	$ret;
}

sub socket_write {
	my $self = shift;
	my $str = shift;

	print S "$str\r\n";
}

sub send {
	my $self = shift;
	my $subject = shift;
	my $body = shift;
	my $ret = 0;

	if ($self->connect()) {
		$self->socket_expect('220') || return $ret;

		$self->socket_write("helo $self->{clientname}");
		$self->socket_expect('250') || return $ret;

		$self->socket_write("mail from: <$self->{from_address}>");
		$self->socket_expect('250') || return $ret;

		$self->socket_write("rcpt to: <$self->{to_address}>");
		$self->socket_expect('250') || return $ret;

		$self->socket_write("data");
		$self->socket_expect('354') || return $ret;

		$self->socket_write("From: \"$self->{from_address}\"");
		$self->socket_write("Organization: \"$self->{organization}\"");
		$self->socket_write("To: \"$self->{to_address}\"");
		$self->socket_write("Subject: $self->{mailpfx} $subject");
		$self->socket_write("Date: " . scalar localtime);
		$self->socket_write("X-Mailer: $self->{mailer}");
		$self->socket_write("Mime-Version: 1.0");
		$self->socket_write("X-Priority: 3 (Normal)");
		$self->socket_write("Content-Type: text/plain; charset=us-ascii");
		$self->socket_write("Content-Transfer-Encoding: 7bit");
		$self->socket_write("");
		$self->socket_write($body);
		$self->socket_write(".");
		$self->socket_expect('250') || return $ret;
	
		$self->socket_write("quit");
		$self->socket_expect('221') || return $ret;

		$ret = $self->disconnect();
	}

	$ret;
}

1;

__END__
