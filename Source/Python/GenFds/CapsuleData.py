## @file
# generate capsule
#
#  Copyright (c) 2007, Intel Corporation
#
#  All rights reserved. This program and the accompanying materials
#  are licensed and made available under the terms and conditions of the BSD License
#  which accompanies this distribution.  The full text of the license may be found at
#  http://opensource.org/licenses/bsd-license.php
#
#  THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
#  WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

##
# Import Modules
#
import Ffs
from GenFdsGlobalVariable import GenFdsGlobalVariable
import StringIO

## base class for capsule data
#
#
class CapsuleData:
    ## The constructor
    #
    #   @param  self        The object pointer
    def __init__(self):
        pass
    
    ## generate capsule data
    #
    #   @param  self        The object pointer
    def GenCapsuleSubItem(self):
        pass
        
## FFS class for capsule data
#
#
class CapsuleFfs (CapsuleData):
    ## The constructor
    #
    #   @param  self        The object pointer
    #
    def __init_(self) :
        self.Ffs = None

    ## generate FFS capsule data
    #
    #   @param  self        The object pointer
    #   @retval string      Generated file name
    #
    def GenCapsuleSubItem(self):
        FfsFile = self.Ffs.GenFfs()
        return FfsFile

## FV class for capsule data
#
#
class CapsuleFv (CapsuleData):
    ## The constructor
    #
    #   @param  self        The object pointer
    #
    def __init__(self) :
        self.FvName = None

    ## generate FV capsule data
    #
    #   @param  self        The object pointer
    #   @retval string      Generated file name
    #
    def GenCapsuleSubItem(self):
        if self.FvName.find('.fv') == -1:
            if self.FvName.upper() in GenFdsGlobalVariable.FdfParser.Profile.FvDict.keys():
                FvObj = GenFdsGlobalVariable.FdfParser.Profile.FvDict.get(self.FvName.upper())
                FdBuffer = StringIO.StringIO('')
                FvFile = FvObj.AddToBuffer(FdBuffer)
                return FvFile
            
        else:
            FvFile = GenFdsGlobalVariable.ReplaceWorkspaceMarco(self.FvName)
            return FvFile
