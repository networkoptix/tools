#!/usr/bin/python

import ttk
import tkFont
import tkMessageBox
import os
import sys
import Tkinter
    
from glob import glob
from pprint import pprint

DEVELOP_PATH = 'C:\\develop'
QT_PATH = os.path.join(DEVELOP_PATH, 'buildenv\\packages\\windows-x64')

QT_PACKAGE_MAKS = 'qt-*'
VMS_DIRECTORY_MASK = 'nx_vms-*'
BUILD_OPTIONS = ('*', 'Debug', 'Release')
ARGUMENT_OPTIONS = '--log-level=DEBUG2'
COMMANDS = ['mediaserver.exe -e', 'desktop_client.exe']

WINDOW_TITLE = "NX Launcher"
WINDOW_FONT = dict(family="Courier New", size=12)

def glob_in_path(path, name):
    return (os.path.basename(p) 
        for p in glob(os.path.join(path, name)))
        
def find_in_path(path, match, binary):
    for directory, _, files in os.walk(path):
        if match == '*' or directory.find(match) != -1:
            for name in files:
                if name == binary.split(' ')[0]:
                    return os.path.join(directory, binary)
    return None
        
class Window(object):
    def __init__(self):
        self._tk = Tkinter.Tk()
        self._tk.title(WINDOW_TITLE)
        self._tk.option_add("*Font", tkFont.Font(**WINDOW_FONT))
        self._qt = self._make_combo(*glob_in_path(QT_PATH, QT_PACKAGE_MAKS))
        self._directory = self._make_combo(*glob_in_path(DEVELOP_PATH, VMS_DIRECTORY_MASK))
        self._build = self._make_combo(*BUILD_OPTIONS)
        self._arguments = self._make_text(ARGUMENT_OPTIONS)
        for command in COMMANDS: 
            self._make_start(command)
        
    def _make_combo(self, *options):
        combo = ttk.Combobox(self._tk, state='readonly')
        combo['values'] = options
        combo.current(0)
        return self._pack(combo)
    
    def _make_text(self, text):
        entry = Tkinter.Text(self._tk, height=2, width=30)
        entry.insert(Tkinter.END, text)
        entry_get = entry.get
        entry.get = lambda *args: entry_get(*(args or (1.0, Tkinter.END)))
        return self._pack(entry)
        
    def _make_start(self, command):
        action = lambda: self._run(command)
        return self._pack(Tkinter.Button(self._tk, text=command, command=action))
        
    def _run(self, command):
        qt_path = os.path.join(QT_PATH, self._qt.get(), 'bin')
        directory, build = self._directory.get(), self._build.get()
        command = find_in_path(os.path.join(DEVELOP_PATH, directory), build, command)
        if not command:
            return tkMessageBox.showerror('Error', 'Unable to find requested binary.') 
        command += ' ' + self._arguments.get().replace('\n', ' ')
        self._start('set PATH=' + qt_path + ';%PATH%', 'echo ' + command, command, 'pause')
        
    def _start(self, *commands):
        pprint(commands)
        os.system('start cmd /c "{}"'.format(' & '.join(commands)))
        
    def _pack(self, widget):
        widget.pack(fill='x')
        return widget;
        
    def main_loop(self):
        def event_check(): self._tk.after(50, event_check)
        event_check()
        try:
            self._tk.mainloop()
        except KeyboardInterrupt:
            print('Exit by Ctrl+C')
    
if __name__ == '__main__':
    COMMANDS += sys.argv[1:]
    Window().main_loop()
