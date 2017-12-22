#!/usr/bin/python

import ttk
import tkMessageBox
import os
import Tkinter

from glob import glob
from pprint import pprint

DEVELOP = 'C:\\develop'
QT_PATH = os.path.join(DEVELOP, 'buildenv\\packages\\windows-x64')
COMMANDS = [
    'mediaserver.exe -e',
    'desktop_client.exe',
]

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
        self._tk.title("NX Launcher")
        self._qt = self._make_combo(*glob_in_path(QT_PATH, 'qt-*'))
        self._directory = self._make_combo(*glob_in_path(DEVELOP, 'nx_vms-*'))
        self._build = self._make_combo('*', 'Debug', 'Release')
        for command in COMMANDS:
            self._make_start(command)
        
    def _make_combo(self, *options):
        combo = ttk.Combobox(self._tk, textvariable=Tkinter.StringVar(), state='readonly')
        combo['values'] = options
        combo.current(0)
        combo.pack(fill='x')
        return combo
        
    def _make_start(self, command):
        action = lambda: self._run(command)
        button = Tkinter.Button(self._tk, text=command, command=action)
        button.pack(fill='x')
        return button
        
    def _run(self, command):
        qt_path = os.path.join(QT_PATH, self._qt.get(), 'bin')
        directory, build = self._directory.get(), self._build.get()
        command = find_in_path(os.path.join(DEVELOP, directory), build, command)
        if command:
            self._start('set PATH=' + qt_path + ';%PATH%', 'echo ' + command, command, 'pause')
        else:
            tkMessageBox.showerror('Error', 'Unable to find requested binary.')
        
    def _start(self, *commands):
        pprint(commands)
        os.system('start cmd /c "{}"'.format(' & '.join(commands)))
        
    def main_loop(self):
        def event_check(): self._tk.after(50, event_check)
        event_check()
        try:
            self._tk.mainloop()
        except KeyboardInterrupt:
            print('Exit by Ctrl+C')
    
if __name__ == '__main__':
    Window().main_loop()
