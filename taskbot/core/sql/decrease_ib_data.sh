#!/bin/bash
# This script is useful to decrease ibdata size

DUMP_FOLDER=$HOME/mysqldumps

DB_NAME=taskbot
DUMP_TIMESTAMP=`date +"%Y%m%d%H%M%S"`
DUMP_FILE="$DUMP_FOLDER/$DB_NAME"_"$DUMP_TIMESTAMP".sql
MYSQL_AUTH="--user=taskbot --password=taskbot"
MYSQLDUMP_OPTIONS="--routines --triggers --single-transaction"

echo "Dump $DB_NAME database"
mysqldump ${MYSQL_AUTH} ${MYSQLDUMP_OPTIONS} \
          --databases $DB_NAME > $DUMP_FILE

echo "Drop $DB_NAME database"
echo "DROP DATABASE $DB_NAME" | sudo -i mysql --user=root mysql 

echo "Stop mysql"
sudo service mysql stop

echo "Clear ibdata"
sudo rm -rv /var/lib/mysql/ibdata1
sudo rm -rv /var/lib/mysql/ib_log*

echo "Start mysql"
sudo service mysql start

echo "Restore $DB_NAME database"
sudo -i mysql --user=root mysql < initial.mysql
mysql ${MYSQL_AUTH} $DB_NAME < $DUMP_FILE
