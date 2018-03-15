
export PATH=/cygwin/c/tools/cygwin/bin:$PATH

# remove separate /home directory
[ -d /home ] && mv /home{,.old}
# symlink /home to C:\Users
ln -s "$(cygpath -H)" /home

# generate /etc/group & /etc/passwd files
mkgroup -l > /etc/group
mkpasswd -l -p "$(cygpath -H)" > /etc/passwd

# configure cygwin sshd
ssh-host-config -y --cygwin "nodosfilewarning" --pwd "$(makepasswd --minchars=20 --maxchars=30)"

# Disable user / group permission checking
sed -i 's/.*StrictModes.*/StrictModes no/' /etc/sshd_config
# Disable reverse DNS lookups
sed -i 's/.*UseDNS.*/UseDNS no/' /etc/sshd_config

# configure Cygwin LSA authentication package
# required for proper privileges changing with ssh key authentication
auto_answer=yes /usr/bin/cyglsa-config
