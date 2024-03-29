/** @file
  
  The definition of CFormPkg's member function

Copyright (c) 2004 - 2008, Intel Corporation                                                         
All rights reserved. This program and the accompanying materials                          
are licensed and made available under the terms and conditions of the BSD License         
which accompanies this distribution.  The full text of the license may be found at        
http://opensource.org/licenses/bsd-license.php                                            
                                                                                          
THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,                     
WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.             

**/

#include "stdio.h"
#include "VfrFormPkg.h"

/*
 * The definition of CFormPkg's member function
 */

SPendingAssign::SPendingAssign (
  IN CHAR8  *Key, 
  IN VOID   *Addr, 
  IN UINT32 Len, 
  IN UINT32 LineNo,
  IN CHAR8  *Msg
  )
{
  mKey    = NULL;
  mAddr   = Addr;
  mLen    = Len;
  mFlag   = PENDING;
  mLineNo = LineNo;
  mMsg    = NULL;
  mNext   = NULL;
  if (Key != NULL) {
    mKey = new CHAR8[strlen (Key) + 1];
    if (mKey != NULL) {
      strcpy (mKey, Key);
    }
  }

  if (Msg != NULL) {
    mMsg = new CHAR8[strlen (Msg) + 1];
    if (mMsg != NULL) {
      strcpy (mMsg, Msg);
    }
  }
}

SPendingAssign::~SPendingAssign (
  VOID
  )
{
  if (mKey != NULL) {
    delete mKey;
  }
  mAddr   = NULL;
  mLen    = 0;
  mLineNo = 0;
  if (mMsg != NULL) {
    delete mMsg;
  }
  mNext   = NULL;
}

VOID
SPendingAssign::SetAddrAndLen (
  IN VOID   *Addr, 
  IN UINT32 LineNo
  )
{
  mAddr   = Addr;
  mLineNo = LineNo;
}

VOID
SPendingAssign::AssignValue (
  IN VOID   *Addr, 
  IN UINT32 Len
  )
{
  memcpy (mAddr, Addr, (mLen < Len ? mLen : Len));
  mFlag = ASSIGNED;
}

CHAR8 *
SPendingAssign::GetKey (
  VOID
  )
{
  return mKey;
}

CFormPkg::CFormPkg (
  IN UINT32 BufferSize = 4096
  )
{
  CHAR8       *BufferStart;
  CHAR8       *BufferEnd;
  SBufferNode *Node;

  mPkgLength           = 0;
  mBufferNodeQueueHead = NULL;
  mCurrBufferNode      = NULL;

  Node = new SBufferNode;
  if (Node == NULL) {
    return ;
  }
  BufferStart = new CHAR8[BufferSize];
  if (BufferStart == NULL) {
    return;
  }
  BufferEnd   = BufferStart + BufferSize;

  memset (BufferStart, 0, BufferSize);
  Node->mBufferStart   = BufferStart;
  Node->mBufferEnd     = BufferEnd;
  Node->mBufferFree    = BufferStart;
  Node->mNext          = NULL;

  mBufferSize          = BufferSize;
  mBufferNodeQueueHead = Node;
  mBufferNodeQueueTail = Node;
  mCurrBufferNode      = Node;
}

CFormPkg::~CFormPkg ()
{
  SBufferNode    *pBNode;
  SPendingAssign *pPNode;

  while (mBufferNodeQueueHead != NULL) {
    pBNode = mBufferNodeQueueHead;
    mBufferNodeQueueHead = mBufferNodeQueueHead->mNext;
    if (pBNode->mBufferStart != NULL) {
      delete pBNode->mBufferStart;
      delete pBNode;
    }
  }
  mBufferNodeQueueTail = NULL;
  mCurrBufferNode      = NULL;

  while (PendingAssignList != NULL) {
    pPNode = PendingAssignList;
    PendingAssignList = PendingAssignList->mNext;
    delete pPNode;
  }
  PendingAssignList = NULL;
}

CHAR8 *
CFormPkg::IfrBinBufferGet (
  IN UINT32 Len
  )
{
  CHAR8 *BinBuffer = NULL;

  if ((Len == 0) || (Len > mBufferSize)) {
    return NULL;
  }

  if ((mCurrBufferNode->mBufferFree + Len) <= mCurrBufferNode->mBufferEnd) {
    BinBuffer = mCurrBufferNode->mBufferFree;
    mCurrBufferNode->mBufferFree += Len;
  } else {
    SBufferNode *Node;

    Node = new SBufferNode;
    if (Node == NULL) {
      return NULL;
    }

    Node->mBufferStart = new CHAR8[mBufferSize];
    if (Node->mBufferStart == NULL) {
      delete Node;
      return NULL;
    } else {
      memset (Node->mBufferStart, 0, mBufferSize);
      Node->mBufferEnd  = Node->mBufferStart + mBufferSize;
      Node->mBufferFree = Node->mBufferStart;
      Node->mNext       = NULL;
    }

    if (mBufferNodeQueueTail == NULL) {
      mBufferNodeQueueHead = mBufferNodeQueueTail = Node;
    } else {
      mBufferNodeQueueTail->mNext = Node;
      mBufferNodeQueueTail = Node;
    }
    mCurrBufferNode = Node;

    //
    // Now try again.
    //
    BinBuffer = mCurrBufferNode->mBufferFree;
    mCurrBufferNode->mBufferFree += Len;
  }

  mPkgLength += Len;

  return BinBuffer;
}

inline
UINT32
CFormPkg::GetPkgLength (
  VOID
  )
{
  return mPkgLength;
}

VOID
CFormPkg::Open (
  VOID
  )
{
  mReadBufferNode   = mBufferNodeQueueHead;
  mReadBufferOffset = 0;
}

VOID
CFormPkg::Close (
  VOID
  )
{
  mReadBufferNode   = NULL;
  mReadBufferOffset = 0;
}

UINT32
CFormPkg::Read (
  IN CHAR8     *Buffer, 
  IN UINT32    Size
  )
{
  UINT32       Index;

  if ((Size == 0) || (Buffer == NULL)) {
    return 0;
  }

  if (mReadBufferNode == NULL) {
  	return 0;
  }

  for (Index = 0; Index < Size; Index++) {
    if ((mReadBufferNode->mBufferStart + mReadBufferOffset) < mReadBufferNode->mBufferFree) {
      Buffer[Index] = mReadBufferNode->mBufferStart[mReadBufferOffset++];
    } else {
      if ((mReadBufferNode = mReadBufferNode->mNext) == NULL) {
        return Index;
      } else {
        mReadBufferOffset = 0;
        Buffer[Index] = mReadBufferNode->mBufferStart[mReadBufferOffset++];
      }
    }
  }

  return Size;
}

