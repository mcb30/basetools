## @file
# Generate AutoGen.h, AutoGen.c and *.depex files
#
# Copyright (c) 2007, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.  The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

## Import Modules
#
import sys
import os
import re
import os.path as path
import imp

import Common.EdkLogger
import GenC
import GenMake
import GenDepex

from BuildInfo import *
from StrGather import *
from BuildEngine import *

from Common.BuildToolError import *
from Common.EdkIIWorkspaceBuild import *
from Common.EdkIIWorkspace import *
from Common.DataType import *
from Common.Misc import *
from Common.String import *

## PlatformBuildClassObject database
gPlatformDatabase = {}      # {arch : {dsc file path : PlatformBuildClassObject}}

## ModuleBuildClassObject database
gModuleDatabase = {}        # {arch : {inf file path : ModuleBuildClassObject}}

## PackageBuildClassObject database
gPackageDatabase = {}       # {arch : {dec file path : PackageBuildClassObject}}

## AutoGen object database
gAutoGenDatabase = {}       # (module/package/platform obj, BuildTarget, ToolChain, Arch) : build info

## Shortcut global of WorkspaceBuild object representing current workspace
gWorkspace = None

## Shortcut global of current workspace directory
gWorkspaceDir = ""

## Regular expression for splitting Dependency Expression stirng into tokens
gDepexTokenPattern = re.compile("(\(|\)|\w+| \S+\.inf)")

## Mapping Makefile type
gMakeTypeMap = {"MSFT":"nmake", "GCC":"gmake"}

## Default output flag for all tools
gDefaultOutputFlag = "-o "

## Output flags for specific tools
gOutputFlag = {
    ("MSFT", "CC", "OUTPUT")      :   "/Fo",
    ("MSFT", "SLINK", "OUTPUT")   :   "/OUT:",
    ("MSFT", "DLINK", "OUTPUT")   :   "/OUT:",
    ("MSFT", "ASMLINK", "OUTPUT") :   "/OUT:",
    ("MSFT", "PCH", "OUTPUT")     :   "/Fp",
    ("MSFT", "ASM", "OUTPUT")     :   "/Fo",

    ("INTEL", "CC", "OUTPUT")          :   "/Fo",
    ("INTEL", "SLINK", "OUTPUT")       :   "/OUT:",
    ("INTEL", "DLINK", "OUTPUT")       :   "/OUT:",
    ("INTEL", "ASMLINK", "OUTPUT")     :   "/OUT:",
    ("INTEL", "PCH", "OUTPUT")         :   "/Fp",
    ("INTEL", "ASM", "OUTPUT")         :   "/Fo",

    ("GCC", "CC", "OUTPUT")        :   "-o ",
    ("GCC", "SLINK", "OUTPUT")     :   "-cr ",
    ("GCC", "DLINK", "OUTPUT")     :   "-o ",
    ("GCC", "ASMLINK", "OUTPUT")   :   "-o ",
    ("GCC", "PCH", "OUTPUT")       :   "-o ",
    ("GCC", "ASM", "OUTPUT")       :   "-o ",
}

## Flag for include file search path
gIncludeFlag = {"MSFT" : "/I", "GCC" : "-I", "INTEL" : "-I"}

## Build rule configuration file
gBuildRuleFile = 'Conf/build_rule.txt'

## Find the package containing the module
#
# Find out the package which contains the given module, according to the path
# of the module and the package.
#
# @param  Module            The module to be found for
# @param  PackageDatabase   Database containing all packages found
#
# @retval package           Package object if found
# @retval None              None if not found
#
def FindModuleOwnerPackage(Module, PackageDatabase):
    for PackagePath in PackageDatabase:
        PackageDir = path.dirname(PackagePath)
        #
        # if package's path is the first part of module's path, bingo!
        #
        if str(Module).find(PackageDir) == 0:
            return PackageDatabase[PackagePath]
    # nothing found
    return None

