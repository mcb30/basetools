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
from GenFdsGlobalVariable import GenFdsGlobalVariable
from CommonDataClass.FdfClass import CapsuleClassObject
import os
import subprocess

T_CHAR_LF = '\n'

## create inf file describes what goes into capsule and call GenFv to generate capsule
#
#
class Capsule (CapsuleClassObject) :
    ## The constructor
    #
    #   @param  self        The object pointer
    #
    def __init__(self):
        CapsuleClassObject.__init__(self)
        # For GenFv
        self.BlockSize = None
        # For GenFv
        self.BlockNum = None

    ## Generate capsule
    #
    #   @param  self        The object pointer
    #
    def GenCapsule(self):
        CapInfFile = self.GenCapInf()
        CapInfFile.writelines("[files]" + T_CHAR_LF)

        for CapsuleDataObj in self.CapsuleDataList :
            FileName = CapsuleDataObj.GenCapsuleSubItem()
            CapInfFile.writelines("EFI_FILE_NAME = " + \
                                   FileName      + \
                                   T_CHAR_LF)
        CapInfFile.close()
        #
        # Call GenFv tool to generate capsule
        #
        CapOutputFile = os.path.join(GenFdsGlobalVariable.FvDir, self.UiCapsuleName)
        CapOutputFile = CapOutputFile + '.Cap'
        GenFdsGlobalVariable.GenerateFirmwareVolume(
                                CapOutputFile,
                                [self.CapInfFileName],
                                Capsule=True
                                )
        GenFdsGlobalVariable.SharpCounter = 0

    ## Generate inf file for capsule
    #
    #   @param  self        The object pointer
    #   @retval file        inf file object
    #
    def GenCapInf(self):
        self.CapInfFileName = os.path.join(GenFdsGlobalVariable.FvDir,
                                   self.UiCapsuleName +  "_Cap" + '.inf')
        CapInfFile = open (self.CapInfFileName , 'w+')

        CapInfFile.writelines("[options]" + T_CHAR_LF)

        for Item in self.TokensDict.keys():
            CapInfFile.writelines("EFI_"                    + \
                                  Item                      + \
                                  ' = '                     + \
                                  self.TokensDict.get(Item) + \
                                  T_CHAR_LF)

        return CapInfFile
