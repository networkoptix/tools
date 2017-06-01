FROM dfritz/zenoss:latest

RUN yum install -y openssh-clients wget

# Prepare to install InterfaceGraphs zenpack (https://www.zenoss.com/product/zenpacks/interface-graphs)
RUN wget \
    http://wiki.zenoss.org/download/zenpacks/ZenPacks.community.InterfaceGraphs/1.0/ZenPacks.community.InterfaceGraphs-1.0.egg \
    -O /opt/zenoss/packs/ZenPacks.community.InterfaceGraphs-1.0.egg
RUN chown zenoss:zenoss /opt/zenoss/packs/ZenPacks.community.InterfaceGraphs-1.0.egg
RUN echo "+/opt/zenoss/packs/ZenPacks.community.InterfaceGraphs-1.0.egg" >> /opt/zenoss/var/zenpack_actions.txt

# Copy zenoss ssh keys,
# Source ssh keys are expected in Dockerfile directory
ADD ./zenoss_dsa* /home/zenoss/.ssh/
RUN chown -R zenoss:zenoss /home/zenoss/.ssh
RUN chmod 700 /home/zenoss/.ssh
RUN chmod 600 /home/zenoss/.ssh/zenoss_dsa
