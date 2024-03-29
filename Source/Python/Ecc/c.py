import sys
import os
import re
import CodeFragmentCollector
import FileProfile
from CommonDataClass import DataClass
import Database
from Common import EdkLogger
from EccToolError import *
import EccGlobalData
import MetaDataParser

IncludeFileListDict = {}
AllIncludeFileListDict = {}
IncludePathListDict = {}
ComplexTypeDict = {}
SUDict = {}
IgnoredKeywordList = ['EFI_ERROR']

def GetIgnoredDirListPattern():
    p = re.compile(r'.*[\\/](?:BUILD|INTELRESTRICTEDTOOLS|INTELRESTRICTEDPKG|PCCTS)[\\/].*')
    return p

def GetFuncDeclPattern():
    p = re.compile(r'(?:EFIAPI|EFI_BOOT_SERVICE|EFI_RUNTIME_SERVICE)?\s*[_\w]+\s*\(.*\)$', re.DOTALL)
    return p

def GetArrayPattern():
    p = re.compile(r'[_\w]*\s*[\[.*\]]+')
    return p

def GetTypedefFuncPointerPattern():
    p = re.compile('[_\w\s]*\([\w\s]*\*+\s*[_\w]+\s*\)\s*\(.*\)', re.DOTALL)
    return p

def GetDB():
    return EccGlobalData.gDb

def GetConfig():
    return EccGlobalData.gConfig

def PrintErrorMsg(ErrorType, Msg, TableName, ItemId):
    Msg = Msg.replace('\n', '').replace('\r', '')
    MsgPartList = Msg.split()
    Msg = ''
    for Part in MsgPartList:
        Msg += Part
        Msg += ' '
    GetDB().TblReport.Insert(ErrorType, OtherMsg = Msg, BelongsToTable = TableName, BelongsToItem = ItemId)

def GetIdType(Str):
    Type = DataClass.MODEL_UNKNOWN
    Str = Str.replace('#', '# ')
    List = Str.split()
    if List[1] == 'include':
        Type = DataClass.MODEL_IDENTIFIER_INCLUDE
    elif List[1] == 'define':
        Type = DataClass.MODEL_IDENTIFIER_MACRO_DEFINE
    elif List[1] == 'ifdef':
        Type = DataClass.MODEL_IDENTIFIER_MACRO_IFDEF
    elif List[1] == 'ifndef':
        Type = DataClass.MODEL_IDENTIFIER_MACRO_IFNDEF
    elif List[1] == 'endif':
        Type = DataClass.MODEL_IDENTIFIER_MACRO_ENDIF
    elif List[1] == 'pragma':
        Type = DataClass.MODEL_IDENTIFIER_MACRO_PROGMA
    else:
        Type = DataClass.MODEL_UNKNOWN
    return Type

def SuOccurInTypedef (Su, TdList):
    for Td in TdList:
        if Su.StartPos[0] >= Td.StartPos[0] and Su.EndPos[0] <= Td.EndPos[0]:
            return True
    return False

def GetIdentifierList():
    IdList = []
    for comment in FileProfile.CommentList:
        IdComment = DataClass.IdentifierClass(-1, '', '', '', comment.Content, DataClass.MODEL_IDENTIFIER_COMMENT, -1, -1, comment.StartPos[0],comment.StartPos[1],comment.EndPos[0],comment.EndPos[1])
        IdList.append(IdComment)
        
    for pp in FileProfile.PPDirectiveList:
        Type = GetIdType(pp.Content)
        IdPP = DataClass.IdentifierClass(-1, '', '', '', pp.Content, Type, -1, -1, pp.StartPos[0],pp.StartPos[1],pp.EndPos[0],pp.EndPos[1])
        IdList.append(IdPP)
        
    for pe in FileProfile.PredicateExpressionList:
        IdPE = DataClass.IdentifierClass(-1, '', '', '', pe.Content, DataClass.MODEL_IDENTIFIER_PREDICATE_EXPRESSION, -1, -1, pe.StartPos[0],pe.StartPos[1],pe.EndPos[0],pe.EndPos[1])
        IdList.append(IdPE)
        
    FuncDeclPattern = GetFuncDeclPattern()
    ArrayPattern = GetArrayPattern()
    for var in FileProfile.VariableDeclarationList:
        DeclText = var.Declarator.lstrip()
        FuncPointerPattern = GetTypedefFuncPointerPattern()
        if FuncPointerPattern.match(DeclText):
            continue
        VarNameStartLine = var.NameStartPos[0]
        VarNameStartColumn = var.NameStartPos[1]
        FirstChar = DeclText[0]
        while not FirstChar.isalpha() and FirstChar != '_':
            if FirstChar == '*':
                var.Modifier += '*'
                VarNameStartColumn += 1
                DeclText = DeclText.lstrip('*')
            elif FirstChar == '\r':
                DeclText = DeclText.lstrip('\r\n').lstrip('\r')
                VarNameStartLine += 1
                VarNameStartColumn = 0
            elif FirstChar == '\n':
                DeclText = DeclText.lstrip('\n')
                VarNameStartLine += 1
                VarNameStartColumn = 0
            elif FirstChar == ' ':
                DeclText = DeclText.lstrip(' ')
                VarNameStartColumn += 1
            elif FirstChar == '\t':
                DeclText = DeclText.lstrip('\t')
                VarNameStartColumn += 8
            else:
                DeclText = DeclText[1:]
                VarNameStartColumn += 1
            FirstChar = DeclText[0]
            
        var.Declarator = DeclText
        if FuncDeclPattern.match(var.Declarator):
            DeclSplitList = var.Declarator.split('(')     
            FuncName = DeclSplitList[0].strip()
            FuncNamePartList = FuncName.split()
            if len(FuncNamePartList) > 1:
                FuncName = FuncNamePartList[-1].strip()
                NameStart = DeclSplitList[0].rfind(FuncName)
                var.Declarator = var.Declarator[NameStart:]
                if NameStart > 0:
                    var.Modifier += ' ' + DeclSplitList[0][0:NameStart]
                    Index = 0
                    PreChar = ''
                    while Index < NameStart:
                        FirstChar = DeclSplitList[0][Index]
                        if DeclSplitList[0][Index:].startswith('EFIAPI'):
                            Index += 6
                            VarNameStartColumn += 6
                            PreChar = ''
                            continue
                        elif FirstChar == '\r':
                            Index += 1
                            VarNameStartLine += 1
                            VarNameStartColumn = 0
                        elif FirstChar == '\n':
                            Index += 1
                            if PreChar != '\r':
                                VarNameStartLine += 1
                                VarNameStartColumn = 0
                        elif FirstChar == ' ':
                            Index += 1
                            VarNameStartColumn += 1
                        elif FirstChar == '\t':
                            Index += 1
                            VarNameStartColumn += 8
                        else:
                            Index += 1
                            VarNameStartColumn += 1
                        PreChar = FirstChar
            IdVar = DataClass.IdentifierClass(-1, var.Modifier, '', var.Declarator, FuncName, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION, -1, -1, var.StartPos[0], var.StartPos[1], VarNameStartLine, VarNameStartColumn)
            IdList.append(IdVar)
            continue
        
        if var.Declarator.find('{') == -1:      
            for decl in var.Declarator.split(','):
                DeclList = decl.split('=')
                Name = DeclList[0].strip()
                if ArrayPattern.match(Name):
                    LSBPos = var.Declarator.find('[')
                    var.Modifier += ' ' + Name[LSBPos:]
                    Name = Name[0:LSBPos]
            
                IdVar = DataClass.IdentifierClass(-1, var.Modifier, '', Name, (len(DeclList) > 1 and [DeclList[1]]or [''])[0], DataClass.MODEL_IDENTIFIER_VARIABLE, -1, -1, var.StartPos[0],var.StartPos[1], VarNameStartLine, VarNameStartColumn)
                IdList.append(IdVar)
        else:
            DeclList = var.Declarator.split('=')
            Name = DeclList[0].strip()
            if ArrayPattern.match(Name):
                LSBPos = var.Declarator.find('[')
                var.Modifier += ' ' + Name[LSBPos:]
                Name = Name[0:LSBPos]
            IdVar = DataClass.IdentifierClass(-1, var.Modifier, '', Name, (len(DeclList) > 1 and [DeclList[1]]or [''])[0], DataClass.MODEL_IDENTIFIER_VARIABLE, -1, -1, var.StartPos[0],var.StartPos[1], VarNameStartLine, VarNameStartColumn)
            IdList.append(IdVar)
            
    for enum in FileProfile.EnumerationDefinitionList:
        LBPos = enum.Content.find('{')
        RBPos = enum.Content.find('}')
        Name = enum.Content[4:LBPos].strip()
        Value = enum.Content[LBPos+1:RBPos]
        IdEnum = DataClass.IdentifierClass(-1, '', '', Name, Value, DataClass.MODEL_IDENTIFIER_ENUMERATE, -1, -1, enum.StartPos[0],enum.StartPos[1],enum.EndPos[0],enum.EndPos[1])
        IdList.append(IdEnum)
        
    for su in FileProfile.StructUnionDefinitionList:
        if SuOccurInTypedef(su, FileProfile.TypedefDefinitionList):
            continue
        Type = DataClass.MODEL_IDENTIFIER_STRUCTURE
        SkipLen = 6
        if su.Content.startswith('union'):
            Type = DataClass.MODEL_IDENTIFIER_UNION
            SkipLen = 5
        LBPos = su.Content.find('{')
        RBPos = su.Content.find('}')
        if LBPos == -1 or RBPos == -1:
            Name = su.Content[SkipLen:].strip()
            Value = ''
        else:
            Name = su.Content[SkipLen:LBPos].strip()
            Value = su.Content[LBPos:RBPos+1]
        IdPE = DataClass.IdentifierClass(-1, '', '', Name, Value, Type, -1, -1, su.StartPos[0],su.StartPos[1],su.EndPos[0],su.EndPos[1])
        IdList.append(IdPE)
    
    TdFuncPointerPattern = GetTypedefFuncPointerPattern()    
    for td in FileProfile.TypedefDefinitionList:
        Modifier = ''
        Name = td.ToType
        Value = td.FromType
        if TdFuncPointerPattern.match(td.ToType):
            Modifier = td.FromType
            LBPos = td.ToType.find('(')
            TmpStr = td.ToType[LBPos+1:].strip()
            StarPos = TmpStr.find('*')
            if StarPos != -1:
                Modifier += ' ' + TmpStr[0:StarPos]
            while TmpStr[StarPos] == '*':
