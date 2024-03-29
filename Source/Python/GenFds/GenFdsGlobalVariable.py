## @file
# Global variables for GenFds
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
import os
import sys
import subprocess
import struct
import array
from Common import BuildToolError
from Common import EdkLogger
from Common.Misc import SaveFileOnChange

## Global variables
#
#
class GenFdsGlobalVariable:
    FvDir = ''
    OutputDirDict = {}
    BinDir = ''
    # will be FvDir + os.sep + 'Ffs'
    FfsDir = ''
    FdfParser = None
    LibDir = ''
    WorkSpace = None
    WorkSpaceDir = ''
    EdkSourceDir = ''
    OutputDirFromDscDict = {}
    TargetName = ''
    ToolChainTag = ''
    RuleDict = {}
    ArchList = None
    VtfDict = {}
    ActivePlatform = None
    FvAddressFileName = ''
    VerboseMode = False
    DebugLevel = -1
    SharpCounter = 0
    SharpNumberPerLine = 40
    FdfFile = ''
    FdfFileTimeStamp = 0
    FixedLoadAddress = False

    SectionHeader = struct.Struct("3B 1B")

    ## SetDir()
    #
    #   @param  OutputDir           Output directory
    #   @param  FdfParser           FDF contents parser
    #   @param  Workspace           The directory of workspace
    #   @param  ArchList            The Arch list of platform
    #
    def SetDir (OutputDir, FdfParser, WorkSpace, ArchList):
        GenFdsGlobalVariable.VerboseLogger( "GenFdsGlobalVariable.OutputDir :%s" %OutputDir)
