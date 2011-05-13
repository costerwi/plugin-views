#!/bin/env python

import time
import datetime

__version__ = '0.1'

class tzUTC(datetime.tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    def tzname(self, dt):
        return "Z"
    def dst(self, dt):
        return datetime.timedelta(0)

class tzLocal(datetime.tzinfo):
    """First attempt at something that might make sense"""
    def __init__(self):
        if hasattr(time, 'tzset'):
            time.tzset()    # Reset the time conversion rules based on TZ
        self.tz_offset = datetime.timedelta(seconds=-time.timezone)
        self.dst_offset = datetime.timedelta(seconds=time.timezone - time.altzone)

    def isdst(self, dt):
        """Use time.localtime to determine if it is locally DST or not"""
        epoch = time.mktime( (
                dt.year, dt.month, dt.day,
                dt.hour, dt.minute, dt.second, 0, 0, -1) )  # seconds
        lt = time.localtime(epoch)  # tuple with correct tm_isdst attribute
        return 1 == lt.tm_isdst

    def tzname(self, dt):
        """Return time zone name"""
        if self.isdst(dt):
            return time.tzname[1]
        else:
            return time.tzname[0]

    def dst(self, dt):
        """Return DST adjustment in minutes east of UTC"""
        if self.isdst(dt):
            return self.dst_offset
        else:
            return datetime.timedelta(0)

    def utcoffset(self, dt):
        """Return local time offset in minutes east of UTC"""
        return self.tz_offset + self.dst(dt)

UTC = tzUTC()
local = tzLocal()

def tostring(sometime):
    """Return UTC iso8601 format"""

    isofmt = "%Y-%m-%dT%H:%M:%SZ"
    if isinstance(sometime, float):
        sometime = datetime.datetime.fromtimestamp(sometime, UTC)
    elif isinstance(sometime, datetime.datetime) and sometime.tzinfo:
        sometime = sometime.astimezone(UTC)

    return sometime.strftime(isofmt)


def parse(datestring):
    """Return seconds since epoch, assuming iso8601 datestring is UTC"""

    import re
    import calendar
    isore = re.compile("(\d+)-(\d+)-(\d+).(\d+):(\d+):(\d+)(.\d+)?(.*)")
    m = isore.match(datestring)
    if m:
        year, month, day, hour, minute, second = map(int, m.groups()[:6])
        return calendar.timegm( (year, month, day, hour, minute, second, 0, 0, 0) )
    else:
        return None


if __name__ == '__main__':
    isofmt="%Y-%m-%dT%H:%M:%S%Z"
    example = "2011-03-23T17:33:30.50Z"

    secs = parse(example)
    print example, tostring(secs)
    parsed = datetime.datetime.fromtimestamp(secs, UTC)

    n = datetime.datetime.now().replace(tzinfo=local)

    print parsed.isoformat()
    print parsed.astimezone(local).isoformat()
    print local.utcoffset(n)
    print n.isoformat()
    print n.strftime(isofmt)
    print n.astimezone(UTC).strftime(isofmt)