#                Modifier += ' ' + '*'
                StarPos += 1
            TmpStr = TmpStr[StarPos:].strip()
            RBPos = TmpStr.find(')')
            Name = TmpStr[0:RBPos]
            Value = 'FP' + TmpStr[RBPos + 1:]
        else:
            while Name.startswith('*'):
                Value += ' ' + '*'
                Name = Name.lstrip('*').strip()
        IdTd = DataClass.IdentifierClass(-1, Modifier, '', Name, Value, DataClass.MODEL_IDENTIFIER_TYPEDEF, -1, -1, td.StartPos[0],td.StartPos[1],td.EndPos[0],td.EndPos[1])
        IdList.append(IdTd)
        
    for funcCall in FileProfile.FunctionCallingList:
        IdFC = DataClass.IdentifierClass(-1, '', '', funcCall.FuncName, funcCall.ParamList, DataClass.MODEL_IDENTIFIER_FUNCTION_CALLING, -1, -1, funcCall.StartPos[0],funcCall.StartPos[1],funcCall.EndPos[0],funcCall.EndPos[1])
        IdList.append(IdFC)
    return IdList

def GetParamList(FuncDeclarator, FuncNameLine = 0, FuncNameOffset = 0):
    ParamIdList = []
    DeclSplitList = FuncDeclarator.split('(')
    if len(DeclSplitList) < 2:
        return ParamIdList
    FuncName = DeclSplitList[0]
    ParamStr = DeclSplitList[1].rstrip(')')
    LineSkipped = 0
    OffsetSkipped = 0
    TailChar = FuncName[-1]
    while not TailChar.isalpha() and TailChar != '_':
        
        if TailChar == '\n':
            FuncName = FuncName.rstrip('\r\n').rstrip('\n')
            LineSkipped += 1
            OffsetSkipped = 0
        elif TailChar == '\r':
            FuncName = FuncName.rstrip('\r')
            LineSkipped += 1
            OffsetSkipped = 0
        elif TailChar == ' ':
            FuncName = FuncName.rstrip(' ')
            OffsetSkipped += 1
        elif TailChar == '\t':
            FuncName = FuncName.rstrip('\t')
            OffsetSkipped += 8
        else:
            FuncName = FuncName[:-1]
        TailChar = FuncName[-1]
               
    OffsetSkipped += 1 #skip '('
    
    for p in ParamStr.split(','):
        ListP = p.split()
        if len(ListP) == 0:
            continue
        ParamName = ListP[-1]
        DeclText = ParamName.strip()
        RightSpacePos = p.rfind(ParamName)
        ParamModifier = p[0:RightSpacePos]
        if ParamName == 'OPTIONAL':
            if ParamModifier == '':
                ParamModifier += ' ' + 'OPTIONAL'
                DeclText = ''
            else:
                ParamName = ListP[-2]
                DeclText = ParamName.strip()
                RightSpacePos = p.rfind(ParamName)
                ParamModifier = p[0:RightSpacePos]
                ParamModifier += 'OPTIONAL'
        while DeclText.startswith('*'):
            ParamModifier += ' ' + '*'
            DeclText = DeclText.lstrip('*').strip()
        ParamName = DeclText
        # ignore array length if exists.
        LBIndex = ParamName.find('[')
        if LBIndex != -1:
            ParamName = ParamName[0:LBIndex]
        
        Start = RightSpacePos
        Index = 0
        PreChar = ''
        while Index < Start:
            FirstChar = p[Index]
                
            if FirstChar == '\r':
                Index += 1
                LineSkipped += 1
                OffsetSkipped = 0
            elif FirstChar == '\n':
                Index += 1
                if PreChar != '\r':
                    LineSkipped += 1
                    OffsetSkipped = 0
            elif FirstChar == ' ':
                Index += 1
                OffsetSkipped += 1
            elif FirstChar == '\t':
                Index += 1
                OffsetSkipped += 8
            else:
                Index += 1
                OffsetSkipped += 1
            PreChar = FirstChar
            
        ParamBeginLine = FuncNameLine + LineSkipped
        ParamBeginOffset = FuncNameOffset + OffsetSkipped
        
        Index = Start + len(ParamName)
        PreChar = ''
        while Index < len(p):
            FirstChar = p[Index]
                
            if FirstChar == '\r':
                Index += 1
                LineSkipped += 1
                OffsetSkipped = 0
            elif FirstChar == '\n':
                Index += 1
                if PreChar != '\r':
                    LineSkipped += 1
                    OffsetSkipped = 0
            elif FirstChar == ' ':
                Index += 1
                OffsetSkipped += 1
            elif FirstChar == '\t':
                Index += 1
                OffsetSkipped += 8
            else:
                Index += 1
                OffsetSkipped += 1
            PreChar = FirstChar
        
        ParamEndLine = FuncNameLine + LineSkipped
        ParamEndOffset = FuncNameOffset + OffsetSkipped
        
        IdParam = DataClass.IdentifierClass(-1, ParamModifier, '', ParamName, '', DataClass.MODEL_IDENTIFIER_PARAMETER, -1, -1, ParamBeginLine, ParamBeginOffset, ParamEndLine, ParamEndOffset)
        ParamIdList.append(IdParam)
        
        OffsetSkipped += 1 #skip ','
    
    return ParamIdList
    
def GetFunctionList():
    FuncObjList = []
    for FuncDef in FileProfile.FunctionDefinitionList:
        ParamIdList = []
        DeclText = FuncDef.Declarator.lstrip()
        FuncNameStartLine = FuncDef.NamePos[0]
        FuncNameStartColumn = FuncDef.NamePos[1]
        FirstChar = DeclText[0]
        while not FirstChar.isalpha() and FirstChar != '_':
            if FirstChar == '*':
                FuncDef.Modifier += '*'
                FuncNameStartColumn += 1
                DeclText = DeclText.lstrip('*')
            elif FirstChar == '\r':
                DeclText = DeclText.lstrip('\r\n').lstrip('\r')
                FuncNameStartLine += 1
                FuncNameStartColumn = 0
            elif FirstChar == '\n':
                DeclText = DeclText.lstrip('\n')
                FuncNameStartLine += 1
                FuncNameStartColumn = 0
            elif FirstChar == ' ':
                DeclText = DeclText.lstrip(' ')
                FuncNameStartColumn += 1
            elif FirstChar == '\t':
                DeclText = DeclText.lstrip('\t')
                FuncNameStartColumn += 8
            else:
                DeclText = DeclText[1:]
                FuncNameStartColumn += 1
            FirstChar = DeclText[0]
        
        FuncDef.Declarator = DeclText
        DeclSplitList = FuncDef.Declarator.split('(')
        if len(DeclSplitList) < 2:
            continue
        
        FuncName = DeclSplitList[0]
        FuncNamePartList = FuncName.split()
        if len(FuncNamePartList) > 1:
            FuncName = FuncNamePartList[-1]
            NameStart = DeclSplitList[0].rfind(FuncName)
            if NameStart > 0:
                FuncDef.Modifier += ' ' + DeclSplitList[0][0:NameStart]
                Index = 0
                PreChar = ''
                while Index < NameStart:
                    FirstChar = DeclSplitList[0][Index]
                    if DeclSplitList[0][Index:].startswith('EFIAPI'):
                        Index += 6
                        FuncNameStartColumn += 6
                        PreChar = ''
                        continue
                    elif FirstChar == '\r':
                        Index += 1
                        FuncNameStartLine += 1
                        FuncNameStartColumn = 0
                    elif FirstChar == '\n':
                        Index += 1
                        if PreChar != '\r':
                            FuncNameStartLine += 1
                            FuncNameStartColumn = 0
                    elif FirstChar == ' ':
                        Index += 1
                        FuncNameStartColumn += 1
                    elif FirstChar == '\t':
                        Index += 1
                        FuncNameStartColumn += 8
                    else:
                        Index += 1
                        FuncNameStartColumn += 1
                    PreChar = FirstChar
                
        FuncObj = DataClass.FunctionClass(-1, FuncDef.Declarator, FuncDef.Modifier, FuncName.strip(), '', FuncDef.StartPos[0],FuncDef.StartPos[1],FuncDef.EndPos[0],FuncDef.EndPos[1], FuncDef.LeftBracePos[0], FuncDef.LeftBracePos[1], -1, ParamIdList, [], FuncNameStartLine, FuncNameStartColumn)
        FuncObjList.append(FuncObj)
        
    return FuncObjList

def GetFileModificationTimeFromDB(FullFileName):
    TimeValue = 0.0
    Db = GetDB()
    SqlStatement = """ select TimeStamp
                       from File
                       where FullPath = \'%s\'
                   """ % (FullFileName)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        TimeValue = Result[0]
    return TimeValue

