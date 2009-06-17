#!/usr/bin/env python

import os, sys
import ntr

p0=os.path.dirname(sys.argv[0])
p1=os.path.abspath(os.path.join(p0, "..", "dom", "automation"))

sys.path.append(p1)

import detect_assertions, detect_malloc_errors, detect_interesting_crashes


# Levels of unhappiness.
# These are in order from "most expected to least expected" rather than "most ok to worst".
# Fuzzing will note the level, and pass it to Lithium.
# Lithium is allowed to go to a higher level.
(JS_FINE, JS_TIMED_OUT, JS_ABNORMAL_EXIT, JS_DID_NOT_FINISH, JS_DECIDED_TO_EXIT, JS_MALLOC_ERROR, JS_NEW_ASSERT_OR_CRASH) = range(7)



def level(runthis, timeout, logPrefix):
    runinfo = ntr.timed_run(runthis, timeout, logPrefix)
    (sta, msg, elapsedtime) = (runinfo.sta, runinfo.msg, runinfo.elapsedtime)

    # Initially, the level will be based on whether certain magic strings appear in the jsfunfuzz output.
    lev = JS_DID_NOT_FINISH
    issues = ["jsfunfuzz didn't finish"]
    logfile = open(logPrefix + "-out", "r")
    for line in logfile:
        if (line == "It's looking good!\n"):
            lev = JS_FINE
            issues = []
        elif (line == "jsfunfuzz stopping due to above error!\n"):
            lev = JS_DECIDED_TO_EXIT
            issues = ["jsfunfuzz decided to exit"]
    logfile.close()

    # But we also check several other places...
    if detect_assertions.amiss(logPrefix, True):
      issues.append("unknown assertion")
      lev = max(lev, JS_NEW_ASSERT_OR_CRASH)
    if sta == ntr.CRASHED and detect_interesting_crashes.amiss(logPrefix, True, msg):
      issues.append("unknown crash")
      lev = max(lev, JS_NEW_ASSERT_OR_CRASH)
    if detect_malloc_errors.amiss(logPrefix):
      issues.append("malloc error")
      lev = max(lev, JS_MALLOC_ERROR)
    if sta == ntr.ABNORMAL:
      issues.append("abnormal exit")
      lev = max(lev, JS_ABNORMAL_EXIT)
    if sta == ntr.TIMED_OUT:
      issues.append("timed out")
      lev = max(lev, JS_TIMED_OUT)

    amiss = len(issues) != 0
    amissStr = "" if not amiss else "*" + repr(issues) + " "
    print "%s: %s%s (%.1f seconds)" % (logPrefix, amissStr, msg, elapsedtime)
    return lev


def interesting(args, tempPrefix):
    minimumInterestingLevel = int(args[0])
    timeout = int(args[1])
    actualLevel = level(args[3:], timeout, tempPrefix)
    return actualLevel >= minimumInterestingLevel

def init(args):
    initWithKnownPath(args[2])

def initWithKnownPath(knownPath):
    detect_assertions.init(knownPath)
    detect_interesting_crashes.init(knownPath)
