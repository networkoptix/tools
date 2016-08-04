# -*- coding: utf-8 -*-
""" Support unittest execution in a docker container.
    Docker registry credetials have to be configured already
    (i.e. you should login there once)
"""
__author__ = 'Danil Lavrentyuk'

import os.path
import sys
import docker
import docker.errors
from docker.utils import Ulimit
from subprocess import check_call, call as subcall

from .utcontainer import *

# TODO: catch and process all docker.errors.APIError and docker.errors.DockerException

if __name__ == '__main__':
    sys.path.append('..') #  just for debug runs
    import testconf as conf
else:
    conf = sys.modules['__main__'].conf

class UtDockerContainer(UtContainerBase):
    notmp = True
    _debug_prefix = "DEBUG(utdocker): "
    client = None  # type: docker.Client
    hostConfig = None  # type:
    imageInfo = None
    container = None

    @classmethod
    def init(cls, buildVars):
        if cls.client is None:
            cls.client = docker.Client()  # base_url='unix://var/run/docker.sock'
            cls.hostConfig = cls.client.create_host_config(ulimits=[Ulimit(name='core', soft=-1, hard=-1)])
        cls._prepare_image()
        cls._create_container()
        cls._fill_container(buildVars)

    @classmethod
    def done(cls):
        """ Stopes and removes container, but not image
        """
        if cls.client and cls.container:
            c_id = cls.container.get('Id')
            if c_id:
                cls.client.stop(c_id)
                # FIXME: should wait here or check
                # posibly should pass time parameter to stop if it possible
                cls.client.remove_container(c_id)
        cls.client = None
        cls.hostConfig = None
        cls.imageInfo = None
        cls.container = None

    @classmethod
    def _check_image(cls):
        for image in cls.client.images(name=conf.DOCKER_IMAGE_NAME):
            cls._debug("Check image: %s", image)
            if conf.DOCKER_IMAGE_NAME in image['RepoTags']:
                cls._debug("Iamage found!")
                return image
        return None

    @classmethod
    def _prepare_image(cls):
        """
        Checks if the image exits here. If not, pulls it from the registry
        """
        cls.imageInfo = cls._check_image()
        if cls.imageInfo is None:
            cls._debug("Image not found, downloading it...")
            cls.client.pull(
                repository = conf.DOCKER_IMAGE_NAME,
                stream = False,
            )
            cls.imageInfo = cls._check_image()
            if cls.imageInfo is None:
                raise ContainerError("Can't find and can't load image %s", conf.DOCKER_IMAGE_NAME)

    @classmethod
    def _create_container(cls):
        cls.container = cls.client.create_container(
            conf.DOCKER_IMAGE_NAME, tty=True, host_config=cls.hostConfig)
        cls.client.start(cls.container['Id'])

    @classmethod
    def _fill_container(cls, buildVars):
        check_call([
            conf.DOCKER_COPIER, cls.container['Id'], conf.DOCKER_DIR, buildVars.bin_path, buildVars.lib_path, buildVars.qt_lib
        ])

    @classmethod
    def _cmdPrefix(cls):
        return [conf.DOCKER, 'exec', cls.container['Id']]

    @classmethod
    def containerId(cls):
        return cls.container['Id']

    @classmethod
    def getWrapper(cls):
        return os.path.join(conf.DOCKER_DIR, conf.UT_WRAPPER)



#TODO: Think about exception strategy! Handle texceptions here or just allow ut.iterate_unittests/ut.call_unittest do it?

if __name__ == '__main__':
    import subprocess
    UtDockerContainer.mode = 'debug'
    UtDockerContainer.init()
    print "Containeer: %s" % UtDockerContainer.container
    print "Image: %s" % UtDockerContainer.imageInfo
    cmd = ['ls', '-l']
    print "Calling command `%s` in container:" % ' '.join(cmd)
    subprocess.call(UtDockerContainer.makeCmd(cmd))
    print "Finishing..."
    UtDockerContainer.done()