EFI_VFR_RETURN_CODE
CFormPkg::BuildPkgHdr (
  OUT EFI_HII_PACKAGE_HEADER **PkgHdr
  )
{
  if (PkgHdr == NULL) {
    return VFR_RETURN_FATAL_ERROR;
  }

  if (((*PkgHdr) = new EFI_HII_PACKAGE_HEADER) == NULL) {
    return VFR_RETURN_OUT_FOR_RESOURCES;
  }

  (*PkgHdr)->Type = EFI_HII_PACKAGE_FORM;
  (*PkgHdr)->Length = mPkgLength + sizeof (EFI_HII_PACKAGE_HEADER);

  return VFR_RETURN_SUCCESS;
}

EFI_VFR_RETURN_CODE
CFormPkg::BuildPkg (
  OUT PACKAGE_DATA &TBuffer
  )
{
  
  CHAR8  *Temp;
  UINT32 Size;
  CHAR8  Buffer[1024];

  if (TBuffer.Buffer != NULL) {
    delete TBuffer.Buffer;
  }

  TBuffer.Size = mPkgLength;
  TBuffer.Buffer = NULL;
  if (TBuffer.Size != 0) {
    TBuffer.Buffer = new CHAR8[TBuffer.Size];
  } else {
    return VFR_RETURN_SUCCESS;
  }

  Temp = TBuffer.Buffer;
  Open ();
  while ((Size = Read (Buffer, 1024)) != 0) {
    memcpy (Temp, Buffer, Size);
    Temp += Size;
  }
  Close ();
  return VFR_RETURN_SUCCESS;
}


EFI_VFR_RETURN_CODE
CFormPkg::BuildPkg (
  IN FILE  *Output,
  IN PACKAGE_DATA *PkgData
  )
{
  EFI_VFR_RETURN_CODE     Ret;
  CHAR8                   Buffer[1024];
  UINT32                  Size;
  EFI_HII_PACKAGE_HEADER  *PkgHdr;

  if (Output == NULL) {
    return VFR_RETURN_FATAL_ERROR;
  }

  if ((Ret = BuildPkgHdr(&PkgHdr)) != VFR_RETURN_SUCCESS) {
    return Ret;
  }
  fwrite (PkgHdr, sizeof (EFI_HII_PACKAGE_HEADER), 1, Output);
  delete PkgHdr;
  
  if (PkgData == NULL) {
    Open ();
    while ((Size = Read (Buffer, 1024)) != 0) {
      fwrite (Buffer, Size, 1, Output);
    }
    Close ();
  } else {
    fwrite (PkgData->Buffer, PkgData->Size, 1, Output);
  }

  return VFR_RETURN_SUCCESS;
}

VOID
CFormPkg::_WRITE_PKG_LINE (
  IN FILE   *pFile,
  IN UINT32 LineBytes,
  IN CHAR8  *LineHeader,
  IN CHAR8  *BlkBuf,
  IN UINT32 BlkSize
  )
{
  UINT32    Index;

  if ((pFile == NULL) || (LineHeader == NULL) || (BlkBuf == NULL)) {
    return;
  }

  for (Index = 0; Index < BlkSize; Index++) {
    if ((Index % LineBytes) == 0) {
      fprintf (pFile, "\n%s", LineHeader);
    }
    fprintf (pFile, "0x%02X,  ", (UINT8)BlkBuf[Index]);
  }
}

VOID
CFormPkg::_WRITE_PKG_END (
  IN FILE   *pFile,
  IN UINT32 LineBytes,
  IN CHAR8  *LineHeader,
  IN CHAR8  *BlkBuf,
  IN UINT32 BlkSize
  )
{
  UINT32    Index;

  if ((BlkSize == 0) || (pFile == NULL) || (LineHeader == NULL) || (BlkBuf == NULL)) {
    return;
  }

  for (Index = 0; Index < BlkSize - 1; Index++) {
    if ((Index % LineBytes) == 0) {
      fprintf (pFile, "\n%s", LineHeader);
    }
    fprintf (pFile, "0x%02X,  ", (UINT8)BlkBuf[Index]);
  }

  if ((Index % LineBytes) == 0) {
    fprintf (pFile, "\n%s", LineHeader);
  }
  fprintf (pFile, "0x%02X\n", (UINT8)BlkBuf[Index]);
}

#define BYTES_PRE_LINE 0x10

EFI_VFR_RETURN_CODE 
CFormPkg::GenCFile (
  IN CHAR8 *BaseName,
  IN FILE *pFile,
  IN PACKAGE_DATA *PkgData
  )
{
  EFI_VFR_RETURN_CODE          Ret;
  CHAR8                        Buffer[BYTES_PRE_LINE * 8];
  EFI_HII_PACKAGE_HEADER       *PkgHdr;
  UINT32                       PkgLength  = 0;
  UINT32                       ReadSize   = 0;

  if ((BaseName == NULL) || (pFile == NULL)) {
    return VFR_RETURN_FATAL_ERROR;
  }

  fprintf (pFile, "\nunsigned char %sBin[] = {\n", BaseName);

  if ((Ret = BuildPkgHdr(&PkgHdr)) != VFR_RETURN_SUCCESS) {
    return Ret;
  }

  fprintf (pFile, "  // ARRAY LENGTH\n");
  PkgLength = PkgHdr->Length + sizeof (UINT32);
  _WRITE_PKG_LINE(pFile, BYTES_PRE_LINE, "  ", (CHAR8 *)&PkgLength, sizeof (UINT32));

  fprintf (pFile, "\n\n  // PACKAGE HEADER\n");
  _WRITE_PKG_LINE(pFile, BYTES_PRE_LINE, "  ", (CHAR8 *)PkgHdr, sizeof (EFI_HII_PACKAGE_HEADER));
  PkgLength = sizeof (EFI_HII_PACKAGE_HEADER);

  fprintf (pFile, "\n\n  // PACKAGE DATA\n");
  
  if (PkgData == NULL) {
    Open ();
    while ((ReadSize = Read ((CHAR8 *)Buffer, BYTES_PRE_LINE * 8)) != 0) {
      PkgLength += ReadSize;
      if (PkgLength < PkgHdr->Length) {
        _WRITE_PKG_LINE (pFile, BYTES_PRE_LINE, "  ", Buffer, ReadSize);
      } else {
        _WRITE_PKG_END (pFile, BYTES_PRE_LINE, "  ", Buffer, ReadSize);
      }
    }
    Close ();
  } else {
    if (PkgData->Size % BYTES_PRE_LINE != 0) {
      PkgLength = PkgData->Size - (PkgData->Size % BYTES_PRE_LINE);
      _WRITE_PKG_LINE (pFile, BYTES_PRE_LINE, "  ", PkgData->Buffer, PkgLength);
      _WRITE_PKG_END (pFile, BYTES_PRE_LINE, "  ", PkgData->Buffer + PkgLength, PkgData->Size % BYTES_PRE_LINE);
    } else {
      PkgLength = PkgData->Size - BYTES_PRE_LINE;
      _WRITE_PKG_LINE (pFile, BYTES_PRE_LINE, "  ", PkgData->Buffer, PkgLength);
      _WRITE_PKG_END (pFile, BYTES_PRE_LINE, "  ", PkgData->Buffer + PkgLength, BYTES_PRE_LINE);
    }
  }

  delete PkgHdr;
  fprintf (pFile, "\n};\n");

  return VFR_RETURN_SUCCESS;
}

