/*++

Copyright (c) 2006, Intel Corporation                                                         
All rights reserved. This program and the accompanying materials                          
are licensed and made available under the terms and conditions of the BSD License         
which accompanies this distribution.  The full text of the license may be found at        
http://opensource.org/licenses/bsd-license.php                                            
                                                                                          
THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,                     
WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.             

Module Name:

  TianoDecompress.c

Abstract:

  Tiano Decompress Library 

--*/

#include "TianoDecompress.h"

EFI_STATUS
GetFileContents (
  IN char    *InputFileName,
  OUT UINT8   *FileBuffer,
  OUT UINT32  *BufferLength
  );
  
VOID
FillBuf (
  IN  SCRATCH_DATA  *Sd,
  IN  UINT16        NumOfBits
  )
/*++

Routine Description:

  Shift mBitBuf NumOfBits left. Read in NumOfBits of bits from source.

Arguments:

  Sd        - The global scratch data
  NumOfBits  - The number of bits to shift and read.

Returns: (VOID)

--*/
{
  Sd->mBitBuf = (UINT32) (Sd->mBitBuf << NumOfBits);

  while (NumOfBits > Sd->mBitCount) {

    Sd->mBitBuf |= (UINT32) (Sd->mSubBitBuf << (NumOfBits = (UINT16) (NumOfBits - Sd->mBitCount)));

    if (Sd->mCompSize > 0) {
      //
      // Get 1 byte into SubBitBuf
      //
      Sd->mCompSize--;
      Sd->mSubBitBuf  = 0;
      Sd->mSubBitBuf  = Sd->mSrcBase[Sd->mInBuf++];
      Sd->mBitCount   = 8;

    } else {
      //
      // No more bits from the source, just pad zero bit.
      //
      Sd->mSubBitBuf  = 0;
      Sd->mBitCount   = 8;

    }
  }

  Sd->mBitCount = (UINT16) (Sd->mBitCount - NumOfBits);
  Sd->mBitBuf |= Sd->mSubBitBuf >> Sd->mBitCount;
}

UINT32
GetBits (
  IN  SCRATCH_DATA  *Sd,
  IN  UINT16        NumOfBits
  )
/*++

Routine Description:

  Get NumOfBits of bits out from mBitBuf. Fill mBitBuf with subsequent 
  NumOfBits of bits from source. Returns NumOfBits of bits that are 
  popped out.

Arguments:

  Sd            - The global scratch data.
  NumOfBits     - The number of bits to pop and read.

Returns:

  The bits that are popped out.

--*/
{
  UINT32  OutBits;

  OutBits = (UINT32) (Sd->mBitBuf >> (BITBUFSIZ - NumOfBits));

  FillBuf (Sd, NumOfBits);

  return OutBits;
}

UINT16
MakeTable (
  IN  SCRATCH_DATA  *Sd,
  IN  UINT16        NumOfChar,
  IN  UINT8         *BitLen,
  IN  UINT16        TableBits,
  OUT UINT16        *Table
  )