def CollectSourceCodeDataIntoDB(RootDir):
    FileObjList = []
    tuple = os.walk(RootDir)
    IgnoredPattern = GetIgnoredDirListPattern()
    ParseErrorFileList = []

    for dirpath, dirnames, filenames in tuple:
        if IgnoredPattern.match(dirpath.upper()):
            continue
        for f in filenames:
            FullName = os.path.join(dirpath, f)
            if os.path.splitext(f)[1] in ('.h', '.c'):
                EdkLogger.info("Parsing " + FullName)
                model = f.endswith('c') and DataClass.MODEL_FILE_C or DataClass.MODEL_FILE_H
                collector = CodeFragmentCollector.CodeFragmentCollector(FullName)
                try:
                    collector.ParseFile()
                except UnicodeError:
                    ParseErrorFileList.append(FullName)
                    collector.CleanFileProfileBuffer()
                    collector.ParseFileWithClearedPPDirective()
#                collector.PrintFragments()
                BaseName = os.path.basename(f)
                DirName = os.path.dirname(FullName)
                Ext = os.path.splitext(f)[1].lstrip('.')
                ModifiedTime = os.path.getmtime(FullName)
                FileObj = DataClass.FileClass(-1, BaseName, Ext, DirName, FullName, model, ModifiedTime, GetFunctionList(), GetIdentifierList(), [])
                FileObjList.append(FileObj)
                collector.CleanFileProfileBuffer()   
    
    if len(ParseErrorFileList) > 0:
        EdkLogger.info("Found unrecoverable error during parsing:\n\t%s\n" % "\n\t".join(ParseErrorFileList))
    
    Db = GetDB()    
    for file in FileObjList:    
        Db.InsertOneFile(file)

    Db.UpdateIdentifierBelongsToFunction()

def GetTableID(FullFileName, ErrorMsgList = None):
    if ErrorMsgList == None:
        ErrorMsgList = []
        
    Db = GetDB()
    SqlStatement = """ select ID
                       from File
                       where FullPath like '%s'
                   """ % FullFileName
    
    ResultSet = Db.TblFile.Exec(SqlStatement)

    FileID = -1
    for Result in ResultSet:
        if FileID != -1:
            ErrorMsgList.append('Duplicate file ID found in DB for file %s' % FullFileName)
            return -2
        FileID = Result[0]
    if FileID == -1:
        ErrorMsgList.append('NO file ID found in DB for file %s' % FullFileName)
        return -1
    return FileID

def GetIncludeFileList(FullFileName):
    IFList = IncludeFileListDict.get(FullFileName)
    if IFList != None:
        return IFList
    
    FileID = GetTableID(FullFileName)
    if FileID < 0:
        return []
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_INCLUDE)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    IncludeFileListDict[FullFileName] = ResultSet
    return ResultSet

def GetFullPathOfIncludeFile(Str, IncludePathList):
    for IncludePath in IncludePathList:
        FullPath = os.path.join(IncludePath, Str)
        FullPath = os.path.normpath(FullPath)
        if os.path.exists(FullPath):
            return FullPath
    return None

def GetAllIncludeFiles(FullFileName):
    if AllIncludeFileListDict.get(FullFileName) != None:
        return AllIncludeFileListDict.get(FullFileName)
    
    IncludePathList = IncludePathListDict.get(os.path.dirname(FullFileName))
    if IncludePathList == None:
        IncludePathList = MetaDataParser.GetIncludeListOfFile(EccGlobalData.gWorkspace, FullFileName, GetDB())
        IncludePathList.insert(0, os.path.dirname(FullFileName))
        IncludePathListDict[os.path.dirname(FullFileName)] = IncludePathList
    IncludeFileQueue = []
    for IncludeFile in GetIncludeFileList(FullFileName):
        FileName = IncludeFile[0].lstrip('#').strip()
        FileName = FileName.lstrip('include').strip()
        FileName = FileName.strip('\"')
        FileName = FileName.lstrip('<').rstrip('>').strip()
        FullPath = GetFullPathOfIncludeFile(FileName, IncludePathList)
        if FullPath != None:
            IncludeFileQueue.append(FullPath)
        
    i = 0
    while i < len(IncludeFileQueue):
        for IncludeFile in GetIncludeFileList(IncludeFileQueue[i]):
            FileName = IncludeFile[0].lstrip('#').strip()
            FileName = FileName.lstrip('include').strip()
            FileName = FileName.strip('\"')
            FileName = FileName.lstrip('<').rstrip('>').strip()
            FullPath = GetFullPathOfIncludeFile(FileName, IncludePathList)
            if FullPath != None and FullPath not in IncludeFileQueue:
                IncludeFileQueue.insert(i + 1, FullPath)
        i += 1
    
    AllIncludeFileListDict[FullFileName] = IncludeFileQueue
    return IncludeFileQueue

def GetPredicateListFromPredicateExpStr(PES):

    PredicateList = []
    i = 0
    PredicateBegin = 0
    #PredicateEnd = 0
    LogicOpPos = -1
    p = GetFuncDeclPattern()
    while i < len(PES) - 1:
        if (PES[i].isalnum() or PES[i] == '_') and LogicOpPos > PredicateBegin:
            PredicateBegin = i
        if (PES[i] == '&' and PES[i+1] == '&') or (PES[i] == '|' and PES[i+1] == '|'):
            LogicOpPos = i
            Exp = PES[PredicateBegin:i].strip()
            # Exp may contain '.' or '->'
            TmpExp = Exp.replace('.', '').replace('->', '')
            if p.match(TmpExp):
                PredicateList.append(Exp)
            else:
                PredicateList.append(Exp.rstrip(';').rstrip(')').strip())
        i += 1
    
    if PredicateBegin > LogicOpPos:
        while PredicateBegin < len(PES):
            if PES[PredicateBegin].isalnum() or PES[PredicateBegin] == '_':
                break
            PredicateBegin += 1
        Exp = PES[PredicateBegin:len(PES)].strip()
        # Exp may contain '.' or '->'
        TmpExp = Exp.replace('.', '').replace('->', '')
        if p.match(TmpExp):
            PredicateList.append(Exp)
        else:
            PredicateList.append(Exp.rstrip(';').rstrip(')').strip())
    return PredicateList
    
def GetCNameList(Lvalue):
    Lvalue += ' '
    i = 0
    SearchBegin = 0
    VarStart = -1
    VarEnd = -1
    VarList = []
    while SearchBegin < len(Lvalue):
        while i < len(Lvalue):
            if Lvalue[i].isalnum() or Lvalue[i] == '_':
                if VarStart == -1:
                    VarStart = i
                VarEnd = i
                i += 1
            elif VarEnd != -1:
                VarList.append(Lvalue[VarStart:VarEnd+1])
                i += 1
                break
            else:
                i += 1
        if VarEnd == -1:
            break
        
        
        DotIndex = Lvalue[VarEnd:].find('.')
        ArrowIndex = Lvalue[VarEnd:].find('->')
        if DotIndex == -1 and ArrowIndex == -1:
            break
        elif DotIndex == -1 and ArrowIndex != -1:
            SearchBegin = VarEnd + ArrowIndex
        elif ArrowIndex == -1 and DotIndex != -1:
            SearchBegin = VarEnd + DotIndex
        else:
            SearchBegin = VarEnd + ((DotIndex < ArrowIndex) and DotIndex or ArrowIndex) 
            
        i = SearchBegin
        VarStart = -1
        VarEnd = -1
    
    return VarList    

def SplitPredicateByOp(Str, Op, IsFuncCalling = False):

    Name = Str.strip()
    Value = None
    
    if IsFuncCalling:
        Index = 0
        LBFound = False
        UnmatchedLBCount = 0
        while Index < len(Str):
            while not LBFound and Str[Index] != '_' and not Str[Index].isalnum():
                Index += 1
            
            while not LBFound and (Str[Index].isalnum() or Str[Index] == '_'):
                Index += 1
            # maybe type-cast at the begining, skip it.
            RemainingStr = Str[Index:].lstrip()
            if RemainingStr.startswith(')') and not LBFound:
                Index += 1
                continue
            
            if RemainingStr.startswith('(') and not LBFound:
                LBFound = True
                
            if Str[Index] == '(':
                UnmatchedLBCount += 1
                Index += 1
                continue
                
            if Str[Index] == ')':
                UnmatchedLBCount -= 1
                Index += 1
                if UnmatchedLBCount == 0:
                    break
                continue
            
            Index += 1
                
        if UnmatchedLBCount > 0:
            return [Name]
            
        IndexInRemainingStr = Str[Index:].find(Op)
        if IndexInRemainingStr == -1:
            return [Name]
        
        Name = Str[0:Index + IndexInRemainingStr].strip()
        Value = Str[Index+IndexInRemainingStr+len(Op):].strip()
        return [Name, Value]
    
    TmpStr = Str.rstrip(';').rstrip(')')
    while True:
        Index = TmpStr.rfind(Op)
        if Index == -1:
            return [Name]
        
        if Str[Index - 1].isalnum() or Str[Index - 1].isspace() or Str[Index - 1] == ')':
            Name = Str[0:Index].strip()
            Value = Str[Index + len(Op):].strip()
            return [Name, Value]   
    
        TmpStr = Str[0:Index - 1]

def SplitPredicateStr(Str):
    IsFuncCalling = False
    p = GetFuncDeclPattern()
    TmpStr = Str.replace('.', '').replace('->', '')
    if p.match(TmpStr):
        IsFuncCalling = True
    
    PredPartList = SplitPredicateByOp(Str, '==', IsFuncCalling)
    if len(PredPartList) > 1:
        return [PredPartList, '==']
    
    PredPartList = SplitPredicateByOp(Str, '!=', IsFuncCalling)
    if len(PredPartList) > 1:
        return [PredPartList, '!=']
    
    PredPartList = SplitPredicateByOp(Str, '>=', IsFuncCalling)
    if len(PredPartList) > 1:
        return [PredPartList, '>=']
        
    PredPartList = SplitPredicateByOp(Str, '<=', IsFuncCalling)
    if len(PredPartList) > 1:
        return [PredPartList, '<=']
        
    PredPartList = SplitPredicateByOp(Str, '>', IsFuncCalling)
    if len(PredPartList) > 1:
        return [PredPartList, '>']
        
    PredPartList = SplitPredicateByOp(Str, '<', IsFuncCalling)
    if len(PredPartList) > 1:
        return [PredPartList, '<']
        
    return [[Str, None], None]