EFI_VFR_RETURN_CODE
CFormPkg::AssignPending (
  IN CHAR8  *Key, 
  IN VOID   *ValAddr, 
  IN UINT32 ValLen,
  IN UINT32 LineNo,
  IN CHAR8  *Msg
  )
{
  SPendingAssign *pNew;

  pNew = new SPendingAssign (Key, ValAddr, ValLen, LineNo, Msg);
  if (pNew == NULL) {
    return VFR_RETURN_OUT_FOR_RESOURCES;
  }

  pNew->mNext       = PendingAssignList;
  PendingAssignList = pNew;
  return VFR_RETURN_SUCCESS;
}

VOID
CFormPkg::DoPendingAssign (
  IN CHAR8  *Key, 
  IN VOID   *ValAddr, 
  IN UINT32 ValLen
  )
{
  SPendingAssign *pNode;

  if ((Key == NULL) || (ValAddr == NULL)) {
    return;
  }

  for (pNode = PendingAssignList; pNode != NULL; pNode = pNode->mNext) {
    if (strcmp (pNode->mKey, Key) == 0) {
      pNode->AssignValue (ValAddr, ValLen);
    }
  }
}

bool
CFormPkg::HavePendingUnassigned (
  VOID
  )
{
  SPendingAssign *pNode;

  for (pNode = PendingAssignList; pNode != NULL; pNode = pNode->mNext) {
    if (pNode->mFlag == PENDING) {
      return TRUE;
    }
  }

  return FALSE;
}

VOID
CFormPkg::PendingAssignPrintAll (
  VOID
  )
{
  SPendingAssign *pNode;

  for (pNode = PendingAssignList; pNode != NULL; pNode = pNode->mNext) {
    if (pNode->mFlag == PENDING) {
      gCVfrErrorHandle.PrintMsg (pNode->mLineNo, pNode->mKey, "Error", pNode->mMsg);
    }
  }
}

EFI_VFR_RETURN_CODE
CFormPkg::DeclarePendingQuestion (
  IN CVfrVarDataTypeDB   &lCVfrVarDataTypeDB,
  IN CVfrDataStorage     &lCVfrDataStorage,
  IN CVfrQuestionDB      &lCVfrQuestionDB,
  IN EFI_GUID            *LocalFormSetGuid,
  IN UINT32 LineNo
  )
{
  SPendingAssign *pNode;
  CHAR8          *VarStr;
  UINT32         ArrayIdx;
  CHAR8          FName[MAX_NAME_LEN];
  EFI_VFR_RETURN_CODE  ReturnCode;
  EFI_VFR_VARSTORE_TYPE VarStoreType  = EFI_VFR_VARSTORE_INVALID;

  for (pNode = PendingAssignList; pNode != NULL; pNode = pNode->mNext) {
    if (pNode->mFlag == PENDING) {
      //
      //  declare this question as Numeric in SuppressIf True
      //
      // SuppressIf
      CIfrSuppressIf SIObj;
      SIObj.SetLineNo (LineNo);
      
      //TrueOpcode
      CIfrTrue TObj (LineNo);
      
      //Numeric qeustion
      CIfrNumeric CNObj;
      EFI_VARSTORE_INFO Info; 
  	  EFI_QUESTION_ID   QId   = EFI_QUESTION_ID_INVALID;

      CNObj.SetLineNo (LineNo);
      CNObj.SetPrompt (0x0);
      CNObj.SetHelp (0x0);

      //
      // Register this question, assume it is normal question, not date or time question
      //
      VarStr = pNode->mKey;
      ReturnCode = lCVfrQuestionDB.RegisterQuestion (NULL, VarStr, QId);
      if (ReturnCode != VFR_RETURN_SUCCESS) {
        gCVfrErrorHandle.HandleError (ReturnCode, pNode->mLineNo, pNode->mKey);
        return ReturnCode;
      }
 
#ifdef VFREXP_DEBUG
      printf ("Undefined Question name is %s and Id is 0x%x\n", VarStr, QId);
#endif
      //
      // Get Question Info, framework vfr VarName == StructName
      //
      ReturnCode = lCVfrVarDataTypeDB.ExtractFieldNameAndArrary (VarStr, FName, ArrayIdx);
      if (ReturnCode != VFR_RETURN_SUCCESS) {
        gCVfrErrorHandle.PrintMsg (pNode->mLineNo, pNode->mKey, "Error", "Var string is not the valid C variable");
        return ReturnCode;
      }
      //
      // Get VarStoreType
      //
      ReturnCode = lCVfrDataStorage.GetVarStoreType (FName, VarStoreType);
      if (ReturnCode == VFR_RETURN_UNDEFINED) {
        lCVfrDataStorage.DeclareBufferVarStore (
                           FName, 
                           LocalFormSetGuid, 
                           &lCVfrVarDataTypeDB, 
                           FName,
                           EFI_VARSTORE_ID_INVALID,
                           FALSE
                           );
        ReturnCode = lCVfrDataStorage.GetVarStoreType (FName, VarStoreType);  
      }
      if (ReturnCode != VFR_RETURN_SUCCESS) {
        gCVfrErrorHandle.PrintMsg (pNode->mLineNo, FName, "Error", "Var Store Type is not defined");
        return ReturnCode;
      }
      
      ReturnCode = lCVfrDataStorage.GetVarStoreId (FName, &Info.mVarStoreId);
      if (ReturnCode != VFR_RETURN_SUCCESS) {
        gCVfrErrorHandle.PrintMsg (pNode->mLineNo, FName, "Error", "Var Store Type is not defined");
        return ReturnCode;
      }

      if (*VarStr == '\0' && ArrayIdx != INVALID_ARRAY_INDEX) {
        ReturnCode = lCVfrDataStorage.GetNameVarStoreInfo (&Info, ArrayIdx);
      } else {
        if (VarStoreType == EFI_VFR_VARSTORE_EFI) {
          ReturnCode = lCVfrDataStorage.GetEfiVarStoreInfo (&Info);
        } else if (VarStoreType == EFI_VFR_VARSTORE_BUFFER) {
          VarStr = pNode->mKey;
          ReturnCode = lCVfrVarDataTypeDB.GetDataFieldInfo (VarStr, Info.mInfo.mVarOffset, Info.mVarType, Info.mVarTotalSize);
        } else {
          ReturnCode = VFR_RETURN_UNSUPPORTED;
        }
      }
      if (ReturnCode != VFR_RETURN_SUCCESS) {
        gCVfrErrorHandle.HandleError (ReturnCode, pNode->mLineNo, pNode->mKey);
        return ReturnCode;
      }

      CNObj.SetQuestionId (QId);
      CNObj.SetVarStoreInfo (&Info);
      CNObj.SetFlags (0, Info.mVarType);

      //
      // For undefined Efi VarStore type question
      // Append the extended guided opcode to contain VarName
      //
      if (VarStoreType == EFI_VFR_VARSTORE_EFI) {
        CIfrVarEqName CVNObj (QId, Info.mInfo.mVarName);
        CVNObj.SetLineNo (LineNo);
      }
      
      //
      // End for Numeric
      //
      CIfrEnd CEObj; 
      CEObj.SetLineNo (LineNo);
      //
      // End for SuppressIf
      //
      CIfrEnd SEObj;
      SEObj.SetLineNo (LineNo);
    }
  }
  return VFR_RETURN_SUCCESS;
}