/*++

Routine Description:

  Creates Huffman Code mapping table according to code length array.

Arguments:

  Sd        - The global scratch data
  NumOfChar - Number of symbols in the symbol set
  BitLen    - Code length array
  TableBits - The width of the mapping table
  Table     - The table
  
Returns:
  
  0         - OK.
  BAD_TABLE - The table is corrupted.

--*/
{
  UINT16  Count[17];
  UINT16  Weight[17];
  UINT16  Start[18];
  UINT16  *Pointer;
  UINT16  Index3;
  volatile UINT16  Index;
  UINT16  Len;
  UINT16  Char;
  UINT16  JuBits;
  UINT16  Avail;
  UINT16  NextCode;
  UINT16  Mask;
  UINT16  WordOfStart;
  UINT16  WordOfCount;

  for (Index = 1; Index <= 16; Index++) {
    Count[Index] = 0;
  }

  for (Index = 0; Index < NumOfChar; Index++) {
    Count[BitLen[Index]]++;
  }

  Start[1] = 0;

  for (Index = 1; Index <= 16; Index++) {
    WordOfStart = Start[Index];
    WordOfCount = Count[Index];
    Start[Index + 1] = (UINT16) (WordOfStart + (WordOfCount << (16 - Index)));
  }

  if (Start[17] != 0) {
    /*(1U << 16)*/
    return (UINT16) BAD_TABLE;
  }

  JuBits = (UINT16) (16 - TableBits);

  for (Index = 1; Index <= TableBits; Index++) {
    Start[Index] >>= JuBits;
    Weight[Index] = (UINT16) (1U << (TableBits - Index));
  }

  while (Index <= 16) {
    Weight[Index] = (UINT16) (1U << (16 - Index));
    Index++;
  }

  Index = (UINT16) (Start[TableBits + 1] >> JuBits);

  if (Index != 0) {
    Index3 = (UINT16) (1U << TableBits);
    while (Index != Index3) {
      Table[Index++] = 0;
    }
  }

  Avail = NumOfChar;
  Mask  = (UINT16) (1U << (15 - TableBits));

  for (Char = 0; Char < NumOfChar; Char++) {

    Len = BitLen[Char];
    if (Len == 0) {
      continue;
    }

    NextCode = (UINT16) (Start[Len] + Weight[Len]);

    if (Len <= TableBits) {

      for (Index = Start[Len]; Index < NextCode; Index++) {
        Table[Index] = Char;
      }

    } else {

      Index3  = Start[Len];
      Pointer = &Table[Index3 >> JuBits];
      Index   = (UINT16) (Len - TableBits);

      while (Index != 0) {
        if (*Pointer == 0) {
          Sd->mRight[Avail]                     = Sd->mLeft[Avail] = 0;
          *Pointer = Avail++;
        }

        if (Index3 & Mask) {
          Pointer = &Sd->mRight[*Pointer];
        } else {
          Pointer = &Sd->mLeft[*Pointer];
        }

        Index3 <<= 1;
        Index--;
      }

      *Pointer = Char;

    }

    Start[Len] = NextCode;
  }
  //
  // Succeeds
  //
  return 0;
}

UINT32
DecodeP (
  IN  SCRATCH_DATA  *Sd
  )
/*++

Routine Description:

  Decodes a position value.

Arguments:

  Sd      - the global scratch data

Returns:

  The position value decoded.

--*/
{
  UINT16  Val;
  UINT32  Mask;
  UINT32  Pos;

  Val = Sd->mPTTable[Sd->mBitBuf >> (BITBUFSIZ - 8)];

  if (Val >= MAXNP) {
    Mask = 1U << (BITBUFSIZ - 1 - 8);

    do {

      if (Sd->mBitBuf & Mask) {
        Val = Sd->mRight[Val];
      } else {
        Val = Sd->mLeft[Val];
      }

      Mask >>= 1;
    } while (Val >= MAXNP);
  }
  //
  // Advance what we have read
  //
  FillBuf (Sd, Sd->mPTLen[Val]);

  Pos = Val;
  if (Val > 1) {
    Pos = (UINT32) ((1U << (Val - 1)) + GetBits (Sd, (UINT16) (Val - 1)));
  }

  return Pos;
}

UINT16
ReadPTLen (
  IN  SCRATCH_DATA  *Sd,
  IN  UINT16        nn,
  IN  UINT16        nbit,
  IN  UINT16        Special
  )