def GetFuncContainsPE(ExpLine, ResultSet):
    for Result in ResultSet:
        if Result[0] < ExpLine and Result[1] > ExpLine:
            return Result
    return None

def PatternInModifier(Modifier, SubStr):
    PartList = Modifier.split()
    for Part in PartList:
        if Part == SubStr:
            return True
    return False

def GetDataTypeFromModifier(ModifierStr):
    MList = ModifierStr.split()
    for M in MList:
        if M in EccGlobalData.gConfig.ModifierList:
            MList.remove(M)
        # remove array sufix
        if M.startswith('['):
            MList.remove(M)
            
    ReturnType = ''
    for M in MList:
        ReturnType += M + ' '
        
    ReturnType = ReturnType.strip()
    if len(ReturnType) == 0:
        ReturnType = 'VOID'
    return ReturnType

def DiffModifier(Str1, Str2):
    PartList1 = Str1.split()
    PartList2 = Str2.split()
    if PartList1 == PartList2:
        return False
    else:
        return True
    
def GetTypedefDict(FullFileName):
    
    Dict = ComplexTypeDict.get(FullFileName)
    if Dict != None:
        return Dict
    
    FileID = GetTableID(FullFileName)
    FileTable = 'Identifier' + str(FileID)
    Db = GetDB()
    SqlStatement = """ select Modifier, Name, Value, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_TYPEDEF)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    
    Dict = {}
    for Result in ResultSet:
        if len(Result[0]) == 0:
            Dict[Result[1]] = Result[2]
        
    IncludeFileList = GetAllIncludeFiles(FullFileName)
    for F in IncludeFileList:
        FileID = GetTableID(F)
        if FileID < 0:
            continue
    
        FileTable = 'Identifier' + str(FileID)
        SqlStatement = """ select Modifier, Name, Value, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_TYPEDEF)
        ResultSet = Db.TblFile.Exec(SqlStatement)
    
        for Result in ResultSet:
            if not Result[2].startswith('FP ('):
                Dict[Result[1]] = Result[2]
            else:
                if len(Result[0]) == 0:
                    Dict[Result[1]] = 'VOID'
                else:
                    Dict[Result[1]] = GetDataTypeFromModifier(Result[0])
                
    ComplexTypeDict[FullFileName] = Dict
    return Dict

def GetSUDict(FullFileName):
    
    Dict = SUDict.get(FullFileName)
    if Dict != None:
        return Dict
    
    FileID = GetTableID(FullFileName)
    FileTable = 'Identifier' + str(FileID)
    Db = GetDB()
    SqlStatement = """ select Name, Value, ID
                       from %s
                       where Model = %d or Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_STRUCTURE, DataClass.MODEL_IDENTIFIER_UNION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    
    Dict = {}
    for Result in ResultSet:
        if len(Result[1]) > 0:
            Dict[Result[0]] = Result[1]
        
    IncludeFileList = GetAllIncludeFiles(FullFileName)
    for F in IncludeFileList:
        FileID = GetTableID(F)
        if FileID < 0:
            continue
    
        FileTable = 'Identifier' + str(FileID)
        SqlStatement = """ select Name, Value, ID
                       from %s
                       where Model = %d or Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_STRUCTURE, DataClass.MODEL_IDENTIFIER_UNION)
        ResultSet = Db.TblFile.Exec(SqlStatement)
    
        for Result in ResultSet:
            if len(Result[1]) > 0:
                Dict[Result[0]] = Result[1]
                
    SUDict[FullFileName] = Dict
    return Dict

def StripComments(Str):
    StrippedStr = ''
    List = Str.splitlines()
    InComment = False
    for StrPart in List:
        Index = StrPart.find('//')
        if Index != -1 and not InComment:
            StrippedStr += StrPart[0:Index]
            continue
        
        Index = StrPart.find('/*')
        if Index != -1:
            InComment = True
            StrippedStr += StrPart[0:Index]
        
        Index = StrPart.find('*/')
        if Index != -1:
            StrippedStr += StrPart[Index+2:]
            InComment = False
            continue
        
        if not InComment:
            StrippedStr += StrPart
             
    return StrippedStr

def GetFinalTypeValue(Type, FieldName, TypedefDict, SUDict):
    Value = TypedefDict.get(Type)
    if Value == None:
        Value = SUDict.get(Type)
    if Value == None:
        return None
    
    LBPos = Value.find('{')
    while LBPos == -1:
        FTList = Value.split()
        for FT in FTList:
            if FT not in ('struct', 'union'):
                Value = TypedefDict.get(FT)
                if Value == None:
                    Value = SUDict.get(FT)
                break
        
        if Value == None:
            return None
     
        LBPos = Value.find('{')
     
#    RBPos = Value.find('}')
    Fields = Value[LBPos + 1:]
    Fields = StripComments(Fields)
    FieldsList = Fields.split(';')
    for Field in FieldsList:
        Field = Field.strip()
        Index = Field.rfind(FieldName)
        if Index < 1:
            continue
        if not Field[Index - 1].isalnum():
            if Index + len(FieldName) == len(Field):
                Type = GetDataTypeFromModifier(Field[0:Index])
                return Type.strip()
            else:
            # For the condition that the field in struct is an array with [] sufixes...               
                if not Field[Index + len(FieldName)].isalnum():
                    Type = GetDataTypeFromModifier(Field[0:Index])
                    return Type.strip()
                
    return None
    
def GetRealType(Type, TypedefDict, TargetType = None):
    if TargetType != None and Type == TargetType:
            return Type
    while TypedefDict.get(Type):
        Type = TypedefDict.get(Type)
        if TargetType != None and Type == TargetType:
            return Type
    return Type

def GetTypeInfo(RefList, Modifier, FullFileName, TargetType = None):
    TypedefDict = GetTypedefDict(FullFileName)
    SUDict = GetSUDict(FullFileName)
    Type = GetDataTypeFromModifier(Modifier).replace('*', '').strip()
    
    Type = Type.split()[-1]
    Index = 0
    while Index < len(RefList):
        FieldName = RefList[Index]
        FromType = GetFinalTypeValue(Type, FieldName, TypedefDict, SUDict)
        if FromType == None:
            return None
        # we want to determine the exact type.
        if TargetType != None:
            Type = FromType.split()[0]
        # we only want to check if it is a pointer
        else:
            Type = FromType
            if Type.find('*') != -1 and Index == len(RefList)-1:
                return Type
            Type = FromType.split()[0]
            
        Index += 1

    Type = GetRealType(Type, TypedefDict, TargetType)

    return Type

