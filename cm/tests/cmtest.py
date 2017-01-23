# $Id$
# Artem V. Nikitin
# Crash monitor tests

import unittest, os, shutil, sys
import crashmon
import crashdb

class CrashMonitorTests(unittest.TestCase):

    def testSkipDriverCall(self):
        'skip driver call'
        calls = ('<c0000005 (Access violation)>', 'ig75icd64', '0x0', 'ig75icd64')
        self.assertFalse(crashmon.need_process_calls(calls))
        calls = ( '<c0000005 (Access violation)>', '0x0', 'nvoglv64',
                  '0x0', '0x0', '0x0', '0x0', '0x0', '0x0', '0x0',
                  'KERNELBASE', '0x0', '0x0', '0x0')
        self.assertFalse(crashmon.need_process_calls(calls))

    def testValidDriverStack(self):
        'valid driver stak'
        calls = ('<c0000005 (Access violation)>', 'ntdll', '0x0', '0x0', '0x0')
        self.assertTrue(crashmon.need_process_calls(calls))
        calls = ('<c0000005 (Access violation)>',
                 'Qt5Gui!QPlatformOffscreenSurface::offscreenSurface',
                 'qwindows!qt_plugin_query_metadata',
                 'Qt5Widgets!QWidgetPrivate::setGeometry_sys',
                 'Qt5Widgets!QWidget::setGeometry',
                 'Qt5Widgets!QWidgetItem::setGeometry',
                 'Qt5Widgets!QBoxLayout::setGeometry',
                 'Qt5Widgets!QBoxLayout::setGeometry',
                 'Qt5Widgets!QLayoutPrivate::doResize',
                 'Qt5Widgets!QApplicationPrivate::notify_helper',
                 'Qt5Widgets!QApplication::notify',
                 'Qt5Core!QCoreApplication::notifyInternal',
                 'Qt5Widgets!QWidgetWindow::handleResizeEvent',
                 'Qt5Widgets!QWidgetWindow::event',
                 'Qt5Widgets!QApplicationPrivate::notify_helper',
                 'Qt5Widgets!QApplication::notify',
                 'Qt5Core!QCoreApplication::notifyInternal',
                 'Qt5Gui!QGuiApplicationPrivate::processGeometryChangeEvent',
                 'Qt5Gui!QGuiApplicationPrivate::processWindowSystemEvent',
                 'Qt5Gui!QWindowSystemInterface::sendWindowSystemEvents',
                 'qwindows!qt_plugin_query_metadata',
                 'qwindows!qt_plugin_query_metadata',
                 'qwindows!qt_plugin_query_metadata',
                 'user32',
                 '0x0',
                 'ntdll', '0x0', '0x0', '0x0', 'nvoglv64', '0x0', '0x0', '0x0')
        self.assertTrue(crashmon.need_process_calls(calls))


