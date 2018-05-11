#!/usr/bin/env python2

import ttk
import tkFont
import tkMessageBox
import os
import sys
import Tkinter
import traceback
    
from glob import glob
from pprint import pprint

DEVELOP_PATH = 'C:\\develop'
QT_PATHS = [
    os.path.join(DEVELOP_PATH, 'packages\\windows-x64'),
    os.path.join(DEVELOP_PATH, 'buildenv\\packages\\windows-x64')
]

QT_PACKAGE_MAKS = 'qt-*'
VMS_DIRECTORY_MASK = 'nx_vms-*'
BUILD_OPTIONS = ('*', 'Debug', 'Release')
ARGUMENT_OPTIONS = '--log-level=DEBUG2'
COMMANDS = [
    ['mediaserver.exe', '-e'], 
    ['desktop_client.exe'], 
    ['HD Witness.exe'],
]

WINDOW_TITLE = "NX Launcher"
WINDOW_FONT = dict(family="Courier New", size=12)

def glob_in_path(path, name):
    return [os.path.basename(p) 
        for p in glob(os.path.join(path, name))]
        
def glob_in_paths(paths, name):
    return sum(map(lambda p: glob_in_path(p, name), paths), [])
        
def find_in_path(path, match, binary):
    for directory, _, files in os.walk(path):
        if match == '*' or directory.find(match) != -1:
            for name in files:
                if name == binary:
                    return os.path.join(directory, binary)
    return None
        
class Window(object):
    def __init__(self):
        self._tk = Tkinter.Tk()
        try:
            self._tk.title(WINDOW_TITLE)
            self._tk.option_add("*Font", tkFont.Font(**WINDOW_FONT))
            self._qt = self._make_combo(*glob_in_paths(QT_PATHS, QT_PACKAGE_MAKS))
            self._directory = self._make_combo(*glob_in_path(DEVELOP_PATH, VMS_DIRECTORY_MASK))
            self._build = self._make_combo(*BUILD_OPTIONS)
            self._arguments = self._make_text(ARGUMENT_OPTIONS)
            for command in COMMANDS:
                self._make_start(command)
        except:
            tkMessageBox.showerror('Error', 'Exception ' + traceback.format_exc())
            raise
        
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
        qt_paths = ';'.join(os.path.join(p, self._qt.get(), 'bin') for p in QT_PATHS)
        directory = os.path.join(DEVELOP_PATH, self._directory.get())
        build = self._build.get()
        binary_path = find_in_path(directory, build, command[0])
        if not binary_path:
            return tkMessageBox.showerror('Error', 'Unable to find "{}" in "{}"'.format(command[0], directory)) 
        command = '"' + binary_path + '"' + ' '.join(command[1:])
        command += ' ' + self._arguments.get().replace('\n', ' ')
        self._start('set PATH=' + qt_paths + ';%PATH%', 'echo ' + command, command, 'pause')
        
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
        except:
            tkMessageBox.showerror('Error', 'Exception ' + traceback.format_exc())
            raise
    
if __name__ == '__main__':
    COMMANDS += sys.argv[1:]
    Window().main_loop()
