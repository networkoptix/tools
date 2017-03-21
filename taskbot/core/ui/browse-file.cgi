#! /usr/bin/perl
# -*- cperl -*-
#
use warnings;
use strict;


my $config_file = 'browse.config';


use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI qw(escapeHTML);
use HTML::Entities qw(encode_entities);

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

my $params = $q->Vars;

$params->{rows} = 20 unless defined $params->{rows};
$params->{cols} = 160 unless defined $params->{cols};
$q->default_dtd('-//W3C//DTD HTML 4.0 Transitional//EN');

my $stmt;
if (defined $params->{id})
{
  my @files_list = split(/,\s*/, $params->{id});

  $stmt = $dbh->prepare(q[
    SELECT id, task_id, name, fullpath, gzipped, content
    FROM file
    WHERE id IN (]. join(',', ('?')x@files_list) .q[)]);
  $stmt->execute(@files_list);
}
elsif (defined $params->{task})
{
  $stmt = $dbh->prepare(q[
    SELECT id, task_id, name, fullpath, gzipped, content
    FROM file
    WHERE task_id = ?]);

  $stmt->execute($params->{task});
}
else
{
  print
  $q->header(-type => 'text/html; charset=utf-8') .
  $q->start_html(-title => 'Taskbot',
                 -dtd => 1).
  $q->span({-class => 'ErrorMessage'},
           'Script requires \'id\' or \'task\' parameters!').
  $q->end_html;
  exit;
}
my @result = @{$stmt->fetchall_arrayref({})};


if (scalar @result == 1)
  {
    my $file_content;
    if ($result[0]->{gzipped}) {
      use Compress::Zlib;
      $file_content =  uncompress($result[0]->{content});
    } else {
      $file_content =  $result[0]->{content};
    }

    my $highlighted = 0;

    # use code highlighting if source-highlight installed
#    my @paths = ();#split(':',$ENV{PATH});
#    foreach my $path (@paths)
#    {
#      if (-e "$path/source-highlightt")
#      {
#        my ($ext) = $result[0]->{name} =~ m/^.*\.([^\.]+)$/i;
#        if ($ext)
#        {
#          use IPC::Open2 qw(open2);
#          $SIG{PIPE} = sub { die "source-highlight exited prematurely\n" };
#          my $pid = open2(\*READ, \*WRITE, 'source-highlight',
#                                           '-s', "$ext", '--failsafe');
#          print WRITE "$file_content" or
#            die "Can't write to pipe to source-highlight: $!";
#          close WRITE or die "Can't close pipe to source-highlight: $!";
#          $file_content = "";
#          while (<READ>) {$file_content .= $_};
#          close READ or die "Can't close pipe from source-highlight: $!";
#          waitpid($pid, 0) == $pid or die $!;
#          $? == 0 or die "return status $? from source-highlight\n";
#          $highlighted = 1;
#          substr($file_content, 136, 5) = ""; # Removes <pre> tag
#          substr($file_content, -7) = ""; # Removes </pre> tag
#        }
#        last;
#      }
#    }

    my ($ext) = $result[0]->{name} =~ m/^.*\.([^\.]+)$/i;
    if ($ext eq "bz2")
    {
      use Compress::Raw::Bzip2;

      my ($bz, $status) = new Compress::Raw::Bunzip2 or
        die "Can't create bzip2 object\n";

      my $uncompressed;

      $status = $bz->bzinflate($file_content, $uncompressed);
      die "Failed to uncompress '$result[0]->{name}' file: return status '$status'!"
        if $status ne 'End of Stream';# or $status ne BZ_STREAM_END;
      $file_content = $uncompressed;
    }

    if (! defined $params->{raw})
    {
      $file_content = escapeHTML(encode_entities($file_content)) unless $highlighted;
      $file_content =~ s/(?<!-->)\n/<br>/g;
      while ($file_content =~ s/(<br>\s*)\s/$1&nbsp;/g) {}; # Leading spaces
    }

    my $header = "";
    if (defined $params->{header_required})
    {
      my ($host_name) = $result[0]->{fullpath} =~ m/.*\/TReport\/(.+)_\d\d\d\d-\d\d-\d\d_\d\d-\d\d-\d\d\/log\/.*/;
      $header .= <<"EOF;";
<div style="font-weight: bold; background-color: lightgrey;">
File: $result[0]->{name}<br>
@{[ defined $host_name ? "Host: $host_name<br>" : "" ]}
</div>
EOF;
    }

    if (defined $params->{raw}) {
      print $q->header(-type => "text/plain; charset=utf-8") .
        $file_content;
    }
    else {
      print $q->header(-type => "text/html; charset=utf-8") .
        $q->start_html(-title => $result[0]->{name},
                       -dtd => 1,
                       -encoding => "utf-8") .
         $header .
         $file_content;
    }
}
elsif (scalar @result > 1)
{
  print $q->header(-type => 'text/html; charset=utf-8') .
        $q->start_html(-title => 'Taskbot',
                       -style => {'src' => '/commons/styles/DirectoriesTree.css'},
                       -script => {'type' => 'text/javascript',
                                   'src' => '/commons/scripts/DirectoriesTree.js'}, 
                       -dtd => 1);
  my $tree = {};
  foreach my $file (@result)
  {
    my @directories = grep {length} split('/', $file->{fullpath});
    push @directories, $file->{name};
    my $expression = '$tree';
    my $file_href = $q->a({-href => $q->url(-full => 1)."?id=$file->{id}",
                           -target => 'Content'}, $file->{name});
    foreach my $dir (@directories)
    {
      $expression .= "->{'$dir'}";
    }
    $expression .= " = '$file_href'";
    eval $expression;
  }
  print <<"EOF;";
<div id="menu">
<h1>Files of</h1>
@{[ print_subfolder($tree) ]}
</div>
<div id="content">
</div>
EOF;
  print $q->end_html;
}
else
{
  print
  $q->header(-type => 'text/html; charset=utf-8') .
  $q->start_html(-title => 'Taskbot',
                 -dtd => 1).
  $q->span({-class => 'ErrorMessage'},
           'Files that match the indicated conditions are not found!').
  $q->end_html;
}
  
sub print_subfolder
{
  my ($tree, $to_path) = @_;
  my $out;
  if (scalar keys %{$tree} == 1 and not $to_path)
  {
    my $subfolder_name = (keys %{$tree})[0];
    $out .= "<b>/</b>" if $subfolder_name eq "home";
    $out .= "<b>$subfolder_name/</b>";
    $out .= print_subfolder($tree->{$subfolder_name}, $to_path);
    return $out;
  }
  $to_path = 1;
  $out = <<"EOF;";
<ul class="Container">
EOF;
  foreach my $subfolder (keys %{$tree})
  {
    if ((ref $tree->{$subfolder}) eq "HASH")
    {
      $out .= <<"EOF;";
<li class="Folder Collapsed">
  <span class="Node">$subfolder</span>
  @{[ print_subfolder($tree->{$subfolder}, $to_path) ]}
</li>
EOF;
    }
    else
    {
      $out .= <<"EOF;";
<li class="Item"><span class="Leaf">$tree->{$subfolder}</span></li>
EOF;
    }
  }
  $out .= <<"EOF;";
</ul>
EOF;

  return $out;
}
