#!/bin/bash
set -ex
cd "$REPOSITORY_ROOT_PATH/$CUSTOMIZATION"
mkdir -p all/{update,install,debug,distrib}
# fix permissions on files from windows builds (and others if there are same problems)
# the problem is that on win nodes jenkins creates files with rwx perm for owner only
# and nginx user can not serve these files/dirs (403 error), so we add read for everyone
# and also add +x on directories
chmod -R a+r .
find . -type d | xargs chmod a+x
for platform in $(ls .) ; do

  if [ $platform == all ] ; then
    continue;
  fi

  mkdir -p $platform/update

  find ./$platform/distrib -type f -and -name '*.'"$BUILD_IDENTITY-"'*' -and -name '*_update-*' -print | \
    xargs -I {} sh -c ' \
      ln -f "$1" ./'"$platform"'/update/$(basename "$1") && \
      ln -f "$1" ./all/update/$(basename "$1") && \
      ln -f "$1" ./all/distrib/$(basename "$1") \
    ' - {}

  mkdir -p $platform/debug
  find ./$platform/distrib -type f -and -name '*.'"$BUILD_IDENTITY-"'*' -and -name '*_debug-*' -print | \
    xargs -I {} sh -c ' \
      ln -f "$1" ./"'$platform/'"debug/$(basename "$1") && \
      ln -f "$1" ./all/debug/$(basename "$1") && \
      ln -f "$1" ./all/distrib/$(basename "$1") \
    ' - {}

  mkdir -p $platform/install
  find ./$platform/distrib -type f -and -name '*.'"$BUILD_IDENTITY-"'*' -and -not -name '*_update-*' -and -not -name '*_debug-*' -print | \
    xargs -I {} sh -c ' \
      ln -f "$1" ./'"$platform"'/install/$(basename "$1") && \
      ln -f "$1" ./all/install/$(basename "$1") && \
      ln -f "$1" ./all/distrib/$(basename "$1") \
    ' - {}
done