CFormPkg gCFormPkg;

SIfrRecord::SIfrRecord (
  VOID
  )
{
  mIfrBinBuf = NULL;
  mBinBufLen = 0;
  mLineNo    = 0xFFFFFFFF;
  mOffset    = 0xFFFFFFFF;
  mNext      = NULL;
}

SIfrRecord::~SIfrRecord (
  VOID
  )
{
  if (mIfrBinBuf != NULL) {
    //
    // IfrRecord to point to form data buffer.
    //
    mIfrBinBuf = NULL;
  }
  mLineNo      = 0xFFFFFFFF;
  mOffset      = 0xFFFFFFFF;
  mBinBufLen   = 0;
  mNext        = NULL;
}

CIfrRecordInfoDB::CIfrRecordInfoDB (
  VOID
  )
{
  mSwitch            = TRUE;
  mRecordCount       = EFI_IFR_RECORDINFO_IDX_START;
  mIfrRecordListHead = NULL;
  mIfrRecordListTail = NULL;
}

CIfrRecordInfoDB::~CIfrRecordInfoDB (
  VOID
  )
{
  SIfrRecord *pNode;

  while (mIfrRecordListHead != NULL) {
    pNode = mIfrRecordListHead;
    mIfrRecordListHead = mIfrRecordListHead->mNext;
    delete pNode;
  }
}

SIfrRecord *
CIfrRecordInfoDB::GetRecordInfoFromIdx (
  IN UINT32 RecordIdx
  )
{
  UINT32     Idx;
  SIfrRecord *pNode = NULL;

  if (RecordIdx == EFI_IFR_RECORDINFO_IDX_INVALUD) {
    return NULL;
  }

  for (Idx = (EFI_IFR_RECORDINFO_IDX_START + 1), pNode = mIfrRecordListHead; 
       (Idx != RecordIdx) && (pNode != NULL); 
       Idx++, pNode = pNode->mNext)
  ;

  return pNode;
}

UINT32
CIfrRecordInfoDB::IfrRecordRegister (
  IN UINT32 LineNo, 
  IN CHAR8  *IfrBinBuf, 
  IN UINT8  BinBufLen,
  IN UINT32 Offset
  )
{
  SIfrRecord *pNew;

  if (mSwitch == FALSE) {
    return EFI_IFR_RECORDINFO_IDX_INVALUD;
  }

  if ((pNew = new SIfrRecord) == NULL) {
    return EFI_IFR_RECORDINFO_IDX_INVALUD;
  }

  if (mIfrRecordListHead == NULL) {
    mIfrRecordListHead = pNew;
    mIfrRecordListTail = pNew;
  } else {
    mIfrRecordListTail->mNext = pNew;
    mIfrRecordListTail = pNew;
  }
  mRecordCount++;

  return mRecordCount;
}

VOID
CIfrRecordInfoDB::IfrRecordInfoUpdate (
  IN UINT32 RecordIdx, 
  IN UINT32 LineNo,
  IN CHAR8  *BinBuf,
  IN UINT8  BinBufLen,
  IN UINT32 Offset
  )
{
  SIfrRecord *pNode;

  if ((pNode = GetRecordInfoFromIdx (RecordIdx)) == NULL) {
    return;
  }

  pNode->mLineNo    = LineNo;
  pNode->mOffset    = Offset;
  pNode->mBinBufLen = BinBufLen;
  pNode->mIfrBinBuf = BinBuf;

}

VOID
CIfrRecordInfoDB::IfrRecordOutput (
  OUT PACKAGE_DATA &TBuffer
  )
{
  CHAR8      *Temp;
  SIfrRecord *pNode; 

  if (TBuffer.Buffer != NULL) {
    delete TBuffer.Buffer;
  }

  TBuffer.Size = 0;
  TBuffer.Buffer = NULL;


  if (mSwitch == FALSE) {
    return;
  } 
   
  for (pNode = mIfrRecordListHead; pNode != NULL; pNode = pNode->mNext) {
    TBuffer.Size += pNode->mBinBufLen;
  }
  
  if (TBuffer.Size != 0) {
    TBuffer.Buffer = new CHAR8[TBuffer.Size];
  } else {
    return;
  }
  
  Temp = TBuffer.Buffer;

  for (pNode = mIfrRecordListHead; pNode != NULL; pNode = pNode->mNext) {
    if (pNode->mIfrBinBuf != NULL) {
      memcpy (Temp, pNode->mIfrBinBuf, pNode->mBinBufLen);
      Temp += pNode->mBinBufLen;
    }
  }

  return;   
}   

VOID
CIfrRecordInfoDB::IfrRecordOutput (
  IN FILE   *File,
  IN UINT32 LineNo
  )
{
  SIfrRecord *pNode;
  UINT8      Index;
  UINT32     TotalSize;

  if (mSwitch == FALSE) {
    return;
  }

  if (File == NULL) {
    return;
  }

  TotalSize = 0;

  for (pNode = mIfrRecordListHead; pNode != NULL; pNode = pNode->mNext) {
    if (pNode->mLineNo == LineNo || LineNo == 0) {
      fprintf (File, ">%08X: ", pNode->mOffset);
      TotalSize += pNode->mBinBufLen;
      if (pNode->mIfrBinBuf != NULL) {
        for (Index = 0; Index < pNode->mBinBufLen; Index++) {
          fprintf (File, "%02X ", (UINT8) pNode->mIfrBinBuf[Index]);
        }
      }
      fprintf (File, "\n");
    }
  }
  
  if (LineNo == 0) {
    fprintf (File, "\nTotal Size of all record is 0x%08X\n", TotalSize);
  }
}

//
// for framework vfr file
// adjust opcode sequence for uefi IFR format
// adjust inconsistent and varstore into the right position.
//
BOOLEAN
CIfrRecordInfoDB::CheckQuestionOpCode (
  IN UINT8 OpCode
  )
{
  switch (OpCode) {
  case EFI_IFR_CHECKBOX_OP:
  case EFI_IFR_NUMERIC_OP:
  case EFI_IFR_PASSWORD_OP:
  case EFI_IFR_ONE_OF_OP:
  case EFI_IFR_ACTION_OP:
  case EFI_IFR_STRING_OP:
  case EFI_IFR_DATE_OP:
  case EFI_IFR_TIME_OP:
  case EFI_IFR_ORDERED_LIST_OP:
    return TRUE;
  default:
    return FALSE;
  }
}

