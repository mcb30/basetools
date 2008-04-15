## @file
# This file is used to create/update/query/erase table for ECC reports
#
# Copyright (c) 2008, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.  The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

##
# Import Modules
#
import Common.EdkLogger as EdkLogger
import os, time
from Table import Table
from Common.String import ConvertToSqlString2
import EotToolError as EotToolError
import EotGlobalData as EotGlobalData

## TableReport
#
# This class defined a table used for data model
# 
# @param object:       Inherited from object class
#
#
class TableEotReport(Table):
    def __init__(self, Cursor):
        Table.__init__(self, Cursor)
        self.Table = 'Report'
    
    ## Create table
    #
    # Create table report
    #
    #
    def Create(self):
        SqlCommand = """create table IF NOT EXISTS %s (ID INTEGER PRIMARY KEY,
                                                       ModuleID INTEGER NOT NULL,
                                                       ModuleName TEXT NOT NULL,
                                                       SourceFileID INTEGER NOT NULL,
                                                       SourceFileFullPath TEXT NOT NULL,
                                                       ItemName TEXT NOT NULL,
                                                       ItemType TEXT NOT NULL,
                                                       ItemMode TEXT NOT NULL,
                                                       GuidName TEXT NOT NULL,
                                                       GuidMacro TEXT,
                                                       GuidValue TEXT,
                                                       Enabled INTEGER DEFAULT 0
                                                      )""" % self.Table
        Table.Create(self, SqlCommand)

    ## Insert table
    #
    # Insert a record into table report
    #
    #
    def Insert(self, ModuleID = -1, ModuleName = '', SourceFileID = -1, SourceFileFullPath = '', \
               ItemName = '', ItemType = '', ItemMode = '', GuidName = '', GuidMacro = '', GuidValue = '', Enabled = 0):
        self.ID = self.ID + 1
        SqlCommand = """insert into %s values(%s, %s, '%s', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', %s)""" \
                     % (self.Table, self.ID, ModuleID, ModuleName, SourceFileID, SourceFileFullPath, \
                        ItemName, ItemType, ItemMode, GuidName, GuidMacro, GuidValue, Enabled)
        Table.Insert(self, SqlCommand)
        
    def GetMaxID(self):
        SqlCommand = """select max(ID) from %s""" % self.Table
        self.Cur.execute(SqlCommand)
        for Item in self.Cur:
            return Item[0]