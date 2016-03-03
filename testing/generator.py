# -*- coding: utf-8 -*-
__author__ = 'Danil Lavrentyuk'
"""The generator utility classes for functional tests.
(Only those simple generators which don't depend on clusterTest object data etc.)
"""
import random
import string
from hashlib import md5


__all__ = ['BasicGenerator', 'UserDataGenerator', 'MediaServerGenerator']

_uniqueSessionNumber = None
_uniqueCameraSeedNumber = 0
_uniqueUserSeedNumber = 0
_uniqueMediaServerSeedNumber = 0


class BasicGenerator():
    def __init__(self):
        global _uniqueSessionNumber
        if _uniqueSessionNumber == None:
            # generate unique session number
            _uniqueSessionNumber = str(random.randint(1,1000000))

    # generate MAC address of the object
    def generateMac(self):
        l = []
        for i in xrange(0,5):
            l.append(str(random.randint(0,255)) + '-')
        l.append(str(random.randint(0,255)))
        return ''.join(l)

    def generateTrueFalse(self):
        if random.randint(0,1) == 0:
            return "false"
        else:
            return "true"

    @staticmethod
    def generateRandomString(length):
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in xrange(length))

    def generateUUIdFromMd5(self,salt):
        v = md5(salt).digest()
        return "{%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x}" \
            % (ord(v[0]),ord(v[1]),ord(v[2]),ord(v[3]),
              ord(v[4]),ord(v[5]),ord(v[6]),ord(v[7]),
              ord(v[8]),ord(v[9]),ord(v[10]),ord(v[11]),
              ord(v[12]),ord(v[13]),ord(v[14]),ord(v[15]))

    def generateRandomId(self):
        length = random.randint(6,12)
        salt = self.generateRandomString(length)
        return self.generateUUIdFromMd5(salt)

    def generateIpV4(self):
        return "%d.%d.%d.%d" % (random.randint(0,255),
            random.randint(0,255),
            random.randint(0,255),
            random.randint(0,255))

    def generateIpV4Endpoint(self):
        return "%s:%d" % (self.generateIpV4(),random.randint(0,65535))

    def generateEmail(self):
        len = random.randint(6,20)
        user_name = self.generateRandomString(len)
        return "%s@gmail.com" % (user_name)

    def generateEnum(self,*args):
        idx = random.randint(0,len(args) - 1)
        return args[idx]

    def generateUsernamePasswordAndDigest(self,namegen):
        pwd_len = random.randint(8,20)

        un = namegen()
        pwd = self.generateRandomString(pwd_len)

        d = md5("%s:NetworkOptix:%s" % (un,pwd)).digest()

        return (un,pwd,''.join('%02x' % ord(i) for i in d))

    def generateDigest(self,uname,pwd):
        d = md5("%s:NetworkOptix:%s" % (uname,pwd)).digest()
        return ''.join("%02x" % ord(i) for i in d)

    def generatePasswordHash(self,pwd):
        salt = "%x" % (random.randint(0,4294967295))
        d = md5(salt+pwd).digest()
        md5_digest = ''.join('%02x' % ord(i) for i in d)
        return "md5$%s$%s" % (salt,md5_digest)


    def generateCameraName(self):
        global _uniqueSessionNumber
        global _uniqueCameraSeedNumber

        ret = "ec2_test_cam_%s_%s" % (_uniqueSessionNumber,_uniqueCameraSeedNumber)
        _uniqueCameraSeedNumber = _uniqueCameraSeedNumber + 1
        return ret

    def generateUserName(self):
        global _uniqueSessionNumber
        global _uniqueUserSeedNumber

        ret = "ec2_test_user_%s_%s" % (_uniqueSessionNumber,_uniqueUserSeedNumber)
        _uniqueUserSeedNumber = _uniqueUserSeedNumber + 1
        return ret

    def generateMediaServerName(self):
        global _uniqueSessionNumber
        global _uniqueMediaServerSeedNumber

        ret = "ec2_test_media_server_%s_%s" % (_uniqueSessionNumber,_uniqueMediaServerSeedNumber)
        _uniqueMediaServerSeedNumber = _uniqueMediaServerSeedNumber + 1
        return ret


class UserDataGenerator(BasicGenerator):
    _template = """
    {
        "digest": "%s",
        "email": "%s",
        "hash": "%s",
        "id": "%s",
        "isAdmin": %s,
        "name": "%s",
        "parentId": "{00000000-0000-0000-0000-000000000000}",
        "permissions": "255",
        "typeId": "{774e6ecd-ffc6-ae88-0165-8f4a6d0eafa7}",
        "url": ""
    }
    """

    def generateUserData(self,number):
        ret = []
        for i in xrange(number):
            id = self.generateRandomId()
            un,pwd,digest = self.generateUsernamePasswordAndDigest(self.generateUserName)
            ret.append((self._template % (digest,
                self.generateEmail(),
                self.generatePasswordHash(pwd),
                id,"false",un),id))

        return ret

    def generateUpdateData(self,id):
        un,pwd,digest = self.generateUsernamePasswordAndDigest(self.generateUserName)
        return (self._template % (digest,
                self.generateEmail(),
                self.generatePasswordHash(pwd),
                id,"false",un),id)

    def createManualUpdateData(self,id,username,password,admin,email):
        digest = self.generateDigest(username,password)
        hash = self.generatePasswordHash(password)
        if admin:
            admin = "true"
        else:
            admin = "false"
        return self._template%(digest,
                                email,
                                hash,id,admin,username)


class MediaServerGenerator(BasicGenerator):
    _template = """
    {
        "apiUrl": "%s",
        "authKey": "%s",
        "flags": "SF_HasPublicIP",
        "id": "%s",
        "name": "%s",
        "networkAddresses": "192.168.0.1;10.0.2.141;192.168.88.1;95.31.23.214",
        "panicMode": "PM_None",
        "parentId": "{00000000-0000-0000-0000-000000000000}",
        "systemInfo": "windows x64 win78",
        "systemName": "%s",
        "typeId": "{be5d1ee0-b92c-3b34-86d9-bca2dab7826f}",
        "url": "rtsp://%s",
        "version": "2.3.0.0"
    }
    """
    def _generateRandomName(self):
        length = random.randint(5,20)
        return self.generateRandomString(length)

    def generateMediaServerData(self,number):
        ret = []
        for i in xrange(number):
            id = self.generateRandomId()
            ret.append((self._template % (self.generateIpV4Endpoint(),
                   self.generateRandomId(),
                   id,
                   self.generateMediaServerName(),
                   self._generateRandomName(),
                   self.generateIpV4Endpoint()),id))

        return ret


