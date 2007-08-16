# Copyright (c) 2007, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.    The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.

#
#This file is used to define each component of INF file
#

import os
import EdkLogger
from CommonDataClass.CommonClass import LibraryClassClass
from CommonDataClass.ModuleClass import *
from String import *
from DataType import *
from Identification import *
from Dictionary import *
from BuildToolError import *

class InfObject(object):
    def __init__(self):
        object.__init__()

class InfDefines(InfObject):
    def __init__(self):
        self.DefinesDictionary = {
            #Required
            TAB_INF_DEFINES_BASE_NAME                               : [''],
            TAB_INF_DEFINES_FILE_GUID                               : [''],
            TAB_INF_DEFINES_MODULE_TYPE                             : [''],
            TAB_INF_DEFINES_EFI_SPECIFICATION_VERSION               : [''],
            TAB_INF_DEFINES_EDK_RELEASE_VERSION                     : [''],
            
            #Optional            
            TAB_INF_DEFINES_INF_VERSION                             : [''],
            TAB_INF_DEFINES_BINARY_MODULE                           : [''],
            TAB_INF_DEFINES_LIBRARY_CLASS                           : [''],
            TAB_INF_DEFINES_COMPONENT_TYPE                          : [''],
            TAB_INF_DEFINES_MAKEFILE_NAME                           : [''],
            TAB_INF_DEFINES_BUILD_NUMBER                            : [''],
            TAB_INF_DEFINES_BUILD_TYPE                              : [''],
            TAB_INF_DEFINES_FFS_EXT                                 : [''],
            TAB_INF_DEFINES_FV_EXT                                  : [''],
            TAB_INF_DEFINES_SOURCE_FV                               : [''],
            TAB_INF_DEFINES_VERSION_NUMBER                          : [''],
            TAB_INF_DEFINES_VERSION_STRING                          : [''],
            TAB_INF_DEFINES_PCD_IS_DRIVER                           : [''],
            TAB_INF_DEFINES_TIANO_R8_FLASHMAP_H                     : [''],
            TAB_INF_DEFINES_ENTRY_POINT                             : [''],
            TAB_INF_DEFINES_UNLOAD_IMAGE                            : [''],
            TAB_INF_DEFINES_CONSTRUCTOR                             : [''],
            TAB_INF_DEFINES_DESTRUCTOR                              : [''],
            TAB_INF_DEFINES_DEFINE                                  : [''],
            TAB_INF_DEFINES_SPEC                                    : [''],
            TAB_INF_DEFINES_CUSTOM_MAKEFILE                         : ['']
        }

class InfContents(InfObject):
    def __init__(self):
        self.Sources = []
        self.BuildOptions = []
        self.Binaries = []
        self.Includes = []
        self.Guids = []
        self.Protocols = []
        self.Ppis = []
        self.Libraries = []
        self.LibraryClasses = []
        self.Packages = []
        self.FixedPcd = []
        self.PatchPcd = []
        self.FeaturePcd = []
        self.Pcd = []
        self.PcdEx = []
        self.Depex = []
        self.Nmake = []
        