BOOLEAN
CIfrRecordInfoDB::CheckIdOpCode (
  IN UINT8 OpCode
  )
{
  switch (OpCode) {
  case EFI_IFR_EQ_ID_VAL_OP:
  case EFI_IFR_EQ_ID_ID_OP:
  case EFI_IFR_EQ_ID_LIST_OP:
  case EFI_IFR_QUESTION_REF1_OP:
    return TRUE;
  default:
    return FALSE;
  }
} 

EFI_QUESTION_ID
CIfrRecordInfoDB::GetOpcodeQuestionId (
  IN EFI_IFR_OP_HEADER *OpHead
  )
{
  EFI_IFR_QUESTION_HEADER *QuestionHead;
  
  QuestionHead = (EFI_IFR_QUESTION_HEADER *) (OpHead + 1);
  
  return QuestionHead->QuestionId;
}

EFI_VFR_RETURN_CODE
CIfrRecordInfoDB::IfrRecordAdjust (
  VOID
  )
{
  SIfrRecord *pNode, *preNode;
  SIfrRecord *uNode, *tNode;
  EFI_IFR_OP_HEADER  *OpHead, *tOpHead;
  EFI_QUESTION_ID    QuestionId;
  UINT32             StackCount;
  UINT32             QuestionScope;
  UINT32             OpcodeOffset;
  CHAR8              ErrorMsg[MAX_STRING_LEN] = {0, };
  EFI_VFR_RETURN_CODE  Status;

  //
  // Init local variable
  //
  Status = VFR_RETURN_SUCCESS;
  pNode = mIfrRecordListHead;
  preNode = pNode;
  QuestionScope = 0;
  while (pNode != NULL) {
    OpHead = (EFI_IFR_OP_HEADER *) pNode->mIfrBinBuf;
    
    //
    // make sure the inconsistent opcode in question scope
    //
    if (QuestionScope > 0) {
      QuestionScope += OpHead->Scope;
      if (OpHead->OpCode == EFI_IFR_END_OP) {
        QuestionScope --;
      }
    }
    
    if (CheckQuestionOpCode (OpHead->OpCode)) {
      QuestionScope = 1;
    }
    //
    // for the inconsistent opcode not in question scope, adjust it
    //
    if (OpHead->OpCode == EFI_IFR_INCONSISTENT_IF_OP && QuestionScope == 0) {
      //
      // for inconsistent opcode not in question scope
      //

      //
      // Count inconsistent opcode Scope 
      //
      StackCount = OpHead->Scope;
      QuestionId = EFI_QUESTION_ID_INVALID;
      tNode = pNode;
      while (tNode != NULL && StackCount > 0) {
        tNode = tNode->mNext;
        tOpHead = (EFI_IFR_OP_HEADER *) tNode->mIfrBinBuf;
        //
        // Calculate Scope Number
        //
        StackCount += tOpHead->Scope;
        if (tOpHead->OpCode == EFI_IFR_END_OP) {
          StackCount --;
        }
        //
        // by IdEqual opcode to get QuestionId
        //
        if (QuestionId == EFI_QUESTION_ID_INVALID && 
            CheckIdOpCode (tOpHead->OpCode)) {
          QuestionId = *(EFI_QUESTION_ID *) (tOpHead + 1);
        }
      }
      if (tNode == NULL || QuestionId == EFI_QUESTION_ID_INVALID) {
        //
        // report error; not found
        //
        sprintf (ErrorMsg, "Inconsistent OpCode Record list invalid QuestionId is 0x%X", QuestionId);
        gCVfrErrorHandle.PrintMsg (0, NULL, "Error", ErrorMsg);
        Status = VFR_RETURN_MISMATCHED;
        break;
      }
      //
      // extract inconsistent opcode list
      // pNode is Incosistent opcode, tNode is End Opcode
      //
      
      //
      // insert inconsistent opcode list into the right question scope by questionid
      //
      for (uNode = mIfrRecordListHead; uNode != NULL; uNode = uNode->mNext) {
        tOpHead = (EFI_IFR_OP_HEADER *) uNode->mIfrBinBuf;
        if (CheckQuestionOpCode (tOpHead->OpCode) && 
            (QuestionId == GetOpcodeQuestionId (tOpHead))) {
          break;
        }
      }
      //
      // insert inconsistent opcode list and check LATE_CHECK flag
      //
      if (uNode != NULL) {
        if ((((EFI_IFR_QUESTION_HEADER *)(tOpHead + 1))->Flags & 0x20) != 0) {
          //
          // if LATE_CHECK flag is set, change inconsistent to nosumbit
          //
          OpHead->OpCode = EFI_IFR_NO_SUBMIT_IF_OP;
        }
        
        //
        // skip the default storage for Date and Time
        //
        if ((uNode->mNext != NULL) && (*uNode->mNext->mIfrBinBuf == EFI_IFR_DEFAULT_OP)) {
          uNode = uNode->mNext;
        }

        preNode->mNext = tNode->mNext;
        tNode->mNext = uNode->mNext;
        uNode->mNext = pNode;
        //
        // reset pNode to head list, scan the whole list again.
        //
        pNode = mIfrRecordListHead;
        preNode = pNode;
        QuestionScope = 0;
        continue;
      } else {
        //
        // not found matched question id, report error
        //
        sprintf (ErrorMsg, "QuestionId required by Inconsistent OpCode is not found. QuestionId is 0x%X", QuestionId);
        gCVfrErrorHandle.PrintMsg (0, NULL, "Error", ErrorMsg);
        Status = VFR_RETURN_MISMATCHED;
        break;
      }
    } else if (OpHead->OpCode == EFI_IFR_VARSTORE_OP || 
               OpHead->OpCode == EFI_IFR_VARSTORE_EFI_OP) {
      //
      // for new added group of varstore opcode
      //
      tNode = pNode;
      while (tNode->mNext != NULL) {
        tOpHead = (EFI_IFR_OP_HEADER *) tNode->mNext->mIfrBinBuf;
        if (tOpHead->OpCode != EFI_IFR_VARSTORE_OP && 
            tOpHead->OpCode != EFI_IFR_VARSTORE_EFI_OP) {
          break;    
        }
        tNode = tNode->mNext;
      }

      if (tNode->mNext == NULL) {
        //
        // invalid IfrCode, IfrCode end by EndOpCode
        // 
        gCVfrErrorHandle.PrintMsg (0, NULL, "Error", "No found End Opcode in the end");
        Status = VFR_RETURN_MISMATCHED;
        break;
      }
      
      if (tOpHead->OpCode != EFI_IFR_END_OP) {
          //
          // not new added varstore, which are not needed to be adjust.
          //
          preNode = tNode;
          pNode   = tNode->mNext;
          continue;        
      } else {
        //
        // move new added varstore opcode to the position befor form opcode 
        // varstore opcode between pNode and tNode
        //

        //
        // search form opcode from begin
        //
        for (uNode = mIfrRecordListHead; uNode->mNext != NULL; uNode = uNode->mNext) {
          tOpHead = (EFI_IFR_OP_HEADER *) uNode->mNext->mIfrBinBuf;
          if (tOpHead->OpCode == EFI_IFR_FORM_OP) {
            break;
          }
        }
        //
        // Insert varstore opcode beform form opcode if form opcode is found
        //
        if (uNode->mNext != NULL) {
          preNode->mNext = tNode->mNext;
          tNode->mNext = uNode->mNext;
          uNode->mNext = pNode;
          //
          // reset pNode to head list, scan the whole list again.
          //
          pNode = mIfrRecordListHead;
          preNode = pNode;
          QuestionScope = 0;
          continue;
        } else {
          //
          // not found form, continue scan IfrRecord list
          //
          preNode = tNode;
          pNode   = tNode->mNext;
          continue;
        }
      }
    }
    //
    // next node
    //
    preNode = pNode;
    pNode = pNode->mNext; 
  }
  
  //
  // Update Ifr Opcode Offset
  //
  if (Status == VFR_RETURN_SUCCESS) {
    OpcodeOffset = 0;
    for (pNode = mIfrRecordListHead; pNode != NULL; pNode = pNode->mNext) {
      pNode->mOffset = OpcodeOffset;
      OpcodeOffset += pNode->mBinBufLen;
    }
  }
  return Status;
}

