#!/usr/bin/perl -w

use strict;
use Carp;

my %tpl;

$tpl{BANNER} = "this is the banner\n";
$tpl{NAME} = "Jorge Morgado\n";

# load templates
my $content = contents("template1.tpl");

# templating...
$content =~ s/<<([A-Z]+)>>/$tpl{$1}/g;

print $content;

exit 0;

sub contents {
	my ($file, %seen) = @_;

	croak "Cyclic insertion of $file" if $seen{$file};

	open my $handle, "./$file" or croak "$file: $!";
	my $text = do { local $/; <$handle> };
	close $handle;

	$text =~ s{^<insert (\w+).tpl>$}{contents("$1.tpl",%seen,$file=>1)}gem;

	return $text;
}