/*++

Routine Description:

  Reads code lengths for the Extra Set or the Position Set

Arguments:

  Sd        - The global scratch data
  nn        - Number of symbols
  nbit      - Number of bits needed to represent nn
  Special   - The special symbol that needs to be taken care of 

Returns:

  0         - OK.
  BAD_TABLE - Table is corrupted.

--*/
{
  UINT16  Number;
  UINT16  CharC;
  volatile UINT16  Index;
  UINT32  Mask;

  Number = (UINT16) GetBits (Sd, nbit);

  if (Number == 0) {
    CharC = (UINT16) GetBits (Sd, nbit);

    for (Index = 0; Index < 256; Index++) {
      Sd->mPTTable[Index] = CharC;
    }

    for (Index = 0; Index < nn; Index++) {
      Sd->mPTLen[Index] = 0;
    }

    return 0;
  }

  Index = 0;

  while (Index < Number) {

    CharC = (UINT16) (Sd->mBitBuf >> (BITBUFSIZ - 3));

    if (CharC == 7) {
      Mask = 1U << (BITBUFSIZ - 1 - 3);
      while (Mask & Sd->mBitBuf) {
        Mask >>= 1;
        CharC += 1;
      }
    }

    FillBuf (Sd, (UINT16) ((CharC < 7) ? 3 : CharC - 3));

    Sd->mPTLen[Index++] = (UINT8) CharC;

    if (Index == Special) {
      CharC = (UINT16) GetBits (Sd, 2);
      while ((INT16) (--CharC) >= 0) {
        Sd->mPTLen[Index++] = 0;
      }
    }
  }

  while (Index < nn) {
    Sd->mPTLen[Index++] = 0;
  }

  return MakeTable (Sd, nn, Sd->mPTLen, 8, Sd->mPTTable);
}

VOID
ReadCLen (
  SCRATCH_DATA  *Sd
  )
/*++

Routine Description:

  Reads code lengths for Char&Len Set.

Arguments:

  Sd    - the global scratch data

Returns: (VOID)

--*/
{
  UINT16  Number;
  UINT16  CharC;
  volatile UINT16  Index;
  UINT32  Mask;

  Number = (UINT16) GetBits (Sd, CBIT);

  if (Number == 0) {
    CharC = (UINT16) GetBits (Sd, CBIT);

    for (Index = 0; Index < NC; Index++) {
      Sd->mCLen[Index] = 0;
    }

    for (Index = 0; Index < 4096; Index++) {
      Sd->mCTable[Index] = CharC;
    }

    return ;
  }

  Index = 0;
  while (Index < Number) {

    CharC = Sd->mPTTable[Sd->mBitBuf >> (BITBUFSIZ - 8)];
    if (CharC >= NT) {
      Mask = 1U << (BITBUFSIZ - 1 - 8);

      do {

        if (Mask & Sd->mBitBuf) {
          CharC = Sd->mRight[CharC];
        } else {
          CharC = Sd->mLeft[CharC];
        }

        Mask >>= 1;

      } while (CharC >= NT);
    }
    //
    // Advance what we have read
    //
    FillBuf (Sd, Sd->mPTLen[CharC]);

    if (CharC <= 2) {

      if (CharC == 0) {
        CharC = 1;
      } else if (CharC == 1) {
        CharC = (UINT16) (GetBits (Sd, 4) + 3);
      } else if (CharC == 2) {
        CharC = (UINT16) (GetBits (Sd, CBIT) + 20);
      }

      while ((INT16) (--CharC) >= 0) {
        Sd->mCLen[Index++] = 0;
      }

    } else {

      Sd->mCLen[Index++] = (UINT8) (CharC - 2);

    }
  }

  while (Index < NC) {
    Sd->mCLen[Index++] = 0;
  }

  MakeTable (Sd, NC, Sd->mCLen, 12, Sd->mCTable);

  return ;
}

UINT16
DecodeC (
  SCRATCH_DATA  *Sd
  )
