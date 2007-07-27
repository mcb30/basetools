# Copyright (c) 2007, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.    The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.

#
# This file is used to define each component of the build database
#

#
# Import Modules
#
import os, string, copy, pdb
import EdkLogger
import DataType
from EdkIIWorkspace import *
from TargetTxtClassObject import *
from ToolDefClassObject import *
from InfClassObject import *
from DecClassObject import *
from DscClassObject import *
from String import *
from ClassObjects.CommonClassObject import *
from FdfParser import *
from BuildToolError import *
from Region import *

class ModuleSourceFilesClassObject(object):
    def __init__(self, SourceFile = '', PcdFeatureFlag = '', TagName = '', ToolCode = '', ToolChainFamily = '', String = ''):
        self.SourceFile         = SourceFile
        self.TagName            = TagName
        self.ToolCode           = ToolCode
        self.ToolChainFamily    = ToolChainFamily
        self.String             = String
        self.PcdFeatureFlag     = PcdFeatureFlag
    
    def __str__(self):
        return self.SourceFile
    
    def __repr__(self):
        rtn = self.SourceFile + DataType.TAB_VALUE_SPLIT + \
              self.PcdFeatureFlag + DataType.TAB_VALUE_SPLIT + \
              self.ToolChainFamily +  DataType.TAB_VALUE_SPLIT + \
              self.TagName + DataType.TAB_VALUE_SPLIT + \
              self.ToolCode + DataType.TAB_VALUE_SPLIT + \
              self.String
        return rtn

class ModuleBinaryFilesClassObject(object):
    def __init__(self, BinaryFile = '', FileType = '', Target = '', PcdFeatureFlag = ''):
        self.BinaryFile = BinaryFile
        self.FileType =FileType
        self.Target = Target
        self.PcdFeatureFlag = PcdFeatureFlag
    
    def __str__(self):
        rtn = self.BinaryFile + DataType.TAB_VALUE_SPLIT + \
              self.FileType + DataType.TAB_VALUE_SPLIT + \
              self.Target +  DataType.TAB_VALUE_SPLIT + \
              self.PcdFeatureFlag
        return rtn
        
class PcdClassObject(object):
    def __init__(self, Name = None, Guid = None, Type = None, DatumType = None, Value = None, Token = None, MaxDatumSize = None, SkuInfoList = []):
        self.TokenCName = Name
        self.TokenSpaceGuidCName = Guid
        self.Type = Type
        self.DatumType = DatumType
        self.DefaultValue = Value
        self.TokenValue = Token
        self.MaxDatumSize = MaxDatumSize
        self.SkuInfoList = SkuInfoList
        self.Phase = "DXE"
        
    def __str__(self):
        rtn = str(self.TokenCName) + DataType.TAB_VALUE_SPLIT + \
              str(self.TokenSpaceGuidCName) + DataType.TAB_VALUE_SPLIT + \
              str(self.Type) + DataType.TAB_VALUE_SPLIT + \
              str(self.DatumType) + DataType.TAB_VALUE_SPLIT + \
              str(self.DefaultValue) + DataType.TAB_VALUE_SPLIT + \
              str(self.TokenValue) + DataType.TAB_VALUE_SPLIT + \
              str(self.MaxDatumSize) + DataType.TAB_VALUE_SPLIT
        for Item in self.SkuInfoList:
            rtn = rtn + str(Item)
        return rtn

    def __eq__(self, other):
        return other != None and self.TokenCName == other.TokenCName and self.TokenSpaceGuidCName == other.TokenSpaceGuidCName

    def __hash__(self):
        return hash((self.TokenCName, self.TokenSpaceGuidCName))

class LibraryClassObject(object):
    def __init__(self, Name = None, Type = None):
        self.LibraryClass = Name
        self.SupModList = []
        if Type != None:
            self.SupModList = CleanString(Type).split(DataType.TAB_SPACE_SPLIT)
        
class ModuleBuildClassObject(object):
    def __init__(self):
        self.DescFilePath            = ''
        self.BaseName                = ''
        self.ModuleType              = ''
        self.Guid                    = ''
        self.Version                 = ''
        self.PcdIsDriver             = ''
        self.BinaryModule            = ''
        self.CustomMakefile          = {}
        self.Specification           = {}
        self.LibraryClass            = None      # LibraryClassObject
        self.ModuleEntryPointList    = []
        self.ModuleUnloadImageList   = []
        self.ConstructorList         = []
        self.DestructorList          = []
        
        self.Binaries                = []        #[ ModuleBinaryClassObject, ...]
        self.Sources                 = []        #[ ModuleSourceFilesClassObject, ... ]
        self.LibraryClasses          = {}        #{ [LibraryClassName, ModuleType] : LibraryClassInfFile }
        self.Protocols               = []        #[ ProtocolName, ... ]
        self.Ppis                    = []        #[ PpiName, ... ]
        self.Guids                   = []        #[ GuidName, ... ]
        self.Includes                = []        #[ IncludePath, ... ]
        self.Packages                = []        #[ DecFileName, ... ]
        self.Pcds                    = {}        #{ [(PcdCName, PcdGuidCName)] : PcdClassObject}
        self.BuildOptions            = {}        #{ [BuildOptionKey] : BuildOptionValue}
        self.Depex                   = ''

    def __str__(self):
        return self.DescFilePath

    def __eq__(self, other):
        return self.DescFilePath == str(other)

    def __hash__(self):
        return hash(self.DescFilePath)