def GetVarInfo(PredVarList, FuncRecord, FullFileName, IsFuncCall = False, TargetType = None):
    
    PredVar = PredVarList[0]
    FileID = GetTableID(FullFileName)
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    # search variable in include files
    IncludeFileList = GetAllIncludeFiles(FullFileName)
    # it is a function call, search function declarations and definitions
    if IsFuncCall:
        SqlStatement = """ select Modifier, ID
                       from %s
                       where Model = %d and Value = \'%s\'
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION, PredVar)
        ResultSet = Db.TblFile.Exec(SqlStatement)
    
        for Result in ResultSet:        
            Type = GetDataTypeFromModifier(Result[0]).split()[-1]
            TypedefDict = GetTypedefDict(FullFileName)
            Type = GetRealType(Type, TypedefDict, TargetType)
            return Type
        
        for F in IncludeFileList:
            FileID = GetTableID(F)
            if FileID < 0:
                continue
        
            FileTable = 'Identifier' + str(FileID)
            SqlStatement = """ select Modifier, ID
                           from %s
                           where Model = %d and Value = \'%s\'
                       """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION, PredVar)
            ResultSet = Db.TblFile.Exec(SqlStatement)
    
            for Result in ResultSet:
                Type = GetDataTypeFromModifier(Result[0]).split()[-1]
                TypedefDict = GetTypedefDict(FullFileName)
                Type = GetRealType(Type, TypedefDict, TargetType)
                return Type
    
        FileID = GetTableID(FullFileName)
        SqlStatement = """ select Modifier, ID
                       from Function
                       where BelongsToFile = %d and Name = \'%s\'
                   """ % (FileID, PredVar)
        ResultSet = Db.TblFile.Exec(SqlStatement)
    
        for Result in ResultSet:        
            Type = GetDataTypeFromModifier(Result[0]).split()[-1]
            TypedefDict = GetTypedefDict(FullFileName)
            Type = GetRealType(Type, TypedefDict, TargetType)
            return Type
        
        for F in IncludeFileList:
            FileID = GetTableID(F)
            if FileID < 0:
                continue
        
            FileTable = 'Identifier' + str(FileID)
            SqlStatement = """ select Modifier, ID
                           from Function
                           where BelongsToFile = %d and Name = \'%s\'
                       """ % (FileID, PredVar)
            ResultSet = Db.TblFile.Exec(SqlStatement)
    
            for Result in ResultSet:
                Type = GetDataTypeFromModifier(Result[0]).split()[-1]
                TypedefDict = GetTypedefDict(FullFileName)
                Type = GetRealType(Type, TypedefDict, TargetType)
                return Type
         
        return None
       
    # really variable, search local variable first
    SqlStatement = """ select Modifier, ID
                       from %s
                       where Model = %d and Name = \'%s\' and StartLine >= %d and StartLine <= %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE, PredVar, FuncRecord[0], FuncRecord[1])
    ResultSet = Db.TblFile.Exec(SqlStatement)
    VarFound = False
    for Result in ResultSet:
        if len(PredVarList) > 1:
            Type = GetTypeInfo(PredVarList[1:], Result[0], FullFileName, TargetType)
            return Type
        else:
            Type = GetDataTypeFromModifier(Result[0]).split()[-1]
            TypedefDict = GetTypedefDict(FullFileName)
            Type = GetRealType(Type, TypedefDict, TargetType)
            return Type
                
    # search function parameters second
    ParamList = GetParamList(FuncRecord[2])
    for Param in ParamList:
        if Param.Name.strip() == PredVar:
            if len(PredVarList) > 1:
                Type = GetTypeInfo(PredVarList[1:], Param.Modifier, FullFileName, TargetType)
                return Type
            else:
                Type = GetDataTypeFromModifier(Param.Modifier).split()[-1]
                TypedefDict = GetTypedefDict(FullFileName)
                Type = GetRealType(Type, TypedefDict, TargetType)
                return Type
          
    # search global variable next
    SqlStatement = """ select Modifier, ID
           from %s
           where Model = %d and Name = \'%s\' and BelongsToFunction = -1
       """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE, PredVar)
    ResultSet = Db.TblFile.Exec(SqlStatement)

    for Result in ResultSet:
        if len(PredVarList) > 1:
            Type = GetTypeInfo(PredVarList[1:], Result[0], FullFileName, TargetType)
            return Type
        else:
            Type = GetDataTypeFromModifier(Result[0]).split()[-1]
            TypedefDict = GetTypedefDict(FullFileName)
            Type = GetRealType(Type, TypedefDict, TargetType)
            return Type
    
    for F in IncludeFileList:
        FileID = GetTableID(F)
        if FileID < 0:
            continue
    
        FileTable = 'Identifier' + str(FileID)
        SqlStatement = """ select Modifier, ID
                       from %s
                       where Model = %d and BelongsToFunction = -1 and Name = \'%s\'
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE, PredVar)
        ResultSet = Db.TblFile.Exec(SqlStatement)

        for Result in ResultSet:
            if len(PredVarList) > 1:
                Type = GetTypeInfo(PredVarList[1:], Result[0], FullFileName, TargetType)
                return Type
            else:
                Type = GetDataTypeFromModifier(Result[0]).split()[-1]
                TypedefDict = GetTypedefDict(FullFileName)
                Type = GetRealType(Type, TypedefDict, TargetType)
                return Type

def CheckFuncLayoutReturnType(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Modifier, ID, StartLine, StartColumn, EndLine 
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        ReturnType = GetDataTypeFromModifier(Result[0]).split()[-1]
        if len(ReturnType) == 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_RETURN_TYPE, 'Function has No Return Type', FileTable, Result[1])
            continue
        Index = Result[0].find(ReturnType)
        if Index != 0 or Result[3] != 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_RETURN_TYPE, 'Return Type should appear at the start of line', FileTable, Result[1])
            
        if Result[2] == Result[4]:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_RETURN_TYPE, 'Return Type should appear on its own line', FileTable, Result[1])
            
    SqlStatement = """ select Modifier, ID, StartLine, StartColumn, FunNameStartLine
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        ReturnType = GetDataTypeFromModifier(Result[0]).split()[-1]
        if len(ReturnType) == 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_RETURN_TYPE, 'Function has No Return Type', 'Function', Result[1])
            continue
        Index = Result[0].find(ReturnType)
        if Index != 0 or Result[3] != 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_RETURN_TYPE, 'Return Type should appear at the start of line', 'Function', Result[1])
            
        if Result[2] == Result[4]:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_RETURN_TYPE, 'Return Type should appear on its own line', 'Function', Result[1])
    
def CheckFuncLayoutModifier(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Modifier, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        ReturnType = GetDataTypeFromModifier(Result[0]).split()[-1]
        if len(ReturnType) == 0:
            continue
        Index = Result[0].find(ReturnType)
        if Index != 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_OPTIONAL_FUNCTIONAL_MODIFIER, '', FileTable, Result[1])
            
    SqlStatement = """ select Modifier, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        ReturnType = GetDataTypeFromModifier(Result[0]).split()[-1]
        if len(ReturnType) == 0:
            continue
        Index = Result[0].find(ReturnType)
        if Index != 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_OPTIONAL_FUNCTIONAL_MODIFIER, '', 'Function', Result[1])

def CheckFuncLayoutName(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Name, ID, EndColumn
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        if Result[2] != 0:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, 'Function name should appear at the start of a line', FileTable, Result[1])
        ParamList = GetParamList(Result[0])
        if len(ParamList) == 0:
            continue
        StartLine = 0
        for Param in ParamList:
            if Param.StartLine <= StartLine:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, 'Parameter %s should be in its own line.' % Param.Name, FileTable, Result[1])
            if Param.StartLine - StartLine > 1:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, 'Empty line appears before Parameter %s.' % Param.Name, FileTable, Result[1])
            StartLine = Param.StartLine
            
        if not Result[0].endswith('\n  )') and not Result[0].endswith('\r  )'):
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, '\')\' should be on a new line and indented two spaces', FileTable, Result[1])
            
    SqlStatement = """ select Modifier, ID, FunNameStartColumn
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        if Result[2] != 0:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, 'Function name should appear at the start of a line', 'Function', Result[1])
        ParamList = GetParamList(Result[0])
        if len(ParamList) == 0:
            continue
        StartLine = 0
        for Param in ParamList:
            if Param.StartLine <= StartLine:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, 'Parameter %s should be in its own line.' % Param.Name, 'Function', Result[1])
            if Param.StartLine - StartLine > 1:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, 'Empty line appears before Parameter %s.' % Param.Name, 'Function', Result[1])
            StartLine = Param.StartLine
        if not Result[0].endswith('\n  )') and not Result[0].endswith('\r  )'):
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_NAME, '\')\' should be on a new line and indented two spaces', 'Function', Result[1])

def CheckFuncLayoutPrototype(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    FileTable = 'Identifier' + str(FileID)
    Db = GetDB()
    SqlStatement = """ select Modifier, Header, Name, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        return ErrorMsgList
    
    FuncDefList = []
    for Result in ResultSet:
        FuncDefList.append(Result)
        
    SqlStatement = """ select Modifier, Name, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    FuncDeclList = []
    for Result in ResultSet:
        FuncDeclList.append(Result)
    
    IncludeFileList = GetAllIncludeFiles(FullFileName)
    for F in IncludeFileList:
        FileID = GetTableID(F, ErrorMsgList)
        if FileID < 0:
            continue
    
        FileTable = 'Identifier' + str(FileID)
        SqlStatement = """ select Modifier, Name, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
        ResultSet = Db.TblFile.Exec(SqlStatement)

        for Result in ResultSet:
            FuncDeclList.append(Result)
    
    for FuncDef in FuncDefList:
        FuncName = FuncDef[2].strip()
        FuncModifier = FuncDef[0]
        FuncDefHeader = FuncDef[1]
        for FuncDecl in FuncDeclList:
            LBPos = FuncDecl[1].find('(')
            DeclName = FuncDecl[1][0:LBPos].strip()
            DeclModifier = FuncDecl[0]
            if DeclName == FuncName:
                if DiffModifier(FuncModifier, DeclModifier):
                    PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_PROTO_TYPE, 'Function modifier different with prototype.', 'Function', FuncDef[3])
                ParamListOfDef = GetParamList(FuncDefHeader)
                ParamListOfDecl = GetParamList(FuncDecl[1])
                if len(ParamListOfDef) != len(ParamListOfDecl):
                    PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_PROTO_TYPE, 'Parameter number different.', 'Function', FuncDef[3])
                    break

                Index = 0
                while Index < len(ParamListOfDef):
                    if DiffModifier(ParamListOfDef[Index].Modifier, ParamListOfDecl[Index].Modifier):
                        PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_PROTO_TYPE, 'Parameter %s has different modifier with prototype.' % ParamListOfDef[Index].Name, 'Function', FuncDef[3])
                    Index += 1
                break
    
def CheckFuncLayoutBody(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    FileTable = 'Identifier' + str(FileID)
    Db = GetDB()
    SqlStatement = """ select BodyStartColumn, EndColumn, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        return ErrorMsgList
    for Result in ResultSet:
        if Result[0] != 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_BODY, 'open brace should be at the very beginning of a line.', 'Function', Result[2])
        if Result[1] != 0:
            PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_FUNCTION_BODY, 'close brace should be at the very beginning of a line.', 'Function', Result[2])

