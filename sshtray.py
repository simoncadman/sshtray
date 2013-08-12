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
import sip,sys,os,subprocess,time,getpass,ConfigParser
from functools import partial
sip.setapi('QVariant', 2)

from PyQt4 import QtGui
from PyQt4 import QtCore

import boto.ec2

class RefreshServers(QtCore.QThread):
    def __init__(self, window):
        self.window = window
        QtCore.QThread.__init__(self)
        self.connect(self, QtCore.SIGNAL('runNow'), self.refreshServers)

    def run(self):
        while True:
            if self.window.configEC2AccessId != "" and self.window.configEC2SecretKey != "":
                try:
                    data = self.refreshServers()
                    self.window.emit(QtCore.SIGNAL('updateMenu'), data)
                except Exception as e:
                    print "Error updating servers"
                    print e
            time.sleep(self.window.configSleep)
        
    def refreshServers(self):
        print "Refreshing servers"
        ec2instances = {}
        for region in [ 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-1', 'sa-east-1', 'us-east-1' , 'us-west-1', 'us-west-2' ]:
            ec2_conn = boto.ec2.connect_to_region(region, aws_access_key_id=self.window.configEC2AccessId, aws_secret_access_key=self.window.configEC2SecretKey)
            for reservation in ec2_conn.get_all_instances():
                for instance in reservation.instances:
                    instanceplatform = ""
                    if instance.platform != None:
                        instanceplatform = instance.platform
                    instancename = "Unknown " + instanceplatform + " Instance " + instance.id
                    if 'Name' in instance.tags:
                        instancename = instance.tags['Name']
                    if instance.region.name not in ec2instances:
                        ec2instances[instance.region.name] = {}
                    groupName = 'Other'
                    if 'aws:autoscaling:groupName' in instance.tags:
                        groupName = instance.tags['aws:autoscaling:groupName']
                    if 'customGroupName' in instance.tags:
                        groupName = instance.tags['customGroupName']
                    if groupName not in ec2instances[instance.region.name]:
                        ec2instances[instance.region.name][groupName] = {}
                    ec2instances[instance.region.name][groupName][instance.id] = {'Name': instancename, 'IP' : instance.ip_address, 'Region' : instance.region.name }
        print "Servers updated"
        return {'ec2' : ec2instances }

class SSHTray(QtGui.QDialog):
    
    # loads config file, returns menu items
    def loadSettingsFromConfig(self):
        self.appName = "sshtray"
        self.configFile = os.path.expanduser('~/.' + self.appName)
        
        # default settings
        self.configEC2AccessId = ""
        self.configEC2SecretKey = ""
        self.configPort = str(22)
        self.configUsername = getpass.getuser()
        self.configSleep = 300
        # load from file
        if os.path.exists(self.configFile):
            try:
                config = ConfigParser.ConfigParser()
                config.readfp(open(self.configFile))
                if config.has_section('ec2'):
                        self.configEC2AccessId = config.get('ec2', 'accessid')
                        self.configEC2SecretKey = config.get('ec2', 'secretkey')
            except:
                pass
            
        return []
    
    def saveSettings(self):
        self.configEC2AccessId = str(self.accountEdit.text())
        self.configEC2SecretKey = str(self.secretEdit.text())
        config = ConfigParser.ConfigParser()
        config.add_section('ec2')
        config.set('ec2', 'accessid', self.configEC2AccessId )
        config.set('ec2', 'secretkey', self.configEC2SecretKey )
        config.write(open(self.configFile,'w'))
        self.refresh.emit(QtCore.SIGNAL('runNow') )
        
    def resetSettings(self):
        self.accountEdit.setText(self.configEC2AccessId)
        self.secretEdit.setText(self.configEC2SecretKey)
    
    def __init__(self):
        self.trayIcon = None
        super(SSHTray, self).__init__()
        
        # load settings from config
        data = self.loadSettingsFromConfig()
        
        # setup the settings window
        self.setupSettings()

        # setup tray and menu on the tray
        self.setupMenuOptions({})
        self.setupTrayIcon()
        
        # connect refresh of menu options to signal
        self.connect(self, QtCore.SIGNAL('updateMenu'), self.setupMenuOptions)
        
        # all setup, show the tray icon
        self.trayIcon.show()
        
        if self.configEC2AccessId == "" or self.configEC2SecretKey == "":
            self.showNormal()

    # user clicked tray, show menu
    def iconActivated(self, reason):
        if reason in (QtGui.QSystemTrayIcon.Trigger, QtGui.QSystemTrayIcon.DoubleClick):
            self.trayIconMenu.popup(QtGui.QCursor.pos())

    def saveSettingsButton(self):
        self.hide()
        self.saveSettings()

    def cancelSettingsButton(self):
        self.hide()
        self.resetSettings()

    # settings window
    def setupSettings(self):
        self.messageGroupBox = QtGui.QGroupBox("Amazon EC2")

        accountLabel = QtGui.QLabel("Access Key ID:")
        self.accountEdit = QtGui.QLineEdit()

        secretLabel = QtGui.QLabel("Secret Access Key:")
        self.secretEdit = QtGui.QLineEdit()
        
        self.saveButton = QtGui.QPushButton("&Save")
        self.saveButton.setDefault(True)
        self.saveButton.clicked.connect(self.saveSettingsButton)
        
        self.cancelButton = QtGui.QPushButton("&Cancel")
        self.cancelButton.clicked.connect(self.cancelSettingsButton)

        messageLayout = QtGui.QGridLayout()
        messageLayout.addWidget(accountLabel, 0, 0)
        messageLayout.addWidget(self.accountEdit, 0, 1)
        messageLayout.addWidget(secretLabel, 1, 0)
        messageLayout.addWidget(self.secretEdit, 1, 1)
        messageLayout.addWidget(self.saveButton, 2, 0)
        messageLayout.addWidget(self.cancelButton, 2, 1)
        self.messageGroupBox.setLayout(messageLayout)
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.messageGroupBox)
        self.setLayout(mainLayout)
        
        self.resetSettings()

    def doSSH(self, instance):
        print "SSHing",instance
        result = 0
        command = "konsole"
        p = subprocess.Popen([command, '--hold', '-e', 'ssh', '-p' + self.configPort, "-v", self.configUsername + '@' + instance], stdout=subprocess.PIPE)
        output = p.communicate()[0]
        result = p.returncode

    # options within tray context menu
    def setupMenuOptions(self, data):
        
        self.trayIconMenu = QtGui.QMenu(self)
        
        # default data
        self.settingsAction = QtGui.QAction("&Settings", self,
                triggered=self.showNormal)
        self.quitAction = QtGui.QAction("&Quit", self,
                triggered=QtGui.qApp.quit)
        
        # ec2 instances
        if 'ec2' in data and len(data['ec2']) > 0:
            self.ec2Menu = QtGui.QMenu("&EC2", self)
            orderedRegions = []
            # sort regions
            orderedRegions = sorted(data['ec2'])
            for region in orderedRegions:
                serverRegion = QtGui.QMenu(region,self)
                orderedGroups = sorted(data['ec2'][region])
                for group in orderedGroups:
                    serverGroup = QtGui.QMenu(group,self)
                    orderedInstances = sorted(data['ec2'][region][group],key=lambda instanceItem: str.lower(str(data['ec2'][region][group][instanceItem]['Name'])))
                    for instanceName in orderedInstances:
                        instance = data['ec2'][region][group][instanceName]
                        serverAction = QtGui.QAction(instance['Name'],self)
                        self.connect(serverAction,QtCore.SIGNAL("triggered()"), partial(self.doSSH, instance['IP']))
                        if len(data['ec2'][region]) > 1:
                            serverGroup.addAction(serverAction)
                        else:
                            if len(data['ec2']) > 1:
                                serverRegion.addAction(serverAction)
                            else:
                                self.ec2Menu.addAction(serverAction)
                    if len(data['ec2'][region]) > 1:
                        if len(data['ec2']) > 1:
                            serverRegion.addMenu(serverGroup)
                        else:
                            self.ec2Menu.addMenu(serverGroup)
                        
                if len(data['ec2']) > 1:
                    self.ec2Menu.addMenu(serverRegion)
                    
            self.trayIconMenu.addMenu(self.ec2Menu)
        
        if 'zeroconf' in data and len(data['zeroconf']) > 0:
            self.discoveredMenu = QtGui.QMenu("&Discovered", self)
            self.trayIconMenu.addMenu(self.discoveredMenu)
        
        if 'custom' in data and len(data['custom']) > 0:
            self.customMenu = QtGui.QMenu("&Custom", self)
            self.trayIconMenu.addMenu(self.customMenu)
        
        # default, need to appear at end of list
        
        if self.trayIcon == None:
            # first run, add message showing still loading
            self.loadingAction = QtGui.QAction("Loading servers...", self)
            self.loadingAction.setDisabled(True)
            self.trayIconMenu.addAction(self.loadingAction)
        
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.settingsAction)
        self.trayIconMenu.addAction(self.quitAction)
        
        if self.trayIcon != None:
            self.trayIcon.setContextMenu(self.trayIconMenu)
            self.trayIcon.activated.connect(self.iconActivated)
            
    # tray icon
    def setupTrayIcon(self):
         icon = QtGui.QIcon('sshtray.svg')
         self.trayIcon = QtGui.QSystemTrayIcon(icon)
         self.setWindowIcon(icon)
         self.trayIcon.setContextMenu(self.trayIconMenu)
         self.trayIcon.activated.connect(self.iconActivated)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    
    if not QtGui.QSystemTrayIcon.isSystemTrayAvailable():
        QtGui.QMessageBox.critical(None, "SSHTray", "Failed to detect a system tray.")
        sys.exit(1)
        
    QtGui.QApplication.setQuitOnLastWindowClosed(False)
    
    window = SSHTray()
    refresh = RefreshServers(window)
    window.refresh = refresh
    refresh.start()
    sys.exit(app.exec_())