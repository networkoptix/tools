FROM dfritz/zenoss:latest

RUN yum install -y openssh-clients wget

RUN wget \
    http://wiki.zenoss.org/download/zenpacks/ZenPacks.community.InterfaceGraphs/1.0/ZenPacks.community.InterfaceGraphs-1.0.egg \
    -O /opt/zenoss/packs/ZenPacks.community.InterfaceGraphs-1.0.egg

RUN chown zenoss:zenoss /opt/zenoss/packs/ZenPacks.community.InterfaceGraphs-1.0.egg
RUN echo "+/opt/zenoss/packs/ZenPacks.community.InterfaceGraphs-1.0.egg" >> /opt/zenoss/var/zenpack_actions.txt

# You have to prepare keys by ssh-keygen
COPY ./zenoss_dsa* /tmp/
RUN chown zenoss:zenoss /tmp/zenoss_dsa*

# Copy zenoss keys
USER zenoss
RUN mkdir -p /home/zenoss/.ssh
RUN mv /tmp/zenoss_dsa* /home/zenoss/.ssh
RUN chmod 700 /home/zenoss/.ssh
RUN chmod 600 /home/zenoss/.ssh/zenoss_dsa

