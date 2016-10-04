#! /usr/bin/perl
# -*- cperl -*-
#
use warnings;
use strict;


my $config_file = 'browse.config';


use CGI;
use CGI::Carp qw(fatalsToBrowser);

my $q = new CGI;
if ($q->cgi_error) {
    print $q->header(-status => $q->cgi_error);

    exit(0);
}


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

my $params = $q->Vars;
$params->{limit} = 20 unless defined $params->{limit};
$params->{offset} = 0 unless defined $params->{offset};
$params->{rows} = 20 unless defined $params->{rows};
$params->{cols} = 160 unless defined $params->{cols};
$params->{history} = 0
  unless grep { exists $params->{$_} } qw(history tasks task report raw);


sub time_str {
    my ($time) = @_;

    return $q->i("unknown") unless $time;

    use POSIX qw(strftime);

    strftime("%Y-%m-%d %H:%M:%S", localtime($time))
      . sprintf("<font size=\"-1\">.%05d</font>",
                int(($time - int($time)) * 10 ** 5));
}

sub descr_str {
    my ($row) = @_;

    if ($row->{is_command}) {
        return $q->pre($q->escapeHTML($row->{description}));
    } else {
        return $q->escapeHTML($row->{description});
    }
}

sub difftime_str {
    my ($stime, $ftime) = @_;

    return $q->i("unknown") unless $ftime;

    my $diff = $ftime - $stime;
    my $h = int($diff / (60 * 60));
    my $m = int(($diff % (60 * 60)) / 60);
    my $s = $diff - ($h * 60 + $m) * 60;

    sprintf("%02d:%02d:%02d<font size=\"-1\">.%05d</font>", $h, $m, int($s),
            int(($s - int($s)) * 10 ** 5));
}

sub status_str {
    my ($row) = @_;

    if (! $row->{host}) {
        if (! $row->{error_message}) {
            if ($row->{finish}) {
                return ("OK", "GREEN", $row->{finish});
            } else {
                return ("KILLED", "BROWN", undef);
            }
        } else {
            return ($row->{error_message}, "RED", $row->{finish});
        }
    } else {
        use Time::HiRes qw(time);
        return ("RUNNING by $row->{user} on $row->{host} PID $row->{pid}",
                "LIGHTGREY", time, 1);
    }
}

sub self_ref {
    my ($label, @params) = @_;

    unshift @params, (history => undef, report => undef,
                      tasks => undef, task => undef);

    my %save;
    while (my ($k, $v) = splice(@params, 0, 2)) {
        $save{$k} = $params->{$k} unless exists $save{$k};
        $params->{$k} = $v;
    }

    my $res = $q->a({ -href => $q->url(-query => 1) },
                    $q->escapeHTML($label));

    while (my ($k, $v) = each %save) {
        $params->{$k} = $v;
    }

    return $res;
}

sub history_list {
    my ($select) = @_;

    print <<"EOF;";
<link rel="stylesheet" type="text/css" href="/commons/styles/TaskbotRunList.css"/>
<script type="text/javascript" src="/commons/scripts/Taskbot.js"></script>
<script type="text/javascript" src="/commons/scripts/Utils.js"></script>
<script type="text/javascript" src="/commons/scripts/TaskbotRunList.js"></script>
EOF;

    print $q->start_table({
      -id=> 'historyList',
      -border => 1}) . "<tbdoy>";

    while (my $row = $select->fetchrow_hashref) {
        print $q->start_Tr({ -align => 'center' });

        print $q->td("#$row->{id}");

        sub loop_list {
            my ($row, $prefix) = @_;

            my $stime = $row->{$prefix . "start"};
            my $running = $row->{$prefix . "host"};
            my $ftime = $row->{$prefix . "finish"} || ($running && time);
            my $msg = self_ref(($running ? "Running" : "Run time"),
                               task => $row->{$prefix . "id"}) . ": ";

            print $q->td({ -bgcolor => ($running
                                        ? "LIGHTGREY"
                                        : "#f0f0f0"),
                          -id => "task".$row->{$prefix."id"} },
                         time_str($stime) . "<br>$msg"
                         . ($ftime ? difftime_str($stime, $ftime) : "KILLED"));

            print $row->{$prefix . "html_table_row"};
        }

        loop_list($row, "");
        loop_list($row, "l_") if $row->{l_start};
        loop_list($row, "l2_") if $row->{l2_start};

        print $q->end_Tr;
    }

    print "</tbody>".$q->end_table;
}

