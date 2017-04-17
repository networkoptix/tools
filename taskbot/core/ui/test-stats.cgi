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

my $dbh = DBI->connect(@{$config->{taskbot_dbi}}[0..2],
                       { AutoCommit => 0, PrintError => 0, RaiseError => 1,
                         FetchHashKeyName => 'NAME_lc' });


sub time_str {
    my ($time) = @_;

    return $q->i("unknown") unless $time;

    use POSIX qw(strftime);
    $ENV{TZ} = 'Europe/Moscow';

    strftime("%Y-%m-%d %Z %H:%M:%S", localtime($time))
      . sprintf("<font size=\"-1\">.%05d</font>",
                int(($time - int($time)) * 10 ** 5));
}

my $stmt;

print $q->header(-type => "text/html; charset=utf-8");

print $q->start_html(-title => "Test fails statistic",
                     -dtd => 1,
                     -encoding => "utf-8");

print <<"EOF;";
<link rel="stylesheet" type="text/css" href="/commons/styles/TestStatisticLink.css"/>
EOF;

my $params = $q->Vars;


if (! defined $params->{branch}) {
  print $q->start_form(
        -method  => 'GET',
        -enctype => &CGI::URL_ENCODED );

  my @branches = map( { $_->[0] } @{ $dbh->selectall_arrayref(q[SELECT description FROM branch]) }) ;


  print $q->h2("Select branch");
  print $q->br;
  print $q->label('Branch: ');
  print $q->popup_menu(
                       -id=>'branch',
                       -name=>'branch',
                       -values=> \@branches,
                       -default=> $branches[0]);

  print $q->br;
  print $q->submit(-value=>'Select');
  print $q->end_form;
}
else {

  print $q->start_table({-border => 1});

  if (defined $params->{id}) {

    my ($test_name) = $dbh->selectrow_array(q[SELECT name From test where id = ?],
                                     undef, $params->{id});

    print $q->h2($test_name);

    $stmt = $dbh->prepare(q[
      SELECT test.id tets_id, test.name name, report_test.failure_reason fail,
         report.id report_id, task.id task_id, task.start task_start,
         task.finish task_finish, platform.host host, 
         platform.description p_description, branch.description b_description
      FROM test
      LEFT JOIN report_test ON test.id = report_test.test_id
      LEFT JOIN report ON report.id = report_test.report_id
      LEFT JOIN task ON task.id = report.task_id
      LEFT JOIN branch ON branch.id = task.branch_id
      LEFT JOIN platform ON platform.id = task.platform_id
      WHERE test.id = ? and branch.description = ?
      ORDER BY task.start ]);
    $stmt->execute($params->{id}, $params->{branch});

    print $q->Tr(
                 { -align => "center", -valign => "top" },
                 $q->th( [ 'Date', 'Platform', 'Branch', 'Reason (report link)'] ));

    while (my $row = $stmt->fetchrow_hashref) {
      print $q->start_Tr;
      print $q->td(time_str($row->{task_start}));
      print $q->td(
                   $q->a({ -href => "browse.cgi?platform=" . $row->{host} . '&branch=' . $row->{b_description} },
                         $row->{p_description} . ' (' . $row->{host} . ')'));
      print $q->td($q->a({ -href => "browse.cgi?platform=" . $row->{host} . '&branch=' . $row->{b_description} },
                         $row->{b_description}));
      print $q->td({-align => "center"},
                   $q->a({ -href => "browse.cgi?report=" . $row->{report_id}}, $row->{fail}));
      print $q->end_Tr;
    }
  }

  else {

    my $show_resolved = $params->{show_resolved}? 1: 0;

    $stmt = $dbh->prepare(q[
      SELECT test.id test_id, test.name test_name, test_platform.count count, platform.id platform_id, branch.id branch_id,
           test_platform.last_fail last_fail, platform.host host, platform.description p_description,
           IF(rt.test_id, 'Resolved', 'Unresolved') as resolve_status
      FROM (SELECT  test.id test_id, platform.id platform_id, branch.id branch_id, COUNT(*) count,
           MAX(task.start) last_fail FROM test
           LEFT JOIN report_test ON test.id = report_test.test_id
           LEFT JOIN report ON report.id = report_test.report_id
           LEFT JOIN task ON task.id = report.task_id
           LEFT JOIN branch ON branch.id = task.branch_id
           LEFT JOIN platform ON platform.id = task.platform_id
           GROUP BY test.id, platform.id, branch.id) test_platform
   LEFT JOIN branch ON branch.id = test_platform.branch_id
   LEFT JOIN platform ON platform.id = test_platform.platform_id
   LEFT JOIN test ON test.id = test_platform.test_id
   LEFT JOIN resolved_test rt ON (platform.id = rt.platform_id AND branch.id = rt.branch_id AND test.id = rt.test_id)
   WHERE branch.description = ? AND (rt.test_id IS NULL OR ? = 1)
   ORDER BY resolve_status DESC, test_platform.last_fail DESC, platform.host, test.name]);
   $stmt->execute($params->{branch}, $show_resolved);

    print $q->h2('Test fails');


    if ($show_resolved) {
      print $q->a({ -href => "?branch=" . $params->{branch} }, 'Show only unresolved tests');
    } else {
      print $q->a({ -href => "?branch=" . $params->{branch} . '&show_resolved=1' }, 'Show all tests');
    }

    print $q->Tr(
                 { -align => "center", -valign => "top" },
                 $q->th( [ 'Test case', 'Platform', 'Last failure', 'Total fails', 'Status' ] ));

    while (my $row = $stmt->fetchrow_hashref) {
        print $q->start_Tr;
        print $q->td($row->{test_name});
        print $q->td(
                     $q->a({ -href => "browse.cgi?platform=" . $row->{host} . '&branch=' . $params->{branch} },
                           $row->{p_description} . ' (' . $row->{host} . ')'));
        print $q->td(time_str($row->{last_fail}));
        print $q->td({-align => "center"},
                     $q->a({ -href => "?branch=" . $params->{branch} .
                             "&id=" . $row->{test_id}}, $row->{count}));
        my $change_status_link = 'resolve_test.cgi?';
        if ($row->{resolve_status} eq 'Resolved')  {
          $change_status_link = 'unresolve_test.cgi?';
        }
        $change_status_link .= 'branch=' . $row->{branch_id} . '&platform=' . $row->{platform_id} . '&test=' .  $row->{test_id};
        print $q->td({-align => "center"},
                     $q->a({-href => "#",
                            -class => $row->{resolve_status},
                            -onclick=>"var xhr = new XMLHttpRequest(); xhr.open('GET', '" . $change_status_link . "', false); xhr.send(); location.reload(true)"},
                           $q->p($q->span($row->{resolve_status}))));
        print $q->end_Tr;
      }
  }

  print $q->end_table;
}

print $q->end_html;


