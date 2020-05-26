class ColorDummy():
    class Empty(object):
        def __getattribute__(self, name):
            return ''

    Style = Empty()
    Fore = Empty()

colorer = ColorDummy()

def info(message):
    print(colorer.Style.BRIGHT + message)

def green(message):
    print(colorer.Style.BRIGHT + colorer.Fore.GREEN + message)

def warn(message):
    print(colorer.Style.BRIGHT + colorer.Fore.YELLOW + message)

def err(message):
    print(colorer.Style.BRIGHT + colorer.Fore.RED + message)

def separator():
    separatorLine = '------------------------------------------------'
    info(separatorLine)

def init_color():
    from colorama import Fore, Back, Style, init
    init(autoreset=True) # use Colorama to make Termcolor work on Windows too
    global colorer
    import colorama as colorer