sub task_list {
    my ($select) = @_;

    print $q->start_table({-border => 1});

    while (my $row = $select->fetchrow_hashref) {
        my $stime = $row->{start};
        my ($message, $color, $ftime) = status_str($row);

        print $q->start_Tr;
        print $q->td(time_str($stime));
        print $q->td(descr_str($row));
        print $q->td({ -bgcolor => $color }, $message);
        print $q->td(self_ref("view", task => $row->{id}));
        print $q->end_Tr;
    }

    print $q->end_table;
}

sub back_ref {
    my ($task_id) = @_;

    my $ref = $dbh->prepare(q[
        SELECT parent_task_id, description
        FROM task
        WHERE id = ?
    ]);

    my @path;
    while ($task_id) {
        my $row = $dbh->selectrow_hashref($ref, undef, $task_id);
        my ($descr) =
          $row->{description} =~ /^(\S+(?: +\S+){0,2})/;
        $descr = substr($descr, 0, 17) . "..." if length($descr) > 20;
        unshift @path, [$descr, $task_id];
        $task_id = $row->{parent_task_id};
    }

    my $self = pop @path;
    print(self_ref("History", history => $self->[1]), $q->start_br x 2,
          join(' > ',
               self_ref("list", tasks => $self->[1]),
               map({ self_ref($_->[0], task => $_->[1]) } @path),
               $q->escapeHTML($self->[0])));
}


sub generate_list {
    my ($list, $count, $title, $generator, $other_list_ref) = @_;

    $list->execute(@$params{ qw(branch platform offset limit) });

    print $q->header(-type => 'text/html; charset=utf-8');
    print $q->start_html('Taskbot');

    print $q->h1($title);

    print $other_list_ref, $q->start_br x 2;

    my @any_list = (history => $params->{history},
                    tasks => $params->{tasks});

    if ($params->{offset}) {
        my $offset = $params->{offset} - $params->{limit};
        $offset = 0 if $offset < 0;
        print self_ref("< next", offset => $offset, @any_list);
    }

    $generator->($list);

    if ($params->{offset} + $params->{limit} < $count) {
        my $offset = $params->{offset} + $params->{limit};
        print self_ref("prev >", offset => $offset, @any_list);
    }

    print $q->end_html;
}


sub generate_history_list {
    my $history = $dbh->prepare(q[
        SELECT t.id, t.start, t.finish, h.html_table_row, r.host,
               t2.id l_id, t2.start l_start, t2.finish l_finish,
               h2.html_table_row l_html_table_row, r2.host l_host,
               t3.id l2_id, t3.start l2_start, t3.finish l2_finish,
               h3.html_table_row l2_html_table_row, r3.host l2_host
        FROM history h
        JOIN task t ON h.task_id = t.id
        LEFT JOIN running_task r ON h.task_id = r.task_id
        LEFT JOIN history h2 ON h2.link_task_id = h.task_id
            AND h2.task_id != h.link_task_id
        LEFT JOIN task t2 ON h2.task_id = t2.id
        LEFT JOIN running_task r2 ON h2.task_id = r2.task_id
        LEFT JOIN history h3 ON h3.link_task_id = h2.task_id
            AND h3.task_id != h2.link_task_id
        LEFT JOIN task t3 ON h3.task_id = t3.id
        LEFT JOIN running_task r3 ON h3.task_id = r3.task_id
        WHERE h.task_id = h.link_task_id
        AND (t.branch_id IN (SELECT id FROM branch where description=?))
        AND (t.platform_id IN (SELECT id FROM platform where host=?))
        ORDER BY h.task_id DESC
        LIMIT ?, ?
    ]);

    my ($platform_dsc) = $dbh->selectrow_array(q[
        SELECT description
        FROM platform
        WHERE host =?
    ], undef, $params->{platform});

    my ($count) = $dbh->selectrow_array(q[
        SELECT COUNT(*)
        FROM history
        WHERE task_id = link_task_id
        AND (task_id IN (SELECT id FROM task WHERE branch_id IN
             (SELECT id FROM branch where description=?)))
        AND (task_id IN (SELECT id FROM task WHERE platform_id IN
             (SELECT id FROM platform where host=?)))
    ], undef, $params->{branch}, $params->{platform});

    generate_list($history, $count, 
                  "Platform: $platform_dsc ($params->{platform}), " .
                  "Branch: $params->{branch}<br><br>" .
                  "Run list (total $count)", \&history_list,
                  self_ref("Task list", tasks => 0));
}


