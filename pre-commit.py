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

import fileinput, re, sys, glob, subprocess
from datetime import datetime

searchRegex = 'SSHTrayVersion = "(\d)+ (\d){6}"'
replaceValue = 'SSHTrayVersion = "' + datetime.utcnow().strftime('%Y%m%d %H%M%S') + '"'

files = glob.glob('*.py')

for file in files:
    replaceLine = False
    for line in fileinput.input(file, inplace=1):
        
        if replaceLine:
            line = re.sub(searchRegex, replaceValue, line)
        
        if '# line below is replaced on commit' in line:
            replaceLine = True
        else:
            replaceLine = False
            
        sys.stdout.write(line)
        
    p = subprocess.Popen(["git", "add", file], stdout=subprocess.PIPE)
    output = p.communicate()[0]
    result = p.returncode
    if result != 0:
        sys.exit(result)