/*++

Routine Description:

  Decode a character/length value.

Arguments:

  Sd    - The global scratch data.

Returns:

  The value decoded.

--*/
{
  UINT16  Index2;
  UINT32  Mask;

  if (Sd->mBlockSize == 0) {
    //
    // Starting a new block
    //
    Sd->mBlockSize    = (UINT16) GetBits (Sd, 16);
    Sd->mBadTableFlag = ReadPTLen (Sd, NT, TBIT, 3);
    if (Sd->mBadTableFlag != 0) {
      return 0;
    }

    ReadCLen (Sd);

    Sd->mBadTableFlag = ReadPTLen (Sd, MAXNP, Sd->mPBit, (UINT16) (-1));
    if (Sd->mBadTableFlag != 0) {
      return 0;
    }
  }

  Sd->mBlockSize--;
  Index2 = Sd->mCTable[Sd->mBitBuf >> (BITBUFSIZ - 12)];

  if (Index2 >= NC) {
    Mask = 1U << (BITBUFSIZ - 1 - 12);

    do {
      if (Sd->mBitBuf & Mask) {
        Index2 = Sd->mRight[Index2];
      } else {
        Index2 = Sd->mLeft[Index2];
      }

      Mask >>= 1;
    } while (Index2 >= NC);
  }
  //
  // Advance what we have read
  //
  FillBuf (Sd, Sd->mCLen[Index2]);

  return Index2;
}

VOID
Decode (
  SCRATCH_DATA  *Sd
  )
/*++

Routine Description:

  Decode the source data and put the resulting data into the destination buffer.

Arguments:

  Sd            - The global scratch data

Returns: (VOID)

 --*/
{
  UINT16  BytesRemain;
  UINT32  DataIdx;
  UINT16  CharC;

  BytesRemain = (UINT16) (-1);

  DataIdx     = 0;

  for (;;) {
    CharC = DecodeC (Sd);
    if (Sd->mBadTableFlag != 0) {
      goto Done ;
    }

    if (CharC < 256) {
      //
      // Process an Original character
      //
      if (Sd->mOutBuf >= Sd->mOrigSize) {
        goto Done ;
      } else {
        Sd->mDstBase[Sd->mOutBuf++] = (UINT8) CharC;
      }

    } else {
      //
      // Process a Pointer
      //
      CharC       = (UINT16) (CharC - (UINT8_MAX + 1 - THRESHOLD));

      BytesRemain = CharC;

      DataIdx     = Sd->mOutBuf - DecodeP (Sd) - 1;

      BytesRemain--;
      while ((INT16) (BytesRemain) >= 0) {
        Sd->mDstBase[Sd->mOutBuf++] = Sd->mDstBase[DataIdx++];
        if (Sd->mOutBuf >= Sd->mOrigSize) {
          goto Done ;
        }

        BytesRemain--;
      }
    }
  }

Done:
  return ;
}

RETURN_STATUS
EFIAPI
DecompressGetInfo (
  IN  CONST VOID  *Source,
  IN  UINT32      SourceSize,
  OUT UINT32      *DestinationSize,
  OUT UINT32      *ScratchSize
  )
/*++

Routine Description:

  The internal implementation of DecompressGetInfo().

Arguments:

  Source          - The source buffer containing the compressed data.
  SourceSize      - The size of source buffer
  DestinationSize - The size of destination buffer.
  ScratchSize     - The size of scratch buffer.

Returns:

  RETURN_SUCCESS           - The size of destination buffer and the size of scratch buffer are successull retrieved.
  RETURN_INVALID_PARAMETER - The source data is corrupted

--*/
{
  UINT32  CompressedSize;
  //
  // Verify input is not NULL
  //
  assert(Source);
  assert(DestinationSize);
  assert(ScratchSize);
  
  *ScratchSize  = sizeof (SCRATCH_DATA);

  if (SourceSize < 8) {
    return RETURN_INVALID_PARAMETER;
  }

  CopyMem (&CompressedSize, Source, sizeof (UINT32));
  CopyMem (DestinationSize, (VOID *)((UINT8 *)Source + 4), sizeof (UINT32));

  if (SourceSize < (CompressedSize + 8)) {
    return RETURN_INVALID_PARAMETER;
  }

  return RETURN_SUCCESS;
}

