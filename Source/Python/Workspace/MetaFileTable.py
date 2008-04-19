## @file
# This file is used to create/update/query/erase a common table
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
from MetaDataTable import Table
from MetaDataTable import ConvertToSqlString

class ModuleTable(Table):
    _ID_STEP_ = 0.00000001
    _ID_MAX_  = 0.99999999
    _COLUMN_ = '''
        ID REAL PRIMARY KEY,
        Model INTEGER NOT NULL,
        Value1 TEXT NOT NULL,
        Value2 TEXT,
        Value3 TEXT,
        Scope1 TEXT,
        Scope2 TEXT,
        BelongsToItem REAL NOT NULL,
        StartLine INTEGER NOT NULL,
        StartColumn INTEGER NOT NULL,
        EndLine INTEGER NOT NULL,
        EndColumn INTEGER NOT NULL,
        Enabled INTEGER DEFAULT 0
        '''
    _DUMMY_ = "-1, -1, '====', '====', '====', '====', '====', -1, -1, -1, -1, -1, -1"

    def __init__(self, Cursor, Name='Inf', IdBase=0, Temporary=False):
        Table.__init__(self, Cursor, Name, IdBase, Temporary)

    #
    # Insert a record into table Inf
    #
    # @param Model:          Model of a Inf item
    # @param Value1:         Value1 of a Inf item
    # @param Value2:         Value2 of a Inf item
    # @param Value3:         Value3 of a Inf item
    # @param Value4:         Value4 of a Inf item
    # @param Value5:         Value5 of a Inf item
    # @param Arch:           Arch of a Inf item
    # @param BelongsToItem:  The item belongs to which another item
    # @param BelongsToFile:  The item belongs to which dsc file
    # @param StartLine:      StartLine of a Inf item
    # @param StartColumn:    StartColumn of a Inf item
    # @param EndLine:        EndLine of a Inf item
    # @param EndColumn:      EndColumn of a Inf item
    # @param Enabled:        If this item enabled
    #
    def Insert(self, Model, Value1, Value2, Value3, Scope1='COMMON', Scope2='COMMON',
               BelongsToItem=-1, StartLine=-1, StartColumn=-1, EndLine=-1, EndColumn=-1, Enabled=0):
        (Value1, Value2, Value3, Scope1, Scope2) = ConvertToSqlString((Value1, Value2, Value3, Scope1, Scope2))
        return Table.Insert(
                        self, 
                        Model, 
                        Value1, 
                        Value2, 
                        Value3, 
                        Scope1, 
                        Scope2,
                        BelongsToItem, 
                        StartLine, 
                        StartColumn, 
                        EndLine, 
                        EndColumn, 
                        Enabled
                        )

    ## Query table
    #
    # @param Model:  The Model of Record 
    #
    # @retval:       A recordSet of all found records 
    #
    def Query(self, Model, Arch=None, Platform=None):
        ConditionString = "Model=%s AND Enabled>=0" % Model
        ValueString = "Value1,Value2,Value3,Scope1,Scope2,ID,StartLine"

        if Arch != None and Arch != 'COMMON':
            ConditionString += " AND (Scope1='%s' OR Scope1='COMMON')" % Arch
        if Platform != None and Platform != 'COMMON':
            ConditionString += " AND (Scope2='%s' OR Scope2='COMMON' OR Scope2='DEFAULT')" % Platform

        SqlCommand = "SELECT %s FROM %s WHERE %s" % (ValueString, self.Table, ConditionString)
        return self.Exec(SqlCommand)

class PackageTable(Table):
    _ID_STEP_ = 0.00000001
    _ID_MAX_ = 1
    _COLUMN_ = '''
        ID REAL PRIMARY KEY,
        Model INTEGER NOT NULL,
        Value1 TEXT NOT NULL,
        Value2 TEXT,
        Value3 TEXT,
        Scope1 TEXT,
        Scope2 TEXT,
        BelongsToItem REAL NOT NULL,
        StartLine INTEGER NOT NULL,
        StartColumn INTEGER NOT NULL,
        EndLine INTEGER NOT NULL,
        EndColumn INTEGER NOT NULL,
        Enabled INTEGER DEFAULT 0
        '''
    _DUMMY_ = "-1, -1, '====', '====', '====', '====', '====', -1, -1, -1, -1, -1, -1"
    def __init__(self, Cursor, Name='Dec', IdBase=0, Temporary=False):
        Table.__init__(self, Cursor, Name, IdBase, Temporary)

    ## Insert table
    #
    # Insert a record into table Dec
    #
    # @param Model:          Model of a Dec item
    # @param Value1:         Value1 of a Dec item
    # @param Value2:         Value2 of a Dec item
    # @param Value3:         Value3 of a Dec item
    # @param Arch:           Arch of a Dec item
    # @param BelongsToItem:  The item belongs to which another item
    # @param BelongsToFile:  The item belongs to which dsc file
    # @param StartLine:      StartLine of a Dec item
    # @param StartColumn:    StartColumn of a Dec item
    # @param EndLine:        EndLine of a Dec item
    # @param EndColumn:      EndColumn of a Dec item
    # @param Enabled:        If this item enabled
    #
    def Insert(self, Model, Value1, Value2, Value3, Scope1='COMMON', Scope2='COMMON',
               BelongsToItem=-1, StartLine=-1, StartColumn=-1, EndLine=-1, EndColumn=-1, Enabled=0):
        (Value1, Value2, Value3, Scope1, Scope2) = ConvertToSqlString((Value1, Value2, Value3, Scope1, Scope2))
        return Table.Insert(
                        self, 
                        Model, 
                        Value1, 
                        Value2, 
                        Value3, 
                        Scope1, 
                        Scope2,
                        BelongsToItem, 
                        StartLine, 
                        StartColumn, 
                        EndLine, 
                        EndColumn, 
                        Enabled
                        )

    ## Query table
    #
    # @param Model:  The Model of Record 
    #
    # @retval:       A recordSet of all found records 
    #
    def Query(self, Model, Arch=None):
        ConditionString = "Model=%s AND Enabled>=0" % Model
        ValueString = "Value1,Value2,Value3,Scope1,ID,StartLine"

        if Arch != None and Arch != 'COMMON':
            ConditionString += " AND (Scope1='%s' OR Scope1='COMMON')" % Arch

        SqlCommand = "SELECT %s FROM %s WHERE %s" % (ValueString, self.Table, ConditionString)
        return self.Exec(SqlCommand)