class Inf(InfObject):
    def __init__(self, Filename = None, IsMergeAllArches = False, IsToModule = False):
        self.Identification = Identification()
        self.Defines = InfDefines()
        self.Contents = {}
        self.UserExtensions = ''
        self.Module = ModuleClass()
        
        for Arch in DataType.ARCH_LIST_FULL:
            self.Contents[Arch] = InfContents()

        self.KeyList = [
            TAB_SOURCES, TAB_BUILD_OPTIONS, TAB_BINARIES, TAB_INCLUDES, TAB_GUIDS, TAB_PROTOCOLS, TAB_PPIS, TAB_LIBRARY_CLASSES, TAB_PACKAGES, TAB_LIBRARIES, \
            TAB_INF_FIXED_PCD, TAB_INF_PATCH_PCD, TAB_INF_FEATURE_PCD, TAB_INF_PCD, TAB_INF_PCD_EX, TAB_DEPEX, TAB_NMAKE
        ]
                
        if Filename != None:
            self.LoadInfFile(Filename)
        
        if IsMergeAllArches:
            self.MergeAllArches()
        
        if IsToModule:
            self.InfToModule()
    
    def MergeAllArches(self):
        for key in self.KeyList:
            for arch in DataType.ARCH_LIST:
                Command = "self.Contents[arch]." + key + ".extend(" + "self.Contents['" + DataType.TAB_ARCH_COMMON + "']." + key + ")"
                eval(Command)     
            
    def ParseInf(self, Lines, Key, KeyField):
        newKey = SplitModuleType(Key)
        if newKey[0].upper().find(DataType.TAB_LIBRARY_CLASSES.upper()) != -1:
            GetLibraryClassesWithModuleType(Lines, Key, KeyField, TAB_COMMENT_SPLIT)
        else:
            GetMultipleValuesOfKeyFromLines(Lines, Key, KeyField, TAB_COMMENT_SPLIT)

    def InfToModule(self):
        #
        # Get value for Header
        #
        self.Module.Header.Name = self.Defines.DefinesDictionary[TAB_INF_DEFINES_BASE_NAME][0]
        self.Module.Header.Guid = self.Defines.DefinesDictionary[TAB_INF_DEFINES_FILE_GUID][0]
        self.Module.Header.Version = self.Defines.DefinesDictionary[TAB_INF_DEFINES_VERSION_NUMBER][0]
        self.Module.Header.FileName = self.Identification.FileName
        self.Module.Header.FullPath = self.Identification.FileFullPath
        
        self.Module.Header.EfiSpecificationVersion = self.Defines.DefinesDictionary[TAB_INF_DEFINES_EFI_SPECIFICATION_VERSION][0]
        self.Module.Header.EdkReleaseVersion = self.Defines.DefinesDictionary[TAB_INF_DEFINES_EDK_RELEASE_VERSION][0]
        self.Module.Header.InfVersion = self.Defines.DefinesDictionary[TAB_INF_DEFINES_INF_VERSION][0]
                
        self.Module.Header.ModuleType = self.Defines.DefinesDictionary[TAB_INF_DEFINES_MODULE_TYPE][0]
        self.Module.Header.BinaryModule = self.Defines.DefinesDictionary[TAB_INF_DEFINES_BINARY_MODULE][0]
        self.Module.Header.ComponentType = self.Defines.DefinesDictionary[TAB_INF_DEFINES_COMPONENT_TYPE][0]
        self.Module.Header.MakefileName = self.Defines.DefinesDictionary[TAB_INF_DEFINES_MAKEFILE_NAME][0]
        self.Module.Header.BuildNumber = self.Defines.DefinesDictionary[TAB_INF_DEFINES_BUILD_NUMBER][0]
        self.Module.Header.BuildType = self.Defines.DefinesDictionary[TAB_INF_DEFINES_BUILD_TYPE][0]
        self.Module.Header.FfsExt = self.Defines.DefinesDictionary[TAB_INF_DEFINES_FFS_EXT][0]
        self.Module.Header.FvExt = self.Defines.DefinesDictionary[TAB_INF_DEFINES_FV_EXT][0]
        self.Module.Header.SourceFv = self.Defines.DefinesDictionary[TAB_INF_DEFINES_SOURCE_FV][0]
        self.Module.Header.PcdIsDriver = self.Defines.DefinesDictionary[TAB_INF_DEFINES_PCD_IS_DRIVER][0]
        self.Module.Header.TianoR8FlashMap_h = self.Defines.DefinesDictionary[TAB_INF_DEFINES_TIANO_R8_FLASHMAP_H][0]
        
        #LibraryClass of Define
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_LIBRARY_CLASS][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_LIBRARY_CLASS]:
                List = GetSplitValueList(Item, DataType.TAB_VALUE_SPLIT, 1)
                Lib = LibraryClassClass()
                Lib.LibraryClass = CleanString(List[0])
                if len(List) == 1:
                    Lib.SupModuleList = DataType.SUP_MODULE_LIST
                elif len(List) == 2:
                    Lib.SupModuleList = GetSplitValueList(CleanString(List[1]), ' ')
                self.Module.Header.LibraryClass.append(Lib)
        
        #Custom makefile
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_CUSTOM_MAKEFILE][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_CUSTOM_MAKEFILE]:
                List = Item.split(DataType.TAB_VALUE_SPLIT)
                if len(List) == 2:
                    self.Module.Header.CustomMakefile[CleanString(List[0])] = CleanString(List[1])
                else:
                    ErrorMsg = "Wrong CUSTOM_MAKEFILE statement '%s' found in section Defines in file '%s', correct format is 'CUSTOM_MAKEFILE = Family|Filename'" % (Item, self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
        
        #EntryPoint and UnloadImage
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_ENTRY_POINT][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_ENTRY_POINT]:
                Image = ModuleExternImageClass()
                Image.ModuleEntryPoint = CleanString(Item)
                self.Module.ExternImages.append(Image)
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_UNLOAD_IMAGE][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_UNLOAD_IMAGE]:
                Image = ModuleExternImageClass()
                Image.ModuleUnloadImage = CleanString(Item)
                self.Module.ExternImages.append(Image)
        
        #Constructor and Destructor
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_CONSTRUCTOR][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_CONSTRUCTOR]:
                LibraryClass = ModuleExternLibraryClass()
                LibraryClass.Constructor = CleanString(Item)
                self.Module.ExternLibraries.append(LibraryClass)
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_DESTRUCTOR][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_DESTRUCTOR]:
                LibraryClass = ModuleExternLibraryClass()
                LibraryClass.Destructor = CleanString(Item)
                self.Module.ExternLibraries.append(LibraryClass)
        
        #Define
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_DEFINE][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_DEFINE]:
                List = Item.split(DataType.TAB_EQUAL_SPLIT)
                if len(List) != 2:
                    ErrorMsg = "Wrong DEFINE statement '%s' found in section Defines in file '%s', correct format is 'DEFINE <Word> = <Word>'" % (Item, self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                else:
                    self.Module.Header.Define[CleanString(List[0])] = CleanString(List[1])
        
        #Spec
        if self.Defines.DefinesDictionary[TAB_INF_DEFINES_SPEC][0] != '':
            for Item in self.Defines.DefinesDictionary[TAB_INF_DEFINES_SPEC]:
                List = Item.split(DataType.TAB_EQUAL_SPLIT)
                if len(List) != 2:
                    ErrorMsg = "Wrong SPEC statement '%s' found in section Defines in file '%s', correct format is 'SPEC <Word> = <Version>'" % (Item, self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                else:
                    self.Module.Header.Specification[CleanString(List[0])] = CleanString(List[1])
                
        #BuildOptions
        BuildOptions = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].BuildOptions:
                MergeArches(BuildOptions, GetBuildOption(Item), Arch)
        for Key in BuildOptions.keys():
            BuildOption = BuildOptionClass(Key[0], Key[1], Key[2])
            BuildOption.SupArchList = BuildOptions[Key]
            self.Module.BuildOptions.append(BuildOption)    
        
        #Includes
        Includes = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Includes:
                MergeArches(Includes, Item, Arch)
        for Key in Includes.keys():
            Include = IncludeClass()
            Include.FilePath = Key
            Include.SupArchList = Includes[Key]
            self.Module.Includes.append(Include)
        
        #Libraries
        Libraries = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Libraries:
                MergeArches(Libraries, Item, Arch)
        for Key in Libraries.keys():
            Library = ModuleLibraryClass()
            Library.Library = Key
            Library.SupArchList = Libraries[Key]
            self.Module.Libraries.append(Library)
        
        #LibraryClasses
        LibraryClasses = {}
        Defines = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].LibraryClasses:
                Status = GenDefines(Item[0], Arch, Defines)
                if Status == 0:       # Find DEFINE statement
                    pass
                elif Status == -1:    # Find DEFINE statement but in wrong format
                    ErrorMsg = "Wrong DEFINE statement '%s' found in section LibraryClasses in file '%s', correct format is 'DEFINE <VarName> = <PATH>'" % (Item[0], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                elif Status == 1:     # Not find DEFINE statement
                    #{ (LibraryClass, Instance, PcdFeatureFlag, ModuleType1|ModuleType2|ModuleType3) : [Arch1, Arch2, ...] }
                    ItemList = GetSplitValueList((Item[0] + DataType.TAB_VALUE_SPLIT * 2))
                    if ItemList[1] != '' and CheckFileType(ItemList[1], '.Inf') == False:
                        ErrorMsg = "Wrong library instance '%s' found for LibraryClasses '%s' in file '%s', it is NOT a valid INF file" % (ItemList[1], ItemList[0], self.Module.Header.FullPath) 
                        raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                    MergeArches(LibraryClasses, (ItemList[0], ItemList[1], ItemList[2], DataType.TAB_VALUE_SPLIT.join(Item[1])), Arch)
        for Key in LibraryClasses.keys():
            KeyList = Key[0].split(DataType.TAB_VALUE_SPLIT)
            LibraryClass = LibraryClassClass()
            LibraryClass.Define = Defines
            LibraryClass.LibraryClass = Key[0]
            LibraryClass.RecommendedInstance = Key[1]
            LibraryClass.FeatureFlag = Key[2]
            LibraryClass.SupArchList = LibraryClasses[Key]
            if Key[3] != '':
                LibraryClass.SupModuleList = GetSplitValueList(Key[3])
            else:
                LibraryClass.SupModuleList = DataType.SUP_MODULE_LIST
            self.Module.LibraryClasses.append(LibraryClass)
        
        #Packages
        Packages = {}
        Defines = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Packages:
                Status = GenDefines(Item, Arch, Defines)
                if Status == 0:       # Find DEFINE statement
                    pass
                elif Status == -1:    # Find DEFINE statement but in wrong format
                    ErrorMsg = "Wrong DEFINE statement '%s' found in section Packages in file '%s', correct format is 'DEFINE <VarName> = <PATH>'" % (Item, self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                elif Status == 1:     # Not find DEFINE statement
                    if Item != '' and CheckFileType(Item, '.Dec') == False:
                        ErrorMsg = "Wrong package definition '%s' found in file '%s', it is NOT a valid DEC file" % (Item, self.Module.Header.FullPath) 
                        raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                    MergeArches(Packages, Item, Arch)
        for Key in Packages.keys():
            Package = ModulePackageDependencyClass()
            Package.Define = Defines
            Package.FilePath = Key
            Package.SupArchList = Packages[Key]
            self.Module.PackageDependencies.append(Package)
            
        #Nmake
        Nmakes = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Nmake:
                MergeArches(Nmakes, Item, Arch)
        for Key in Nmakes.keys():
            List = GetSplitValueList(Key, DataType.TAB_EQUAL_SPLIT)
            if len(List) != 2:
                ErrorMsg = "Wrong statement '%s' found in section Nmake in file '%s', correct format is '<Word>=<Word>'" % (Item, self.Module.Header.FullPath) 
                raise ParserError(PARSER_ERROR, msg = ErrorMsg)
            Nmake = ModuleNmakeClass()
            Nmake.Name = List[0]
            Nmake.Value = List[1]
            Nmake.SupArchList = Nmakes[Key]
            self.Module.Nmake.append(Nmake)
        
        #Pcds
        Pcds = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].FixedPcd:
                Item = Item + DataType.TAB_VALUE_SPLIT
                List = GetSplitValueList(Item)
                if len(List) < 2:
                    ErrorMsg = "Wrong statement '%s' found in section FixedPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                TokenInfo = GetSplitValueList(List[0], DataType.TAB_SPLIT)
                if len(TokenInfo) != 2:
                    ErrorMsg = "Wrong statement '%s' found in section FixedPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                MergeArches(Pcds, (TokenInfo[0], TokenInfo[1], List[1], TAB_PCDS_FIXED_AT_BUILD), Arch)
            
            for Item in self.Contents[Arch].PatchPcd:
                Item = Item + DataType.TAB_VALUE_SPLIT
                List = GetSplitValueList(Item)
                if len(List) < 2:
                    ErrorMsg = "Wrong statement '%s' found in section PatchPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                TokenInfo = GetSplitValueList(List[0], DataType.TAB_SPLIT)
                if len(TokenInfo) != 2:
                    ErrorMsg = "Wrong statement '%s' found in section FixedPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                MergeArches(Pcds, (TokenInfo[0], TokenInfo[1], List[1], TAB_PCDS_PATCHABLE_IN_MODULE), Arch)
            
            for Item in self.Contents[Arch].FeaturePcd:
                Item = Item + DataType.TAB_VALUE_SPLIT
                List = GetSplitValueList(Item)
                if len(List) < 2:
                    ErrorMsg = "Wrong statement '%s' found in section FeaturePcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                TokenInfo = GetSplitValueList(List[0], DataType.TAB_SPLIT)
                if len(TokenInfo) != 2:
                    ErrorMsg = "Wrong statement '%s' found in section FixedPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                MergeArches(Pcds, (TokenInfo[0], TokenInfo[1], List[1], TAB_PCDS_FEATURE_FLAG), Arch)
            
            for Item in self.Contents[Arch].PcdEx:
                Item = Item + DataType.TAB_VALUE_SPLIT
                List = GetSplitValueList(Item)
                if len(List) < 2:
                    ErrorMsg = "Wrong statement '%s' found in section PcdEx in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                TokenInfo = GetSplitValueList(List[0], DataType.TAB_SPLIT)
                if len(TokenInfo) != 2:
                    ErrorMsg = "Wrong statement '%s' found in section FixedPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                MergeArches(Pcds, (TokenInfo[0], TokenInfo[1], List[1], TAB_PCDS_DYNAMIC_EX), Arch)
            
            for Item in self.Contents[Arch].Pcd:
                Item = Item + DataType.TAB_VALUE_SPLIT
                List = GetSplitValueList(Item)
                if len(List) < 2:
                    ErrorMsg = "Wrong statement '%s' found in section Pcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                TokenInfo = GetSplitValueList(List[0], DataType.TAB_SPLIT)
                if len(TokenInfo) != 2:
                    ErrorMsg = "Wrong statement '%s' found in section FixedPcd in file '%s', correct format is '<TokenSpaceGuidCName>.<PcdCName>[|<Value>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                MergeArches(Pcds, (TokenInfo[0], TokenInfo[1], List[1], TAB_PCDS_DYNAMIC), Arch)
        for Key in Pcds.keys():
            Pcd = PcdClass()
            Pcd.CName = Key[1]
            Pcd.TokenSpaceGuidCName = Key[0]
            Pcd.DefaultValue = Key[2]
            Pcd.ItemType = Key[3]
            Pcd.SupArchList = Pcds[Key]
            self.Module.PcdCodes.append(Pcd)
        
        #Sources
        Sources = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Sources:
                Item = Item + DataType.TAB_VALUE_SPLIT * 4
                List = GetSplitValueList(Item)
                MergeArches(Sources, (List[0], List[1], List[2], List[3], List[4]), Arch)
        for Key in Sources.keys():
            Source = ModuleSourceFileClass(Key[0], Key[3], Key[4], Key[1], Key[2], Sources[Key])
            self.Module.Sources.append(Source)
        
        #UserExtensions
        if self.UserExtensions != '':
            UserExtension = UserExtensionsClass()
            Lines = self.UserExtensions.splitlines()
            List = GetSplitValueList(Lines[0], DataType.TAB_SPLIT, 2)
            if len(List) != 3:
                ErrorMsg = "Wrong statement '%s' found in section UserExtensions in file '%s', correct format is 'UserExtensions.UserId.'Identifier''" % (Item[0:-1], self.Module.Header.FullPath) 
                raise ParserError(PARSER_ERROR, msg = ErrorMsg)
            else:
                UserExtension.UserID = List[1]
                UserExtension.Identifier = List[2][0:-1].replace("'", '').replace('\"', '')
                for Line in Lines[1:]:
                    UserExtension.Content = UserExtension.Content + CleanString(Line) + '\n'
            self.Module.UserExtensions.append(UserExtension)
        
        #Guids
        Guids = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Guids:
                MergeArches(Guids, Item, Arch)
        for Key in Guids.keys():
            Guid = GuidClass()
            Guid.CName = Key
            Guid.SupArchList = Guids[Key]
            self.Module.Guids.append(Guid)

        #Protocols
        Protocols = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Protocols:
                MergeArches(Protocols, Item, Arch)
        for Key in Protocols.keys():
            Protocol = ProtocolClass()
            Protocol.CName = Key
            Protocol.SupArchList = Protocols[Key]
            self.Module.Protocols.append(Protocol)
        
        #Ppis
        Ppis = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Ppis:
                MergeArches(Ppis, Item, Arch)
        for Key in Ppis.keys():
            Ppi = PpiClass()
            Ppi.CName = Key
            Ppi.SupArchList = Ppis[Key]
            self.Module.Ppis.append(Ppi)
        
        #Depex
        Depex = {}
        Defines = {}
        for Arch in DataType.ARCH_LIST:
            Line = ''
            for Item in self.Contents[Arch].Depex:
                Status = GenDefines(Item, Arch, Defines)
                if Status == 0:       # Find DEFINE statement
                    pass
                elif Status == -1:    # Find DEFINE statement but in wrong format
                    ErrorMsg = "Wrong DEFINE statement '%s' found in section Depex in file '%s', correct format is 'DEFINE <VarName> = <PATH>'" % (Item, self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                elif Status == 1:     # Not find DEFINE statement
                    Line = Line + Item + ' '
            MergeArches(Depex, Line, Arch)
        for Key in Depex.keys():
            Dep = ModuleDepexClass()
            Dep.Depex = Key
            Dep.SupArchList = Depex[Key]
            Dep.Define = Defines
            self.Module.Depex.append(Dep)
        
        #Binaries
        Binaries = {}
        for Arch in DataType.ARCH_LIST:
            for Item in self.Contents[Arch].Binaries:
                Item = Item + DataType.TAB_VALUE_SPLIT
                List = GetSplitValueList(Item)
                if len(List) < 4:
                    ErrorMsg = "Wrong statement '%s' found in section Binaries in file '%s', correct format is '<FileType>|<Target>|<FileName>[|<PcdFeatureFlag>]'" % (Item[0:-1], self.Module.Header.FullPath) 
                    raise ParserError(PARSER_ERROR, msg = ErrorMsg)
                else:
                    MergeArches(Binaries, (List[0], List[1], List[2], List[3]), Arch)
        for Key in Binaries.keys():
            Binary = ModuleBinaryFileClass(Key[2], Key[0], Key[1], Key[3], Binaries[Key])
            self.Module.Binaries.append(Binary)
        
    def LoadInfFile(self, Filename):     
        (Filepath, Name) = os.path.split(Filename)
        self.Identification.FileName = Name
        self.Identification.FileFullPath = Filename
        self.Identification.FileRelativePath = Filepath
        
        F = open(Filename, 'r').read()
        PreCheck(Filename, F, self.KeyList)
        Sects = F.split(DataType.TAB_SECTION_START)
        for Sect in Sects:
            TabList = GetSplitValueList(Sect.split(TAB_SECTION_END, 1)[0], DataType.TAB_COMMA_SPLIT)
            for Tab in TabList:            
                if Tab.upper() == TAB_INF_DEFINES.upper():
                    GetSingleValueOfKeyFromLines(Sect, self.Defines.DefinesDictionary, TAB_COMMENT_SPLIT, TAB_EQUAL_SPLIT, False, None)
                    continue
                if Tab.upper().find(DataType.TAB_USER_EXTENSIONS.upper()) > -1:
                    self.UserExtensions = Sect
                    continue
                for Arch in DataType.ARCH_LIST_FULL + [DataType.TAB_ARCH_NULL]:
                    for Key in self.KeyList:
                        if Arch != DataType.TAB_ARCH_NULL:
                            Target = (Key + DataType.TAB_SPLIT + Arch).upper()
                        else:
                            Target = Key.upper()
                        if SplitModuleType(Tab)[0].upper() == Target:
                            if Arch != DataType.TAB_ARCH_NULL:
                                Command = 'self.ParseInf(Sect, Tab, self.Contents[Arch].' + Key + ')'
                                eval(Command)
                                continue
                            else:
                                Command = "self.ParseInf(Sect, Tab, self.Contents['" + DataType.TAB_ARCH_COMMON + "']." + Key + ')'
                                eval(Command)
                                continue
            #EndFor

    def ShowInf(self):
        print TAB_SECTION_START + TAB_INF_DEFINES + TAB_SECTION_END
        printDict(self.Defines.DefinesDictionary)

        for key in self.KeyList:
            for arch in DataType.ARCH_LIST_FULL:
                Command = "printList(TAB_SECTION_START + '" + \
                          key + DataType.TAB_SPLIT + arch + \
                          "' + TAB_SECTION_END, self.Contents[arch]." + key + ')'
                eval(Command)
        print ""
    
    def ShowModule(self):
        m = self.Module
        print 'Filename =', m.Header.FileName
        print 'FullPath =', m.Header.FullPath
        print 'BaseName =', m.Header.Name
        print 'Guid =', m.Header.Guid
        print 'Version =', m.Header.Version
        print 'InfVersion =', m.Header.InfVersion
        print 'EfiSpecificationVersion =', m.Header.EfiSpecificationVersion
        print 'EdkReleaseVersion =', m.Header.EdkReleaseVersion                
        print 'ModuleType =', m.Header.ModuleType
        print 'BinaryModule =', m.Header.BinaryModule
        print 'ComponentType =', m.Header.ComponentType
        print 'MakefileName =', m.Header.MakefileName
        print 'BuildNumber =', m.Header.BuildNumber
        print 'BuildType =', m.Header.BuildType
        print 'FfsExt =', m.Header.FfsExt
        print 'FvExt =', m.Header.FvExt
        print 'SourceFv =', m.Header.SourceFv
        print 'PcdIsDriver =', m.Header.PcdIsDriver
        print 'TianoR8FlashMap_h =', m.Header.TianoR8FlashMap_h
        print 'LibraryClass =', m.Header.LibraryClass
        for Item in m.Header.LibraryClass:
            print Item.LibraryClass, DataType.TAB_VALUE_SPLIT.join(Item.SupModuleList)
        print 'CustomMakefile =', m.Header.CustomMakefile
        for Item in self.Module.ExternImages:
            print 'Entry_Point = %s, UnloadImage = %s' % (Item.ModuleEntryPoint, Item.ModuleUnloadImage)
        for Item in self.Module.ExternLibraries:
            print 'Constructor = %s, Destructor = %s' % (Item.Constructor, Item.Destructor)
        print 'Define =', m.Header.Define
        print 'Specification =', m.Header.Specification
        print '\nBuildOptions =', m.BuildOptions
        for Item in m.BuildOptions:
            print Item.ToolChainFamily, Item.ToolChain, Item.Option, Item.SupArchList
        print '\nIncludes =', m.Includes
        for Item in m.Includes:
            print Item.FilePath, Item.SupArchList
        print '\nLibraries =', m.Libraries
        for Item in m.Libraries:
            print Item.Library, Item.SupArchList
        print '\nLibraryClasses =', m.LibraryClasses
        for Item in m.LibraryClasses:
            print Item.LibraryClass, Item.RecommendedInstance, Item.FeatureFlag, Item.SupModuleList, Item.SupArchList, Item.Define
        print '\nPackageDependencies =', m.PackageDependencies
        for Item in m.PackageDependencies:
            print Item.FilePath, Item.SupArchList, Item.Define
        print '\nNmake =', m.Nmake
        for Item in m.Nmake:
            print Item.Name, Item.Value, Item.SupArchList
        print '\nPcds =', m.PcdCodes
        for Item in m.PcdCodes:
            print '\tCName=', Item.CName, 'TokenSpaceGuidCName=', Item.TokenSpaceGuidCName, 'DefaultValue=', Item.DefaultValue, 'ItemType=', Item.ItemType, Item.SupArchList
        print '\nSources =', m.Sources
        for Source in m.Sources:
            print Source.SourceFile, Source.ToolChainFamily, Source.FeatureFlag, Source.TagName, Source.ToolCode, Source.SupArchList
        print '\nUserExtensions =', m.UserExtensions
        for UserExtension in m.UserExtensions:
            print UserExtension.UserID, UserExtension.Identifier,UserExtension.Content
        print '\nGuids =', m.Guids
        for Item in m.Guids:
            print Item.CName, Item.SupArchList
        print '\nProtocols =', m.Protocols
        for Item in m.Protocols:
            print Item.CName, Item.SupArchList
        print '\nPpis =', m.Ppis
        for Item in m.Ppis:
            print Item.CName, Item.SupArchList
        print '\nDepex =', m.Depex
        for Item in m.Depex:
            print Item.Depex, Item.SupArchList, Item.Define
        print '\nBinaries =', m.Binaries
        for Binary in m.Binaries:
            print Binary.FileType, Binary.Target, Binary.BinaryFile, Binary.FeatureFlag
        
if __name__ == '__main__':
    w = os.getenv('WORKSPACE')
    f = os.path.join(w, 'MdeModulePkg/Application/HelloWorld/HelloWorld.inf')
    p = Inf(os.path.normpath(f), True, True)
    p.ShowModule()