RETURN_STATUS
EFIAPI
Decompress (
  IN VOID  *Source,
  IN OUT VOID    *Destination,
  IN OUT VOID    *Scratch,
  IN UINT32      Version
  )
/*++

Routine Description:

  The internal implementation of Decompress().

Arguments:

  Source          - The source buffer containing the compressed data.
  Destination     - The destination buffer to store the decompressed data
  Scratch         - The buffer used internally by the decompress routine. This  buffer is needed to store intermediate data.
  Version         - 1 for EFI1.1 Decompress algoruthm, 2 for Tiano Decompress algorithm

Returns:

  RETURN_SUCCESS           - Decompression is successfull
  RETURN_INVALID_PARAMETER - The source data is corrupted

--*/
{
  volatile UINT32  Index;
  UINT32           CompSize;
  UINT32           OrigSize;
  SCRATCH_DATA     *Sd;
  CONST UINT8      *Src;
  UINT8            *Dst;

  //
  // Verify input is not NULL
  //
  assert(Source);
//  assert(Destination);
  assert(Scratch);
  
  Src     = (UINT8 *)Source;
  Dst     = (UINT8 *)Destination;

  Sd      = (SCRATCH_DATA *) Scratch;
  CompSize  = Src[0] + (Src[1] << 8) + (Src[2] << 16) + (Src[3] << 24);
  OrigSize  = Src[4] + (Src[5] << 8) + (Src[6] << 16) + (Src[7] << 24);
  
  //
  // If compressed file size is 0, return
  //
  if (OrigSize == 0) {
    return RETURN_SUCCESS;
  }

  Src = Src + 8;

  for (Index = 0; Index < sizeof (SCRATCH_DATA); Index++) {
    ((UINT8 *) Sd)[Index] = 0;
  }
  //
  // The length of the field 'Position Set Code Length Array Size' in Block Header.
  // For EFI 1.1 de/compression algorithm(Version 1), mPBit = 4
  // For Tiano de/compression algorithm(Version 2), mPBit = 5
  //
  switch (Version) {
    case 1 :
      Sd->mPBit = 4;
      break;
    case 2 :
      Sd->mPBit = 5;
      break;
    default:
      assert(FALSE);
  }
  Sd->mSrcBase  = (UINT8 *)Src;
  Sd->mDstBase  = Dst;
  Sd->mCompSize = CompSize;
  Sd->mOrigSize = OrigSize;

  //
  // Fill the first BITBUFSIZ bits
  //
  FillBuf (Sd, BITBUFSIZ);
  
  //
  // Decompress it
  //
  Decode (Sd);

  if (Sd->mBadTableFlag != 0) {
    //
    // Something wrong with the source
    //
    return RETURN_INVALID_PARAMETER;
  }

  return RETURN_SUCCESS;
}

RETURN_STATUS
EFIAPI
EfiDecompress (
  IN VOID  *Source,
  IN OUT VOID    *Destination,
  IN OUT VOID    *Scratch
  )
/*++

Routine Description:

  The internal implementation of *_DECOMPRESS_PROTOCOL.Decompress().

Arguments:

  Source          - The source buffer containing the compressed data.
  Destination     - The destination buffer to store the decompressed data
  Scratch         - The buffer used internally by the decompress routine. This  buffer is needed to store intermediate data.

Returns:

  RETURN_SUCCESS           - Decompression is successfull
  RETURN_INVALID_PARAMETER - The source data is corrupted

--*/
{
  return Decompress (Source, Destination, Scratch, 1);
}

RETURN_STATUS
EFIAPI
TianoDecompressGetInfo (
  IN  CONST VOID  *Source,
  IN  UINT32      SourceSize,
  OUT UINT32      *DestinationSize,
  OUT UINT32      *ScratchSize
  )
