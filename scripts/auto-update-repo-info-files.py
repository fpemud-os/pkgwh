#!/usr/bin/env python3

import os
import time
import robust_layer
import lxml.etree
import urllib.request
import robust_layer.simple_fops
from datetime import datetime


def downloadGentooOverlays():
    url = "https://api.gentoo.org/overlays/repositories.xml"
    fullfn = os.path.join(Util.repoInfoDir(), "gentoo-overlays.xml")
    tm = None
    while True:
        try:
            tm = Util.downloadIfNewer(url, fullfn)
            Util.myParseXml(fullfn)
            break
        except lxml.etree.XMLSyntaxError as e:
            print("Failed to parse %s, %s" % (fullfn, e))
            robust_layer.simple_fops.rm(fullfn)
            time.sleep(robust_layer.RETRY_WAIT)
        except BaseException as e:
            print("Failed to acces %s, %s" % (url, e))
            time.sleep(robust_layer.RETRY_WAIT)
    print("Gentoo overlay database updated: %s" % (tm.strftime("%Y%m%d%H%M%S")))


class Util:

    @staticmethod
    def repoInfoDir():
        selfDir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(selfDir, "..", "python3", "pkgwh", "repos-info")

    @staticmethod
    def myParseXml(fullfn):
        cList = [
            ("git", "https"),
            ("git", "http"),
            ("git", "git"),
            ("svn", "https"),
            ("svn", "http"),
            ("mercurial", "https"),
            ("mercurial", "http"),
            ("rsync", "rsync"),
        ]

        ret = dict()
        rootElem = lxml.etree.parse(fullfn).getroot()
        for nameTag in rootElem.xpath(".//repo/name"):
            overlayName = nameTag.text
            if overlayName in ret:
                raise Exception("duplicate overlay \"%s\"" % (overlayName))

            for vcsType, urlPrefix in cList:
                for sourceTag in nameTag.xpath("../source"):
                    tVcsType = sourceTag.get("type")
                    tUrl = sourceTag.text
                    if tVcsType == vcsType and tUrl.startswith(urlPrefix + "://"):
                        ret[overlayName] = (tVcsType, tUrl)
                        break
                if overlayName in ret:
                    break

            if overlayName not in ret:
                raise Exception("no appropriate source for overlay \"%s\"" % (overlayName))

        return ret

    @staticmethod
    def downloadIfNewer(url, fullfn):
        if os.path.exists(fullfn):
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=robust_layer.TIMEOUT) as resp:
                remoteTm = datetime.strptime(resp.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z")
                localTm = datetime.utcfromtimestamp(os.path.getmtime(fullfn))
                if remoteTm <= localTm:
                    return localTm
        with urllib.request.urlopen(url, timeout=robust_layer.TIMEOUT) as resp:
            with open(fullfn, "wb") as f:
                f.write(resp.read())
            remoteTm = datetime.strptime(resp.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z")
            os.utime(fullfn, (remoteTm.timestamp(), remoteTm.timestamp()))
            return remoteTm


if __name__ == "__main__":
    downloadGentooOverlays()
