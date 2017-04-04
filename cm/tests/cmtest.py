# $Id$
# Artem V. Nikitin
# Crash monitor tests

import unittest, os, shutil, sys
import crashmon
import crashdb

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
        'Add new stack and set issue' 
        calls1 = ('<c0000005 (Access violation)>',
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
        self.assertFalse(self.db.has(calls1))
        self.db.add(calls1)
        self.assertEqual(self.db.get_faults(calls1), self.dbSize+1)
        self.db.set_issue(calls1, ('VMS_TEST', 1))
        calls2 = ('<c0000005 (Access violation)>',
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
                  'user32!ZwUserMessageCall',
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
                  'user32!ZwUserSetWindowPos',
                  'qwindows!QWindowsWindow::setWindowState_sys',
                  'qwindows!QWindowsWindow::QWindowsWindow',
                  'qwindows!QWindowsIntegration::createPlatformWindow',
                  'Qt5Gui!QWindow::create',
                  'Qt5Gui!QWindowPrivate::setScreen',
                  'Qt5Gui!QWindow::screenDestroyed',
                  'Qt5Core!QMetaObject::activate',
                  'Qt5Core!QObject::~QObject',
                  "Qt5Gui!QPlatformScreenPageFlipper::`vector deleting destructor'", 'Qt5Gui!QPlatformScreen::~QPlatformScreen',
                  "qwindows!QWindowsScreen::`scalar deleting destructor'", 'qwindows!QWindowsScreenManager::handleScreenChanges',
                  'qwindows!QWindowsScreenManager::handleDisplayChange',
                  'qwindows!QWindowsContext::windowsProc',
                  'qwindows!qWindowsWndProc',
                  'user32!UserCallWinProcCheckWow',
                  'user32!DispatchClientMessage',
                  'user32!_fnDWORD',
                  'ntdll!KiUserCallbackDispatcherContinue',
                  'user32!ZwUserPeekMessage',
                  'user32!PeekMessageW',
                  'Qt5Core!QEventDispatcherWin32::processEvents',
                  'qwindows!QWindowsGuiEventDispatcher::processEvents',
                  'Qt5Core!QEventLoop::exec',
                  'Qt5Core!QCoreApplication::exec',
                  'DW_Spectrum!runApplication',
                  'DW_Spectrum!main',
                  'DW_Spectrum!WinMain',
                  'DW_Spectrum!__tmainCRTStartup',
                  'kernel32!BaseThreadInitThunk',
                  'ntdll!RtlUserThreadStart')
        self.db.add(calls2)
        for key, crashinfo in self.db.crashes.iteritems():
            self.assertEqual(crashinfo.issue,'VMS_TEST')
        self.assertEqual(self.db.get_faults(calls1), self.dbSize+2)
        self.assertEqual(self.db.get_faults(calls2), self.dbSize+2)
        ci = self.db.crashes[calls2]
        ci.faults+=1
        self.db.rewrite()
        self.assertEqual(self.db.get_faults(calls1), self.dbSize+3)
        self.assertEqual(self.db.get_faults(calls2), self.dbSize+3)
        

class CrashDBHashTest(unittest.TestCase):

    def testCompareHashes(self):
        'Compare hashes'
        calls1 = ('<c0000005 (Access violation)>',
                  'Qt5Gui!QOpenGLContext::shareGroup',
                  'Qt5Gui!QOpenGLMultiGroupSharedResource::value<QOpenGLFunctionsPrivateEx>',
                  'Qt5Gui!qt_gl_functions',
                  'Qt5Gui!QOpenGLFunctions::initializeOpenGLFunctions',
                  'Qt5OpenGL!QGL2PaintEngineEx::begin',
                  'Qt5Gui!QPainter::begin',
                  'Qt5Gui!QPainter::QPainter',
                  'Qt5Widgets!QGraphicsView::paintEvent',
                  'DW_Spectrum!QnGraphicsView::paintEvent',
                  'Qt5Widgets!QWidget::event',
                  'Qt5Widgets!QFrame::event',
                  'DW_Spectrum!ForwardingInstrument::event',
                  'DW_Spectrum!InstrumentEventDispatcher<QWidget>::dispatch',
                  'Qt5Core!QCoreApplicationPrivate::sendThroughObjectEventFilters',
                  'Qt5Widgets!QApplicationPrivate::notify_helper',
                  'Qt5Widgets!QApplication::notify',
                  'Qt5Core!QCoreApplication::notifyInternal',
                  'Qt5Widgets!QWidgetPrivate::drawWidget',
                  'Qt5Widgets!QWidgetPrivate::repaint_sys',
                  'Qt5Widgets!QWidgetWindow::event',
                  'Qt5Widgets!QApplicationPrivate::notify_helper',
                  'Qt5Widgets!QApplication::notify',
                  'Qt5Core!QCoreApplication::notifyInternal',
                  'Qt5Gui!QGuiApplicationPrivate::processExposeEvent',
                  'Qt5Gui!QGuiApplicationPrivate::processWindowSystemEvent',
                  'Qt5Gui!QWindowSystemInterface::sendWindowSystemEvents',
                  'qwindows!QWindowsWindow::handleWmPaint',
                  'qwindows!QWindowsContext::windowsProc',
                  'qwindows!qWindowsWndProc',
                  'user32!UserCallWinProcCheckWow',
                  'user32!CallWindowProcW',
                  'opengl32!wglWndProc',
                  'user32!UserCallWinProcCheckWow',
                  'user32!DispatchClientMessage',
                  'user32!_fnDWORD',
                  'ntdll!KiUserCallbackDispatcherContinue',
                  'win32u!NtUserDispatchMessage',
                  'user32!DispatchMessageWorker',
                  'Qt5Core!QEventDispatcherWin32::processEvents',
                  'qwindows!QWindowsGuiEventDispatcher::processEvents',
                  'Qt5Core!QCoreApplication::processEvents',
                  'DW_Spectrum!runApplication',
                  'DW_Spectrum!main',
                  'DW_Spectrum!WinMain',
                  'DW_Spectrum!__tmainCRTStartup',
                  'kernel32!BaseThreadInitThunk',
                  'ntdll!RtlUserThreadStart')
        calls2 = ('<c0000005 (Access violation)>',
                  'Qt5Gui!QOpenGLContext::shareGroup',
                  'Qt5Gui!QOpenGLMultiGroupSharedResource::value<QOpenGLFunctionsPrivateEx>',
                  'Qt5Gui!qt_gl_functions',
                  'Qt5Gui!QOpenGLFunctions::initializeOpenGLFunctions',
                  'Qt5OpenGL!QGL2PaintEngineEx::begin',
                  'Qt5Gui!QPainter::begin',
                  'Qt5Gui!QPainter::QPainter',
                  'Qt5Widgets!QGraphicsView::paintEvent',
                  'DW_Spectrum!QnGraphicsView::paintEvent',
                  'Qt5Widgets!QWidget::event',
                  'Qt5Widgets!QFrame::event',
                  'DW_Spectrum!ForwardingInstrument::event',
                  'DW_Spectrum!InstrumentEventDispatcher<QWidget>::dispatch',
                  'Qt5Core!QCoreApplicationPrivate::sendThroughObjectEventFilters',
                  'Qt5Widgets!QApplicationPrivate::notify_helper',
                  'Qt5Widgets!QApplication::notify',
                  'Qt5Core!QCoreApplication::notifyInternal',
                  'Qt5Widgets!QWidgetPrivate::drawWidget',
                  'Qt5Widgets!QWidgetPrivate::repaint_sys',
                  'Qt5Widgets!QWidgetWindow::event',
                  'Qt5Widgets!QApplicationPrivate::notify_helper',
                  'Qt5Widgets!QApplication::notify',
                  'Qt5Core!QCoreApplication::notifyInternal',
                  'Qt5Gui!QGuiApplicationPrivate::processExposeEvent',
                  'Qt5Gui!QGuiApplicationPrivate::processWindowSystemEvent',
                  'Qt5Gui!QWindowSystemInterface::sendWindowSystemEvents',
                  'qwindows!QWindowsWindow::handleWmPaint',
                  'qwindows!QWindowsContext::windowsProc',
                  'qwindows!qWindowsWndProc',
                  'user32!UserCallWinProcCheckWow',
                  'user32!CallWindowProcAorW',
                  'user32!CallWindowProcW',
                  'opengl32!wglWndProc',
                  'user32!UserCallWinProcCheckWow',
                  'user32!DispatchClientMessage',
                  'user32!_fnDWORD',
                  'ntdll!KiUserCallbackDispatcherContinue',
                  'user32!NtUserDispatchMessage',
                  'user32!DispatchMessageWorker',
                  'Qt5Core!QEventDispatcherWin32::processEvents',
                  'qwindows!QWindowsGuiEventDispatcher::processEvents',
                  'Qt5Core!QCoreApplication::processEvents',
                  'DW_Spectrum!runApplication',
                  'DW_Spectrum!main',
                  'DW_Spectrum!WinMain',
                  'DW_Spectrum!__tmainCRTStartup',
                  'kernel32!BaseThreadInitThunk',
                  'ntdll!RtlUserThreadStart')
        hash1 = crashdb.KnowCrashDB.prepare2hash(calls1)
        hash2 = crashdb.KnowCrashDB.prepare2hash(calls2)
        self.assertEqual(hash1, hash2)

    
        
    

        