CIfrRecordInfoDB gCIfrRecordInfoDB;

VOID
CIfrObj::_EMIT_PENDING_OBJ (
  VOID
  )
{
  CHAR8  *ObjBinBuf = NULL;
  
  //
  // do nothing
  //
  if (!mDelayEmit || !gCreateOp) {
    return;
  }

  mPkgOffset = gCFormPkg.GetPkgLength ();
  //
  // update data buffer to package data
  //
  ObjBinBuf  = gCFormPkg.IfrBinBufferGet (mObjBinLen);
  if (ObjBinBuf != NULL) {
    memcpy (ObjBinBuf, mObjBinBuf, mObjBinLen);
  }
  
  //
  // update bin buffer to package data buffer
  //
  if (mObjBinBuf != NULL) {
    delete mObjBinBuf;
    mObjBinBuf = ObjBinBuf;
  }
  
  mDelayEmit = FALSE;
}

/*
 * The definition of CIfrObj's member function
 */
static struct {
  UINT8  mSize;
  UINT8  mScope;
} gOpcodeSizesScopeTable[] = {
  { 0, 0 },                                    // EFI_IFR_INVALID - 0x00
  { sizeof (EFI_IFR_FORM), 1 },                // EFI_IFR_FORM_OP
  { sizeof (EFI_IFR_SUBTITLE), 1 },            // EFI_IFR_SUBTITLE_OP
  { sizeof (EFI_IFR_TEXT), 0 },                // EFI_IFR_TEXT_OP
  { sizeof (EFI_IFR_IMAGE), 0 },               // EFI_IFR_IMAGE_OP
  { sizeof (EFI_IFR_ONE_OF), 1 },              // EFI_IFR_ONE_OF_OP - 0x05
  { sizeof (EFI_IFR_CHECKBOX), 1},             // EFI_IFR_CHECKBOX_OP
  { sizeof (EFI_IFR_NUMERIC), 1 },             // EFI_IFR_NUMERIC_OP
  { sizeof (EFI_IFR_PASSWORD), 1 },            // EFI_IFR_PASSWORD_OP
  { sizeof (EFI_IFR_ONE_OF_OPTION), 0 },       // EFI_IFR_ONE_OF_OPTION_OP
  { sizeof (EFI_IFR_SUPPRESS_IF), 1 },         // EFI_IFR_SUPPRESS_IF - 0x0A
  { sizeof (EFI_IFR_LOCKED), 0 },              // EFI_IFR_LOCKED_OP
  { sizeof (EFI_IFR_ACTION), 1 },              // EFI_IFR_ACTION_OP
  { sizeof (EFI_IFR_RESET_BUTTON), 1 },        // EFI_IFR_RESET_BUTTON_OP
  { sizeof (EFI_IFR_FORM_SET), 1 },            // EFI_IFR_FORM_SET_OP -0xE
  { sizeof (EFI_IFR_REF), 0 },                 // EFI_IFR_REF_OP
  { sizeof (EFI_IFR_NO_SUBMIT_IF), 1},         // EFI_IFR_NO_SUBMIT_IF_OP -0x10
  { sizeof (EFI_IFR_INCONSISTENT_IF), 1 },     // EFI_IFR_INCONSISTENT_IF_OP
  { sizeof (EFI_IFR_EQ_ID_VAL), 0 },           // EFI_IFR_EQ_ID_VAL_OP
  { sizeof (EFI_IFR_EQ_ID_ID), 0 },            // EFI_IFR_EQ_ID_ID_OP
  { sizeof (EFI_IFR_EQ_ID_LIST), 0 },          // EFI_IFR_EQ_ID_LIST_OP - 0x14
  { sizeof (EFI_IFR_AND), 0 },                 // EFI_IFR_AND_OP
  { sizeof (EFI_IFR_OR), 0 },                  // EFI_IFR_OR_OP
  { sizeof (EFI_IFR_NOT), 0 },                 // EFI_IFR_NOT_OP
  { sizeof (EFI_IFR_RULE), 1 },                // EFI_IFR_RULE_OP
  { sizeof (EFI_IFR_GRAY_OUT_IF), 1 },         // EFI_IFR_GRAYOUT_IF_OP - 0x19
  { sizeof (EFI_IFR_DATE), 1 },                // EFI_IFR_DATE_OP
  { sizeof (EFI_IFR_TIME), 1 },                // EFI_IFR_TIME_OP
  { sizeof (EFI_IFR_STRING), 1 },              // EFI_IFR_STRING_OP
  { sizeof (EFI_IFR_REFRESH), 1 },             // EFI_IFR_REFRESH_OP
  { sizeof (EFI_IFR_DISABLE_IF), 1 },          // EFI_IFR_DISABLE_IF_OP - 0x1E
  { 0, 0 },                                    // 0x1F
  { sizeof (EFI_IFR_TO_LOWER), 0 },            // EFI_IFR_TO_LOWER_OP - 0x20
  { sizeof (EFI_IFR_TO_UPPER), 0 },            // EFI_IFR_TO_UPPER_OP - 0x21
  { 0, 0 },                                    // 0x22
  { sizeof (EFI_IFR_ORDERED_LIST), 1 },        // EFI_IFR_ORDERED_LIST_OP - 0x23
  { sizeof (EFI_IFR_VARSTORE), 0 },            // EFI_IFR_VARSTORE_OP
  { sizeof (EFI_IFR_VARSTORE_NAME_VALUE), 0 }, // EFI_IFR_VARSTORE_NAME_VALUE_OP
  { sizeof (EFI_IFR_VARSTORE_EFI), 0 },        // EFI_IFR_VARSTORE_EFI_OP
  { sizeof (EFI_IFR_VARSTORE_DEVICE), 1 },     // EFI_IFR_VARSTORE_DEVICE_OP
  { sizeof (EFI_IFR_VERSION), 0 },             // EFI_IFR_VERSION_OP - 0x28
  { sizeof (EFI_IFR_END), 0 },                 // EFI_IFR_END_OP
  { sizeof (EFI_IFR_MATCH), 1 },               // EFI_IFR_MATCH_OP - 0x2A
  { 0, 0 }, { 0, 0} , { 0, 0} , { 0, 0} ,      // 0x2B ~ 0x2E
  { sizeof (EFI_IFR_EQUAL), 0 },               // EFI_IFR_EQUAL_OP - 0x2F
  { sizeof (EFI_IFR_NOT_EQUAL), 0 },           // EFI_IFR_NOT_EQUAL_OP
  { sizeof (EFI_IFR_GREATER_THAN), 0 },        // EFI_IFR_GREATER_THAN_OP
  { sizeof (EFI_IFR_GREATER_EQUAL), 0 },       // EFI_IFR_GREATER_EQUAL_OP
  { sizeof (EFI_IFR_LESS_THAN), 0 },           // EFI_IFR_LESS_THAN_OP
  { sizeof (EFI_IFR_LESS_EQUAL), 0 },          // EFI_IFR_LESS_EQUAL_OP - 0x34
  { sizeof (EFI_IFR_BITWISE_AND), 0 },         // EFI_IFR_BITWISE_AND_OP
  { sizeof (EFI_IFR_BITWISE_OR), 0 },          // EFI_IFR_BITWISE_OR_OP
  { sizeof (EFI_IFR_BITWISE_NOT), 0 },         // EFI_IFR_BITWISE_NOT_OP
  { sizeof (EFI_IFR_SHIFT_LEFT), 0 },          // EFI_IFR_SHIFT_LEFT_OP
  { sizeof (EFI_IFR_SHIFT_RIGHT), 0 },         // EFI_IFR_SHIFT_RIGHT_OP
  { sizeof (EFI_IFR_ADD), 0 },                 // EFI_IFR_ADD_OP - 0x3A
  { sizeof (EFI_IFR_SUBTRACT), 0 },            // EFI_IFR_SUBTRACT_OP
  { sizeof (EFI_IFR_MULTIPLY), 0 },            // EFI_IFR_MULTIPLY_OP
  { sizeof (EFI_IFR_DIVIDE), 0 },              // EFI_IFR_DIVIDE_OP
  { sizeof (EFI_IFR_MODULO), 0 },              // EFI_IFR_MODULO_OP - 0x3E
  { sizeof (EFI_IFR_RULE_REF), 0 },            // EFI_IFR_RULE_REF_OP
  { sizeof (EFI_IFR_QUESTION_REF1), 0 },       // EFI_IFR_QUESTION_REF1_OP
  { sizeof (EFI_IFR_QUESTION_REF2), 0 },       // EFI_IFR_QUESTION_REF2_OP - 0x41
  { sizeof (EFI_IFR_UINT8), 0},                // EFI_IFR_UINT8
  { sizeof (EFI_IFR_UINT16), 0},               // EFI_IFR_UINT16
  { sizeof (EFI_IFR_UINT32), 0},               // EFI_IFR_UINT32
  { sizeof (EFI_IFR_UINT64), 0},               // EFI_IFR_UTNT64
  { sizeof (EFI_IFR_TRUE), 0 },                // EFI_IFR_TRUE_OP - 0x46
  { sizeof (EFI_IFR_FALSE), 0 },               // EFI_IFR_FALSE_OP
  { sizeof (EFI_IFR_TO_UINT), 0 },             // EFI_IFR_TO_UINT_OP
  { sizeof (EFI_IFR_TO_STRING), 0 },           // EFI_IFR_TO_STRING_OP
  { sizeof (EFI_IFR_TO_BOOLEAN), 0 },          // EFI_IFR_TO_BOOLEAN_OP
  { sizeof (EFI_IFR_MID), 0 },                 // EFI_IFR_MID_OP
  { sizeof (EFI_IFR_FIND), 0 },                // EFI_IFR_FIND_OP
  { sizeof (EFI_IFR_TOKEN), 0 },               // EFI_IFR_TOKEN_OP
  { sizeof (EFI_IFR_STRING_REF1), 0 },         // EFI_IFR_STRING_REF1_OP - 0x4E
  { sizeof (EFI_IFR_STRING_REF2), 0 },         // EFI_IFR_STRING_REF2_OP
  { sizeof (EFI_IFR_CONDITIONAL), 0 },         // EFI_IFR_CONDITIONAL_OP
  { sizeof (EFI_IFR_QUESTION_REF3), 0 },       // EFI_IFR_QUESTION_REF3_OP
  { sizeof (EFI_IFR_ZERO), 0 },                // EFI_IFR_ZERO_OP
  { sizeof (EFI_IFR_ONE), 0 },                 // EFI_IFR_ONE_OP
  { sizeof (EFI_IFR_ONES), 0 },                // EFI_IFR_ONES_OP
  { sizeof (EFI_IFR_UNDEFINED), 0 },           // EFI_IFR_UNDEFINED_OP
  { sizeof (EFI_IFR_LENGTH), 0 },              // EFI_IFR_LENGTH_OP
  { sizeof (EFI_IFR_DUP), 0 },                 // EFI_IFR_DUP_OP - 0x57
  { sizeof (EFI_IFR_THIS), 0 },                // EFI_IFR_THIS_OP
  { sizeof (EFI_IFR_SPAN), 0 },                // EFI_IFR_SPAN_OP
  { sizeof (EFI_IFR_VALUE), 1 },               // EFI_IFR_VALUE_OP
  { sizeof (EFI_IFR_DEFAULT), 0 },             // EFI_IFR_DEFAULT_OP
  { sizeof (EFI_IFR_DEFAULTSTORE), 0 },        // EFI_IFR_DEFAULTSTORE_OP - 0x5C
  { 0, 0},                                     // 0x5D
  { sizeof (EFI_IFR_CATENATE), 0 },            // EFI_IFR_CATENATE_OP
  { sizeof (EFI_IFR_GUID), 0 },                // EFI_IFR_GUID_OP
};