## AutoGen class
#
# This class encapsules the AutoGen behaviors for the build tools. In addition to
# the generation of AutoGen.h and AutoGen.c, it can generate *.depex file according
# to the [depex] section in module's inf file. The result of parsing unicode file
# has been incorporated either.
#
class AutoGen(object):

    def __init__(self, ModuleFile, PlatformFile, Workspace, Target, Toolchain, Arch):
        global gModuleDatabase, gPackageDatabase, gPlatformDatabase, gAutoGenDatabase, gWorkspace, gWorkspaceDir, gBuildRuleDatabase

        if ModuleFile != None:
            ModuleFile = NormPath(str(ModuleFile))
        if PlatformFile != None:
            PlatformFile = NormPath(str(PlatformFile))

        if gWorkspace == None:
            gWorkspace = Workspace
        if gWorkspaceDir == "":
            gWorkspaceDir = Workspace.WorkspaceDir

        if gModuleDatabase == {}:
            for a in Workspace.Build:
                gModuleDatabase[a] = gWorkspace.Build[a].ModuleDatabase
        if gPackageDatabase == {}:
            for a in Workspace.Build:
                gPackageDatabase[a] = gWorkspace.Build[a].PackageDatabase
        if gPlatformDatabase == {}:
            for a in Workspace.Build:
                gPlatformDatabase[a] = gWorkspace.Build[a].PlatformDatabase

        self.ToolChain = Toolchain
        self.ToolChainFamily = "MSFT"
        self.BuildTarget = Target
        self.IsMakefileCreated = False
        self.IsAutoGenCodeCreated = False

        Key = (self.BuildTarget, self.ToolChain, str(PlatformFile))
        if ModuleFile == None:
            #
            # autogen for platform
            #
            self.PlatformBuildInfo = {}     # arch : PlatformBuildInfo Object
            self.Platform = {}
            self.IsPlatformAutoGen = True
            if type(Arch) == type([]):
                self.Arch = Arch
            else:
                self.Arch = [Arch]
            EdkLogger.verbose("")
            EdkLogger.verbose("\nAutoGen platform [%s] %s" % (PlatformFile, self.Arch))

            self.Platform = {}
            self.BuildInfo = {}
            for a in self.Arch:
                if a not in gPlatformDatabase or str(PlatformFile) not in gPlatformDatabase[a]:
                    raise AutoGenError(msg="[%s] is not the active platform, or %s is not supported by the active platform!" % (PlatformFile, a))
                p = gPlatformDatabase[a][str(PlatformFile)]
                self.Platform[a] = p
                self.BuildInfo[a] = self.GetPlatformBuildInfo(p, self.BuildTarget, self.ToolChain, a)
            gAutoGenDatabase[Key] = self
            return
        elif Key not in gAutoGenDatabase:
            gAutoGenDatabase[Key] = AutoGen(None, PlatformFile, Workspace, Target, Toolchain, Arch)

        #
        # autogen for module
        #
        self.IsPlatformAutoGen = False
        if type(Arch) == type([]):
            if len(Arch) > 1:
                raise AutoGenError(msg="Cannot AutoGen a module for more than one platform object at a time!")
            self.Arch = Arch[0]
        else:
            self.Arch = Arch
        EdkLogger.verbose("")
        EdkLogger.verbose("AutoGen module [%s] [%s]" % (ModuleFile, self.Arch))

        if self.Arch not in gPlatformDatabase or str(PlatformFile) not in gPlatformDatabase[Arch]:
            raise AutoGenError(msg="[%s] is not the active platform, or %s is not supported by the platform!" % (PlatformFile, self.Arch))
        if self.Arch not in gModuleDatabase or str(ModuleFile) not in gModuleDatabase[self.Arch]:
            raise AutoGenError(msg="[%s] architecture %s is not supported by active platform [%s]!" % (ModuleFile, self.Arch, PlatformFile))

        self.Platform = gPlatformDatabase[Arch][str(PlatformFile)]
        if str(ModuleFile) not in self.Platform.Modules and str(ModuleFile) not in self.Platform.Libraries:
            raise AutoGenError(msg="Cannot find module %s for architecture [%s] in the active platform:\n\t%s\n" % (ModuleFile, self.Arch, self.Platform))
        self.Module = gModuleDatabase[Arch][str(ModuleFile)]

        self.Package = FindModuleOwnerPackage(self.Module, gPackageDatabase[Arch])

        self.AutoGenC = GenC.AutoGenString()
        self.AutoGenH = GenC.AutoGenString()

        self.BuildInfo = None
        self.GetModuleBuildInfo()
        gAutoGenDatabase[self.BuildTarget, self.ToolChain, self.Arch, self.Module] = self

    def GetModuleBuildInfo(self):
        Key = (self.BuildTarget, self.ToolChain, self.Arch, self.Module)
        if Key in gAutoGenDatabase:
            self.BuildInfo = gAutoGenDatabase[Key].BuildInfo
            self.IsAutoGenCodeCreated = gAutoGenDatabase[Key].IsAutoGenCodeCreated
            self.IsMakefileCreated = gAutoGenDatabase[Key].IsMakefileCreated
            return gAutoGenDatabase[Key].BuildInfo

        Info = ModuleBuildInfo(self.Module)
        self.BuildInfo = Info
        Info.PlatformInfo = self.GetPlatformBuildInfo(self.Platform, self.BuildTarget, self.ToolChain, self.Arch)

        # basic information
        Info.WorkspaceDir = gWorkspaceDir
        Info.BuildTarget = self.BuildTarget
        Info.ToolChain = self.ToolChain
        Info.Arch = self.Arch
        Info.IsBinary = False
        Info.BaseName = self.Module.BaseName
        Info.FileBase, Info.FileExt = path.splitext(path.basename(self.Module.DescFilePath))
        Info.SourceDir = path.dirname(self.Module.DescFilePath)
        Info.BuildDir = os.path.join(Info.PlatformInfo.BuildDir,
                                     Info.Arch,
                                     Info.SourceDir,
                                     Info.FileBase)
        Info.OutputDir = os.path.join(Info.BuildDir, "OUTPUT")
        Info.DebugDir = os.path.join(Info.BuildDir, "DEBUG")
        Info.MakefileDir = Info.BuildDir
        if os.path.isabs(Info.BuildDir):
            CreateDirectory(Info.OutputDir)
            CreateDirectory(Info.DebugDir)
        else:
            CreateDirectory(os.path.join(gWorkspaceDir, Info.OutputDir))
            CreateDirectory(os.path.join(gWorkspaceDir, Info.DebugDir))

        for Type in self.Module.CustomMakefile:
            MakeType = gMakeTypeMap[Type]
            Info.CustomMakefile[MakeType] = os.path.join(Info.SourceDir, self.Module.CustomMakefile[Type])

        if self.Module.LibraryClass != None and self.Module.LibraryClass != []:
            Info.IsLibrary = True
            Info.DependentLibraryList = []
        else:
            Info.IsLibrary = False
            Info.DependentLibraryList = self.GetSortedLibraryList()

        Info.DependentPackageList = self.GetDependentPackageList()
        Info.DerivedPackageList = self.GetDerivedPackageList()

        Info.BuildOption = self.GetModuleBuildOption(Info.PlatformInfo)
        if "DLINK" in Info.PlatformInfo.ToolStaticLib:
            Info.SystemLibraryList = Info.PlatformInfo.ToolStaticLib["DLINK"]

        Info.PcdIsDriver = self.Module.PcdIsDriver
        Info.PcdList = self.GetPcdList(Info.DependentLibraryList)
        Info.GuidList = self.GetGuidList()
        Info.ProtocolList = self.GetProtocolGuidList()
        Info.PpiList = self.GetPpiGuidList()
        Info.MacroList = self.GetMacroList()
        Info.DepexList = self.GetDepexTokenList(Info)

        Info.IncludePathList = [Info.SourceDir, Info.DebugDir]
        Info.IncludePathList.extend(self.GetIncludePathList(Info.DependentPackageList))

        Info.SourceFileList = self.GetBuildFileList(Info.PlatformInfo)
        Info.AutoGenFileList = self.GetAutoGenFileList(Info)

        return Info

    def InitPackageBuildInfo(self, Info):
        Info.SourceDir = path.dirname(Info.Package.DescFilePath)
        Info.IncludePathList.append(Info.SourceDir)
        for Inc in Info.Package.Includes:
            Info.IncludePathList.append(os.path.join(Info.SourceDir, Inc))

    def GetPlatformBuildInfo(self, Platform, Target, Toolchain, Arch):
        Key = Target, Toolchain, Platform
        PlatformAutoGen = None
        if Key in gAutoGenDatabase:
            PlatformAutoGen = gAutoGenDatabase[Key]
            if type(PlatformAutoGen.BuildInfo) == type({}):
                if Arch in PlatformAutoGen.BuildInfo:
                    return PlatformAutoGen.BuildInfo[Arch]
            else:
                return PlatformAutoGen.BuildInfo

        Info = PlatformBuildInfo(Platform)

        Info.Arch = Arch
        Info.ToolChain = self.ToolChain
        Info.BuildTarget = self.BuildTarget

        Info.WorkspaceDir = gWorkspace.WorkspaceDir
        Info.SourceDir = path.dirname(Platform.DescFilePath)
        Info.OutputDir = Platform.OutputDirectory
        Info.BuildDir = path.join(Info.OutputDir, self.BuildTarget + "_" + self.ToolChain)
        Info.MakefileDir = Info.BuildDir
        if Platform.FlashDefinition != "":
            Info.FdfFileList.append(path.join(gWorkspaceDir, Platform.FlashDefinition))

        Info.DynamicPcdList = self.GetDynamicPcdList(Platform, Arch)
        Info.PcdTokenNumber = self.GeneratePcdTokenNumber(Platform, Info.DynamicPcdList)
        Info.PackageList = gPackageDatabase[Arch].values()

        self.ProcessToolDefinition(Info)
        Info.BuildRule = self.GetBuildRule()

        if PlatformAutoGen != None:
            if type(PlatformAutoGen.BuildInfo) == type({}):
                PlatformAutoGen.BuildInfo[Arch] = Info
            else:
                PlatformAutoGen.BuildInfo = Info
        return Info

    def GetBuildRule(self):
        return BuildRule(gWorkspace.WorkspaceFile(gBuildRuleFile))

    def GetDerivedPackageList(self):
        PackageList = []
        for M in [self.Module] + self.BuildInfo.DependentLibraryList:
            for Package in M.Packages:
                if Package not in PackageList:
                    PackageList.append(gPackageDatabase[self.Arch][Package])
        return PackageList

    def GetDepexTokenList(self, Info):
        Dxs = self.Module.Depex
        if Dxs == None or Dxs == "":
            return []

        #
        # Append depex from dependent libraries
        #
        for Lib in Info.DependentLibraryList:
            if Lib.Depex != None and Lib.Depex != "":
                Dxs += " AND (" + Lib.Depex + ")"
                EdkLogger.verbose("DEPEX string (+%s) = %s" % (Lib.BaseName, Dxs))
        if Dxs == "":
            return []

        TokenList = gDepexTokenPattern.findall(Dxs)
        EdkLogger.debug(EdkLogger.DEBUG_8, "TokenList(raw) = %s" % (TokenList))
        for I in range(0, len(TokenList)):
            Token = TokenList[I].strip()
            if Token.endswith(".inf"):  # module file name
                ModuleFile = os.path.normpath(Token)
                Token = gModuleDatabase[ModuleFile].Guid
            elif Token.upper() in GenDepex.DependencyExpression.SupportedOpcode: # Opcode name
                Token = Token.upper()
            elif Token not in ['(', ')']:   # GUID C Name
                GuidCName = Token
                for P in Info.DerivedPackageList:
                    if GuidCName in P.Protocols:
                        Token = P.Protocols[GuidCName]
                        break
                    elif GuidCName in P.Ppis:
                        Token = P.Ppis[GuidCName]
                        break
                    elif GuidCName in P.Guids:
                        Token = P.Guids[GuidCName]
                        break
                else:
                    raise AutoGenError(msg="%s used in module %s cannot be found in any package!" % (GuidCName, self.Module))
            TokenList[I] = Token
        EdkLogger.debug(EdkLogger.DEBUG_8, "TokenList(guid) = %s" % " ".join(TokenList))
        return TokenList

    def GetMacroList(self):
        return ["%s %s" % (Name, self.Module.Specification[Name]) for Name in self.Module.Specification]

    def ProcessToolDefinition(self, Info):
        ToolDefinition = gWorkspace.ToolDef.ToolsDefTxtDictionary
        ToolCodeList = gWorkspace.ToolDef.ToolsDefTxtDatabase["COMMAND_TYPE"]
        for Tool in ToolCodeList:
            KeyBaseString = "%s_%s_%s_%s" % (Info.BuildTarget, Info.ToolChain, Info.Arch, Tool)
            Key = "%s_NAME" % KeyBaseString
            if Key not in ToolDefinition:
                continue
            Name = ToolDefinition[Key]

            Key = "%s_PATH" % KeyBaseString
            if Key in ToolDefinition:
                Path = ToolDefinition[Key]
            else:
                Path = ""

            Key = "%s_FAMILY" % KeyBaseString
            if Key in ToolDefinition:
                Family = ToolDefinition[Key]
            else:
                Family = ""

            Key = "%s_FLAGS" % KeyBaseString
            if Key in ToolDefinition:
                Option = ToolDefinition[Key]
            else:
                Option = ""

            Key = "%s_DPATH" % KeyBaseString
            if Key in ToolDefinition:
                Dll = ToolDefinition[Key]
                os.environ["PATH"] = Dll + os.pathsep + os.environ["PATH"]
            else:
                Dll = ""

            Key = "%s_SPATH" % KeyBaseString
            if Key in ToolDefinition:
                Lib = ToolDefinition[Key]
            else:
                Lib = ""

            Key = KeyBaseString + "_OUTPUT"
            if Key in ToolDefinition:
                OutputFlag = ToolDefinition[Key]
            elif (Family, Tool, "OUTPUT") in gOutputFlag:
                OutputFlag = gOutputFlag[Family, Tool, "OUTPUT"]
                if OutputFlag[0] == '"' and OutputFlag[-1] == '"':
                    OutputFlag = OutputFlag[1:-1]
            else:
                OutputFlag = gDefaultOutputFlag

            InputFlag = gIncludeFlag[Family]

            Info.ToolPath[Tool] = os.path.join(Path, Name)
            Info.ToolDynamicLib[Tool] = Dll
            Info.ToolStaticLib[Tool] = Lib
            Info.ToolChainFamily[Tool] = Family
            Info.DefaultToolOption[Tool] = Option
            Info.OutputFlag[Tool] = OutputFlag
            Info.IncludeFlag[Tool] = InputFlag

        self.ToolChainFamily = Info.ToolChainFamily["CC"]
        if self.IsPlatformAutoGen:
            BuildOptions = self.Platform[Info.Arch].BuildOptions
        else:
            BuildOptions = self.Platform.BuildOptions

        for Key in BuildOptions:
            Family = Key[0]
            Target, Tag, Arch, Tool, Attr = Key[1].split("_")
            if Tool not in Info.ToolPath:
                continue
            if Family != None and Family != "" and Family != Info.ToolChainFamily[Tool]:
                continue
            if Target == "*" or Target == Info.BuildTarget:
                if Tag == "*" or Tag == Info.ToolChain:
                    if Arch == "*" or Arch == Info.Arch:
                        Info.BuildOption[Tool] = BuildOptions[Key]
        for Tool in Info.DefaultToolOption:
            if Tool not in Info.BuildOption:
                Info.BuildOption[Tool] = ""

    def GetModuleBuildOption(self, PlatformInfo):
        BuildOption = self.Module.BuildOptions
        OptionList = {}
        for Key in BuildOption:
            Family = Key[0]
            Target, Tag, Arch, Tool, Attr = Key[1].split("_")
            if Tool not in PlatformInfo.ToolPath:
                continue
            if Family != None and Family != "" and Family != PlatformInfo.ToolChainFamily[Tool]:
                continue
            if Target == "*" or Target == self.BuildTarget:
                if Tag == "*" or Tag == self.ToolChain:
                    if Arch == "*" or Arch == self.Arch:
                        OptionList[Tool] = BuildOption[Key]
        for Tool in PlatformInfo.DefaultToolOption:
            if Tool not in OptionList:
                OptionList[Tool] = ""

        return OptionList

    def GetBuildFileList(self, PlatformInfo):
        ToolChainFamily = PlatformInfo.ToolChainFamily["CC"]
        BuildRule = PlatformInfo.BuildRule
        BuildFileList = []
        for F in self.Module.Sources:
            SourceFile = F.SourceFile
            # ToolCode = F.ToolCode
            if F.TagName != "" and F.TagName != self.ToolChain:
                EdkLogger.verbose("The toolchain [%s] for processing file [%s] is found, "
                                  "but [%s] is needed" % (F.TagName, F.SourceFile, self.ToolChain))
                continue
            if F.ToolChainFamily != "" and F.ToolChainFamily != ToolChainFamily:
                EdkLogger.verbose("The file [%s] must be built by tools of [%s], "
                                  "but current toolchain family is [%s]" % (SourceFile, F.ToolChainFamily, ToolChainFamily))
                continue

            Dir = path.dirname(SourceFile)
            if Dir != "":
                Dir = path.join(self.BuildInfo.SourceDir, Dir)
                if Dir not in self.BuildInfo.IncludePathList:
                    self.BuildInfo.IncludePathList.insert(0, Dir)

            # skip unknown file
            Base, Ext = path.splitext(SourceFile)

            # skip file which needs a tool having no matching toolchain family
            FileType, RuleObject = BuildRule.Get(Ext, ToolChainFamily)
            if FileType == None:
                EdkLogger.verbose("Don't know how to process file [%s]." % SourceFile)
                continue

            # unicode must be processed by AutoGen
            if FileType == "Unicode-Text-File":
                self.BuildInfo.UnicodeFileList.append(os.path.join(gWorkspaceDir, self.BuildInfo.SourceDir, SourceFile))
                continue

            # no command, no build
            if RuleObject == None or RuleObject.CommandList == []:
                Buildable = False
                EdkLogger.warn("No rule or command defined for building [%s], ignore file [%s]" % (FileType, SourceFile))
                continue

            if Ext == ".dxs":
                print "###", SourceFile, FileType, RuleObject
            BuildFileList.append([SourceFile, FileType, RuleObject])

        return BuildFileList

    def GetToolChainFamily(self, FileType):
        PlatformInfo = self.BuildInfo.PlatformInfo
        ToolChainFamily = PlatformInfo.ToolChainFamily
        if FileType not in gBuildRuleDatabase[ToolChainFamily]:
            for Family in gBuildRuleDatabase:
                if FileType in gBuildRuleDatabase[Family]:
                    ToolChainFamily = Family
                    break
            else:
                return ""
        FileBuildRule = gBuildRuleDatabase[ToolChainFamily][FileType]
        ToolCodeList = FileBuildRule.ToolList

        ToolChainFamily = ""
        for ToolCode in ToolCodeList:
            # if one tool is not defined in current toolchain, break the build
            if ToolCode in PlatformInfo.ToolChainFamily:
                ToolChainFamily = PlatformInfo.ToolChainFamily[ToolCode]
                break

        return ToolChainFamily

    def GetDependentPackageList(self):
        #if self.Package != None and self.Package not in self.Module.Packages:
        #    self.Module.Packages.insert(0, str(self.Package))

        if self.Arch not in gPackageDatabase:
            raise AutoGenError(msg="[%s] is not supported!")
        PackageDatabase = gPackageDatabase[self.Arch]

        PackageList = []
        for PackageFile in self.Module.Packages:
            if PackageFile in PackageList:
                continue
            if PackageFile not in PackageDatabase:
                raise AutoGenError(FILE_NOT_FOUND, name=PackageFile)
            PackageList.append(PackageDatabase[PackageFile])
        return PackageList

    def GetAutoGenFileList(self, BuildInfo):
        GenC.CreateCode(BuildInfo, self.AutoGenC, self.AutoGenH)
        FileList = []
        if self.AutoGenC.String != "":
            FileList.append("AutoGen.c")
        if self.AutoGenH.String != "":
            FileList.append("AutoGen.h")
            #print self.AutoGenH.String
        return FileList

    def GetSortedLibraryList(self):
        LibraryList = []
        ModuleDatabase = gModuleDatabase[self.Arch]
        for Key in self.Module.LibraryClasses:
            Library = ModuleDatabase[self.Module.LibraryClasses[Key]]
            if Library not in LibraryList:
                LibraryList.append(Library)
        return LibraryList

    def GetDynamicPcdList(self, Platform, Arch):
        PcdList = []
        NotFoundPcdList = set()
        NoDatumTypePcdList = set()
        PcdConsumerList = set()
        for F in Platform.Modules:
            M = gModuleDatabase[Arch][F]
            for Key in M.Pcds:
                PcdFromModule = M.Pcds[Key]
                if not PcdFromModule.IsOverrided:
                    NotFoundPcdList.add(" | ".join(Key))
                    PcdConsumerList.add(str(M))
                    continue

                if Key not in Platform.Pcds:
                    PcdFromPlatform = PcdFromModule
                else:
                    PcdFromPlatform = Platform.Pcds[Key]

                if PcdFromModule.DatumType == "VOID*" and PcdFromPlatform.MaxDatumSize == None:
                    NoDatumTypePcdList.add(" | ".join(Key))
                    PcdConsumerList.add(str(M))

                if PcdFromPlatform.Type in GenC.gDynamicPcd + GenC.gDynamicExPcd:
                    if M.ModuleType in ["PEIM", "PEI_CORE"]:
                        PcdFromPlatform.Phase = "PEI"
                    if PcdFromPlatform not in PcdList:
                        PcdFromPlatform.DatumType = PcdFromModule.DatumType
                        PcdList.append(PcdFromPlatform)

        if len(NotFoundPcdList) > 0 or len(NoDatumTypePcdList) > 0:
            NotFoundPcdListString = "\n\t\t".join(NotFoundPcdList)
            NoDatumTypePcdListString = "\n\t\t".join(NoDatumTypePcdList)
            ModuleListString = "\n\t\t".join(PcdConsumerList)
            raise AutoGenError(msg="\n\tPCD(s) not found in platform:\n\t\t%s"
                                   "\n\tPCD(s) without MaxDatumSize:\n\t\t%s"
                                   "\n\tUsed by:\n\t\t%s\n"
                                   % (NotFoundPcdListString, NoDatumTypePcdListString, ModuleListString))
        return PcdList

    def GeneratePcdTokenNumber(self, Platform, DynamicPcdList):
        PcdTokenNumber = {}
        TokenNumber = 1
        for Pcd in DynamicPcdList:
            if Pcd.Phase == "PEI":
                EdkLogger.debug(EdkLogger.DEBUG_5, "%s %s (%s) -> %d" % (Pcd.TokenCName, Pcd.TokenSpaceGuidCName, Pcd.Phase, TokenNumber))
                PcdTokenNumber[Pcd.TokenCName, Pcd.TokenSpaceGuidCName] = TokenNumber
                TokenNumber += 1

        for Pcd in DynamicPcdList:
            if Pcd.Phase == "DXE":
                EdkLogger.debug(EdkLogger.DEBUG_5, "%s %s (%s) -> %d" % (Pcd.TokenCName, Pcd.TokenSpaceGuidCName, Pcd.Phase, TokenNumber))
                PcdTokenNumber[Pcd.TokenCName, Pcd.TokenSpaceGuidCName] = TokenNumber
                TokenNumber += 1

        PlatformPcds = Platform.Pcds
        for Key in PlatformPcds:
            Pcd = PlatformPcds[Key]
            if Key not in PcdTokenNumber:
                PcdTokenNumber[Key] = TokenNumber
                TokenNumber += 1
        return PcdTokenNumber

    def GetPcdList(self, DependentLibraryList):
        PlatformPcds = self.Platform.Pcds

        PcdList = []
        for PcdKey in self.Module.Pcds:
            Pcd = self.Module.Pcds[PcdKey]
            #if pcdKey not in platformPcds:
            #    EdkLogger.info("%s / %s not in current platform" % pcdKey)
            if (Pcd.Type in GenC.gDynamicPcd + GenC.gDynamicExPcd) and self.Module.ModuleType in ["PEIM", "PEI_CORE"]:
                Pcd.Phase = "PEI"
            PcdList.append(Pcd)
        return PcdList

    def GetGuidList(self):
        Guid = {}
        Key = ""
        for Key in self.Module.Guids:
            for P in self.BuildInfo.DerivedPackageList:
                if Key in P.Guids:
                    Guid[Key] = P.Guids[Key]
                    break
                if Key in P.Protocols:
                    Guid[Key] = P.Protocols[Key]
                    break
                if Key in P.Ppis:
                    Guid[Key] = P.Ppis[Key]
                    break
            else:
                PackageListString = "\n\t".join([str(P) for P in self.BuildInfo.DerivedPackageList])
                raise AutoGenError(msg='GUID [%s] used by [%s] cannot be found in dependent packages:\n\t%s' % (Key, self.Module, PackageListString))
        return Guid

    def GetProtocolGuidList(self):
        Guid = {}
        Key = ""
        for Key in self.Module.Protocols:
            for P in self.BuildInfo.DerivedPackageList:
                if Key in P.Guids:
                    Guid[Key] = P.Guids[Key]
                    break
                if Key in P.Protocols:
                    Guid[Key] = P.Protocols[Key]
                    break
                if Key in P.Ppis:
                    Guid[Key] = P.Ppis[Key]
                    break
            else:
                PackageListString = "\n\t".join([str(P) for P in self.BuildInfo.DerivedPackageList])
                raise AutoGenError(msg='Protocol [%s] used by [%s] cannot be found in dependent packages:\n\t%s' % (Key, self.Module, PackageListString))
        return Guid

    def GetPpiGuidList(self):
        Guid = {}
        Key = ""
        for Key in self.Module.Ppis:
            for P in self.BuildInfo.DerivedPackageList:
                if Key in P.Guids:
                    Guid[Key] = P.Guids[Key]
                    break
                if Key in P.Protocols:
                    Guid[Key] = P.Protocols[Key]
                    break
                if Key in P.Ppis:
                    Guid[Key] = P.Ppis[Key]
                    break
            else:
                PackageListString = "\n\t".join([str(P) for P in self.BuildInfo.DerivedPackageList])
                raise AutoGenError(msg='PPI [%s] used by [%s] cannot be found in dependent packages:\n\t%s' % (Key, self.Module, PackageListString))
        return Guid

    def GetIncludePathList(self, DependentPackageList):
        IncludePathList = []
        for Inc in self.Module.Includes:
            IncludePathList.append(Inc)

        for Package in DependentPackageList:
            PackageDir = path.dirname(Package.DescFilePath)
            IncludePathList.append(PackageDir)
            for Inc in Package.Includes:
                Inc = os.path.join(PackageDir, Inc)
                if Inc not in IncludePathList:
                    IncludePathList.append(Inc)
        return IncludePathList

    def CreateMakefile(self, FilePath=None):
        myBuildOption = {
            "ENABLE_PCH"        :   False,
            "ENABLE_LOCAL_LIB"  :   True,
        }
        if self.IsMakefileCreated:
            return

        if self.IsPlatformAutoGen:
            for Arch in self.BuildInfo:
                Info = self.BuildInfo[Arch]
                for ModuleFile in Info.Platform.Modules:
                    Key = (Info.BuildTarget, Info.ToolChain, Arch, ModuleFile)
                    ModuleAutoGen = None
                    if Key not in gAutoGenDatabase:
                        ModuleAutoGen = AutoGen(ModuleFile, Info.Platform, gWorkspace,
                                                Info.BuildTarget, Info.ToolChain, Info.Arch)
                    else:
                        ModuleAutoGen = gAutoGenDatabase[Key]
                    ModuleAutoGen.CreateMakefile()
        else:
            PlatformInfo = self.BuildInfo.PlatformInfo
            if not self.BuildInfo.IsLibrary:
                if self not in PlatformInfo.ModuleAutoGenList:
                    PlatformInfo.ModuleAutoGenList.append(self)
            elif self not in PlatformInfo.LibraryAutoGenList:
                PlatformInfo.LibraryAutoGenList.append(self)

            for Lib in self.BuildInfo.DependentLibraryList:
                EdkLogger.debug(EdkLogger.DEBUG_1, "###" + str(Lib))
                Key = (self.BuildTarget, self.ToolChain, self.Arch, Lib)
                LibraryAutoGen = None
                if Key not in gAutoGenDatabase:
                    LibraryAutoGen = AutoGen(Lib, self.Platform, gWorkspace,
                                             self.BuildTarget, self.ToolChain, self.Arch)
                else:
                    LibraryAutoGen = gAutoGenDatabase[Key]
                if LibraryAutoGen not in self.BuildInfo.LibraryAutoGenList:
                    self.BuildInfo.LibraryAutoGenList.append(LibraryAutoGen)
                LibraryAutoGen.CreateMakefile()

            Makefile = GenMake.Makefile(self.BuildInfo, myBuildOption)
            F = Makefile.Generate()
            self.IsMakefileCreated = True
            EdkLogger.info("Generated [%s] for module %s [%s]" % (path.basename(F), self.BuildInfo.Name, self.BuildInfo.Arch))
            return F

        Makefile = GenMake.Makefile(self.BuildInfo, myBuildOption)
        F = Makefile.Generate()
        self.IsMakefileCreated = True
        EdkLogger.info("Generated [%s] for platform %s\n" % (path.basename(F), self.BuildInfo[self.Arch[0]].Name))

        return F

    def CreateAutoGenFile(self, FilePath=None):
        if self.IsAutoGenCodeCreated:
            return

        if self.IsPlatformAutoGen:
            for Arch in self.BuildInfo:
                Info = self.BuildInfo[Arch]
                for ModuleFile in Info.Platform.Modules:
                    Key = (Info.BuildTarget, Info.ToolChain, Arch, ModuleFile)
                    ModuleAutoGen = None
                    if Key not in gAutoGenDatabase:
                        ModuleAutoGen = AutoGen(ModuleFile, Info.Platform, gWorkspace,
                                                Info.BuildTarget, Info.ToolChain, Info.Arch)
                    else:
                        ModuleAutoGen = gAutoGenDatabase[Key]
                    ModuleAutoGen.CreateAutoGenFile()
            print
        else:
            PlatformInfo = self.BuildInfo.PlatformInfo
            if not self.BuildInfo.IsLibrary and self not in PlatformInfo.ModuleAutoGenList:
                PlatformInfo.ModuleAutoGenList.append(self)
            elif self.BuildInfo.IsLibrary and self not in PlatformInfo.LibraryAutoGenList:
                PlatformInfo.LibraryAutoGenList.append(self)

            for Lib in self.BuildInfo.DependentLibraryList:
                Key = (self.BuildTarget, self.ToolChain, self.Arch, Lib)
                LibraryAutoGen = None
                if Key not in gAutoGenDatabase:
                    LibraryAutoGen = AutoGen(Lib, self.Platform, gWorkspace,
                                             self.BuildTarget, self.ToolChain, self.Arch)
                else:
                    LibraryAutoGen = gAutoGenDatabase[Key]
                if LibraryAutoGen not in self.BuildInfo.LibraryAutoGenList:
                    self.BuildInfo.LibraryAutoGenList.append(LibraryAutoGen)
                LibraryAutoGen.CreateAutoGenFile()

            AutoGenList = GenC.Generate(os.path.join(self.BuildInfo.WorkspaceDir, self.BuildInfo.DebugDir),
                                        self.AutoGenC, self.AutoGenH)

            if self.BuildInfo.DepexList != []:
                dpx = GenDepex.DependencyExpression(self.BuildInfo.DepexList, self.BuildInfo.ModuleType)
                dpxFile = dpx.Generate(os.path.join(gWorkspaceDir, self.BuildInfo.OutputDir, self.BuildInfo.Name + ".depex"))
                AutoGenList.append(dpxFile)

            self.IsAutoGenCodeCreated = True
            EdkLogger.info("Generated [%s] files for module %s [%s]" % (" ".join([path.basename(f) for f in AutoGenList]), self.BuildInfo.Name, self.BuildInfo.Arch))

            return AutoGenList

# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
if __name__ == '__main__':
    print "Running Operating System =", sys.platform
    ewb = WorkspaceBuild()
    #print ewb.Build.keys()

    myArch = ewb.Build["IA32"].Arch
    print myArch

    myBuild = ewb.Build["IA32"]

    myWorkspace = ewb
    apf = os.path.normpath(ewb.TargetTxt.TargetTxtDictionary["ACTIVE_PLATFORM"][0])
    myPlatform = myBuild.PlatformDatabase[os.path.normpath(apf)]

    #LoadBuildRule(myWorkspace.Workspace.WorkspaceFile('Tools/Conf/build.rule'))

    myToolchain = ewb.TargetTxt.TargetTxtDictionary["TOOL_CHAIN_TAG"][0]
    #print myToolchain

    myBuildTarget = ewb.TargetTxt.TargetTxtDictionary["TARGET"][0]
    #print myBuildTarget

    myBuildOption = {
        "ENABLE_PCH"        :   False,
        "ENABLE_LOCAL_LIB"  :   True,
    }

    def PrintAutoGen(ag):
        bi = ag.ModuleBuildInfo

        print " WorkSpaceDir =",bi.WorkspaceDir
        print " SourceDir =",bi.SourceDir
        print " Is Library =",bi.IsLibrary
        print " BaseName =",bi.BaseName
        print " FileBase =",bi.FileBase
        print " FileExt =",bi.FileExt
        print " BuildDir =",bi.BuildDir
        print " OutputDir =",bi.OutputDir
        print " DebugDir =",bi.DebugDir
        print " MakefileDir =",bi.MakefileDir

        print " Include Path:","\n   ","\n    ".join(bi.InclduePathList)
        print " SourceFileList:","\n   ","\n    ".join(bi.SourceFileList)

        print " BuildOption:","\n   ","\n    ".join(["%s = %s" % (tool,bi.BuildOption[tool]) for tool in bi.BuildOption])
        print " PcdList:","\n   ","\n    ".join([pcd.TokenCName for pcd in bi.PcdList])
        print " GuidList:","\n   ","\n    ".join(bi.GuidList)
        print " ProtocolList:","\n   ","\n    ".join(bi.ProtocolList)
        print " PpiList:","\n   ","\n    ".join(bi.PpiList)
        print " LibraryList:","\n   ","\n    ".join([str(l) for l in bi.DependentLibraryList])

        print