class PackageBuildClassObject(object):
    def __init__(self):
        self.DescFilePath            = ''
        self.PackageName             = ''
        self.Guid                    = ''
        self.Version                 = ''
        
        self.Protocols               = {}       #{ [ProtocolName] : Protocol Guid, ... }
        self.Ppis                    = {}       #{ [PpiName] : Ppi Guid, ... }
        self.Guids                   = {}       #{ [GuidName] : Guid, ... }
        self.Includes                = []       #[ IncludePath, ... ]        
        self.LibraryClasses          = {}       #{ [LibraryClassName] : LibraryClassInfFile }
        self.Pcds                    = {}       #{ [(PcdCName, PcdGuidCName)] : PcdClassObject}
        
    def __str__(self):
        return self.DescFilePath

    def __eq__(self, other):
        return self.DescFilePath == str(other)

    def __hash__(self):
        return hash(self.DescFilePath)

class PlatformBuildClassObject(object):
    def __init__(self):
        self.DescFilePath            = ''
        self.PlatformName            = ''
        self.Guid                    = ''
        self.Version                 = ''
        self.DscSpecification        = ''
        self.OutputDirectory         = ''
        self.FlashDefinition         = ''
        self.BuildNumber             = ''
        self.MakefileName            = ''
                
        self.SkuIds                  = {}       #{ 'SkuName' : SkuId, '!include' : includefilename, ...}
        self.Modules                 = []       #[ InfFileName, ... ]
        self.Libraries               = []       #[ InfFileName, ... ]
        self.LibraryClasses          = {}       #{ (LibraryClassName, ModuleType) : LibraryClassInfFile }
        self.Pcds                    = {}       #{ [(PcdCName, PcdGuidCName)] : PcdClassObject }
        self.BuildOptions            = {}       #{ [BuildOptionKey] : BuildOptionValue }    

    def __str__(self):
        return self.DescFilePath

    def __eq__(self, other):
        return self.DescFilePath == str(other)

    def __hash__(self):
        return hash(self.DescFilePath)

class ItemBuild(object):
    def __init__(self, arch, platform = None, package = None, module = None):
        self.Arch                    = arch
        self.PlatformDatabase        = {}        #{ [DscFileName] : PlatformBuildClassObject, ...}
        self.PackageDatabase         = {}        #{ [DecFileName] : PacakgeBuildClassObject, ...}
        self.ModuleDatabase          = {}        #{ [InfFileName] : ModuleBuildClassObject, ...}
        