def CheckFuncLayoutLocalVariable(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        return ErrorMsgList
    FL = []
    for Result in ResultSet:
        FL.append(Result)
        
    for F in FL:
        SqlStatement = """ select Name, Value, ID
                       from %s
                       where Model = %d and BelongsToFunction = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE, F[0])
        ResultSet = Db.TblFile.Exec(SqlStatement)
        if len(ResultSet) == 0:
            continue
        
        for Result in ResultSet:
            if len(Result[1]) > 0:
                PrintErrorMsg(ERROR_C_FUNCTION_LAYOUT_CHECK_NO_INIT_OF_VARIABLE, 'Variable Name: %s' % Result[0], FileTable, Result[2])
        

def CheckDeclTypedefFormat(FullFileName, ModelId):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Name, StartLine, EndLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, ModelId)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    ResultList = []
    for Result in ResultSet:
        ResultList.append(Result)
    
    ErrorType = ERROR_DECLARATION_DATA_TYPE_CHECK_ALL
    if ModelId == DataClass.MODEL_IDENTIFIER_STRUCTURE:
        ErrorType = ERROR_DECLARATION_DATA_TYPE_CHECK_STRUCTURE_DECLARATION
    if ModelId == DataClass.MODEL_IDENTIFIER_ENUMERATE:
        ErrorType = ERROR_DECLARATION_DATA_TYPE_CHECK_ENUMERATED_TYPE
    if ModelId == DataClass.MODEL_IDENTIFIER_UNION:
        ErrorType = ERROR_DECLARATION_DATA_TYPE_CHECK_UNION_TYPE
    
    SqlStatement = """ select Modifier, Name, Value, StartLine, EndLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_TYPEDEF)
    TdSet = Db.TblFile.Exec(SqlStatement)
    
    for Result in ResultList:
        Found = False
        for Td in TdSet:
            if len(Td[0]) > 0:
                continue
            if Result[1] >= Td[3] and Td[4] >= Result[2]:
                Found = True
                if not Td[1].isupper():
                    PrintErrorMsg(ErrorType, 'Typedef should be UPPER case', FileTable, Td[5])
            if Result[0] in Td[2].split():
                Found = True
                if not Td[1].isupper():
                    PrintErrorMsg(ErrorType, 'Typedef should be UPPER case', FileTable, Td[5])
        
        if not Found:
            PrintErrorMsg(ErrorType, 'No Typedef for %s' % Result[0], FileTable, Result[3])
            continue
                
def CheckDeclStructTypedef(FullFileName):
    CheckDeclTypedefFormat(FullFileName, DataClass.MODEL_IDENTIFIER_STRUCTURE)

def CheckDeclEnumTypedef(FullFileName):
    CheckDeclTypedefFormat(FullFileName, DataClass.MODEL_IDENTIFIER_ENUMERATE)
    
def CheckDeclUnionTypedef(FullFileName):
    CheckDeclTypedefFormat(FullFileName, DataClass.MODEL_IDENTIFIER_UNION)

def CheckDeclArgModifier(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Modifier, Name, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    ModifierTuple = ('IN', 'OUT', 'OPTIONAL', 'UNALIGNED')
    MAX_MODIFIER_LENGTH = 100
    for Result in ResultSet:
        for Modifier in ModifierTuple:
            if PatternInModifier(Result[0], Modifier) and len(Result[0]) < MAX_MODIFIER_LENGTH:
                PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_IN_OUT_MODIFIER, 'Variable Modifier %s' % Result[0], FileTable, Result[2])
                break
    
    SqlStatement = """ select Modifier, Name, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        for Modifier in ModifierTuple:
            if PatternInModifier(Result[0], Modifier):
                PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_IN_OUT_MODIFIER, 'Return Type Modifier %s' % Result[0], FileTable, Result[2])
                break
                    
    SqlStatement = """ select Modifier, Header, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        for Modifier in ModifierTuple:
            if PatternInModifier(Result[0], Modifier):
                PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_IN_OUT_MODIFIER, 'Return Type Modifier %s' % Result[0], FileTable, Result[2])
                break

def CheckDeclNoUseCType(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Modifier, Name, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    CTypeTuple = ('int', 'unsigned', 'char', 'void', 'static', 'long')
    for Result in ResultSet:
        for Type in CTypeTuple:
            if PatternInModifier(Result[0], Type):
                PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_NO_USE_C_TYPE, 'Variable type %s' % Type, FileTable, Result[2])
                break
    
    SqlStatement = """ select Modifier, Name, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        ParamList = GetParamList(Result[1])
        for Type in CTypeTuple:
            if PatternInModifier(Result[0], Type):
                PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_NO_USE_C_TYPE, 'Return type %s' % Result[0], FileTable, Result[2])
            
            for Param in ParamList:
                if PatternInModifier(Param.Modifier, Type):
                    PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_NO_USE_C_TYPE, 'Parameter %s' % Param.Name, FileTable, Result[2])
                    
    SqlStatement = """ select Modifier, Header, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        ParamList = GetParamList(Result[1])
        for Type in CTypeTuple:
            if PatternInModifier(Result[0], Type):
                PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_NO_USE_C_TYPE, 'Return type %s' % Result[0], FileTable, Result[2])
            
            for Param in ParamList:
                if PatternInModifier(Param.Modifier, Type):
                    PrintErrorMsg(ERROR_DECLARATION_DATA_TYPE_CHECK_NO_USE_C_TYPE, 'Parameter %s' % Param.Name, FileTable, Result[2])
            