##        for key in gAutoGenDatabase:
##            if str(myPlatform) == str(key[0]):
##                pi = gAutoGenDatabase[key]
##                print " BuildDir =",pi.BuildDir
##                print " OutputDir =",pi.OutputDir
##                print " DebugDir =",pi.DebugDir
##                print " LibraryDir =",pi.LibraryDir
##                print " FvDir =",pi.FvDir
##                print " MakefileDir =",pi.MakefileDir
##                print " PcdTokenNumber:","\n   ","\n    ".join(["%s = %s" % (pcd,pi.PcdTokenNumber[pcd]) for pcd in pi.PcdTokenNumber])
##                print " DynamicPcdList:","\n   ","\n    ".join([str(pcd) for pcd in pi.DynamicPcdList])
##
##                print " ToolPath:","\n   ","\n    ".join(["%s = %s" % (tool,pi.ToolPath[tool]) for tool in pi.ToolPath])
##                print " ToolDynamicLib:","\n   ","\n    ".join(["%s = %s" % (tool,pi.ToolDynamicLib[tool]) for tool in pi.ToolDynamicLib])
##                print " ToolStaticLib:","\n   ","\n    ".join(["%s = %s" % (tool,pi.ToolStaticLib[tool]) for tool in pi.ToolStaticLib])
##                print " ToolChainFamily:","\n   ","\n    ".join(["%s = %s" % (tool,pi.ToolChainFamily[tool]) for tool in pi.ToolChainFamily])
##                print " BuildOption:","\n   ","\n    ".join(["%s = %s" % (tool,pi.BuildOption[tool]) for tool in pi.BuildOption])
##                print " DefaultToolOption:","\n   ","\n    ".join(["%s = %s" % (tool,pi.DefaultToolOption[tool]) for tool in pi.DefaultToolOption])

    for mf in myBuild.ModuleDatabase:
        #mf = "MdePkg\\Library\\BaseLib\\BaseLib.inf"
        #if mf in myPlatform.Modules and mf in myBuild.ModuleDatabase:
        #print mf
        myModule = myBuild.ModuleDatabase[mf]
        ag = AutoGen(myModule, myPlatform, myWorkspace, myBuildTarget, myToolchain, myArch)
        ag.CreateAutoGenFile()
        ag.CreateMakefile()

        #PrintAutoGen(ag)
##        for lib in ag.ModuleBuildInfo.DependentLibraryList:
##            ag = AutoGen(lib, myPlatform, myWorkspace, myArch, myToolchain, myBuildTarget)
##            ag.CreateAutoGenFile()
##            ag.CreateMakefile()
##            #PrintAutoGen(ag)
    platformAutoGen = AutoGen(None, apf, myWorkspace, myBuildTarget, myToolchain, myWorkspace.SupArchList)
    platformAutoGen.CreateAutoGenFile()
    platformAutoGen.CreateMakefile()