class CrashDBTest(unittest.TestCase):

    def setUp(self):
        self.testPath = os.path.dirname(sys.modules[__name__].__file__)
        self.testFile = os.path.join(self.testPath, 'known-faults-test.list')
        self.resultFile = os.path.join(self.testPath, 'known-faults-test.result')
        if os.path.exists(self.resultFile):
            os.remove(self.resultFile)
        shutil.copyfile(self.testFile,  self.resultFile)
        self.db = crashdb.KnowCrashDB(self.resultFile)
        self.dbSize = len(self.db.crashes)

    def testAddNewStackAndSetIssue(self):
        calls = ('<c0000005 (Access violation)>',
                 'Qt5Gui!QPlatformOffscreenSurface::offscreenSurface',
                 'qwindows!QWindowsBackingStore::resize',
                 'Qt5Widgets!QWidgetPrivate::setGeometry_sys',
                 'Qt5Widgets!QWidget::setGeometry',
                 'Qt5Widgets!QWidgetItem::setGeometry',
                 'Qt5Widgets!QBoxLayout::setGeometry',
                 'Qt5Widgets!QBoxLayout::setGeometry',
                 'Qt5Widgets!QLayoutPrivate::doResize',
                 'Qt5Widgets!QApplicationPrivate::notify_helper',
                 'Qt5Widgets!QApplication::notify',
                 'Qt5Core!QCoreApplication::notifyInternal',
                 'Qt5Widgets!QWidgetWindow::handleResizeEvent',
                 'Qt5Widgets!QWidgetWindow::event',
                 'Qt5Widgets!QApplicationPrivate::notify_helper',
                 'Qt5Widgets!QApplication::notify',
                 'Qt5Core!QCoreApplication::notifyInternal',
                 'Qt5Gui!QGuiApplicationPrivate::processGeometryChangeEvent',
                 'Qt5Gui!QGuiApplicationPrivate::processWindowSystemEvent',
                 'Qt5Gui!QWindowSystemInterface::sendWindowSystemEvents',
                 'qwindows!QWindowsWindow::handleGeometryChange',
                 'qwindows!QWindowsContext::windowsProc',
                 'qwindows!qWindowsWndProc',
                 'user32!UserCallWinProcCheckWow',
                 'user32!DispatchClientMessage',
                 'user32!_fnDWORD',
                 'ntdll!KiUserCallbackDispatcherContinue',
                 'win32u!NtUserMessageCall',
                 'user32!SendMessageWorker',
                 'user32!RealDefWindowProcWorker',
                 'user32!RealDefWindowProcW',
                 'uxtheme!_ThemeDefWindowProc',
                 'uxtheme!ThemeDefWindowProcW',
                 'user32!DefWindowProcW',
                 'qwindows!qWindowsWndProc',
                 'user32!UserCallWinProcCheckWow',
                 'user32!DispatchClientMessage',
                 'user32!_fnINLPWINDOWPOS',
                 'ntdll!KiUserCallbackDispatcherContinue',
                 'win32u!NtUserSetWindowPos',
                 'qwindows!QWindowsWindow::setWindowState_sys',
                 'qwindows!QWindowsWindow::QWindowsWindow',
                 'qwindows!QWindowsIntegration::createPlatformWindow',
                 'Qt5Gui!QWindow::create',
                 'Qt5Gui!QWindowPrivate::setScreen',
                 'Qt5Gui!QWindow::screenDestroyed',
                 'Qt5Core!QMetaObject::activate',
                 'Qt5Core!QObject::~QObject',
                 "Qt5Gui!QPlatformScreenPageFlipper::`vector deleting destructor'",
                 'Qt5Gui!QPlatformScreen::~QPlatformScreen',
                 "qwindows!QWindowsScreen::`scalar deleting destructor'",
                 'qwindows!QWindowsScreenManager::handleScreenChanges',
                 'qwindows!QWindowsScreenManager::handleDisplayChange',
                 'qwindows!QWindowsContext::windowsProc',
                 'qwindows!qWindowsWndProc',
                 'user32!UserCallWinProcCheckWow',
                 'user32!DispatchClientMessage',
                 'user32!_fnEMPTY',
                 'ntdll!KiUserCallbackDispatcherContinue',
                 'win32u!NtUserPeekMessage',
                 'user32!PeekMessageW',
                 'Qt5Core!QEventDispatcherWin32::processEvents',
                 'qwindows!QWindowsGuiEventDispatcher::processEvents',
                 'Qt5Core!QEventLoop::exec',
                 'Qt5Core!QCoreApplication::exec',
                 'HD_Witness!runApplication',
                 'HD_Witness!main',
                 'HD_Witness!WinMain',
                 'HD_Witness!__tmainCRTStartup',
                 'kernel32!BaseThreadInitThunk',
                 'ntdll!RtlUserThreadStart')
        self.assertFalse(self.db.has(calls))
        self.db.add(calls)
        self.assertEqual(len(self.db.crashes), self.dbSize+1)
        self.db.set_issue(calls, 'VMS_TEST')
        self.db.rewrite()
        for key, issue in self.db.crashes.iteritems():
            self.assertEqual(issue, 'VMS_TEST')
        



    
        
    

        