def CheckPointerNullComparison(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    # cache the found function return type to accelerate later checking in this file.
    FuncReturnTypeDict = {}
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, StartLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_PREDICATE_EXPRESSION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        return
    PSL = []
    for Result in ResultSet:
        PSL.append([Result[0], Result[1], Result[2]])
    
    SqlStatement = """ select BodyStartLine, EndLine, Header, Modifier, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    FL = []
    for Result in ResultSet:
        FL.append([Result[0], Result[1], Result[2], Result[3], Result[4]])
    
    p = GetFuncDeclPattern()
    for Str in PSL:
        FuncRecord = GetFuncContainsPE(Str[1], FL)
        if FuncRecord == None:
            continue
        
        for Exp in GetPredicateListFromPredicateExpStr(Str[0]):
            PredInfo = SplitPredicateStr(Exp)
            if PredInfo[1] == None:
                PredVarStr = PredInfo[0][0].strip()
                IsFuncCall = False
                SearchInCache = False
                # PredVarStr may contain '.' or '->'
                TmpStr = PredVarStr.replace('.', '').replace('->', '')
                if p.match(TmpStr):
                    PredVarStr = PredVarStr[0:PredVarStr.find('(')]
                    SearchInCache = True
                    # Only direct function call using IsFuncCall branch. Multi-level ref. function call is considered a variable.
                    if TmpStr.startswith(PredVarStr):    
                        IsFuncCall = True
                    
                if PredVarStr.strip() in IgnoredKeywordList:
                    continue
                PredVarList = GetCNameList(PredVarStr)
                # No variable found, maybe value first? like (0 == VarName)
                if len(PredVarList) == 0:
                    continue
                if SearchInCache:
                    Type = FuncReturnTypeDict.get(PredVarStr)
                    if Type != None:
                        if Type.find('*') == -1:
                            PrintErrorMsg(ERROR_PREDICATE_EXPRESSION_CHECK_NO_BOOLEAN_OPERATOR, 'Predicate Expression: %s' % Exp, FileTable, Str[2])
                        continue
                    
                    if PredVarStr in FuncReturnTypeDict:
                        continue
                
                Type = GetVarInfo(PredVarList, FuncRecord, FullFileName)
                if SearchInCache:
                    FuncReturnTypeDict[PredVarStr] = Type
                if Type == None:
                    continue
                if Type.find('*') != -1:
                    PrintErrorMsg(ERROR_PREDICATE_EXPRESSION_CHECK_COMPARISON_NULL_TYPE, 'Predicate Expression: %s' % Exp, FileTable, Str[2])

def CheckNonBooleanValueComparison(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    # cache the found function return type to accelerate later checking in this file.
    FuncReturnTypeDict = {}
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, StartLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_PREDICATE_EXPRESSION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        return
    PSL = []
    for Result in ResultSet:
        PSL.append([Result[0], Result[1], Result[2]])
    
    SqlStatement = """ select BodyStartLine, EndLine, Header, Modifier, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    FL = []
    for Result in ResultSet:
        FL.append([Result[0], Result[1], Result[2], Result[3], Result[4]])
    
    p = GetFuncDeclPattern()
    for Str in PSL:
        FuncRecord = GetFuncContainsPE(Str[1], FL)
        if FuncRecord == None:
            continue
        
        for Exp in GetPredicateListFromPredicateExpStr(Str[0]):
#            if p.match(Exp):
#                continue
            PredInfo = SplitPredicateStr(Exp)
            if PredInfo[1] == None:
                PredVarStr = PredInfo[0][0].strip()
                IsFuncCall = False
                SearchInCache = False
                # PredVarStr may contain '.' or '->'
                TmpStr = PredVarStr.replace('.', '').replace('->', '')
                if p.match(TmpStr):
                    PredVarStr = PredVarStr[0:PredVarStr.find('(')]
                    SearchInCache = True
                    # Only direct function call using IsFuncCall branch. Multi-level ref. function call is considered a variable.
                    if TmpStr.startswith(PredVarStr):    
                        IsFuncCall = True
                    
                if PredVarStr.strip() in IgnoredKeywordList:
                    continue
                PredVarList = GetCNameList(PredVarStr)
                # No variable found, maybe value first? like (0 == VarName)
                if len(PredVarList) == 0:
                    continue
                   
                if SearchInCache:
                    Type = FuncReturnTypeDict.get(PredVarStr)
                    if Type != None:
                        if Type.find('BOOLEAN') == -1:
                            PrintErrorMsg(ERROR_PREDICATE_EXPRESSION_CHECK_NO_BOOLEAN_OPERATOR, 'Predicate Expression: %s' % Exp, FileTable, Str[2])
                        continue
                    
                    if PredVarStr in FuncReturnTypeDict:
                        continue
                    
                Type = GetVarInfo(PredVarList, FuncRecord, FullFileName, IsFuncCall, 'BOOLEAN')
                if SearchInCache:
                    FuncReturnTypeDict[PredVarStr] = Type
                if Type == None:
                    continue
                if Type.find('BOOLEAN') == -1:
                    PrintErrorMsg(ERROR_PREDICATE_EXPRESSION_CHECK_NO_BOOLEAN_OPERATOR, 'Predicate Expression: %s' % Exp, FileTable, Str[2])
            

def CheckBooleanValueComparison(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    # cache the found function return type to accelerate later checking in this file.
    FuncReturnTypeDict = {}
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, StartLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_PREDICATE_EXPRESSION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        return
    PSL = []
    for Result in ResultSet:
        PSL.append([Result[0], Result[1], Result[2]])
    
    SqlStatement = """ select BodyStartLine, EndLine, Header, Modifier, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    FL = []
    for Result in ResultSet:
        FL.append([Result[0], Result[1], Result[2], Result[3], Result[4]])
    
    p = GetFuncDeclPattern()
    for Str in PSL:
        FuncRecord = GetFuncContainsPE(Str[1], FL)
        if FuncRecord == None:
            continue
        
        for Exp in GetPredicateListFromPredicateExpStr(Str[0]):
            PredInfo = SplitPredicateStr(Exp)
            if PredInfo[1] in ('==', '!=') and PredInfo[0][1] in ('TRUE', 'FALSE'):
                PredVarStr = PredInfo[0][0].strip()
                IsFuncCall = False
                SearchInCache = False
                # PredVarStr may contain '.' or '->'
                TmpStr = PredVarStr.replace('.', '').replace('->', '')
                if p.match(TmpStr):
                    PredVarStr = PredVarStr[0:PredVarStr.find('(')]
                    SearchInCache = True
                    # Only direct function call using IsFuncCall branch. Multi-level ref. function call is considered a variable.
                    if TmpStr.startswith(PredVarStr):    
                        IsFuncCall = True
                    
                if PredVarStr.strip() in IgnoredKeywordList:
                    continue
                PredVarList = GetCNameList(PredVarStr)
                # No variable found, maybe value first? like (0 == VarName)
                if len(PredVarList) == 0:
                    continue
          
                if SearchInCache:
                    Type = FuncReturnTypeDict.get(PredVarStr)
                    if Type != None:
                        if Type.find('BOOLEAN') != -1:
                            PrintErrorMsg(ERROR_PREDICATE_EXPRESSION_CHECK_BOOLEAN_VALUE, 'Predicate Expression: %s' % Exp, FileTable, Str[2])
                        continue
                    
                    if PredVarStr in FuncReturnTypeDict:
                        continue
                
                Type = GetVarInfo(PredVarList, FuncRecord, FullFileName, IsFuncCall, 'BOOLEAN')
                if SearchInCache:
                    FuncReturnTypeDict[PredVarStr] = Type
                if Type == None:
                    continue
                if Type.find('BOOLEAN') != -1:
                    PrintErrorMsg(ERROR_PREDICATE_EXPRESSION_CHECK_BOOLEAN_VALUE, 'Predicate Expression: %s' % Exp, FileTable, Str[2])
                

def CheckHeaderFileData(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select ID, Modifier
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_VARIABLE)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        if not Result[1].startswith('extern'):
            PrintErrorMsg(ERROR_INCLUDE_FILE_CHECK_DATA, 'Variable definition appears in header file', FileTable, Result[0])
        
    SqlStatement = """ select ID
                       from Function
                       where BelongsToFile = %d
                   """ % FileID
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        PrintErrorMsg(ERROR_INCLUDE_FILE_CHECK_DATA, 'Function definition appears in header file', 'Function', Result[0])

    return ErrorMsgList

def CheckHeaderFileIfndef(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, StartLine
                       from %s
                       where Model = %d order by StartLine
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_MACRO_IFNDEF)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        PrintErrorMsg(ERROR_INCLUDE_FILE_CHECK_IFNDEF_STATEMENT_1, '', 'File', FileID)
        return ErrorMsgList
    for Result in ResultSet:
        SqlStatement = """ select Value, EndLine
                       from %s
                       where EndLine < %d
                   """ % (FileTable, Result[1])
        ResultSet = Db.TblFile.Exec(SqlStatement)
        for Result in ResultSet:
            if not Result[0].startswith('/*') and not Result[0].startswith('//'):
                PrintErrorMsg(ERROR_INCLUDE_FILE_CHECK_IFNDEF_STATEMENT_2, '', 'File', FileID)
        break
    
    SqlStatement = """ select Value
                       from %s
                       where StartLine > (select max(EndLine) from %s where Model = %d)
                   """ % (FileTable, FileTable, DataClass.MODEL_IDENTIFIER_MACRO_ENDIF)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        if not Result[0].startswith('/*') and not Result[0].startswith('//'):
            PrintErrorMsg(ERROR_INCLUDE_FILE_CHECK_IFNDEF_STATEMENT_3, '', 'File', FileID)
    return ErrorMsgList

def CheckDoxygenCommand(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, ID
                       from %s
                       where Model = %d or Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_COMMENT, DataClass.MODEL_IDENTIFIER_FUNCTION_HEADER)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    DoxygenCommandList = ['bug', 'todo', 'example', 'file', 'attention', 'param', 'post', 'pre', 'retval', 'return', 'sa', 'since', 'test', 'note', 'par']
    for Result in ResultSet:
        CommentStr = Result[0]
        CommentPartList = CommentStr.split()
        for Part in CommentPartList:
            if Part.upper() == 'BUGBUG':
                PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMAND, 'Bug should be marked with doxygen tag @bug', FileTable, Result[1])
            if Part.upper() == 'TODO':
                PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMAND, 'ToDo should be marked with doxygen tag @todo', FileTable, Result[1])
            if Part.startswith('@'):
                if Part.lstrip('@').isalpha():
                    if Part.lstrip('@') not in DoxygenCommandList:
                        PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMAND, 'Unknown doxygen command %s' % Part, FileTable, Result[1])
                else:
                    Index = Part.find('[')
                    if Index == -1:
                        PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMAND, 'Unknown doxygen command %s' % Part, FileTable, Result[1])
                    RealCmd = Part[1:Index]
                    if RealCmd not in DoxygenCommandList:
                        PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMAND, 'Unknown doxygen command %s' % Part, FileTable, Result[1])
        
    
def CheckDoxygenTripleForwardSlash(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, ID, StartLine
                       from %s
                       where Model = %d or Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_COMMENT, DataClass.MODEL_IDENTIFIER_FUNCTION_HEADER)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    CommentSet = []
    try:
        for Result in ResultSet:
            CommentSet.append(Result)
    except:
        print 'Unrecognized chars in comment of file %s', FullFileName
    
    SqlStatement = """ select ID, StartLine, EndLine
                       from %s
                       where Model = %d or Model = %d or Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_STRUCTURE, DataClass.MODEL_IDENTIFIER_ENUMERATE, DataClass.MODEL_IDENTIFIER_UNION)
    SUEResultSet = Db.TblFile.Exec(SqlStatement)
    
    for Result in CommentSet:
        CommentStr = Result[0]
        StartLine = Result[2]
        if not CommentStr.startswith('///<'):
            continue
        if len(ResultSet) == 0:
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMENT_FORMAT, '', FileTable, Result[1])
            continue
        Found = False
        for SUE in SUEResultSet:
            if StartLine > SUE[1] and StartLine < SUE[2]:
                Found = True
                break
        if not Found:
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMENT_FORMAT, '', FileTable, Result[1])


def CheckFileHeaderDoxygenComments(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, ID
                       from %s
                       where Model = %d and StartLine = 1 and StartColumn = 0
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_COMMENT)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    if len(ResultSet) == 0:
        PrintErrorMsg(ERROR_HEADER_CHECK_FILE, 'No Comment appear at the very beginning of file.', 'File', FileID)
        return ErrorMsgList
    
    for Result in ResultSet:
        CommentStr = Result[0]
        if not CommentStr.startswith('/** @file'):
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_FILE_HEADER, 'File header comment should begin with ""/** @file""', FileTable, Result[1])
        if not CommentStr.endswith('**/'):
            PrintErrorMsg(ERROR_HEADER_CHECK_FILE, 'File header comment should end with **/', FileTable, Result[1])
        if CommentStr.find('.') == -1:
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMENT_DESCRIPTION, 'Comment description should end with period \'.\'', FileTable, Result[1])

def CheckFuncHeaderDoxygenComments(FullFileName):
    ErrorMsgList = []
    
    FileID = GetTableID(FullFileName, ErrorMsgList)
    if FileID < 0:
        return ErrorMsgList
    
    Db = GetDB()
    FileTable = 'Identifier' + str(FileID)
    SqlStatement = """ select Value, StartLine, EndLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_COMMENT)
    
    ResultSet = Db.TblFile.Exec(SqlStatement)
    CommentSet = []
    try:
        for Result in ResultSet:
            CommentSet.append(Result)
    except:
        print 'Unrecognized chars in comment of file %s', FullFileName
    
    # Func Decl check
    SqlStatement = """ select Modifier, Name, StartLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_DECLARATION)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        FunctionHeaderComment = CheckCommentImmediatelyPrecedeFunctionHeader(Result[1], Result[2], CommentSet)
        if FunctionHeaderComment:
            CheckFunctionHeaderConsistentWithDoxygenComment(Result[0], Result[1], Result[2], FunctionHeaderComment[0], FunctionHeaderComment[1], ErrorMsgList, FunctionHeaderComment[3], FileTable)
        else:
            ErrorMsgList.append('Line %d :Function %s has NO comment immediately preceding it.' % (Result[2], Result[1]))
            PrintErrorMsg(ERROR_HEADER_CHECK_FUNCTION, 'Function %s has NO comment immediately preceding it.' % (Result[1]), FileTable, Result[3])
    
    # Func Def check
    SqlStatement = """ select Value, StartLine, EndLine, ID
                       from %s
                       where Model = %d
                   """ % (FileTable, DataClass.MODEL_IDENTIFIER_FUNCTION_HEADER)
    
    ResultSet = Db.TblFile.Exec(SqlStatement)
    CommentSet = []
    try:
        for Result in ResultSet:
            CommentSet.append(Result)
    except:
        print 'Unrecognized chars in comment of file %s', FullFileName
    
    SqlStatement = """ select Modifier, Header, StartLine, ID
                       from Function
                       where BelongsToFile = %d
                   """ % (FileID)
    ResultSet = Db.TblFile.Exec(SqlStatement)
    for Result in ResultSet:
        FunctionHeaderComment = CheckCommentImmediatelyPrecedeFunctionHeader(Result[1], Result[2], CommentSet)
        if FunctionHeaderComment:
            CheckFunctionHeaderConsistentWithDoxygenComment(Result[0], Result[1], Result[2], FunctionHeaderComment[0], FunctionHeaderComment[1], ErrorMsgList, FunctionHeaderComment[3], FileTable)
        else:
            ErrorMsgList.append('Line %d :Function %s has NO comment immediately preceding it.' % (Result[2], Result[1]))
            PrintErrorMsg(ERROR_HEADER_CHECK_FUNCTION, 'Function %s has NO comment immediately preceding it.' % (Result[1]), 'Function', Result[3])
    return ErrorMsgList

