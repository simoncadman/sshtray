#! /usr/bin/env python2
#    SSHTray - SSH Systray menu
#    Copyright (C) 2013 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License    
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sip,sys
sip.setapi('QVariant', 2)

from PyQt4 import QtGui
from PyQt4 import QtCore

if __name__ == '__main__':
    QtGui.QApplication.setAttribute(QtCore.Qt.AA_X11InitThreads, True)
    app = QtGui.QApplication(sys.argv)
    trayIconMenu = QtGui.QMenu()

    while True:
        testAction = QtGui.QAction("Test", trayIconMenu)
        trayIconMenu.addAction(testAction)
        trayIconMenu.removeAction(testAction)
        sip.delete(testAction)
        
    sys.exit(app.exec_())