/*++

Routine Description:

  The internal implementation of *_DECOMPRESS_PROTOCOL.GetInfo().

Arguments:

  Source          - The source buffer containing the compressed data.
  SourceSize      - The size of source buffer
  DestinationSize - The size of destination buffer.
  ScratchSize     - The size of scratch buffer.

Returns:

  RETURN_SUCCESS           - The size of destination buffer and the size of scratch buffer are successull retrieved.
  RETURN_INVALID_PARAMETER - The source data is corrupted

--*/
{
  return DecompressGetInfo (Source, SourceSize, DestinationSize, ScratchSize);
}

RETURN_STATUS
EFIAPI
TianoDecompress (
  IN VOID  *Source,
  IN OUT VOID    *Destination,
  IN OUT VOID    *Scratch
  )
/*++

Routine Description:

  The internal implementation of TianoDecompress().

Arguments:

  Source          - The source buffer containing the compressed data.
  Destination     - The destination buffer to store the decompressed data
  Scratch         - The buffer used internally by the decompress routine. This  buffer is needed to store intermediate data.

Returns:

  RETURN_SUCCESS           - Decompression is successfull
  RETURN_INVALID_PARAMETER - The source data is corrupted

--*/
{
  return Decompress (Source, Destination, Scratch, 2);
}

VOID
Version (
  VOID
  )
/*++

Routine Description:

  Displays the standard utility information to SDTOUT

Arguments:

  None

Returns:

  None

--*/
{
  printf (
    "%s, Tiano Decompress Utility. Version %i.%i.\n",
    UTILITY_NAME,
    UTILITY_MAJOR_VERSION,
    UTILITY_MINOR_VERSION
    );
}

VOID
Usage (
  VOID
  )
/*++

Routine Description:

  Displays the utility usage syntax to STDOUT

Arguments:

  None

Returns:

  None

--*/
{
  printf ("Usage: "UTILITY_NAME "  [-o OutputFile --version -v Verbose\
         -q Quiet -d DebugLevel -h Help]  CompressedFileName\n\n");
}


int
main (
  int  argc,
  char *argv[]
  )