def CheckCommentImmediatelyPrecedeFunctionHeader(FuncName, FuncStartLine, CommentSet):

    for Comment in CommentSet:
        if Comment[2] == FuncStartLine - 1:
            return Comment
    return None

def GetDoxygenStrFromComment(Str):
    DoxygenStrList = []
    ParamTagList = Str.split('@param')
    if len(ParamTagList) > 1:
        i = 1
        while i < len(ParamTagList):
            DoxygenStrList.append('@param' + ParamTagList[i])
            i += 1
    
    Str = ParamTagList[0]
            
    RetvalTagList = ParamTagList[-1].split('@retval')
    if len(RetvalTagList) > 1:
        if len(ParamTagList) > 1:
            DoxygenStrList[-1] = '@param' + RetvalTagList[0]
        i = 1
        while i < len(RetvalTagList):
            DoxygenStrList.append('@retval' + RetvalTagList[i])
            i += 1
    
    ReturnTagList = RetvalTagList[-1].split('@return')
    if len(ReturnTagList) > 1:
        if len(RetvalTagList) > 1:
            DoxygenStrList[-1] = '@retval' + ReturnTagList[0]
        elif len(ParamTagList) > 1:
            DoxygenStrList[-1] = '@param' + ReturnTagList[0]
        i = 1
        while i < len(ReturnTagList):
            DoxygenStrList.append('@return' + ReturnTagList[i])
            i += 1
    
    if len(DoxygenStrList) > 0:
        DoxygenStrList[-1] = DoxygenStrList[-1].rstrip('--*/')
    
    return DoxygenStrList
    
def CheckGeneralDoxygenCommentLayout(Str, StartLine, ErrorMsgList, CommentId = -1, TableName = ''):
    #/** --*/ @retval after @param
    if not Str.startswith('/**'):
        ErrorMsgList.append('Line %d : Comment does NOT have prefix /** ' % StartLine)
        PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'Comment does NOT have prefix /** ', TableName, CommentId)
    if not Str.endswith('**/'):
        ErrorMsgList.append('Line %d : Comment does NOT have tail **/ ' % StartLine)
        PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'Comment does NOT have tail **/ ', TableName, CommentId)
    FirstRetvalIndex = Str.find('@retval')
    LastParamIndex = Str.rfind('@param')
    if (FirstRetvalIndex > 0) and (LastParamIndex > 0) and (FirstRetvalIndex < LastParamIndex):
        ErrorMsgList.append('Line %d : @retval appear before @param ' % StartLine)
        PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'in Comment, @retval appear before @param  ', TableName, CommentId)
    
def CheckFunctionHeaderConsistentWithDoxygenComment(FuncModifier, FuncHeader, FuncStartLine, CommentStr, CommentStartLine, ErrorMsgList, CommentId = -1, TableName = ''):
    
    ParamList = GetParamList(FuncHeader) 
    CheckGeneralDoxygenCommentLayout(CommentStr, CommentStartLine, ErrorMsgList, CommentId, TableName)
    DescriptionStr = CommentStr
    DoxygenStrList = GetDoxygenStrFromComment(DescriptionStr)
    if DescriptionStr.find('.') == -1:
        PrintErrorMsg(ERROR_DOXYGEN_CHECK_COMMENT_DESCRIPTION, 'Comment description should end with period \'.\'', TableName, CommentId)
    DoxygenTagNumber = len(DoxygenStrList)
    ParamNumber = len(ParamList)
    for Param in ParamList:
        if Param.Name.upper() == 'VOID':
            ParamNumber -= 1
    Index = 0
    if ParamNumber > 0 and DoxygenTagNumber > 0:
        while Index < ParamNumber and Index < DoxygenTagNumber:
            ParamModifier = ParamList[Index].Modifier
            ParamName = ParamList[Index].Name.strip()
            Tag = DoxygenStrList[Index].strip(' ')
            if (not Tag[-1] == ('\n')) and (not Tag[-1] == ('\r')):
                ErrorMsgList.append('Line %d : in Comment, \"%s\" does NOT end with new line ' % (CommentStartLine, Tag.replace('\n', '').replace('\r', '')))
                PrintErrorMsg(ERROR_HEADER_CHECK_FUNCTION, 'in Comment, \"%s\" does NOT end with new line ' % (Tag.replace('\n', '').replace('\r', '')), TableName, CommentId)
            TagPartList = Tag.split()
            if len(TagPartList) < 2:
                ErrorMsgList.append('Line %d : in Comment, \"%s\" does NOT contain doxygen contents ' % (CommentStartLine, Tag.replace('\n', '').replace('\r', '')))
                PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'in Comment, \"%s\" does NOT contain doxygen contents ' % (Tag.replace('\n', '').replace('\r', '')), TableName, CommentId)
                Index += 1
                continue
            if Tag.find('[') > 0:
                InOutStr = ''
                ModifierPartList = ParamModifier.split()
                for Part in ModifierPartList:
                    if Part.strip() == 'IN':
                        InOutStr += 'in'
                    if Part.strip() == 'OUT':
                        if InOutStr != '':    
                            InOutStr += ', out'
                        else:
                            InOutStr = 'out'
                
                if InOutStr != '':
                    if Tag.find('['+InOutStr+']') == -1:
                        ErrorMsgList.append('Line %d : in Comment, \"%s\" does NOT have %s ' % (CommentStartLine, (TagPartList[0] + ' ' +TagPartList[1]).replace('\n', '').replace('\r', ''), '['+InOutStr+']'))    
                        PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'in Comment, \"%s\" does NOT have %s ' % ((TagPartList[0] + ' ' +TagPartList[1]).replace('\n', '').replace('\r', ''), '['+InOutStr+']'), TableName, CommentId)
            if Tag.find(ParamName) == -1 and ParamName != 'VOID' and ParamName != 'void':
                ErrorMsgList.append('Line %d : in Comment, \"%s\" does NOT consistent with parameter name %s ' % (CommentStartLine, (TagPartList[0] + ' ' +TagPartList[1]).replace('\n', '').replace('\r', ''), ParamName))    
                PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'in Comment, \"%s\" does NOT consistent with parameter name %s ' % ((TagPartList[0] + ' ' +TagPartList[1]).replace('\n', '').replace('\r', ''), ParamName), TableName, CommentId)
            Index += 1
        
        if Index < ParamNumber:
            ErrorMsgList.append('Line %d : Number of doxygen tags in comment less than number of function parameters' % CommentStartLine)
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'Number of doxygen tags in comment less than number of function parameters ', TableName, CommentId)
        if (FuncModifier.find('VOID') != -1 or FuncModifier.find('void') != -1) and FuncModifier.find('*') == -1:
            
            # assume we allow a return description tag for void func. return. that's why 'DoxygenTagNumber - 1' is used instead of 'DoxygenTagNumber'
            if Index < DoxygenTagNumber - 1 or (Index < DoxygenTagNumber and DoxygenStrList[Index].startswith('@retval')):
                ErrorMsgList.append('Line %d : Excessive doxygen tags in comment' % CommentStartLine)
                PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'Excessive doxygen tags in comment ', TableName, CommentId)
        else:
            if Index < DoxygenTagNumber and not DoxygenStrList[Index].startswith('@retval') and not DoxygenStrList[Index].startswith('@return'): 
                ErrorMsgList.append('Line %d : Number of @param doxygen tags in comment does NOT match number of function parameters' % CommentStartLine)
                PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'Number of @param doxygen tags in comment does NOT match number of function parameters ', TableName, CommentId)
    else:
        if ParamNumber == 0 and DoxygenTagNumber != 0 and ((FuncModifier.find('VOID') != -1 or FuncModifier.find('void') != -1) and FuncModifier.find('*') == -1):
            ErrorMsgList.append('Line %d : Excessive doxygen tags in comment' % CommentStartLine)
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'Excessive doxygen tags in comment ', TableName, CommentId)
        if ParamNumber != 0 and DoxygenTagNumber == 0:
            ErrorMsgList.append('Line %d : No doxygen tags in comment' % CommentStartLine)
            PrintErrorMsg(ERROR_DOXYGEN_CHECK_FUNCTION_HEADER, 'No doxygen tags in comment ', TableName, CommentId)

if __name__ == '__main__':

#    EdkLogger.Initialize()
#    EdkLogger.SetLevel(EdkLogger.QUIET)
#    CollectSourceCodeDataIntoDB(sys.argv[1])       
    MsgList = CheckFuncHeaderDoxygenComments('C:\\Combo\\R9\\LakeportX64Dev\\FlashDevicePkg\\Library\\SpiFlashChipM25P64\\SpiFlashChipM25P64.c')
    for Msg in MsgList:
        print Msg
    print 'Done!'