class PlatformTable(Table):
    _ID_STEP_ = 0.00000001
    _ID_MAX_ = 1
    _COLUMN_ = '''
        ID REAL PRIMARY KEY,
        Model INTEGER NOT NULL,
        Value1 TEXT NOT NULL,
        Value2 TEXT,
        Value3 TEXT,
        Scope1 TEXT,
        Scope2 TEXT,
        BelongsToItem REAL NOT NULL,
        FromItem REAL NOT NULL,
        StartLine INTEGER NOT NULL,
        StartColumn INTEGER NOT NULL,
        EndLine INTEGER NOT NULL,
        EndColumn INTEGER NOT NULL,
        Enabled INTEGER DEFAULT 0
        '''
    _DUMMY_ = "-1, -1, '====', '====', '====', '====', '====', -1, -1, -1, -1, -1, -1, -1"
    def __init__(self, Cursor, Name='Dsc', IdBase=0, Temporary=False):
        Table.__init__(self, Cursor, Name, IdBase, Temporary)

    ## Insert table
    #
    # Insert a record into table Dsc
    #
    # @param Model:          Model of a Dsc item
    # @param Value1:         Value1 of a Dsc item
    # @param Value2:         Value2 of a Dsc item
    # @param Value3:         Value3 of a Dsc item
    # @param Arch:           Arch of a Dsc item
    # @param BelongsToItem:  The item belongs to which another item
    # @param BelongsToFile:  The item belongs to which dsc file
    # @param StartLine:      StartLine of a Dsc item
    # @param StartColumn:    StartColumn of a Dsc item
    # @param EndLine:        EndLine of a Dsc item
    # @param EndColumn:      EndColumn of a Dsc item
    # @param Enabled:        If this item enabled
    #
    def Insert(self, Model, Value1, Value2, Value3, Scope1='COMMON', Scope2='COMMON', BelongsToItem=-1, 
               FromItem=-1, StartLine=-1, StartColumn=-1, EndLine=-1, EndColumn=-1, Enabled=1):
        (Value1, Value2, Value3, Scope1, Scope2) = ConvertToSqlString((Value1, Value2, Value3, Scope1, Scope2))
        return Table.Insert(
                        self, 
                        Model, 
                        Value1, 
                        Value2, 
                        Value3, 
                        Scope1, 
                        Scope2,
                        BelongsToItem, 
                        FromItem,
                        StartLine, 
                        StartColumn, 
                        EndLine, 
                        EndColumn, 
                        Enabled
                        )

    ## Query table
    #
    # @param Model:  The Model of Record 
    #
    # @retval:       A recordSet of all found records 
    #
    def Query(self, Model, Scope1=None, Scope2=None, BelongsToItem=None, FromItem=None):
        ConditionString = "Model=%s AND Enabled>=0" % Model
        ValueString = "Value1,Value2,Value3,Scope1,Scope2,ID,StartLine"

        if Scope1 != None and Scope1 != 'COMMON':
            ConditionString += " AND (Scope1='%s' OR Scope1='COMMON')" % Scope1
        if Scope2 != None and Scope2 != 'COMMON':
            ConditionString += " AND (Scope2='%s' OR Scope2='COMMON' OR Scope2='DEFAULT')" % Scope2

        if BelongsToItem != None:
            ConditionString += " AND BelongsToItem=%s" % BelongsToItem
        else:
            ConditionString += " AND BelongsToItem<0"

        if FromItem != None:
            ConditionString += " AND FromItem=%s" % FromItem

        SqlCommand = "SELECT %s FROM %s WHERE %s" % (ValueString, self.Table, ConditionString)
        #print SqlCommand
        return self.Exec(SqlCommand)