class WorkspaceBuild(object):
    def __init__(self, ActivePlatform = None):
        self.Workspace               = EdkIIWorkspace()
        self.PrintRunTime            = True
        self.PlatformBuild           = True
        self.TargetTxt               = TargetTxtClassObject()
        self.ToolDef                 = ToolDefClassObject()

        self.SupArchList             = []        #[ 'IA32', 'X64', ...]
        self.BuildTarget             = []        #[ 'RELEASE', 'DEBUG']
        self.SkuId                   = ''
        
        self.InfDatabase             = {}        #{ [InfFileName] : InfClassObject}
        self.DecDatabase             = {}        #{ [DecFileName] : DecClassObject}
        self.DscDatabase             = {}        #{ [DscFileName] : DscClassObject}
        
        self.Build                   = {}
        for key in DataType.ARCH_LIST:
            self.Build[key] = ItemBuild(key)
        
        self.TargetTxt.LoadTargetTxtFile(self.Workspace.WorkspaceFile('Conf/target.txt'))
        self.ToolDef.LoadToolDefFile(self.Workspace.WorkspaceFile('Conf/tools_def.txt'))
        
        if ActivePlatform != None:
            self.TargetTxt.TargetTxtDictionary[DataType.TAB_TAT_DEFINES_ACTIVE_PLATFORM][0] = ActivePlatform
        
        #get active platform
        dscFileName = NormPath(self.TargetTxt.TargetTxtDictionary[DataType.TAB_TAT_DEFINES_ACTIVE_PLATFORM][0])
        file = self.Workspace.WorkspaceFile(dscFileName)
        if os.path.exists(file) and os.path.isfile(file):
            self.DscDatabase[dscFileName] = Dsc(file, True)
        else:
            EdkLogger.verbose('No Active Platform')
            return
        
        #parse platform to get module
        for dsc in self.DscDatabase.keys():
            dscObj = self.DscDatabase[dsc]
            
            #
            # Get global information
            #
            self.SupArchList = dscObj.Defines.DefinesDictionary[TAB_DSC_DEFINES_SUPPORTED_ARCHITECTURES]
            self.BuildTarget = dscObj.Defines.DefinesDictionary[TAB_DSC_DEFINES_BUILD_TARGETS]
            self.SkuId = dscObj.Defines.DefinesDictionary[TAB_DSC_DEFINES_SKUID_IDENTIFIER][0]
            
            #Get all inf
            for key in DataType.ARCH_LIST:
                for index in range(len(dscObj.Contents[key].LibraryClasses)):
                    self.AddToInfDatabase(dscObj.Contents[key].LibraryClasses[index][0].split(DataType.TAB_VALUE_SPLIT, 1)[1])
                for index in range(len(dscObj.Contents[key].Components)):
                    Module = dscObj.Contents[key].Components[index][0]
                    LibList = dscObj.Contents[key].Components[index][1]
                    self.AddToInfDatabase(Module)
                    for indexOfLib in range(len(LibList)):
                        Lib = LibList[indexOfLib]
                        if len(Lib.split(DataType.TAB_VALUE_SPLIT)) == 2:
                            self.AddToInfDatabase(CleanString(Lib.split(DataType.TAB_VALUE_SPLIT)[1]))
                            self.UpdateInfDatabase(Module, CleanString(Lib.split(DataType.TAB_VALUE_SPLIT)[0]), key)
        #End For of Dsc
        
        #parse module to get package
        for inf in self.InfDatabase.keys():
            infObj = self.InfDatabase[inf]
            #Get all dec
            for key in DataType.ARCH_LIST:
                for index in range(len(infObj.Contents[key].Packages)):
                    self.AddToDecDatabase(infObj.Contents[key].Packages[index])
        
        #Build databases
        #Build PlatformDatabase
        for dsc in self.DscDatabase.keys():
            dscObj = self.DscDatabase[dsc]
            
            for key in DataType.ARCH_LIST:
                pb = PlatformBuildClassObject()
                pb.DescFilePath = dsc
                pb.PlatformName = dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_PLATFORM_NAME][0]
                pb.Guid = dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_PLATFORM_GUID][0]
                pb.Version = dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_PLATFORM_VERSION][0]
                pb.DscSpecification = dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_DSC_SPECIFICATION][0]
                pb.OutputDirectory = NormPath(dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_OUTPUT_DIRECTORY][0])
                pb.FlashDefinition = NormPath(dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_FLASH_DEFINITION][0])
                pb.BuildNumber = dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_BUILD_NUMBER][0]
                pb.MakefileName = NormPath(dscObj.Defines.DefinesDictionary[DataType.TAB_DSC_DEFINES_MAKEFILE_NAME][0])
        
                #SkuId
                for index in range(len(dscObj.Contents[key].SkuIds)):
                    SkuInfo = dscObj.Contents[key].SkuIds[index]
                    SkuName = ''
                    SkuId = ''
                    if SkuInfo.find('!include') > -1:
                        SkuName = '!include'
                        SkuId = NormPath(CleanString(SkuInfo[SkuInfo.find('!include') + len('!include'):]))
                    elif len(SkuInfo.split(DataType.TAB_VALUE_SPLIT)) == 2:
                        SkuName = CleanString(SkuInfo.split(DataType.TAB_VALUE_SPLIT)[1])
                        SkuId = CleanString(SkuInfo.split(DataType.TAB_VALUE_SPLIT)[0])
                    else:
                        raise ParseError('Wrong defintion for SkuId: %s' % SkuInfo)
                    pb.SkuIds[SkuName] = SkuId
                
                #Module
                for index in range(len(dscObj.Contents[key].Components)):
                    pb.Modules.append(NormPath(dscObj.Contents[key].Components[index][0]))
                
                #BuildOptions
                for index in range(len(dscObj.Contents[key].BuildOptions)):
                    b = dscObj.Contents[key].BuildOptions[index].split(DataType.TAB_EQUAL_SPLIT, 1)
                    Family = ''
                    ToolChain = ''
                    Flag = ''
                    if b[0].find(':') > -1:
                        Family = CleanString(b[0][ : b[0].find(':')])
                        ToolChain = CleanString(b[0][b[0].find(':') + 1 : ])
                    else:
                        ToolChain = CleanString(b[0])
                    Flag = CleanString(b[1])
                    pb.BuildOptions[(Family, ToolChain)] = Flag
                    
                #LibraryClass
                for index in range(len(dscObj.Contents[key].LibraryClasses)):
                    #['DebugLib|MdePkg/Library/PeiDxeDebugLibReportStatusCode/PeiDxeDebugLibReportStatusCode.inf', 'DXE_CORE']
                    list = dscObj.Contents[key].LibraryClasses[index][0].split(DataType.TAB_VALUE_SPLIT, 1)
                    type = dscObj.Contents[key].LibraryClasses[index][1]
                    pb.LibraryClasses[(list[0], type)] = NormPath(list[1])

                #Pcds
                for index in range(len(dscObj.Contents[key].PcdsFixedAtBuild)):
                    pcd = dscObj.Contents[key].PcdsFixedAtBuild[index].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_FIXED_AT_BUILD, None, pcd[2], None, pcd[3])
                for index in range(len(dscObj.Contents[key].PcdsPatchableInModule)):
                    pcd = dscObj.Contents[key].PcdsPatchableInModule[index].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_PATCHABLE_IN_MODULE, None, pcd[2], None, pcd[3])
                for index in range(len(dscObj.Contents[key].PcdsFeatureFlag)):
                    pcd = dscObj.Contents[key].PcdsFeatureFlag[index].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)                    
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_FEATURE_FLAG, None, pcd[2], None, pcd[3])
                #
                # PcdsDynamic
                #
                for index in range(len(dscObj.Contents[key].PcdsDynamicDefault)):
                    pcd = dscObj.Contents[key].PcdsDynamicDefault[index][0].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    SkuName = dscObj.Contents[key].PcdsDynamicDefault[index][1]
                    SkuInfoList = []
                    if SkuName == None:
                        SkuName = 'DEFAULT'
                    SkuNameList = map(lambda l: l.strip(), SkuName.split(DataType.TAB_VALUE_SPLIT))
                    for Item in SkuNameList:
                        SkuInfo = SkuInfoClassObject()
                        SkuInfo.SkuId = pb.SkuIds[Item]
                        SkuInfo.DefaultValue = pcd[2]
                        SkuInfoList.append(SkuInfo)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_DEFAULT, None, None, None, pcd[3], SkuInfoList)
                for index in range(len(dscObj.Contents[key].PcdsDynamicVpd)):
                    pcd = dscObj.Contents[key].PcdsDynamicVpd[index][0].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    SkuId = dscObj.Contents[key].PcdsDynamicVpd[index][1]
                    SkuInfoList = []
                    if SkuId == None:
                        SkuId = 'DEFAULT'
                    SkuIdList = map(lambda l: l.strip(), SkuId.split(DataType.TAB_VALUE_SPLIT))
                    for Item in SkuIdList:
                        SkuInfo = SkuInfoClassObject()
                        SkuInfo.SkuId = Item
                        SkuInfo.VpdOffset = pcd[2]
                        SkuInfoList.append(SkuInfo)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_VPD, None, None, None, pcd[3], SkuInfoList)
                for index in range(len(dscObj.Contents[key].PcdsDynamicHii)):
                    pcd = dscObj.Contents[key].PcdsDynamicHii[index][0].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    SkuId = dscObj.Contents[key].PcdsDynamicHii[index][1]
                    SkuInfoList = []
                    if SkuId == None:
                        SkuId = 'DEFAULT'
                    SkuIdList = map(lambda l: l.strip(), SkuId.split(DataType.TAB_VALUE_SPLIT))
                    for Item in SkuIdList:
                        SkuInfo = SkuInfoClassObject()
                        SkuInfo.SkuId = Item
                        SkuInfo.VariableName = pcd[2]
                        SkuInfo.VariableGuid = pcd[3]
                        SkuInfo.VariableOffset = pcd[4]
                        SkuInfo.HiiDefaultValue = pcd[5]                                                
                        SkuInfoList.append(SkuInfo)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_HII, None, None, None, pcd[6], SkuInfoList)
                #
                # PcdsDynamicEx
                #
                for index in range(len(dscObj.Contents[key].PcdsDynamicExDefault)):
                    pcd = dscObj.Contents[key].PcdsDynamicExDefault[index][0].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    SkuId = dscObj.Contents[key].PcdsDynamicExDefault[index][1]
                    SkuInfoList = []
                    if SkuId == None:
                        SkuId = 'DEFAULT'
                    SkuIdList = map(lambda l: l.strip(), SkuId.split(DataType.TAB_VALUE_SPLIT))
                    for Item in SkuIdList:
                        SkuInfo = SkuInfoClassObject()
                        SkuInfo.SkuId = Item
                        SkuInfo.DefaultValue = pcd[2]
                        SkuInfoList.append(SkuInfo)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_EX_DEFAULT, None, None, None, pcd[3], SkuInfoList)
                for index in range(len(dscObj.Contents[key].PcdsDynamicExVpd)):
                    pcd = dscObj.Contents[key].PcdsDynamicExVpd[index][0].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    SkuId = dscObj.Contents[key].PcdsDynamicExVpd[index][1]
                    SkuInfoList = []
                    if SkuId == None:
                        SkuId = 'DEFAULT'
                    SkuIdList = map(lambda l: l.strip(), SkuId.split(DataType.TAB_VALUE_SPLIT))
                    for Item in SkuIdList:
                        SkuInfo = SkuInfoClassObject()
                        SkuInfo.SkuId = Item
                        SkuInfo.VpdOffset = pcd[2]
                        SkuInfoList.append(SkuInfo)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_EX_VPD, None, None, None, pcd[3], SkuInfoList)
                for index in range(len(dscObj.Contents[key].PcdsDynamicExHii)):
                    pcd = dscObj.Contents[key].PcdsDynamicExHii[index][0].split(DataType.TAB_VALUE_SPLIT)
                    pcd.append(None)
                    SkuId = dscObj.Contents[key].PcdsDynamicExHii[index][1]
                    SkuInfoList = []
                    if SkuId == None:
                        SkuId = 'DEFAULT'
                    SkuIdList = map(lambda l: l.strip(), SkuId.split(DataType.TAB_VALUE_SPLIT))
                    for Item in SkuIdList:
                        SkuInfo = SkuInfoClassObject()
                        SkuInfo.SkuId = Item
                        SkuInfo.VariableName = pcd[2]
                        SkuInfo.VariableGuid = pcd[3]
                        SkuInfo.VariableOffset = pcd[4]
                        SkuInfo.HiiDefaultValue = pcd[5]                                                
                        SkuInfoList.append(SkuInfo)
                    pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_EX_HII, None, None, None, pcd[6], SkuInfoList)
              
                self.Build[key].PlatformDatabase[dsc] = pb
                pb = None    
            #End of Arch List Go Through    
                
        #End of Dsc Go Through
        
        #End of build PlatformDatabase
        
        #Build PackageDatabase
        for dec in self.DecDatabase.keys():
            decObj = self.DecDatabase[dec]

            for key in DataType.ARCH_LIST:
                pb = PackageBuildClassObject()
                #Defines
                pb.DescFilePath = dec
                pb.PackageName = decObj.Defines.DefinesDictionary[TAB_DEC_DEFINES_PACKAGE_NAME][0]
                pb.Guid = decObj.Defines.DefinesDictionary[TAB_DEC_DEFINES_PACKAGE_GUID][0]
                pb.Version = decObj.Defines.DefinesDictionary[TAB_DEC_DEFINES_PACKAGE_VERSION][0]
                
                #Protocols
                for index in range(len(decObj.Contents[key].Protocols)):
                    list = decObj.Contents[key].Protocols[index].split(DataType.TAB_EQUAL_SPLIT)
                    pb.Protocols[CleanString(list[0])] = CleanString(list[1])

                #Ppis
                for index in range(len(decObj.Contents[key].Ppis)):
                    list = decObj.Contents[key].Ppis[index].split(DataType.TAB_EQUAL_SPLIT)
                    pb.Ppis[CleanString(list[0])] = CleanString(list[1])            

                #Guids
                for index in range(len(decObj.Contents[key].Guids)):
                    list = decObj.Contents[key].Guids[index].split(DataType.TAB_EQUAL_SPLIT)
                    pb.Guids[CleanString(list[0])] = CleanString(list[1])        
                
                #Includes
                for index in range(len(decObj.Contents[key].Includes)):
                    pb.Includes.append(NormPath(decObj.Contents[key].Includes[index]))
            
                #LibraryClasses
                for index in range(len(decObj.Contents[key].LibraryClasses)):
                    list = decObj.Contents[key].LibraryClasses[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.LibraryClasses[CleanString(list[0])] = NormPath(CleanString(list[1]))
                                                
                #Pcds
                for index in range(len(decObj.Contents[key].PcdsFixedAtBuild)):
                    pcd = decObj.Contents[key].PcdsFixedAtBuild[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[2])] = PcdClassObject(pcd[0], pcd[2], DataType.TAB_PCDS_FIXED_AT_BUILD, pcd[3], pcd[4], pcd[1], None)
                for index in range(len(decObj.Contents[key].PcdsPatchableInModule)):
                    pcd = decObj.Contents[key].PcdsPatchableInModule[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[2])] = PcdClassObject(pcd[0], pcd[2], DataType.TAB_PCDS_PATCHABLE_IN_MODULE, pcd[3], pcd[4], pcd[1], None)
                for index in range(len(decObj.Contents[key].PcdsFeatureFlag)):
                    pcd = decObj.Contents[key].PcdsFeatureFlag[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[2])] = PcdClassObject(pcd[0], pcd[2], DataType.TAB_PCDS_FEATURE_FLAG, pcd[3], pcd[4], pcd[1], None)
                for index in range(len(decObj.Contents[key].PcdsDynamic)):
                    pcd = decObj.Contents[key].PcdsDynamic[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[2])] = PcdClassObject(pcd[0], pcd[2], DataType.TAB_PCDS_DYNAMIC, pcd[3], pcd[4], pcd[1], None)
                for index in range(len(decObj.Contents[key].PcdsDynamicEx)):
                    pcd = decObj.Contents[key].PcdsDynamicEx[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[2])] = PcdClassObject(pcd[0], pcd[2], DataType.TAB_PCDS_DYNAMIC_EX, pcd[3], pcd[4], pcd[1], None)
            
                #Add to database
                self.Build[key].PackageDatabase[dec] = pb
                pb = None    
            #End of Arch List Go Through
        
        #End of Dec Go Through    
        
        #End of build PackageDatabase
    
        #Build ModuleDatabase
        for inf in self.InfDatabase.keys():
            infObj = self.InfDatabase[inf]
            
            for key in DataType.ARCH_LIST:
                #Defines
                pb = ModuleBuildClassObject()
                pb.DescFilePath = inf
                pb.BaseName = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_BASE_NAME][0]
                pb.Guid = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_FILE_GUID][0]
                pb.Version = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_VERSION_STRING][0]
                pb.ModuleType = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_MODULE_TYPE][0]
                pb.PcdIsDriver = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_PCD_IS_DRIVER][0]
                pb.BinaryModule = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_BINARY_MODULE][0]
                
                for Index in range(len(infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_CUSTOM_MAKEFILE])):
                    Makefile = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_CUSTOM_MAKEFILE][Index]
                    if Makefile != '':
                        MakefileList = Makefile.split(DataType.TAB_VALUE_SPLIT)
                        if len(MakefileList) == 2:
                            pb.CustomMakefile[CleanString(MakefileList[0])] = CleanString(MakefileList[1])
                        else:
                            raise ParseError('Wrong custom makefile defined in file ' + inf + ', correct format is CUSTOM_MAKEFILE = Family|Filename')
                
                if infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_EDK_RELEASE_VERSION][0] != '':
                    pb.Specification[TAB_INF_DEFINES_EDK_RELEASE_VERSION] = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_EDK_RELEASE_VERSION][0]
                if infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_EFI_SPECIFICATION_VERSION][0] != '':
                    pb.Specification[TAB_INF_DEFINES_EFI_SPECIFICATION_VERSION] = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_EFI_SPECIFICATION_VERSION][0]                
                
                LibraryClass = infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_LIBRARY_CLASS][0]
                if LibraryClass != '':
                    l = LibraryClass.split(DataType.TAB_VALUE_SPLIT, 1)
                    if len(l) == 1:
                        pb.LibraryClass = LibraryClassObject(l[0], DataType.SUP_MODULE_LIST_STRING)
                    else:
                        pb.LibraryClass = LibraryClassObject(l[0], l[1])

                pb.ModuleEntryPointList.extend(infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_ENTRY_POINT])
                pb.ModuleUnloadImageList.extend(infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_UNLOAD_IMAGE])
                pb.ConstructorList.extend(infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_CONSTRUCTOR])
                pb.DestructorList.extend(infObj.Defines.DefinesDictionary[TAB_INF_DEFINES_DESTRUCTOR])

                #Binaries
                for index in range(len(infObj.Contents[key].Binaries)):
                    BinaryFile = infObj.Contents[key].Binaries[index].split(DataType.TAB_VALUE_SPLIT)
                    BinaryFile.append('')
                    FileType = BinaryFile[0].strip()
                    Target = BinaryFile[1].strip()
                    FileName = NormPath(BinaryFile[2].strip())
                    PcdFeatureFlag = BinaryFile[3].strip()
                    pb.Binaries.append(ModuleBinaryFilesClassObject(FileName, FileType, Target, PcdFeatureFlag))
                    
                #Sources
                for index in range(len(infObj.Contents[key].Sources)):
                    SourceFile = infObj.Contents[key].Sources[index].split(DataType.TAB_VALUE_SPLIT)
                    if len(SourceFile) == 6:
                        FileName = NormPath(SourceFile[0].strip())
                        PcdFeatureFlag = SourceFile[1].strip()
                        TagName = SourceFile[3].strip()
                        ToolCode = SourceFile[4].strip()
                        ToolChainFamily = SourceFile[2].strip()
                        String = SourceFile[5].strip()
                        pb.Sources.append(ModuleSourceFilesClassObject(FileName, PcdFeatureFlag, TagName, ToolCode, ToolChainFamily, String))
                    elif len(SourceFile) == 1:
                        pb.Sources.append(ModuleSourceFilesClassObject(NormPath(infObj.Contents[key].Sources[index])))
                    else:
                        raise ParseError("Inconsistent '|' value defined in SourceFiles." + key + " section in file " + inf)

                #Protocols
                for index in range(len(infObj.Contents[key].Protocols)):
                    pb.Protocols.append(infObj.Contents[key].Protocols[index])
            
                #Ppis
                for index in range(len(infObj.Contents[key].Ppis)):
                    pb.Ppis.append(infObj.Contents[key].Ppis[index])
                                
                #Guids
                for index in range(len(infObj.Contents[key].Guids)):
                    pb.Guids.append(infObj.Contents[key].Guids[index])
            
                #Includes
                for index in range(len(infObj.Contents[key].Includes)):
                    pb.Includes.append(NormPath(infObj.Contents[key].Includes[index]))
            
                #Packages
                for index in range(len(infObj.Contents[key].Packages)):
                    pb.Packages.append(NormPath(infObj.Contents[key].Packages[index]))
                    
                #BuildOptions
                for index in range(len(infObj.Contents[key].BuildOptions)):
                    b = infObj.Contents[key].BuildOptions[index].split(DataType.TAB_EQUAL_SPLIT, 1)
                    Family = ''
                    ToolChain = ''
                    Flag = ''
                    if b[0].find(':') > -1:
                        Family = CleanString(b[0][ : b[0].find(':')])
                        ToolChain = CleanString(b[0][b[0].find(':') + 1 : ])
                    else:
                        ToolChain = CleanString(b[0])
                    Flag = CleanString(b[1])
                    pb.BuildOptions[(Family, ToolChain)] = Flag
                self.FindBuildOptions(key, inf, pb.BuildOptions)
                
                #Depex
                pb.Depex = ' '.join(infObj.Contents[key].Depex)
                
                #LibraryClasses
                for index in range(len(infObj.Contents[key].LibraryClasses)):
                    #Get LibraryClass name and default instance if existing
                    list = infObj.Contents[key].LibraryClasses[index].split(DataType.TAB_VALUE_SPLIT)
                    if len(list) < 2:
                        v = ''
                    else:
                        v = list[1]
                    
                    if pb.LibraryClass != None:
                        #For Library
                        for type in pb.LibraryClass.SupModList:
                            instance = self.FindLibraryClassInstanceOfLibrary(CleanString(list[0]), key, type)
                            if instance != None:
                                v = instance
                                pb.LibraryClasses[(CleanString(list[0]), type)] = NormPath(CleanString(v))
                    else:
                        #For Module                        
                        instance = self.FindLibraryClassInstanceOfModule(CleanString(list[0]), key, pb.ModuleType, inf) 
                        if instance != None:
                            v = instance
                            pb.LibraryClasses[(CleanString(list[0]), pb.ModuleType)] = NormPath(CleanString(v))

                #Pcds
                for index in range(len(infObj.Contents[key].PcdsFixedAtBuild)):
                    pcd = infObj.Contents[key].PcdsFixedAtBuild[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[1])] = self.FindPcd(key, pcd[0], pcd[1], DataType.TAB_PCDS_FIXED_AT_BUILD)
                for index in range(len(infObj.Contents[key].PcdsPatchableInModule)):
                    pcd = infObj.Contents[key].PcdsPatchableInModule[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[1])] = self.FindPcd(key, pcd[0], pcd[1], DataType.TAB_PCDS_PATCHABLE_IN_MODULE)
                    #pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_PATCHABLE_IN_MODULE, None, None, None, None)                    
                for index in range(len(infObj.Contents[key].PcdsFeatureFlag)):
                    pcd = infObj.Contents[key].PcdsFeatureFlag[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[1])] = self.FindPcd(key, pcd[0], pcd[1], DataType.TAB_PCDS_FEATURE_FLAG)
                    #pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_FEATURE_FLAG, None, None, None, None)                    
                for index in range(len(infObj.Contents[key].PcdsDynamic)):
                    pcd = infObj.Contents[key].PcdsDynamic[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[1])] = self.FindPcd(key, pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC)
                    #pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC, None, None, None, None)
                for index in range(len(infObj.Contents[key].PcdsDynamicEx)):
                    pcd = infObj.Contents[key].PcdsDynamicEx[index].split(DataType.TAB_VALUE_SPLIT)
                    pb.Pcds[(pcd[0], pcd[1])] = self.FindPcd(key, pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_EX)
                    #pb.Pcds[(pcd[0], pcd[1])] = PcdClassObject(pcd[0], pcd[1], DataType.TAB_PCDS_DYNAMIC_EX, None, None, None, None)
                                        
                #Add to database
                self.Build[key].ModuleDatabase[inf] = pb
                pb = None    
            #End of Arch List Go Through
        
        #End of Inf Go Through
        
        #End of build ModuleDatabase    

        for arch in self.Build:
            PlatformDatabase = self.Build[arch].PlatformDatabase
            for dsc in PlatformDatabase:
                platform = PlatformDatabase[dsc]
                for inf in platform.Modules:
                    module = self.Build[arch].ModuleDatabase[inf]
                    stack = [module]
                    while len(stack) > 0:
                        m = self.Build[arch].ModuleDatabase[stack.pop()]
                        if m != module:
                            platform.Libraries.append(m)
                        for lib in m.LibraryClasses.values():
                            if lib not in platform.Libraries:
                                platform.Libraries.append(lib)
                                stack.append(lib)
    #End of self.Init
    
    def UpdateInfDatabase(self, infFileName, LibraryClass, Arch):
        infFileName = NormPath(infFileName)
        LibList = self.InfDatabase[infFileName].Contents[Arch].LibraryClasses
        NotFound = True
        for Item in LibList:
            LibName = Item.split(DataType.TAB_VALUE_SPLIT)[0].strip()
            if LibName == LibraryClass:
                return
        
        if NotFound:
            self.InfDatabase[infFileName].Contents[Arch].LibraryClasses.extend([LibraryClass])
    
    def AddToInfDatabase(self, infFileName):
        infFileName = NormPath(infFileName)
        file = self.Workspace.WorkspaceFile(infFileName)
        if os.path.exists(file) and os.path.isfile(file):
            if infFileName not in self.InfDatabase:
                self.InfDatabase[infFileName] = Inf(file, True)
                
    def AddToDecDatabase(self, decFileName):
        decFileName = NormPath(decFileName)
        file = self.Workspace.WorkspaceFile(decFileName)
        if os.path.exists(file) and os.path.isfile(file):
            if decFileName not in self.DecDatabase:
                self.DecDatabase[decFileName] = Dec(file, True)
                
    def FindLibraryClassInstanceOfModule(self, lib, arch, moduleType, moduleName):
        for dsc in self.DscDatabase.keys():
            #First find if exist in <LibraryClass> of <Components> from dsc file            
            dscObj = self.DscDatabase[dsc]
            for index in range(len(dscObj.Contents[arch].Components)):
                if NormPath(dscObj.Contents[arch].Components[index][0]) == moduleName and len(dscObj.Contents[arch].Components[index][1]) > 0:
                    #Search each library class
                    LibList = dscObj.Contents[arch].Components[index][1]
                    for indexOfLib in range(len(LibList)):
                        if LibList[indexOfLib].split(DataType.TAB_VALUE_SPLIT)[0].strip() == lib:
                            return LibList[indexOfLib].split(DataType.TAB_VALUE_SPLIT)[1].strip()
            
            #Second find if exist in <LibraryClass> of <LibraryClasses> from dsc file            
            if (lib, moduleType) in self.Build[arch].PlatformDatabase[dsc].LibraryClasses:
                return self.Build[arch].PlatformDatabase[dsc].LibraryClasses[(lib, moduleType)]
            elif (lib, None) in self.Build[arch].PlatformDatabase[dsc].LibraryClasses:
                return self.Build[arch].PlatformDatabase[dsc].LibraryClasses[(lib, None)]
            
    def FindLibraryClassInstanceOfLibrary(self, lib, arch, type):
        for dsc in self.DscDatabase.keys():
            dscObj = self.DscDatabase[dsc]
            if (lib, type) in self.Build[arch].PlatformDatabase[dsc].LibraryClasses:
                return self.Build[arch].PlatformDatabase[dsc].LibraryClasses[(lib, type)]
            elif (lib, None) in self.Build[arch].PlatformDatabase[dsc].LibraryClasses:
                return self.Build[arch].PlatformDatabase[dsc].LibraryClasses[(lib, None)]
            
    def FindBuildOptions(self, arch, moduleName, BuildOptions):
        for dsc in self.DscDatabase.keys():
            #First find if exist in <BuildOptions> of <Components> from dsc file
            dscObj = self.DscDatabase[dsc]
            for index in range(len(dscObj.Contents[arch].Components)):
                if NormPath(dscObj.Contents[arch].Components[index][0]) == moduleName and len(dscObj.Contents[arch].Components[index][2]) > 0:
                    list = dscObj.Contents[arch].Components[index][2]
                    for l in list:
                        b = l.split(DataType.TAB_EQUAL_SPLIT, 1)
                        Family = ''
                        ToolChain = ''
                        Flag = ''
                        if b[0].find(':') > -1:
                            Family = CleanString(b[0][ : b[0].find(':')])
                            ToolChain = CleanString(b[0][b[0].find(':') + 1 : ])
                        else:
                            ToolChain = CleanString(b[0])
                        Flag = CleanString(b[1])
                        BuildOptions[(Family, ToolChain)] = Flag
                        
    def FindPcd(self, arch, CName, GuidCName, Type):
        DatumType = ''
        DefaultValue = ''
        TokenValue = ''
        MaxDatumSize = ''
        SkuInfoList = None
        for dsc in self.Build[arch].PlatformDatabase.keys():
            platform = self.Build[arch].PlatformDatabase[dsc]
            pcds = platform.Pcds
            if (CName, GuidCName) in pcds:
                Type = pcds[(CName, GuidCName)].Type
                DatumType = pcds[(CName, GuidCName)].DatumType
                DefaultValue = pcds[(CName, GuidCName)].DefaultValue
                TokenValue = pcds[(CName, GuidCName)].TokenValue
                MaxDatumSize = pcds[(CName, GuidCName)].MaxDatumSize
                SkuInfoList =  pcds[(CName, GuidCName)].SkuInfoList
                break

        for dec in self.Build[arch].PackageDatabase.keys():
            package = self.Build[arch].PackageDatabase[dec]
            pcds = package.Pcds
            if (CName, GuidCName) in pcds:
                DatumType = pcds[(CName, GuidCName)].DatumType
                #DefaultValue = pcds[(CName, GuidCName)].DefaultValue
                TokenValue = pcds[(CName, GuidCName)].TokenValue
                #MaxDatumSize = pcds[(CName, GuidCName)].MaxDatumSize
                break
        
        return PcdClassObject(CName, GuidCName, Type, DatumType, DefaultValue, TokenValue, MaxDatumSize, SkuInfoList)
    
    def ReloadPcd(self, FvDict):
        pass
                
# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
if __name__ == '__main__':

    # Nothing to do here. Could do some unit tests.
    ewb = WorkspaceBuild()
    #printDict(ewb.TargetTxt.TargetTxtDictionary)
    #printDict(ewb.ToolDef.ToolsDefTxtDictionary)
#    print ewb.DscDatabase
#    print ewb.InfDatabase
#    print ewb.DecDatabase
    print 'SupArchList', ewb.SupArchList
    print 'BuildTarget', ewb.BuildTarget
    print 'SkuId', ewb.SkuId
    
    #
    for arch in DataType.ARCH_LIST:
        print arch
        print 'Platform'
        for platform in ewb.Build[arch].PlatformDatabase.keys():
            p = ewb.Build[arch].PlatformDatabase[platform]
            print 'DescFilePath = ', p.DescFilePath     
            print 'PlatformName = ', p.PlatformName     
            print 'Guid = ', p.Guid                     
            print 'Version = ', p.Version
            print 'OutputDirectory = ', p.OutputDirectory                
            print 'FlashDefinition = ', p.FlashDefinition
            print 'SkuIds = ', p.SkuIds
            print 'Modules = ', p.Modules
            print 'LibraryClasses = ', p.LibraryClasses 
            print 'Pcds = ', p.Pcds
            for item in p.Pcds.keys():
                print p.Pcds[item]
            print 'BuildOptions = ', p.BuildOptions
            print ''   
        #End of Platform
    
        print 'package'
        for package in ewb.Build[arch].PackageDatabase.keys():
            p = ewb.Build[arch].PackageDatabase[package]
            print 'DescFilePath = ', p.DescFilePath    
            print 'PackageName = ', p.PackageName     
            print 'Guid = ', p.Guid                    
            print 'Version = ', p.Version             
            print 'Protocols = ', p.Protocols         
            print 'Ppis = ', p.Ppis                    
            print 'Guids = ', p.Guids                 
            print 'Includes = ', p.Includes            
            print 'LibraryClasses = ', p.LibraryClasses
            print 'Pcds = ', p.Pcds
            print ''                    
        #End of Package
        
        print 'module'
        for module in ewb.Build[arch].ModuleDatabase.keys():
            p = ewb.Build[arch].ModuleDatabase[module]
            print 'DescFilePath = ', p.DescFilePath                    
            print 'BaseName = ', p.BaseName                         
            print 'ModuleType = ', p.ModuleType                     
            print 'Guid = ', p.Guid                                 
            print 'Version = ', p.Version
            print 'CustomMakefile = ', p.CustomMakefile
            print 'Specification = ', p.Specification
            print 'PcdIsDriver = ', p.PcdIsDriver
            if p.LibraryClass != None:
                print 'LibraryClass = ', p.LibraryClass.LibraryClass
                print 'SupModList = ', p.LibraryClass.SupModList
            print 'ModuleEntryPointList = ', p.ModuleEntryPointList 
            print 'ModuleUnloadImageList = ', p.ModuleUnloadImageList
            print 'ConstructorList = ', p.ConstructorList            
            print 'DestructorList = ', p.DestructorList             
                                                                     
            print 'Binaries = '
            for item in p.Binaries:
                print str(item)
            print 'Sources = '
            for item in p.Sources:
                print str(item)
            print 'LibraryClasses = ', p.LibraryClasses             
            print 'Protocols = ', p.Protocols                        
            print 'Ppis = ', p.Ppis                                 
            print 'Guids = ', p.Guids                                
            print 'Includes = ', p.Includes                         
            print 'Packages = ', p.Packages                         
            print 'Pcds = ', p.Pcds
            print 'BuildOptions = ', p.BuildOptions
            print 'Depex = ', p.Depex
            print ''
        #End of Module    
            
    #End of Arch List