sub generate_report {
    my ($gzipped, $html) = $dbh->selectrow_array(q[
        SELECT gzipped, html
        FROM report
        WHERE id = ?
    ], undef, $params->{report});

    my $views = $dbh->selectall_arrayref(q[
        SELECT v.type as type, v.url as url
        FROM report_view rv JOIN view v ON rv.view_id = v.id
        WHERE rv.report_id = ?
    ], { Slice => {} }, $params->{report});

    my $head = <<"EOF;";
<link rel="stylesheet" type="text/css" href="/commons/styles/TaskbotReport.css"/>
<script type="text/javascript" src="/commons/scripts/Taskbot.js"></script>
EOF;
    foreach my $view (@{$views})
    {
      if ($view->{type} eq 'css')
      {
        $head = <<"EOF;";
<link rel="stylesheet" type="text/css" href="$view->{url}" />
$head
EOF;
      }
      elsif ($view->{type} eq 'js')
      {
        $head .= "<script type=\"text/javascript\" src=\"$view->{url}\"></script>";
      }
    }

    print $q->header(-type => 'text/html; charset=utf-8');
    print $q->start_html(-title => 'Taskbot',
                         -head => $head);

    if ($gzipped) {
        use Compress::Zlib;
        print uncompress($html);
    } else {
        print $html;
    }

    print $q->end_html;
  }

sub generate_raw {
    my ($gzipped, $out);
    if ($params->{report}) {
      ($gzipped, $out) = $dbh->selectrow_array(q[
          SELECT gzipped, html
          FROM report
          WHERE id = ?
      ], undef, $params->{report});
    } elsif ($params->{stderr}) {
      ($gzipped, $out) = $dbh->selectrow_array(q[
          SELECT stderr_gzipped, stderr
          FROM command
          WHERE task_id = ?
      ], undef, $params->{stderr});
    } elsif ($params->{stdout}) {
      ($gzipped, $out) = $dbh->selectrow_array(q[
          SELECT stdout_gzipped, stdout
          FROM command
          WHERE task_id = ?
      ], undef, $params->{stdout});
    }

    if ($gzipped) {
        use Compress::Zlib;
        $out = uncompress($out);
      }
    my $type = $params->{type} or 'text/html';
    print $q->header(-type => $type,
                     -content_length => length($out));
    print $out;
}


sub generate_task_list {
    my $tasks = $dbh->prepare(q[
        SELECT t.id, t.description, t.start, t.finish, t.error_message,
               t.is_command, r.host, r.pid, r.user
        FROM task t
        LEFT JOIN running_task r ON r.task_id = t.id
        WHERE t.parent_task_id IS NULL 
        AND (t.branch_id IN (SELECT id FROM branch where description=?))
        AND (t.platform_id IN (SELECT id FROM platform where host=?))
        ORDER BY t.id DESC
        LIMIT ?, ?
    ]);

    my ($count) = $dbh->selectrow_array(q[
        SELECT COUNT(*)
        FROM task
        WHERE parent_task_id IS NULL 
        AND (branch_id IN (SELECT id FROM branch where description=?))
        AND (platform_id IN (SELECT id FROM platform where host=?))
    ], undef, $params->{branch}, $params->{platform});

    generate_list($tasks, $count, "Task list (total $count)", \&task_list,
                  self_ref("History", history => 0));
}


