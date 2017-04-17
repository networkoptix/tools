#! /usr/bin/perl
# -*- cperl -*-
#
use warnings;
use strict;


my $config_file = 'browse.config';


use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI qw(escapeHTML);

my $q = new CGI;
if ($q->cgi_error) {
    print $q->header(-status => $q->cgi_error);
    exit(0);
  };

my $config = do $config_file;
unless ($config) {
    die "While reading $config_file: $!" if ($!);
    die "While compiling $config_file: $@" if ($@);
    die "While executing $config_file: returned '$config'";
}

use DBI;

print $q->header(-type => "text/html; charset=utf-8");

print $q->start_html(-title => "Resolve test",  -dtd => 1,  -encoding => "utf-8");

my $params = $q->Vars;

my $dsn = "DBI:mysql:database=taskbot;host=localhost";

my $dbh = DBI->connect($dsn, 'taskbot', 'taskbot',
                       { AutoCommit => 0, PrintError => 0, RaiseError => 1,
                         FetchHashKeyName => 'NAME_lc' }) or die "DBI::errstr: $DBI::errstr";

my $stmt = $dbh->prepare(q[INSERT INTO resolved_test (test_id, branch_id, platform_id) VALUES (?, ?, ?)]);
$stmt->execute($params->{test}, $params->{branch}, $params->{platform}) or die "DBI::errstr: $DBI::errstr";
$dbh->commit;

print $q->end_html;
