#!/usr/bin/python
# encoding: utf-8
#
# Copyright 2009 Greg Neagle.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#      http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
munkistatus.py

Created by Greg Neagle on 2009-09-24.

Utility functions for using MunkiStatus.app
to display status and progress.
"""

import os
import subprocess
import socket
import time

# module socket variable
s = None

def launchMunkiStatus():
    # use launchd KeepAlive path so it launches from a launchd agent
    # in the correct context.
    # this is more complicated to set up, but makes Apple (and launchservices)
    # happier.
    # there needs to be a launch agent that is triggered when the launchfile
    # is created; and that launch agent then runs MunkiStatus.app.
    launchfile = "/var/run/com.googlecode.munki.MunkiStatus"
    cmd = ['/usr/bin/touch', launchfile]
    retcode = subprocess.call(cmd)
    time.sleep(0.1)
    if os.path.exists(launchfile):
        os.unlink(launchfile)


def launchAndConnectToMunkiStatus():
    global s
    if not getMunkiStatusPID():
        launchMunkiStatus()
    socketpath = getMunkiStatusSocket()
    if socketpath:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(socketpath)
    #else:
        #raise Exception("Could not open connection to MunkiStatus.app")


def sendCommand(message):
    global s
    if s == None:
        launchAndConnectToMunkiStatus()
    if s:        
        try:
            # we can send only a single line.
            messagelines = message.splitlines(True)
            s.send(messagelines[0].encode('UTF-8'))
        except socket.error, (err, errmsg):
            if err == 32 or err == 9:
                # broken pipe
                # MunkiStatus must have died; try relaunching
                s.close()
                s = None
                launchAndConnectToMunkiStatus()
                if s:
                    # try again!
                    try:
                        s.send(messagelines[0].encode('UTF-8'))
                    except socket.error, (err, errmsg):
                        # ok, we give up.
                        pass
            

def readResponse():
    global s
    if s:
        try:
            # our responses are really short
            data = s.recv(256)
            return int(data.rstrip('\n'))
        except socket.error, (err, errmsg):
            print err, errmsg
            s.close()
            s = None
            
    return ''
    

def getPIDforProcessName(processname):
    cmd = ['/bin/ps', '-eo', 'pid=,command=']
    p = subprocess.Popen(cmd, shell=False, bufsize=1, stdin=subprocess.PIPE, 
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True: 
        line =  p.stdout.readline().decode('UTF-8')
        if not line and (p.poll() != None):
            break
        line = line.rstrip('\n');
        if line:
            (pid, proc) = line.split(None,1)
            if proc.find(processname) != -1:
                return str(pid)

    return 0
    
    
def getMunkiStatusPID():
    return getPIDforProcessName("MunkiStatus.app/Contents/MacOS/MunkiStatus")


def getMunkiStatusSocket():
    pid = None
    for i in range(8):
        pid = getMunkiStatusPID()
        if pid:
            break
        else:
            # sleep and try again
            time.sleep(.25)
    if pid:
        for i in range(12):
            socketpath = "/tmp/com.googlecode.munki.munkistatus.%s" % pid
            if os.path.exists(socketpath):
                return socketpath
            
            # sleep and try again
            time.sleep(.25)
    return ""
        
        
def activate():
    '''Brings MunkiStatus window to the front.'''
    sendCommand(u"ACTIVATE: \n")
        
        
def hide():
    '''Hides MunkiStatus window.'''
    sendCommand(u"HIDE: \n")


def show():
    '''Shows MunkiStatus window.'''
    sendCommand(u"SHOW: \n")


def title(titleText):
    '''Sets the window title.'''
    sendCommand(u"TITLE: %s\n" % titleText)


def message(messageText):
    '''Sets the status message.'''
    sendCommand(u"MESSAGE: %s\n" % messageText)
        
        
def detail(detailsText):
    '''Sets the detail text.'''
    sendCommand(u"DETAIL: %s\n" % detailsText)
        
    
def percent(percentage):
    '''Sets the progress indicator to 0-100 percent done.
    If you pass a negative number, the progress indicator
    is shown as an indeterminate indicator (barber pole).'''
    sendCommand(u"PERCENT: %s\n" % percentage)
        

def hideStopButton():
    '''Hides the stop button.'''
    sendCommand(u"HIDESTOPBUTTON: \n")


def showStopButton():
    '''Shows the stop button.'''
    sendCommand(u"SHOWSTOPBUTTON: \n")


def disableStopButton():
    '''Disables (grays out) the stop button.'''
    sendCommand(u"DISABLESTOPBUTTON: \n")       


def enableStopButton():
    '''Enables the stop button.'''
    sendCommand(u"ENABLESTOPBUTTON: \n")
    
    
def restartAlert():
    try:
        sendCommand(u"ACTIVATE: \n")
        sendCommand(u"RESTARTALERT: \n")
        return readResponse()
    except IOError:
        return 0
    

def getStopButtonState():
    '''Returns 1 if the stop button has been clicked, 0 otherwise.'''
    if not s:
        return 0
    try:
        s.send(u"GETSTOPBUTTONSTATE: \n")
        state = readResponse()
        if state:
            return state
        else:
            return 0
    except IOError:
        return 0


def quit():
    '''Quits MunkiStatus.app.'''
    global s
    try:
        s.send(u"QUIT: \n")
        s.close()
        s = None
    except (AttributeError, IOError):
        if getMunkiStatusPID():
            retcode = subprocess.call(["/usr/bin/killall", "MunkiStatus"])