#        GenFdsGlobalVariable.OutputDirDict = OutputDir
        GenFdsGlobalVariable.FdfParser = FdfParser
        GenFdsGlobalVariable.WorkSpace = WorkSpace
        GenFdsGlobalVariable.FvDir = os.path.join(GenFdsGlobalVariable.OutputDirDict[ArchList[0]], 'FV')
        if not os.path.exists(GenFdsGlobalVariable.FvDir) :
            os.makedirs(GenFdsGlobalVariable.FvDir)
        GenFdsGlobalVariable.FfsDir = os.path.join(GenFdsGlobalVariable.FvDir, 'Ffs')
        if not os.path.exists(GenFdsGlobalVariable.FfsDir) :
            os.makedirs(GenFdsGlobalVariable.FfsDir)
        if ArchList != None:
            GenFdsGlobalVariable.ArchList = ArchList

        T_CHAR_LF = '\n'
        #
        # Create FV Address inf file
        #
        GenFdsGlobalVariable.FvAddressFileName = os.path.join(GenFdsGlobalVariable.FfsDir, 'FvAddress.inf')
        FvAddressFile = open (GenFdsGlobalVariable.FvAddressFileName, 'w')
        #
        # Add [Options]
        #
        FvAddressFile.writelines("[options]" + T_CHAR_LF)
        BsAddress = '0'
        for Arch in ArchList:
            if GenFdsGlobalVariable.WorkSpace.BuildObject[GenFdsGlobalVariable.ActivePlatform, Arch].BsBaseAddress:
                BsAddress = GenFdsGlobalVariable.WorkSpace.BuildObject[GenFdsGlobalVariable.ActivePlatform, Arch].BsBaseAddress
                break

        FvAddressFile.writelines("EFI_BOOT_DRIVER_BASE_ADDRESS = " + \
                                       BsAddress          + \
                                       T_CHAR_LF)

        RtAddress = '0'
        for Arch in ArchList:
            if GenFdsGlobalVariable.WorkSpace.BuildObject[GenFdsGlobalVariable.ActivePlatform, Arch].RtBaseAddress:
                RtAddress = GenFdsGlobalVariable.WorkSpace.BuildObject[GenFdsGlobalVariable.ActivePlatform, Arch].RtBaseAddress

        FvAddressFile.writelines("EFI_RUNTIME_DRIVER_BASE_ADDRESS = " + \
                                       RtAddress          + \
                                       T_CHAR_LF)

        FvAddressFile.close()

    ## ReplaceWorkspaceMacro()
    #
    #   @param  String           String that may contain macro
    #
    def ReplaceWorkspaceMacro(String):
        Str = String.replace('$(WORKSPACE)', GenFdsGlobalVariable.WorkSpaceDir)
        if os.path.exists(Str):
            if not os.path.isabs(Str):
                Str = os.path.abspath(Str)
        else:
            Str = os.path.join(GenFdsGlobalVariable.WorkSpaceDir, String)
        return os.path.normpath(Str)

    ## Check if the input files are newer than output files
    #
    #   @param  Output          Path of output file
    #   @param  Input           Path list of input files
    #
    #   @retval True            if Output doesn't exist, or any Input is newer
    #   @retval False           if all Input is older than Output
    #
    @staticmethod
    def NeedsUpdate(Output, Input):
        if not os.path.exists(Output):
            return True
        # always update "Output" if no "Input" given
        if Input == None or len(Input) == 0:
            return True

        # if fdf file is changed after the 'Output" is generated, update the 'Output'
        OutputTime = os.path.getmtime(Output)
        if GenFdsGlobalVariable.FdfFileTimeStamp > OutputTime:
            return True

        for F in Input:
            # always update "Output" if any "Input" doesn't exist
            if not os.path.exists(F):
                return True
            # always update "Output" if any "Input" is newer than "Output"
            if os.path.getmtime(F) > OutputTime:
                return True
        return False

    @staticmethod
    def GenerateSection(Output, Input, Type=None, CompressionType=None, Guid=None,
                        GuidHdrLen=None, GuidAttr=None, Ui=None, Ver=None):
        if not GenFdsGlobalVariable.NeedsUpdate(Output, Input):
            return
        GenFdsGlobalVariable.DebugLogger(EdkLogger.DEBUG_5, "%s needs update because of newer %s" % (Output, Input))

        Cmd = ["GenSec"]
        if Type not in [None, '']:
            Cmd += ["-s", Type]
        if CompressionType not in [None, '']:
            Cmd += ["-c", CompressionType]
        if Guid != None:
            Cmd += ["-g", Guid]
        if GuidHdrLen not in [None, '']:
            Cmd += ["-l", GuidHdrLen]
        if GuidAttr not in [None, '']:
            Cmd += ["-r", GuidAttr]

        if Ui not in [None, '']:
            #Cmd += ["-n", '"' + Ui + '"']
            SectionData = array.array('B', [0,0,0,0])
            SectionData.fromstring(Ui.encode("utf_16_le"))
            SectionData.append(0)
            SectionData.append(0)
            Len = len(SectionData)
            GenFdsGlobalVariable.SectionHeader.pack_into(SectionData, 0, Len & 0xff, (Len >> 8) & 0xff, (Len >> 16) & 0xff, 0x15)
            SaveFileOnChange(Output,  SectionData.tostring())
        elif Ver not in [None, '']:
            #Cmd += ["-j", Ver]
            SectionData = array.array('B', [0,0,0,0])
            SectionData.fromstring(Ver.encode("utf_16_le"))
            SectionData.append(0)
            SectionData.append(0)
            Len = len(SectionData)
            GenFdsGlobalVariable.SectionHeader.pack_into(SectionData, 0, Len & 0xff, (Len >> 8) & 0xff, (Len >> 16) & 0xff, 0x15)
            SaveFileOnChange(Output,  SectionData.tostring())
        else:
            Cmd += ["-o", Output]
            Cmd += Input
            GenFdsGlobalVariable.CallExternalTool(Cmd, "Failed to generate section")

    @staticmethod
    def GenerateFfs(Output, Input, Type, Guid, Fixed=False, CheckSum=False, Align=None,
                    SectionAlign=None):
        if not GenFdsGlobalVariable.NeedsUpdate(Output, Input):
            return
        GenFdsGlobalVariable.DebugLogger(EdkLogger.DEBUG_5, "%s needs update because of newer %s" % (Output, Input))

        Cmd = ["GenFfs", "-t", Type, "-g", Guid]
        if Fixed == True:
            Cmd += ["-x"]
        if CheckSum:
            Cmd += ["-s"]
        if Align not in [None, '']:
            Cmd += ["-a", Align]

        Cmd += ["-o", Output]
        for I in range(0, len(Input)):
            Cmd += ("-i", Input[I])
            if SectionAlign not in [None, '', []] and SectionAlign[I] not in [None, '']:
                Cmd += ("-n", SectionAlign[I])
        GenFdsGlobalVariable.CallExternalTool(Cmd, "Failed to generate FFS")

    @staticmethod
    def GenerateFirmwareVolume(Output, Input, BaseAddress=None, Capsule=False, Dump=False,
                               AddressFile=None, MapFile=None):
        if not GenFdsGlobalVariable.NeedsUpdate(Output, Input):
            return
        GenFdsGlobalVariable.DebugLogger(EdkLogger.DEBUG_5, "%s needs update because of newer %s" % (Output, Input))

        Cmd = ["GenFv"]
        if BaseAddress not in [None, '']:
            Cmd += ["-r", BaseAddress]
        if Capsule:
            Cmd += ["-c"]
        if Dump:
            Cmd += ["-p"]
        if AddressFile not in [None, '']:
            Cmd += ["-a", AddressFile]
        if MapFile not in [None, '']:
            Cmd += ["-m", MapFile]
        Cmd += ["-o", Output]
        for I in Input:
            Cmd += ["-i", I]

        GenFdsGlobalVariable.CallExternalTool(Cmd, "Failed to generate FV")

    @staticmethod
    def GenerateVtf(Output, Input, BaseAddress=None, FvSize=None):
        if not GenFdsGlobalVariable.NeedsUpdate(Output, Input):
            return
        GenFdsGlobalVariable.DebugLogger(EdkLogger.DEBUG_5, "%s needs update because of newer %s" % (Output, Input))

        Cmd = ["GenVtf"]
        if BaseAddress not in [None, ''] and FvSize not in [None, ''] \
            and len(BaseAddress) == len(FvSize):
            for I in range(0, len(BaseAddress)):
                Cmd += ["-r", BaseAddress[i], "-s", FvSize[I]]
        Cmd += ["-o", Output]
        for F in Input:
            Cmd += ["-f", F]

        GenFdsGlobalVariable.CallExternalTool(Cmd, "Failed to generate VTF")

    @staticmethod
    def GenerateFirmwareImage(Output, Input, Type="efi", SubType=None, Zero=False,
                              Strip=False, Replace=False, TimeStamp=None, Join=False,
                              Align=None, Padding=None, Convert=False):
        if not GenFdsGlobalVariable.NeedsUpdate(Output, Input):
            return
        GenFdsGlobalVariable.DebugLogger(EdkLogger.DEBUG_5, "%s needs update because of newer %s" % (Output, Input))

        Cmd = ["GenFw"]
        if Type.lower() == "te":
            Cmd += ["-t"]
        if SubType not in [None, '']:
            Cmd += ["-e", SubType]
        if TimeStamp not in [None, '']:
            Cmd += ["-s", TimeStamp]
        if Align not in [None, '']:
            Cmd += ["-a", Align]
        if Padding not in [None, '']:
            Cmd += ["-p", Padding]
        if Zero:
            Cmd += ["-z"]
        if Strip:
            Cmd += ["-l"]
        if Replace:
            Cmd += ["-r"]
        if Join:
            Cmd += ["-j"]
        if Convert:
            Cmd += ["-m"]
        Cmd += ["-o", Output]
        Cmd += Input

        GenFdsGlobalVariable.CallExternalTool(Cmd, "Failed to generate firmware image")

    @staticmethod
    def GuidTool(Output, Input, ToolPath, Options=''):
        if not GenFdsGlobalVariable.NeedsUpdate(Output, Input):
            return
        GenFdsGlobalVariable.DebugLogger(EdkLogger.DEBUG_5, "%s needs update because of newer %s" % (Output, Input))

        Cmd = [ToolPath, Options]
        Cmd += ["-o", Output]
        Cmd += Input

        GenFdsGlobalVariable.CallExternalTool(Cmd, "Failed to call " + ToolPath)

    def CallExternalTool (cmd, errorMess):

        if type(cmd) not in (tuple, list):
            GenFdsGlobalVariable.ErrorLogger("ToolError!  Invalid parameter type in call to CallExternalTool")

        if GenFdsGlobalVariable.DebugLevel != -1:
            cmd += ('-d', str(GenFdsGlobalVariable.DebugLevel))
            GenFdsGlobalVariable.InfLogger (cmd)

        if GenFdsGlobalVariable.VerboseMode:
            cmd += ('-v',)
            GenFdsGlobalVariable.InfLogger (cmd)
        else:
            sys.stdout.write ('#')
            sys.stdout.flush()
            GenFdsGlobalVariable.SharpCounter = GenFdsGlobalVariable.SharpCounter + 1
            if GenFdsGlobalVariable.SharpCounter % GenFdsGlobalVariable.SharpNumberPerLine == 0:
                sys.stdout.write('\n')

        PopenObject = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr= subprocess.PIPE)
        (out, error) = PopenObject.communicate()

        while PopenObject.returncode == None :
            PopenObject.wait()
        if PopenObject.returncode != 0 or GenFdsGlobalVariable.VerboseMode or GenFdsGlobalVariable.DebugLevel != -1:
            GenFdsGlobalVariable.InfLogger ("Return Value = %d" %PopenObject.returncode)
            GenFdsGlobalVariable.InfLogger (out)
            GenFdsGlobalVariable.InfLogger (error)
            if PopenObject.returncode != 0:
                EdkLogger.error("GenFds", BuildToolError.COMMAND_FAILURE, errorMess)

    def VerboseLogger (msg):
        EdkLogger.verbose(msg)

    def InfLogger (msg):
        EdkLogger.info(msg)

    def ErrorLogger (msg, File = None, Line = None, ExtraData = None):
        EdkLogger.error('GenFds', BuildToolError.GENFDS_ERROR, msg, File, Line, ExtraData)

    def DebugLogger (Level, msg):
        EdkLogger.debug(Level, msg)

    ## ReplaceWorkspaceMacro()
    #
    #   @param  Str           String that may contain macro
    #   @param  MacroDict     Dictionary that contains macro value pair
    #
    def MacroExtend (Str, MacroDict = {}, Arch = 'COMMON'):
        if Str == None :
            return None

        Dict = {'$(WORKSPACE)'   : GenFdsGlobalVariable.WorkSpaceDir,
                '$(EDK_SOURCE)'  : GenFdsGlobalVariable.EdkSourceDir,
#                '$(OUTPUT_DIRECTORY)': GenFdsGlobalVariable.OutputDirFromDsc,
                '$(TARGET)' : GenFdsGlobalVariable.TargetName,
                '$(TOOL_CHAIN_TAG)' : GenFdsGlobalVariable.ToolChainTag
               }
        OutputDir = GenFdsGlobalVariable.OutputDirFromDscDict[GenFdsGlobalVariable.ArchList[0]]
        if Arch != 'COMMON' and Arch in GenFdsGlobalVariable.ArchList:
            OutputDir = GenFdsGlobalVariable.OutputDirFromDscDict[Arch]

        Dict['$(OUTPUT_DIRECTORY)'] = OutputDir

        if MacroDict != None  and len (MacroDict) != 0:
            Dict.update(MacroDict)

        for key in Dict.keys():
            if Str.find(key) >= 0 :
                Str = Str.replace (key, Dict[key])

        if Str.find('$(ARCH)') >= 0:
            if len(GenFdsGlobalVariable.ArchList) == 1:
                Str = Str.replace('$(ARCH)', GenFdsGlobalVariable.ArchList[0])
            else:
                EdkLogger.error("GenFds", GENFDS_ERROR, "No way to determine $(ARCH) for %s" % Str)

        return Str


    SetDir = staticmethod(SetDir)
    ReplaceWorkspaceMacro = staticmethod(ReplaceWorkspaceMacro)
    CallExternalTool = staticmethod(CallExternalTool)
    VerboseLogger = staticmethod(VerboseLogger)
    InfLogger = staticmethod(InfLogger)
    ErrorLogger = staticmethod(ErrorLogger)
    DebugLogger = staticmethod(DebugLogger)
    MacroExtend = staticmethod (MacroExtend)