sub generate_task_description {
    my $task = $dbh->selectrow_hashref(q[
        SELECT t.description, t.start, t.finish, t.error_message,
               t.parent_task_id, t.is_command, r.user, r.host, r.pid,
               c.stdout_gzipped, c.stdout,
               c.stderr_gzipped, c.stderr, c.exit_status
        FROM task t
        LEFT JOIN running_task r ON r.task_id = t.id
        LEFT JOIN command c ON c.task_id = t.id
        WHERE t.id = ?
    ], undef, $params->{task});

    my ($subtask_count) = $dbh->selectrow_array(q[
        SELECT COUNT(*)
        FROM task
        WHERE parent_task_id = ?
    ], undef, $params->{task});

    $q->default_dtd('-//W3C//DTD HTML 4.0 Transitional//EN');
    print $q->header(-type => 'text/html; charset=utf-8');
    print $q->start_html(-title => 'Taskbot',
                         -dtd => 1);

    print $q->h1($task->{is_command} ? 'Command' : 'Task');

    back_ref($params->{task});
    print $q->start_br x 2;

    my $stime = $task->{start};
    my ($message, $color, $ftime, $running) = status_str($task);

    print $q->start_table({-border => 0 });
    if ($task->{is_command}) {
        print $q->Tr({ valign => "top" },
                     $q->td("Command:"), $q->td({ -bgcolor => "LIGHTGREY" },
                                                descr_str($task)));
    } else {
        print $q->Tr({ valign => "top" },
                     $q->td(["Task:", descr_str($task)]));
    }
    print $q->Tr($q->td(["Start time:", time_str($stime)]));
    print $q->Tr($q->td(["Finish time:",
                         $running
                         ? $q->i("still running")
                         : time_str($ftime)]));
    print $q->Tr($q->td(["Run time: ", difftime_str($stime, $ftime)]));
    print $q->Tr($q->td("Status:"), $q->td({ -bgcolor => $color }, $message));
    if (defined $task->{stdout}) {
        foreach my $stream (qw(stdout stderr)) {
            use Compress::Zlib;
            my $out;
            if ($task->{"${stream}_gzipped"}) {
                $out = uncompress($task->{$stream});
            } else {
                $out = $task->{$stream};
            }

            next if $out eq '';

            my @lines = $out =~ /\n/mg;
            my $lines = @lines;
            my $rows = $lines > $params->{rows} ? $params->{rows} : $lines;
            print $q->Tr({ valign => "top" },
                         $q->td({ -align => 'center' },
                                $q->i("$stream<br>($lines lines)")),
                         $q->td($q->textarea(-rows => $rows,
                                             -columns => $params->{cols},
                                             -style => "width: 100%; height: 100%;",
                                             -readonly => 1,
                                             -default => $out)));
        }

        if (defined $task->{exit_status}) {
            print $q->Tr($q->td([$q->i("exit status:"),
                                 $q->pre($task->{exit_status})]));
        }
    }
    print $q->end_table;

    if ($subtask_count) {
        print $q->h2("$subtask_count subtasks");

        my $subtask_list = $dbh->prepare(q[
            SELECT t.id, t.description, t.start, t.finish, t.error_message,
                   t.is_command, r.user, r.host, r.pid
            FROM task t
            LEFT JOIN running_task r ON r.task_id = t.id
            WHERE t.parent_task_id = ?
            ORDER BY t.id ASC
        ]);

        $subtask_list->execute($params->{task});

        task_list($subtask_list);
    }

    print $q->end_html;
}

sub generate_main {
    if (!$q->param || !($q->param('platform') && $q->param('branch'))) {
      print $q->header(-type => 'text/html; charset=utf-8');
      print $q->start_html('Taskbot');
      print $q->start_form(
        -method  => 'GET',
        -enctype => &CGI::URL_ENCODED);

      print $q->h3("Select platform & branch");

      print $q->br;

      {
        # Platform
        my $select = $dbh->prepare(
         q[SELECT host, description
          FROM platform]);

        $select->execute();

        my %platform_hash;

        while (my $row = $select->fetchrow_hashref) {
          $platform_hash{$row->{host}} = 
            "$row->{description} ($row->{host})";
        }

        my @platforms = keys %platform_hash;

        print $q->label('Platform:');
        print $q->popup_menu(
                             -name=>'platform',
                             -values=>\@platforms,
                             -default=>$params->{platform} || $platforms[0],
                             -labels=>\%platform_hash);
      }

      print $q->br;

      {
        # Branch
        my $select = $dbh->prepare(
          q[SELECT description FROM branch]);

        $select->execute();
        my @branches = ();
        while (my $row = $select->fetchrow_hashref) {
          push @branches, $row->{description};
        }

        print $q->label('Branch: ');
        print $q->popup_menu(
                             -name=>'branch',
                             -values=>\@branches,
                             -default=>$params->{branch} || $branches[0]);
      }
      print $q->br;
      print $q->submit(-value=>'Select');
      print $q->end_form;

      print $q->end_html;
    }
}

if (exists $params->{history}) {
  if (not (defined $params->{branch} && defined $params->{platform})) {
    generate_main;
  }
  else
  {
    generate_history_list;
  }
} elsif (exists $params->{tasks}) {
  generate_task_list;
} elsif (exists $params->{raw}) {
  generate_raw;
} elsif (exists $params->{report}) {
  generate_report;
} elsif (exists $params->{task}) {
    generate_task_description;
}