/*++

Routine Description:

  Main

Arguments:

  command line parameters

Returns:

  EFI_SUCCESS    Section header successfully generated and section concatenated.
  EFI_ABORTED    Could not generate the section
  EFI_OUT_OF_RESOURCES  No resource to complete the operation.

--*/  
{
  FILE      *Output, *Input;
  char      *OutputFileName, *InputFileName;
  SCRATCH_DATA      *Scratch;
  INTN      Index;
  VOID      *InputBuffer;
  UINT8     *OutputBuffer, *Src;
  UINT32    BufferLength,OrigSize;
  EFI_STATUS Status;
  
  InputBuffer = NULL;
  OutputBuffer = NULL;
  BufferLength = 0;
  //
  // Verify the correct number of arguments
  //
   
  if (argc == 1) {
    Usage();
    return 1;
  }
  
  if ((strcmp(argv[1], "-h") == 0) || (strcmp(argv[1], "--help") == 0)) {
    Usage();
    return 1;
  }
  
  if ((strcmp(argv[1], "-V") == 0) || (strcmp(argv[1], "--version") == 0)) {
    Version();
    return 1;
  }
  
  Index = 1;
  if ((strcmp(argv[Index], "-O") == 0) || (strcmp(argv[Index], "-o") == 0)) {
    Index++;
    if (Index < argc) {
    if ((argv[Index][0]!='-') && (Index+1 < argc)){
    OutputFileName = argv[Index];
    InputFileName = argv[Index+1];
    } else {
      printf("\nError Parameters!\n");
      Usage();
      return 1;
    }
    } else {
      printf("\nError Parameters!\n");
      Usage();
      return 1;       
    }
  } else if (argv[Index][0]!='-') {
    OutputFileName = NULL;
    InputFileName = argv[Index];
  } else {
  printf("\nError Parameters!\n");
  Usage();
  return 1;
  }

  //
  // Now we have parsed all the parameters
  //
  Scratch = (SCRATCH_DATA *)malloc(sizeof(SCRATCH_DATA));
  if (Scratch == NULL) {
    fprintf (stdout, "ERROR: Memory allocation failed\n");
    return 1;
  }

//  printf("\nInputFileName is %s\n", InputFileName);
  Input = fopen(InputFileName, "rb");
  if ( Input == NULL) {
    printf("\n%s failed to open input file\n", InputFileName);
    return 1;
  }

  //
  // Copy input file contents to InputBuffer
  //
  Status = GetFileContents(
            InputFileName,
            InputBuffer,
            &BufferLength);

  if (Status == EFI_BUFFER_TOO_SMALL) {
    InputBuffer = (UINT8 *) malloc (BufferLength);
    if (InputBuffer == NULL) {
      printf ("application error", "failed to allocate memory\n");
      return EFI_OUT_OF_RESOURCES;
    }

    Status = GetFileContents (
              InputFileName,
              InputBuffer,
              &BufferLength
              );
              } 

  //
  // Get Compressed file original size
  // 
  Src     = (UINT8 *)InputBuffer;                     
  OrigSize  = Src[4] + (Src[5] << 8) + (Src[6] << 16) + (Src[7] << 24);  
  
  //
  // Allocate OutputBuffer
  //
  OutputBuffer = (UINT8 *)malloc(OrigSize);
  if (OutputBuffer == NULL) {
    printf("\n No enough memory to allocate!");
    return 1;
  }
  TianoDecompress(InputBuffer, (VOID *)OutputBuffer, (VOID *)Scratch);
  
  //
  // open Output file for writing
  //
  if (OutputFileName == NULL) {
    Output = stdout;
  } else {
    Output = fopen(OutputFileName, "wb");
    if ( Output == NULL) {
      printf("\n%s failed to open output file for writing\n", OutputFileName);
      if (Input != NULL) {
        fclose (Input);
        }
        return 1;
        }  
  }  
  fwrite(OutputBuffer, (size_t)(Scratch->mOrigSize), 1, Output);
  free(Scratch);
  free(InputBuffer);
  free(OutputBuffer);
  return 0;  
}

EFI_STATUS
GetFileContents (
  IN char    *InputFileName,
  OUT UINT8   *FileBuffer,
  OUT UINT32  *BufferLength
  )
/*++
        
Routine Description:
           
  Get the contents of file specified in InputFileName
  into FileBuffer.
            
Arguments:
               
  InputFileName  - Name of the input file.
                
  FileBuffer     - Output buffer to contain data

  BufferLength   - Actual length of the data 

Returns:
                       
  EFI_SUCCESS on successful return
  EFI_ABORTED if unable to open input file.

--*/
{
  UINTN   Size;
  UINTN   FileSize;
  INTN    Index;
  FILE    *InputFile;

  Size = 0;
  //
  // Copy the file contents to the output buffer.
  //
  InputFile = fopen (InputFileName, "rb");
    if (InputFile == NULL) {
      printf ("%s failed to open input file\n", InputFileName);
      return EFI_ABORTED;
    }
  
    fseek (InputFile, 0, SEEK_END);
    FileSize = ftell (InputFile);
    fseek (InputFile, 0, SEEK_SET);
    //
    // Now read the contents of the file into the buffer
    // 
    if (FileSize > 0 && FileBuffer != NULL) {
      if (fread (FileBuffer + Size, (size_t) FileSize, 1, InputFile) != 1) {
        printf ("%s failed to read contents of input file\n", InputFileName);
        fclose (InputFile);
        return EFI_ABORTED;
      }
    }

  fclose (InputFile);
  Size += (UINTN) FileSize;
  *BufferLength = Size;
  
  if (FileBuffer != NULL) {
    return EFI_SUCCESS;
  } else {
    return EFI_BUFFER_TOO_SMALL;
  }
}