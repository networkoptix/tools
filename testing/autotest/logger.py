# -*- coding: utf-8 -*-
""" Common logging methods to access from other modules.
"""
__author__ = 'Danil Lavrentyuk'
import time, traceback

DEBUG = False

def raw_log(s):
    print s


def _logStr(text, *args):
    return "[%s] %s" % (time.strftime("%Y.%m.%d %X %Z"), ((text % args) if args else text))


def log(text, *args):
    text = _logStr(text, *args)
    raw_log(text)
    return text


def set_debug(value):
    global DEBUG
    DEBUG = value
    raw_log("Debug mode " + ("ON" if value else "OFF"))


def debug(text, *args):
    if DEBUG:
        if args:
            text = text % args
        text = "DEBUG: " + text
        raw_log(text)
        ToSend.debug(text)


class ToSend(object):
    "Logs accumulator, singleton-class (no objects created)."
    lines = []
    last_line_src = ''
    empty = True
    flushed = False
    stdout = False
    repeats = 0

    @classmethod
    def append(cls, text, *args):
        cls.last_line_src = text
        if text != '':
            text = _logStr(text, *args)
        cls.empty = False
        if cls.stdout and cls.flushed:
            raw_log(text)
        else:
            cls.lines.append(text)

    @classmethod
    def count(cls):
        return len(cls.lines)

    @classmethod
    def log(cls, text, *args):
        cls.last_line_src = text
        if text != '':
            text = _logStr(text, *args)
        raw_log(text)
        cls.empty = False
        if not cls.stdout:
            cls.lines.append(text)

    @classmethod
    def debug(cls, text):
        if not (cls.stdout and cls.flushed):
            cls.last_line_src = text
            cls.lines.append(_logStr(text))

    @classmethod
    def flush(cls, pos=0):
        # used only with -o mode
        if cls.stdout and not cls.flushed:
            cls.flushed = True
            for text in cls.lines[pos:]:
                raw_log(text)
            del cls.lines[:]

    @classmethod
    def clear(cls):
        del cls.lines[:]
        cls.empty = True
        cls.flushed = False
        cls.last_line_src= ''

    @classmethod
    def lastLineAppend(cls, text):
        if cls.lines:
            cls.lines[-1] += text
        else:
            cls.log("INTERNAL ERROR: tried to append text to the last line when no lines collected.\n"
                    "Text to append: " + text + "\n"
                    "Called from: " + traceback.format_stack())

    @classmethod
    def cutLastLine(cls):
        if cls.lines:
            del cls.lines[-1]

    @classmethod
    def cutTail(cls, pos):
        if len(cls.lines) > pos:
            del cls.lines[pos:]

    @classmethod
    def check_repeats(cls):
        if not cls.stdout:
            if cls.repeats > 1:
                cls.lastLineAppend("   [ REPEATS %s TIMES ]" % cls.repeats)
        cls.repeats = 1

    @classmethod
    def clear_repeats(cls):
        cls.repeats = 0

    @classmethod
    def check_last_line(cls, line):
        if len(cls.lines) and (line == cls.last_line_src):
            cls.repeats += 1
        else:
            cls.check_repeats()
            cls.append(line)