#ifdef CIFROBJ_DEUBG
static struct {
  CHAR8 *mIfrName;
} gIfrObjPrintDebugTable[] = {
  "EFI_IFR_INVALID",    "EFI_IFR_FORM",                 "EFI_IFR_SUBTITLE",      "EFI_IFR_TEXT",            "EFI_IFR_IMAGE",         "EFI_IFR_ONE_OF",
  "EFI_IFR_CHECKBOX",   "EFI_IFR_NUMERIC",              "EFI_IFR_PASSWORD",      "EFI_IFR_ONE_OF_OPTION",   "EFI_IFR_SUPPRESS_IF",   "EFI_IFR_LOCKED",
  "EFI_IFR_ACTION",     "EFI_IFR_RESET_BUTTON",         "EFI_IFR_FORM_SET",      "EFI_IFR_REF",             "EFI_IFR_NO_SUBMIT_IF",  "EFI_IFR_INCONSISTENT_IF",
  "EFI_IFR_EQ_ID_VAL",  "EFI_IFR_EQ_ID_ID",             "EFI_IFR_EQ_ID_LIST",    "EFI_IFR_AND",             "EFI_IFR_OR",            "EFI_IFR_NOT",
  "EFI_IFR_RULE",       "EFI_IFR_GRAY_OUT_IF",          "EFI_IFR_DATE",          "EFI_IFR_TIME",            "EFI_IFR_STRING",        "EFI_IFR_REFRESH",
  "EFI_IFR_DISABLE_IF", "EFI_IFR_INVALID",              "EFI_IFR_TO_LOWER",      "EFI_IFR_TO_UPPER",        "EFI_IFR_INVALID",       "EFI_IFR_ORDERED_LIST",
  "EFI_IFR_VARSTORE",   "EFI_IFR_VARSTORE_NAME_VALUE",  "EFI_IFR_VARSTORE_EFI",  "EFI_IFR_VARSTORE_DEVICE", "EFI_IFR_VERSION",       "EFI_IFR_END",
  "EFI_IFR_MATCH",      "EFI_IFR_INVALID",              "EFI_IFR_INVALID",       "EFI_IFR_INVALID",         "EFI_IFR_INVALID",       "EFI_IFR_EQUAL",
  "EFI_IFR_NOT_EQUAL",  "EFI_IFR_GREATER_THAN",         "EFI_IFR_GREATER_EQUAL", "EFI_IFR_LESS_THAN",       "EFI_IFR_LESS_EQUAL",    "EFI_IFR_BITWISE_AND",
  "EFI_IFR_BITWISE_OR", "EFI_IFR_BITWISE_NOT",          "EFI_IFR_SHIFT_LEFT",    "EFI_IFR_SHIFT_RIGHT",     "EFI_IFR_ADD",           "EFI_IFR_SUBTRACT",
  "EFI_IFR_MULTIPLY",   "EFI_IFR_DIVIDE",               "EFI_IFR_MODULO",        "EFI_IFR_RULE_REF",        "EFI_IFR_QUESTION_REF1", "EFI_IFR_QUESTION_REF2",
  "EFI_IFR_UINT8",      "EFI_IFR_UINT16",               "EFI_IFR_UINT32",        "EFI_IFR_UINT64",          "EFI_IFR_TRUE",          "EFI_IFR_FALSE",
  "EFI_IFR_TO_UINT",    "EFI_IFR_TO_STRING",            "EFI_IFR_TO_BOOLEAN",    "EFI_IFR_MID",             "EFI_IFR_FIND",          "EFI_IFR_TOKEN",
  "EFI_IFR_STRING_REF1","EFI_IFR_STRING_REF2",          "EFI_IFR_CONDITIONAL",   "EFI_IFR_QUESTION_REF3",   "EFI_IFR_ZERO",          "EFI_IFR_ONE",
  "EFI_IFR_ONES",       "EFI_IFR_UNDEFINED",            "EFI_IFR_LENGTH",        "EFI_IFR_DUP",             "EFI_IFR_THIS",          "EFI_IFR_SPAN",
  "EFI_IFR_VALUE",      "EFI_IFR_DEFAULT",              "EFI_IFR_DEFAULTSTORE",  "EFI_IFR_INVALID",         "EFI_IFR_CATENATE",      "EFI_IFR_GUID",
};

VOID
CIFROBJ_DEBUG_PRINT (
  IN UINT8 OpCode
  )
{
  printf ("======Create IFR [%s]\n", gIfrObjPrintDebugTable[OpCode].mIfrName);
}
#else

#define CIFROBJ_DEBUG_PRINT(OpCode)

#endif

bool gCreateOp = TRUE;

CIfrObj::CIfrObj (
  IN  UINT8   OpCode,
  OUT CHAR8   **IfrObj,
  IN  UINT8   ObjBinLen,
  IN  BOOLEAN DelayEmit
  )
{
  mDelayEmit   = DelayEmit;
  mPkgOffset   = gCFormPkg.GetPkgLength ();
  mObjBinLen   = (ObjBinLen == 0) ? gOpcodeSizesScopeTable[OpCode].mSize : ObjBinLen;
  mObjBinBuf   = ((DelayEmit == FALSE) && (gCreateOp == TRUE)) ? gCFormPkg.IfrBinBufferGet (mObjBinLen) : new CHAR8[EFI_IFR_MAX_LENGTH];
  mRecordIdx   = (gCreateOp == TRUE) ? gCIfrRecordInfoDB.IfrRecordRegister (0xFFFFFFFF, mObjBinBuf, mObjBinLen, mPkgOffset) : EFI_IFR_RECORDINFO_IDX_INVALUD;

  if (IfrObj != NULL) {
    *IfrObj    = mObjBinBuf;
  }

  CIFROBJ_DEBUG_PRINT (OpCode);
}

CIfrObj::~CIfrObj (
  VOID
  )
{
  if ((mDelayEmit == TRUE) && ((gCreateOp == TRUE))) {
    _EMIT_PENDING_OBJ ();
  }

  gCIfrRecordInfoDB.IfrRecordInfoUpdate (mRecordIdx, mLineNo, mObjBinBuf, mObjBinLen, mPkgOffset);
}

/*
 * The definition of CIfrObj's member function
 */
UINT8 gScopeCount = 0;

CIfrOpHeader::CIfrOpHeader (
  IN UINT8 OpCode, 
  IN VOID *StartAddr,
  IN UINT8 Length 
  ) : mHeader ((EFI_IFR_OP_HEADER *)StartAddr) 
{
  mHeader->OpCode = OpCode;
  mHeader->Length = (Length == 0) ? gOpcodeSizesScopeTable[OpCode].mSize : Length;
  mHeader->Scope  = (gOpcodeSizesScopeTable[OpCode].mScope + gScopeCount > 0) ? 1 : 0;
}

CIfrOpHeader::CIfrOpHeader (
  IN CIfrOpHeader &OpHdr
  )
{
  mHeader = OpHdr.mHeader;
}

UINT32 CIfrForm::FormIdBitMap[EFI_FREE_FORM_ID_BITMAP_SIZE] = {0, };
