/*++

Copyright (c) 2004 - 2007, Intel Corporation                                                         
All rights reserved. This program and the accompanying materials                          
are licensed and made available under the terms and conditions of the BSD License         
which accompanies this distribution.  The full text of the license may be found at        
http://opensource.org/licenses/bsd-license.php                                            
                                                                                          
THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,                     
WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.             

Module Name:

    GenFw.c

Abstract:

    Converts a pe32+ image to an FW image type

--*/

#include "WinNtInclude.h"

//
// List of OS and CPU which support ELF to PE conversion
//
#if defined(linux)
#if defined (__i386__) || defined(__x86_64__)
#define HAVE_ELF
#endif
#endif

#ifndef __GNUC__
#include <windows.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef HAVE_ELF
#include <elf.h>
#endif

#include <Common/UefiBaseTypes.h>
#include <Common/EfiImage.h>

#include "CommonLib.h"
#include "EfiUtilityMsgs.c"

//
// Acpi Table definition
//
#include "Acpi.h"
#include "Acpi1_0.h"
#include "Acpi2_0.h"
#include "Acpi3_0.h"
#include "MemoryMappedConfigurationSpaceAccessTable.h"

//
// Version of this utility
//
#define UTILITY_NAME "GenFw"
#define UTILITY_MAJOR_VERSION 1
#define UTILITY_MINOR_VERSION 0

UINT8 *InImageName;

#define FW_DUMMY_IMAGE   0
#define FW_EFI_IMAGE     1
#define FW_TE_IMAGE      2
#define FW_ACPI_IMAGE    3

#define MAX_STRING_LENGTH 100

STATIC
VOID
Version (
  VOID
  )
{
  printf ("%s v%d.%d -EDK Utility mainly for Converting a pe32+ image to an FW image type.\n", UTILITY_NAME, UTILITY_MAJOR_VERSION, UTILITY_MINOR_VERSION);
  printf ("Copyright (c) 2007 Intel Corporation. All rights reserved.\n");
}

STATIC
VOID
Usage (
  VOID
  )
{
  Version();
  printf ("\nUsage: " UTILITY_NAME " [inputfilename]\n\
        -o, --outputfile [FileName]\n\
        -e, --efiImage <BASE|SEC|PEI_CORE|PEIM|DXE_CORE|DXE_DRIVER|\n\
                        DXE_RUNTIME_DRIVER|DXE_SAL_DRIVER|DXE_SMM_DRIVER|\n\
                        UEFI_DRIVER|UEFI_APPLICATION|SECURITY_CORE|\n\
                        COMBINED_PEIM_DRIVER|PIC_PEIM|RELOCATABLE_PEIM|\n\
                        BS_DRIVER|RT_DRIVER|SAL_RT_DRIVER|APPLICATION>\n\
        -c, --acpi\n\
        -t, --terse\n\
        -h, --help\n\
        -V, --version\n");
}

static
STATUS
CheckAcpiTable (
  VOID      *AcpiTable,
  UINT32    Length
  )
/*++

Routine Description:
  
  Check Acpi Table 

Arguments:

  AcpiTable     Buffer for AcpiSection
  Length        AcpiSection Length

Returns:

  0             success
  non-zero      otherwise

--*/
{
  EFI_ACPI_DESCRIPTION_HEADER                   *AcpiHeader;
  EFI_ACPI_3_0_FIRMWARE_ACPI_CONTROL_STRUCTURE  *Facs;
  UINT32                                        ExpectedLength;

  AcpiHeader = (EFI_ACPI_DESCRIPTION_HEADER *)AcpiTable;

  //
  // Generic check for AcpiTable length.
  //
  if (AcpiHeader->Length > Length) {
    Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass AcpiTable Length check");
    return STATUS_ERROR;
  }

  //
  // Currently, we only check must-have tables: FADT, FACS, DSDT,
  // and some important tables: MADT, MCFG.
  //
  switch (AcpiHeader->Signature) {

  //
  // "FACP" Fixed ACPI Description Table
  //
  case EFI_ACPI_3_0_FIXED_ACPI_DESCRIPTION_TABLE_SIGNATURE:
    switch (AcpiHeader->Revision) {
    case EFI_ACPI_1_0_FIXED_ACPI_DESCRIPTION_TABLE_REVISION:
      ExpectedLength = sizeof(EFI_ACPI_1_0_FIXED_ACPI_DESCRIPTION_TABLE);
      break;
    case EFI_ACPI_2_0_FIXED_ACPI_DESCRIPTION_TABLE_REVISION:
      ExpectedLength = sizeof(EFI_ACPI_2_0_FIXED_ACPI_DESCRIPTION_TABLE);
      break;
    case EFI_ACPI_3_0_FIXED_ACPI_DESCRIPTION_TABLE_REVISION:
      ExpectedLength = sizeof(EFI_ACPI_3_0_FIXED_ACPI_DESCRIPTION_TABLE);
      break;
    default:
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass FACP revision check");
      return STATUS_ERROR;
    }
    if (ExpectedLength != AcpiHeader->Length) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass FACP Length check");
      return STATUS_ERROR;
    }
    break;

  //
  // "FACS" Firmware ACPI Control Structure
  //
  case EFI_ACPI_3_0_FIRMWARE_ACPI_CONTROL_STRUCTURE_SIGNATURE:
    Facs = (EFI_ACPI_3_0_FIRMWARE_ACPI_CONTROL_STRUCTURE *)AcpiTable;
    if ((Facs->Version != 0) &&
        (Facs->Version != EFI_ACPI_2_0_FIRMWARE_ACPI_CONTROL_STRUCTURE_VERSION) &&
        (Facs->Version != EFI_ACPI_3_0_FIRMWARE_ACPI_CONTROL_STRUCTURE_VERSION)){
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass FACS version check");
      return STATUS_ERROR;
    }
    if ((Facs->Length != sizeof(EFI_ACPI_1_0_FIRMWARE_ACPI_CONTROL_STRUCTURE)) &&
        (Facs->Length != sizeof(EFI_ACPI_2_0_FIRMWARE_ACPI_CONTROL_STRUCTURE)) &&
        (Facs->Length != sizeof(EFI_ACPI_3_0_FIRMWARE_ACPI_CONTROL_STRUCTURE))) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass FACS Length check");
      return STATUS_ERROR;
    }
    break;

  //
  // "DSDT" Differentiated System Description Table
  //
  case EFI_ACPI_3_0_DIFFERENTIATED_SYSTEM_DESCRIPTION_TABLE_SIGNATURE:
    if (AcpiHeader->Revision > EFI_ACPI_3_0_DIFFERENTIATED_SYSTEM_DESCRIPTION_TABLE_REVISION) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass DSDT revision check");
      return STATUS_ERROR;
    }
    if (AcpiHeader->Length <= sizeof(EFI_ACPI_DESCRIPTION_HEADER)) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass DSDT Length check");
      return STATUS_ERROR;
    }
    break;

  //
  // "APIC" Multiple APIC Description Table
  //
  case EFI_ACPI_3_0_MULTIPLE_APIC_DESCRIPTION_TABLE_SIGNATURE:
    if ((AcpiHeader->Revision != EFI_ACPI_1_0_MULTIPLE_APIC_DESCRIPTION_TABLE_REVISION) &&
        (AcpiHeader->Revision != EFI_ACPI_2_0_MULTIPLE_APIC_DESCRIPTION_TABLE_REVISION) &&
        (AcpiHeader->Revision != EFI_ACPI_3_0_MULTIPLE_APIC_DESCRIPTION_TABLE_REVISION)) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass APIC revision check");
      return STATUS_ERROR;
    }
    if (AcpiHeader->Length <= sizeof(EFI_ACPI_DESCRIPTION_HEADER) + sizeof(UINT32) + sizeof(UINT32)) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass APIC Length check");
      return STATUS_ERROR;
    }
    break;

  //
  // "MCFG" PCI Express Memory Mapped Configuration Space Base Address Description Table
  //
  case EFI_ACPI_3_0_PCI_EXPRESS_MEMORY_MAPPED_CONFIGURATION_SPACE_BASE_ADDRESS_DESCRIPTION_TABLE_SIGNATURE:
    if (AcpiHeader->Revision != EFI_ACPI_MEMORY_MAPPED_CONFIGURATION_SPACE_ACCESS_TABLE_REVISION) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass MCFG revision check");
      return STATUS_ERROR;
    }
    if (AcpiHeader->Length <= sizeof(EFI_ACPI_DESCRIPTION_HEADER) + sizeof(UINT64)) {
      Error (NULL, 0, 0, "CheckAcpiTable", "failed to pass MCFG Length check");
      return STATUS_ERROR;
    }
    break;

  //
  // Other table pass check
  //
  default:
    break;
  }

  return STATUS_SUCCESS;
}

static
STATUS
FCopyFile (
  FILE    *in,
  FILE    *out
  )
{
  UINT32  filesize;
  UINT32  offset;
  UINT32  length;
  UINT8 Buffer[8 * 1024];

  fseek (in, 0, SEEK_END);
  filesize = ftell (in);

  fseek (in, 0, SEEK_SET);
  fseek (out, 0, SEEK_SET);

  offset = 0;
  while (offset < filesize) {
    length = sizeof (Buffer);
    if (filesize - offset < length) {
      length = filesize - offset;
    }

    fread (Buffer, length, 1, in);
    fwrite (Buffer, length, 1, out);
    offset += length;
  }

  if ((UINT32 ) ftell (out) != filesize) {
    Error (NULL, 0, 0, "write error", NULL);
    return STATUS_ERROR;
  }

  return STATUS_SUCCESS;
}

static
STATUS
FReadFile (
  FILE    *in,
  VOID    **Buffer,
  UINTN   *Length
  )
{
  fseek (in, 0, SEEK_END);
  *Length = ftell (in);
  *Buffer = malloc (*Length);
  fseek (in, 0, SEEK_SET);
  fread (*Buffer, *Length, 1, in);
  return STATUS_SUCCESS;
}

static
STATUS
FWriteFile (
  FILE    *out,
  VOID    *Buffer,
  UINTN   Length
  )
{
  fseek (out, 0, SEEK_SET);
  fwrite (Buffer, Length, 1, out);
  if ((UINT32 ) ftell (out) != Length) {
    Error (NULL, 0, 0, "write error", NULL);
    return STATUS_ERROR;
  }
  free (Buffer);
  return STATUS_SUCCESS;
}

#ifdef HAVE_ELF
INTN
IsElfHeader(
  UINT8  *FileBuffer
)
{
  return (FileBuffer[EI_MAG0] == ELFMAG0
    && FileBuffer[EI_MAG1] == ELFMAG1
    && FileBuffer[EI_MAG2] == ELFMAG2
    && FileBuffer[EI_MAG3] == ELFMAG3);
}

typedef Elf32_Shdr Elf_Shdr;
typedef Elf32_Ehdr Elf_Ehdr;
typedef Elf32_Rel Elf_Rel;
typedef Elf32_Sym Elf_Sym;
#define ELFCLASS ELFCLASS32
#define ELF_R_TYPE(r) ELF32_R_TYPE(r)
#define ELF_R_SYM(r) ELF32_R_SYM(r)

//
// Well known ELF structures.
//
Elf_Ehdr *Ehdr;
Elf_Shdr *ShdrBase;

//
// PE section alignment.
//
const UINT32 CoffAlignment = 0x20;
const UINT32 CoffNbrSections = 4;

//
// Current offset in coff file.
//
UINT32 CoffOffset;

//
// Result Coff file in memory.
//
UINT8 *CoffFile;

//
// Offset in Coff file of headers and sections.
//
UINT32 NtHdrOffset;
UINT32 TableOffset;
UINT32 TextOffset;
UINT32 DataOffset;
UINT32 RelocOffset;

//
// ELF sections to offset in Coff file.
//
UINT32 *CoffSectionsOffset;

EFI_IMAGE_BASE_RELOCATION *CoffBaseRel;
UINT16 *CoffEntryRel;

UINT32
CoffAlign(
  UINT32 Offset
  )
{
  return (Offset + CoffAlignment - 1) & ~(CoffAlignment - 1);
}

Elf_Shdr *
GetShdrByIndex(
  UINT32 Num
  )
{
  if (Num >= Ehdr->e_shnum)
    return NULL;
  return (Elf_Shdr*)((UINT8*)ShdrBase + Num * Ehdr->e_shentsize);
}

INTN
CheckElfHeader(
  VOID
  )
{
  //
  // Note: Magic has already been tested.
  //
  if (Ehdr->e_ident[EI_CLASS] != ELFCLASS)
    return 0;
  if (Ehdr->e_ident[EI_DATA] != ELFDATA2LSB)
    return 0;
  if (Ehdr->e_type != ET_EXEC)
    return 0;
  if (Ehdr->e_machine != EM_386)
    return 0;
  if (Ehdr->e_version != EV_CURRENT)
    return 0;

  //
  // Find the section header table
  // 
  ShdrBase = (Elf_Shdr *)((UINT8 *)Ehdr + Ehdr->e_shoff);

  CoffSectionsOffset = (UINT32 *)malloc(Ehdr->e_shnum * sizeof (UINT32));

  memset(CoffSectionsOffset, 0, Ehdr->e_shnum * sizeof(UINT32));
  return 1;
}

int
IsTextShdr(
  Elf_Shdr *Shdr
  )
{
  return (Shdr->sh_flags & (SHF_WRITE | SHF_ALLOC)) == SHF_ALLOC;
}

int
IsDataShdr(
  Elf_Shdr *Shdr
  )
{
  return (Shdr->sh_flags & (SHF_WRITE | SHF_ALLOC)) == (SHF_ALLOC | SHF_WRITE);
}

void
CreateSectionHeader(
  const char *Name,
  UINT32     Offset,
  UINT32     Size,
  UINT32     Flags
  )
{
  EFI_IMAGE_SECTION_HEADER *Hdr;
  Hdr = (EFI_IMAGE_SECTION_HEADER*)(CoffFile + TableOffset);

  strcpy(Hdr->Name, Name);
  Hdr->Misc.VirtualSize = Size;
  Hdr->VirtualAddress = Offset;
  Hdr->SizeOfRawData = Size;
  Hdr->PointerToRawData = Offset;
  Hdr->PointerToRelocations = 0;
  Hdr->PointerToLinenumbers = 0;
  Hdr->NumberOfRelocations = 0;
  Hdr->NumberOfLinenumbers = 0;
  Hdr->Characteristics = Flags;

  TableOffset += sizeof (EFI_IMAGE_SECTION_HEADER);
}

void
ScanSections(
  VOID
  )
{
  UINT32 i;
  EFI_IMAGE_DOS_HEADER *DosHdr;
  EFI_IMAGE_NT_HEADERS *NtHdr;
  UINT32 CoffEntry = 0;

  CoffOffset = 0;

  //
  // Coff file start with a DOS header.
  //
  CoffOffset = sizeof(EFI_IMAGE_DOS_HEADER) + 0x40;
  NtHdrOffset = CoffOffset;
  CoffOffset += sizeof(EFI_IMAGE_NT_HEADERS);
  TableOffset = CoffOffset;
  CoffOffset += CoffNbrSections * sizeof(EFI_IMAGE_SECTION_HEADER);

  //
  // First text sections.
  //
  CoffOffset = CoffAlign(CoffOffset);
  TextOffset = CoffOffset;
  for (i = 0; i < Ehdr->e_shnum; i++) {
    Elf_Shdr *shdr = GetShdrByIndex(i);
    if (IsTextShdr(shdr)) {
      //
      // Align the coff offset to meet with the alignment requirement of section
      // itself.
      // 
      if ((shdr->sh_addralign != 0) && (shdr->sh_addralign != 1)) {
        CoffOffset = (CoffOffset + shdr->sh_addralign - 1) & ~(shdr->sh_addralign - 1);
      }

      /* Relocate entry.  */
      if ((Ehdr->e_entry >= shdr->sh_addr) && 
          (Ehdr->e_entry < shdr->sh_addr + shdr->sh_size)) {
        CoffEntry = CoffOffset + Ehdr->e_entry - shdr->sh_addr;
      }
      CoffSectionsOffset[i] = CoffOffset;
      CoffOffset += shdr->sh_size;
    }
  }
  CoffOffset = CoffAlign(CoffOffset);

  //
  //  Then data sections.
  //
  DataOffset = CoffOffset;
  for (i = 0; i < Ehdr->e_shnum; i++) {
    Elf_Shdr *shdr = GetShdrByIndex(i);
    if (IsDataShdr(shdr)) {
      //
      // Align the coff offset to meet with the alignment requirement of section
      // itself.
      // 
      if ((shdr->sh_addralign != 0) && (shdr->sh_addralign != 1)) {
        CoffOffset = (CoffOffset + shdr->sh_addralign - 1) & ~(shdr->sh_addralign - 1);
      }
     
      CoffSectionsOffset[i] = CoffOffset;
      CoffOffset += shdr->sh_size;
    }
  }
  CoffOffset = CoffAlign(CoffOffset);

  RelocOffset = CoffOffset;  

  //
  // Allocate base Coff file.  Will be expanded later for relocations. 
  //
  CoffFile = (UINT8 *)malloc(CoffOffset);
  memset(CoffFile, 0, CoffOffset);

  //
  // Fill headers.
  //
  DosHdr = (EFI_IMAGE_DOS_HEADER *)CoffFile;
  DosHdr->e_magic = EFI_IMAGE_DOS_SIGNATURE;
  DosHdr->e_lfanew = NtHdrOffset;

  NtHdr = (EFI_IMAGE_NT_HEADERS*)(CoffFile + NtHdrOffset);

  NtHdr->Signature = EFI_IMAGE_NT_SIGNATURE;

  NtHdr->FileHeader.Machine = EFI_IMAGE_MACHINE_IA32;
  NtHdr->FileHeader.NumberOfSections = CoffNbrSections;
  NtHdr->FileHeader.TimeDateStamp = time(NULL);
  NtHdr->FileHeader.PointerToSymbolTable = 0;
  NtHdr->FileHeader.NumberOfSymbols = 0;
  NtHdr->FileHeader.SizeOfOptionalHeader = sizeof(NtHdr->OptionalHeader);
  NtHdr->FileHeader.Characteristics = EFI_IMAGE_FILE_EXECUTABLE_IMAGE
    | EFI_IMAGE_FILE_LINE_NUMS_STRIPPED
    | EFI_IMAGE_FILE_LOCAL_SYMS_STRIPPED
    | EFI_IMAGE_FILE_32BIT_MACHINE;
  
  NtHdr->OptionalHeader.Magic = EFI_IMAGE_NT_OPTIONAL_HDR32_MAGIC;
  NtHdr->OptionalHeader.SizeOfCode = DataOffset - TextOffset;
  NtHdr->OptionalHeader.SizeOfInitializedData = RelocOffset - DataOffset;
  NtHdr->OptionalHeader.SizeOfUninitializedData = 0;
  NtHdr->OptionalHeader.AddressOfEntryPoint = CoffEntry;
  NtHdr->OptionalHeader.BaseOfCode = TextOffset;

  NtHdr->OptionalHeader.BaseOfData = DataOffset;
  NtHdr->OptionalHeader.ImageBase = 0;
  NtHdr->OptionalHeader.SectionAlignment = CoffAlignment;
  NtHdr->OptionalHeader.FileAlignment = CoffAlignment;
  NtHdr->OptionalHeader.SizeOfImage = 0;

  NtHdr->OptionalHeader.SizeOfHeaders = TextOffset;
  NtHdr->OptionalHeader.NumberOfRvaAndSizes = EFI_IMAGE_NUMBER_OF_DIRECTORY_ENTRIES;

  //
  // Section headers.
  //
  CreateSectionHeader (".text", TextOffset, DataOffset - TextOffset,
           EFI_IMAGE_SCN_CNT_CODE
           | EFI_IMAGE_SCN_MEM_EXECUTE
           | EFI_IMAGE_SCN_MEM_READ);
  CreateSectionHeader (".data", DataOffset, RelocOffset - DataOffset,
           EFI_IMAGE_SCN_CNT_INITIALIZED_DATA
           | EFI_IMAGE_SCN_MEM_WRITE
           | EFI_IMAGE_SCN_MEM_READ);
}

void
WriteSections(
  int   (*Filter)(Elf_Shdr *)
  )
{
  UINT32 Idx;

  //
  // First: copy sections.
  //
  for (Idx = 0; Idx < Ehdr->e_shnum; Idx++) {
    Elf_Shdr *Shdr = GetShdrByIndex(Idx);
    if ((*Filter)(Shdr)) {
      switch (Shdr->sh_type) {
      case SHT_PROGBITS:
  /* Copy.  */
  memcpy(CoffFile + CoffSectionsOffset[Idx],
         (UINT8*)Ehdr + Shdr->sh_offset,
         Shdr->sh_size);
  break;
      case SHT_NOBITS:
  memset(CoffFile + CoffSectionsOffset[Idx], 0, Shdr->sh_size);
  break;
      default:
  Error (NULL, 0, 0, InImageName, "unhandle section type %x",
         (UINTN)Shdr->sh_type);
      }
    }
  }

  //
  // Second: apply relocations.
  //
  for (Idx = 0; Idx < Ehdr->e_shnum; Idx++) {
    Elf_Shdr *RelShdr = GetShdrByIndex(Idx);
    if (RelShdr->sh_type != SHT_REL)
      continue;
    Elf_Shdr *SecShdr = GetShdrByIndex(RelShdr->sh_info);
    UINT32 SecOffset = CoffSectionsOffset[RelShdr->sh_info];
    if (RelShdr->sh_type == SHT_REL && (*Filter)(SecShdr)) {
      UINT32 RelIdx;
      Elf_Shdr *SymtabShdr = GetShdrByIndex(RelShdr->sh_link);
      UINT8 *Symtab = (UINT8*)Ehdr + SymtabShdr->sh_offset;

      for (RelIdx = 0; RelIdx < RelShdr->sh_size; RelIdx += RelShdr->sh_entsize) {
  Elf_Rel *Rel = (Elf_Rel *)((UINT8*)Ehdr + RelShdr->sh_offset + RelIdx);
  Elf_Sym *Sym = (Elf_Sym *)
    (Symtab + ELF_R_SYM(Rel->r_info) * SymtabShdr->sh_entsize);
  Elf_Shdr *SymShdr;
  UINT8 *Targ;

  if (Sym->st_shndx == SHN_UNDEF
      || Sym->st_shndx == SHN_ABS
      || Sym->st_shndx > Ehdr->e_shnum) {
    Error (NULL, 0, 0, InImageName, "bad symbol definition");
  }
  SymShdr = GetShdrByIndex(Sym->st_shndx);

  //
  // Note: r_offset in a memory address.
  //  Convert it to a pointer in the coff file.
  //
  Targ = CoffFile + SecOffset + (Rel->r_offset - SecShdr->sh_addr);

  switch (ELF_R_TYPE(Rel->r_info)) {
  case R_386_NONE:
    break;
  case R_386_32:
    //
    // Absolute relocation.
    //
    *(UINT32 *)Targ = *(UINT32 *)Targ - SymShdr->sh_addr
      + CoffSectionsOffset[Sym->st_shndx];
    break;
  case R_386_PC32:
    //
    // Relative relocation: Symbol - Ip + Addend
    //
    *(UINT32 *)Targ = *(UINT32 *)Targ
      + (CoffSectionsOffset[Sym->st_shndx] - SymShdr->sh_addr)
      - (SecOffset - SecShdr->sh_addr);
    break;
  default:
    Error (NULL, 0, 0, InImageName, "unhandled relocation type %x",
     ELF_R_TYPE(Rel->r_info));
  }
      }
    }
  }
}

void
CoffAddFixupEntry(
  UINT16 Val
  )
{
  *CoffEntryRel = Val;
  CoffEntryRel++;
  CoffBaseRel->SizeOfBlock += 2;
  CoffOffset += 2;
}

void
CoffAddFixup(
  UINT32 Offset,
  UINT8  Type
  )
{
  if (CoffBaseRel == NULL
      || CoffBaseRel->VirtualAddress != (Offset & ~0xfff)) {
    if (CoffBaseRel != NULL) {
      //
      // Add a null entry (is it required ?)
      //
      CoffAddFixupEntry (0);
      //
      // Pad for alignment.
      //
      if (CoffOffset % 4 != 0)
  CoffAddFixupEntry (0);
    }
      
    CoffFile = realloc
      (CoffFile,
       CoffOffset + sizeof(EFI_IMAGE_BASE_RELOCATION) + 2*0x1000);
    memset(CoffFile + CoffOffset, 0,
     sizeof(EFI_IMAGE_BASE_RELOCATION) + 2*0x1000);

    CoffBaseRel = (EFI_IMAGE_BASE_RELOCATION*)(CoffFile + CoffOffset);
    CoffBaseRel->VirtualAddress = Offset & ~0xfff;
    CoffBaseRel->SizeOfBlock = sizeof(EFI_IMAGE_BASE_RELOCATION);

    CoffEntryRel = (UINT16 *)(CoffBaseRel + 1);
    CoffOffset += sizeof(EFI_IMAGE_BASE_RELOCATION);
  }

  //
  // Fill the entry.
  //
  CoffAddFixupEntry((Type << 12) | (Offset & 0xfff));
}

void
WriteRelocations(
  VOID
  )
{
  UINT32 Idx;
  EFI_IMAGE_NT_HEADERS *NtHdr;
  EFI_IMAGE_DATA_DIRECTORY *Dir;

  for (Idx = 0; Idx < Ehdr->e_shnum; Idx++) {
    Elf_Shdr *RelShdr = GetShdrByIndex(Idx);
    if (RelShdr->sh_type == SHT_REL) {
      Elf_Shdr *SecShdr = GetShdrByIndex(RelShdr->sh_info);
      if (IsTextShdr(SecShdr) || IsDataShdr(SecShdr)) {
  UINT32 RelIdx;
  for (RelIdx = 0; RelIdx < RelShdr->sh_size; RelIdx += RelShdr->sh_entsize) {
    Elf_Rel *Rel = (Elf_Rel *)
      ((UINT8*)Ehdr + RelShdr->sh_offset + RelIdx);
    switch (ELF_R_TYPE(Rel->r_info)) {
    case R_386_NONE:
    case R_386_PC32:
      break;
    case R_386_32:
      CoffAddFixup(CoffSectionsOffset[RelShdr->sh_info]
       + (Rel->r_offset - SecShdr->sh_addr),
       EFI_IMAGE_REL_BASED_HIGHLOW);
      break;
    default:
      Error (NULL, 0, 0, InImageName, "unhandled relocation type %x",
       ELF_R_TYPE(Rel->r_info));
    }
  }
      }
    }
  }

  //
  // Pad by adding empty entries. 
  //
  while (CoffOffset & (CoffAlignment - 1)) {
    CoffAddFixupEntry(0);
  }

  CreateSectionHeader (".reloc", RelocOffset, CoffOffset - RelocOffset,
           EFI_IMAGE_SCN_CNT_INITIALIZED_DATA
           | EFI_IMAGE_SCN_MEM_DISCARDABLE
           | EFI_IMAGE_SCN_MEM_READ);

  NtHdr = (EFI_IMAGE_NT_HEADERS *)(CoffFile + NtHdrOffset);
  Dir = &NtHdr->OptionalHeader.DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC];
  Dir->VirtualAddress = RelocOffset;
  Dir->Size = CoffOffset - RelocOffset;
}

void
WriteDebug(
  VOID
  )
{
  UINT32 Len = strlen(InImageName) + 1;
  UINT32 DebugOffset = CoffOffset;
  EFI_IMAGE_NT_HEADERS *NtHdr;
  EFI_IMAGE_DATA_DIRECTORY *DataDir;
  EFI_IMAGE_DEBUG_DIRECTORY_ENTRY *Dir;
  EFI_IMAGE_DEBUG_CODEVIEW_NB10_ENTRY *Nb10;

  CoffOffset += sizeof(EFI_IMAGE_DEBUG_DIRECTORY_ENTRY)
    + sizeof(EFI_IMAGE_DEBUG_CODEVIEW_NB10_ENTRY)
    + Len;
  CoffOffset = CoffAlign(CoffOffset);

  CoffFile = realloc
    (CoffFile, CoffOffset);
  memset(CoffFile + DebugOffset, 0, CoffOffset - DebugOffset);
  
  Dir = (EFI_IMAGE_DEBUG_DIRECTORY_ENTRY*)(CoffFile + DebugOffset);
  Dir->Type = EFI_IMAGE_DEBUG_TYPE_CODEVIEW;
  Dir->SizeOfData = sizeof(EFI_IMAGE_DEBUG_DIRECTORY_ENTRY) + Len;
  Dir->RVA = DebugOffset + sizeof(EFI_IMAGE_DEBUG_DIRECTORY_ENTRY);
  Dir->FileOffset = DebugOffset + sizeof(EFI_IMAGE_DEBUG_DIRECTORY_ENTRY);
  
  Nb10 = (EFI_IMAGE_DEBUG_CODEVIEW_NB10_ENTRY*)(Dir + 1);
  Nb10->Signature = CODEVIEW_SIGNATURE_NB10;
  strcpy ((UINT8 *)(Nb10 + 1), InImageName);

  CreateSectionHeader (".debug", DebugOffset, CoffOffset - DebugOffset,
           EFI_IMAGE_SCN_CNT_INITIALIZED_DATA
           | EFI_IMAGE_SCN_MEM_DISCARDABLE
           | EFI_IMAGE_SCN_MEM_READ);

  NtHdr = (EFI_IMAGE_NT_HEADERS *)(CoffFile + NtHdrOffset);
  DataDir = &NtHdr->OptionalHeader.DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_DEBUG];
  DataDir->VirtualAddress = DebugOffset;
  DataDir->Size = CoffOffset - DebugOffset;
}

void
ConvertElf (
  UINT8  **FileBuffer,
  UINTN *FileLength
  )
{
  EFI_IMAGE_NT_HEADERS *NtHdr;

  //
  // Check header, read section table.
  //
  Ehdr = (Elf32_Ehdr*)*FileBuffer;
  if (!CheckElfHeader())
    return;

  //
  // Compute sections new address.
  //
  ScanSections();

  //
  // Write and relocate sections.
  //
  WriteSections(IsTextShdr);
  WriteSections(IsDataShdr);

  //
  // Translate and write relocations.
  //
  WriteRelocations();

  //
  // Write debug info.
  //
  WriteDebug();

  NtHdr = (EFI_IMAGE_NT_HEADERS *)(CoffFile + NtHdrOffset);
  NtHdr->OptionalHeader.SizeOfImage = CoffOffset;

  //
  // Replace.
  //
  free(*FileBuffer);
  *FileBuffer = CoffFile;
  *FileLength = CoffOffset;
}
#endif // HAVE_ELF

int
main (
  int  argc,
  char *argv[]
  )
/*++

Routine Description:

  Main function.

Arguments:

  argc - Number of command line parameters.
  argv - Array of pointers to command line parameter strings.

Returns:
  STATUS_SUCCESS - Utility exits successfully.
  STATUS_ERROR   - Some error occurred during execution.

--*/
{
  UINT32            Type;
  UINT8             *OutImageName;
  UINT8             *ModuleType;
  CHAR8             FileName[MAX_STRING_LENGTH];
  UINT8             OutImageType;
  FILE              *fpIn;
  FILE              *fpOut;
  VOID              *ZeroBuffer;
  UINT32            Index;
  UINT32            Index1;
  UINT32            Index2;
  UINTN             AllignedRelocSize;
  UINT8             *FileBuffer;
  UINTN             FileLength;
  RUNTIME_FUNCTION  *RuntimeFunction;
  UNWIND_INFO       *UnwindInfo;
  STATUS            Status;

  EFI_TE_IMAGE_HEADER          TEImageHeader;
  EFI_IMAGE_SECTION_HEADER     *SectionHeader;
  EFI_IMAGE_DOS_HEADER         *DosHdr;
  EFI_IMAGE_NT_HEADERS         *PeHdr;
  EFI_IMAGE_OPTIONAL_HEADER32  *Optional32;
  EFI_IMAGE_OPTIONAL_HEADER64  *Optional64;
  EFI_IMAGE_DOS_HEADER         BackupDosHdr;


  SetUtilityName (UTILITY_NAME);

  //
  // Assign to fix compile warning
  //
  InImageName       = NULL;
  OutImageName      = NULL;
  ModuleType        = NULL;
  OutImageType      = FW_DUMMY_IMAGE;
  Type              = 0;
  Status            = STATUS_SUCCESS;
  FileBuffer        = NULL;

  if (argc == 1) {
    Usage();
    return STATUS_ERROR;
  }
  
  argc --;
  argv ++;  

  if ((stricmp (argv[0], "-h") == 0) || (stricmp (argv[0], "--help") == 0)) {
    Usage();
    return STATUS_ERROR;    
  }

  if ((stricmp (argv[0], "-v") == 0) || (stricmp (argv[0], "--version") == 0)) {
    Version();
    return STATUS_ERROR;    
  }
  
  while (argc > 0) {
    if ((stricmp (argv[0], "-o") == 0) || (stricmp (argv[0], "--outputfile") == 0)) {
      OutImageName = argv[1];
      argc -= 2;
      argv += 2;
      continue; 
    }

    if ((stricmp (argv[0], "-e") == 0) || (stricmp (argv[0], "--efiImage") == 0)) {
      ModuleType   = argv[1];
      if (OutImageType == FW_DUMMY_IMAGE) {
        OutImageType = FW_EFI_IMAGE;
      }
      argc -= 2;
      argv += 2;
      continue;
    }

    if ((stricmp (argv[0], "-c") == 0) || (stricmp (argv[0], "--acpi") == 0)) {
      OutImageType = FW_ACPI_IMAGE;
      argc --;
      argv ++;
      continue;
    }

    if ((stricmp (argv[0], "-t") == 0) || (stricmp (argv[0], "--terse") == 0)) {
      OutImageType = FW_TE_IMAGE;
      argc --;
      argv ++;
      continue;
    }

    InImageName = argv[0];
    argc --;
    argv ++;
  }
  
  if (OutImageType == FW_DUMMY_IMAGE) {
    Error (NULL, 0, 0, NULL, "No action specified, such as -e, -c or -t\n");
    Usage ();
    return STATUS_ERROR;    
  }

  //
  // get InImageName from stdin
  //
  if (InImageName == NULL) {
    fscanf (stdin, "%s", FileName);
    InImageName = (UINT8 *) FileName;
  }

  //
  // Open input file
  //
  fpIn = fopen (InImageName, "rb");
  if (!fpIn) {
    Error (NULL, 0, 0, InImageName, "failed to open input file for reading");
    return STATUS_ERROR;
  }

  FReadFile (fpIn, (VOID **)&FileBuffer, &FileLength);
  fclose (fpIn);

  //
  // Open output file and Write image into the output file.
  // if OutImageName == NULL, output data to stdout.
  //
  if (OutImageName == NULL) {
    fpOut = stdout; // binary stream can't be output to string strem stdout
                    // because 0x0A can be auto converted to 0x0D 0x0A.
  } else {
    fpOut = fopen (OutImageName, "w+b");
  }
  if (!fpOut) {
    Error (NULL, 0, 0, OutImageName, "could not open output file for writing");
    Status = STATUS_ERROR;
    goto Finish;
  }

  //
  // Following code to convert dll to efi image or te image.
  // Get new image type
  //
  if ((OutImageType == FW_EFI_IMAGE) || (OutImageType == FW_TE_IMAGE)) {
    if (ModuleType == NULL) {
      Error (NULL, 0, 0, NULL, "No ModuleType specified, such as PEIM, DXE_DRIVER\n");
      Usage ();
      Status = STATUS_ERROR;
      goto Finish;
    }
    
    if (stricmp (ModuleType, "BASE") == 0 ||
        stricmp (ModuleType, "SEC") == 0 ||
        stricmp (ModuleType, "SECURITY_CORE") == 0 ||
        stricmp (ModuleType, "PEI_CORE") == 0 ||
        stricmp (ModuleType, "PEIM") == 0 ||
        stricmp (ModuleType, "COMBINED_PEIM_DRIVER") == 0 ||
        stricmp (ModuleType, "PIC_PEIM") == 0 ||
        stricmp (ModuleType, "RELOCATABLE_PEIM") == 0 ||
        stricmp (ModuleType, "DXE_CORE") == 0 ||
        stricmp (ModuleType, "BS_DRIVER") == 0  ||
        stricmp (ModuleType, "DXE_DRIVER") == 0 ||
        stricmp (ModuleType, "DXE_SMM_DRIVER") == 0  ||
        stricmp (ModuleType, "UEFI_DRIVER") == 0) {
      Type = EFI_IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER;
  
    } else if (stricmp (ModuleType, "UEFI_APPLICATION") == 0 || 
               stricmp (ModuleType, "APPLICATION") == 0) {
      Type = EFI_IMAGE_SUBSYSTEM_EFI_APPLICATION;
  
    } else if (stricmp (ModuleType, "DXE_RUNTIME_DRIVER") == 0 || 
               stricmp (ModuleType, "RT_DRIVER") == 0) {
      Type = EFI_IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER;
  
    } else if (stricmp (ModuleType, "DXE_SAL_DRIVER") == 0 || 
               stricmp (ModuleType, "SAL_RT_DRIVER") == 0) {
      Type = EFI_IMAGE_SUBSYSTEM_SAL_RUNTIME_DRIVER;
  
    } else {
      Error (NULL, 0, 0, ModuleType, "%s is not one valid Module type.\n");
      Usage ();
      Status = STATUS_ERROR;
      goto Finish;
    }
  }

  //
  // Convert EFL image to PeImage
  //
#ifdef HAVE_ELF
  if (IsElfHeader(FileBuffer)) {
    ConvertElf(&FileBuffer, &FileLength);
  }
#endif

  //
  // Read the dos & pe hdrs of the image
  //
  DosHdr = (EFI_IMAGE_DOS_HEADER *)FileBuffer;
  if (DosHdr->e_magic != EFI_IMAGE_DOS_SIGNATURE) {
    Error (NULL, 0, 0, InImageName, "DOS header signature not found in source image");
    Status = STATUS_ERROR;
    goto Finish;
  }

  PeHdr = (EFI_IMAGE_NT_HEADERS *)(FileBuffer + DosHdr->e_lfanew);
  if (PeHdr->Signature != EFI_IMAGE_NT_SIGNATURE) {
    Error (NULL, 0, 0, InImageName, "PE header signature not found in source image");
    Status = STATUS_ERROR;
    goto Finish;
  }
  
  if (OutImageType == FW_ACPI_IMAGE) {
    SectionHeader = (EFI_IMAGE_SECTION_HEADER *) ((UINT8 *) &(PeHdr->OptionalHeader) + PeHdr->FileHeader.SizeOfOptionalHeader); 
    for (Index = 0; Index < PeHdr->FileHeader.NumberOfSections; Index ++, SectionHeader ++) {
      if (strcmp (SectionHeader->Name, ".data") == 0 || strcmp (SectionHeader->Name, ".sdata") == 0) {
        //
        // Check Acpi Table
        //
        if (SectionHeader->Misc.VirtualSize < SectionHeader->SizeOfRawData) {
          FileLength = SectionHeader->Misc.VirtualSize;
        } else {
          FileLength = SectionHeader->SizeOfRawData;
        }

        if (CheckAcpiTable (FileBuffer + SectionHeader->PointerToRawData, FileLength) != STATUS_SUCCESS) {
          Error (NULL, 0, 0, InImageName, "failed to check ACPI table");
          Status = STATUS_ERROR;
          goto Finish;
        }
        
        //
        // Output Apci data to file
        //
        memcpy (FileBuffer, FileBuffer + SectionHeader->PointerToRawData, FileLength);
        FWriteFile (fpOut, FileBuffer, FileLength);
        fclose (fpOut);
        return STATUS_SUCCESS;
      }
    }
    Error (NULL, 0, 0, InImageName, "failed to get ACPI table");
    Status = STATUS_ERROR;
    goto Finish;
  }
  //
  // Zero all unused fields of the DOS header
  //
  memcpy (&BackupDosHdr, DosHdr, sizeof (EFI_IMAGE_DOS_HEADER));
  memset (DosHdr, 0, sizeof (EFI_IMAGE_DOS_HEADER));
  DosHdr->e_magic  = BackupDosHdr.e_magic;
  DosHdr->e_lfanew = BackupDosHdr.e_lfanew;

  for (Index = sizeof (EFI_IMAGE_DOS_HEADER); Index < (UINT32 ) DosHdr->e_lfanew; Index++) {
    FileBuffer[Index] = DosHdr->e_cp;
  }
  
  //
  // Initialize TeImage Header
  //
  memset (&TEImageHeader, 0, sizeof (EFI_TE_IMAGE_HEADER));
  TEImageHeader.Signature        = EFI_TE_IMAGE_HEADER_SIGNATURE;
  TEImageHeader.Machine          = PeHdr->FileHeader.Machine;
  TEImageHeader.NumberOfSections = (UINT8) PeHdr->FileHeader.NumberOfSections;
  TEImageHeader.StrippedSize     = (UINT16) ((UINTN) ((UINT8 *) &(PeHdr->OptionalHeader) + PeHdr->FileHeader.SizeOfOptionalHeader) - (UINTN) FileBuffer);
  TEImageHeader.Subsystem        = (UINT8) Type;

  //
  // Patch the PE header
  //
  PeHdr->OptionalHeader.Subsystem = (UINT16) Type;

  if (PeHdr->OptionalHeader.Magic == EFI_IMAGE_NT_OPTIONAL_HDR32_MAGIC) {
    Optional32 = (EFI_IMAGE_OPTIONAL_HEADER32 *)&PeHdr->OptionalHeader;
    Optional32->MajorLinkerVersion          = 0;
    Optional32->MinorLinkerVersion          = 0;
    Optional32->MajorOperatingSystemVersion = 0;
    Optional32->MinorOperatingSystemVersion = 0;
    Optional32->MajorImageVersion           = 0;
    Optional32->MinorImageVersion           = 0;
    Optional32->MajorSubsystemVersion       = 0;
    Optional32->MinorSubsystemVersion       = 0;
    Optional32->Win32VersionValue           = 0;
    Optional32->CheckSum                    = 0;
    Optional32->SizeOfStackReserve = 0;
    Optional32->SizeOfStackCommit  = 0;
    Optional32->SizeOfHeapReserve  = 0;
    Optional32->SizeOfHeapCommit   = 0;
    
    TEImageHeader.AddressOfEntryPoint = Optional32->AddressOfEntryPoint;
    TEImageHeader.BaseOfCode          = Optional32->BaseOfCode;
    TEImageHeader.ImageBase           = (UINT64) (Optional32->ImageBase);

    if (Optional32->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC) {
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress = Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress;
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size = Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size;
    }

    if (Optional32->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_DEBUG) {
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_DEBUG].VirtualAddress = Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_DEBUG].VirtualAddress;
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_DEBUG].Size = Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_DEBUG].Size;
    }

    //
    // Strip zero padding at the end of the .reloc section 
    //
    if (Optional32->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC) {
      if (Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size != 0) {
        SectionHeader = (EFI_IMAGE_SECTION_HEADER *)(FileBuffer + DosHdr->e_lfanew + sizeof(UINT32) + sizeof (EFI_IMAGE_FILE_HEADER) + PeHdr->FileHeader.SizeOfOptionalHeader);
        for (Index = 0; Index < PeHdr->FileHeader.NumberOfSections; Index++, SectionHeader++) {
          //
          // Look for the Section Header that starts as the same virtual address as the Base Relocation Data Directory
          //
          if (SectionHeader->VirtualAddress == Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress) {
            SectionHeader->Misc.VirtualSize = Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size;
            AllignedRelocSize = (Optional32->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size + Optional32->FileAlignment - 1) & (~(Optional32->FileAlignment - 1));
            //
            // Check to see if there is zero padding at the end of the base relocations
            //
            if (AllignedRelocSize < SectionHeader->SizeOfRawData) {
              //
              // Check to see if the base relocations are at the end of the file
              //
              if (SectionHeader->PointerToRawData + SectionHeader->SizeOfRawData == Optional32->SizeOfImage) {
                //
                // All the required conditions are met to strip the zero padding of the end of the base relocations section
                //
                Optional32->SizeOfImage -= (SectionHeader->SizeOfRawData - AllignedRelocSize);
                Optional32->SizeOfInitializedData -= (SectionHeader->SizeOfRawData - AllignedRelocSize);
                SectionHeader->SizeOfRawData = AllignedRelocSize;
                FileLength = Optional32->SizeOfImage;
              }
            }
          }
        }
      }
    }
  } 

  if (PeHdr->OptionalHeader.Magic == EFI_IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
    Optional64 = (EFI_IMAGE_OPTIONAL_HEADER64 *)&PeHdr->OptionalHeader;
    Optional64->MajorLinkerVersion          = 0;
    Optional64->MinorLinkerVersion          = 0;
    Optional64->MajorOperatingSystemVersion = 0;
    Optional64->MinorOperatingSystemVersion = 0;
    Optional64->MajorImageVersion           = 0;
    Optional64->MinorImageVersion           = 0;
    Optional64->MajorSubsystemVersion       = 0;
    Optional64->MinorSubsystemVersion       = 0;
    Optional64->Win32VersionValue           = 0;
    Optional64->CheckSum                    = 0;
    Optional64->SizeOfStackReserve = 0;
    Optional64->SizeOfStackCommit  = 0;
    Optional64->SizeOfHeapReserve  = 0;
    Optional64->SizeOfHeapCommit   = 0;

    TEImageHeader.AddressOfEntryPoint = Optional64->AddressOfEntryPoint;
    TEImageHeader.BaseOfCode          = Optional64->BaseOfCode;
    TEImageHeader.ImageBase           = (UINT64) (Optional64->ImageBase);

    if (Optional64->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC) {
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress = Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress;
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size = Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size;
    }

    if (Optional64->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_DEBUG) {
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_DEBUG].VirtualAddress = Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_DEBUG].VirtualAddress;
      TEImageHeader.DataDirectory[EFI_TE_IMAGE_DIRECTORY_ENTRY_DEBUG].Size = Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_DEBUG].Size;
    }

    //
    // Zero the .pdata section if the machine type is X64 and the Debug Directory is empty
    //
    if (PeHdr->FileHeader.Machine == IMAGE_FILE_MACHINE_X64) { // X64
      if (Optional64->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_EXCEPTION) {
        if (Optional64->NumberOfRvaAndSizes <= EFI_IMAGE_DIRECTORY_ENTRY_DEBUG || (Optional64->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_DEBUG && Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_DEBUG].Size == 0)) {
          SectionHeader = (EFI_IMAGE_SECTION_HEADER *)(FileBuffer + DosHdr->e_lfanew + sizeof(UINT32) + sizeof (EFI_IMAGE_FILE_HEADER) + PeHdr->FileHeader.SizeOfOptionalHeader);
          for (Index = 0; Index < PeHdr->FileHeader.NumberOfSections; Index++, SectionHeader++) {
            if (SectionHeader->VirtualAddress == Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_EXCEPTION].VirtualAddress) {
              RuntimeFunction = (RUNTIME_FUNCTION *)(FileBuffer + SectionHeader->PointerToRawData);
              for (Index1 = 0; Index1 < Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_EXCEPTION].Size / sizeof (RUNTIME_FUNCTION); Index1++, RuntimeFunction++) {
                SectionHeader = (EFI_IMAGE_SECTION_HEADER *)(FileBuffer + DosHdr->e_lfanew + sizeof(UINT32) + sizeof (EFI_IMAGE_FILE_HEADER) + PeHdr->FileHeader.SizeOfOptionalHeader);
                for (Index2 = 0; Index2 < PeHdr->FileHeader.NumberOfSections; Index2++, SectionHeader++) {
                  if (RuntimeFunction->UnwindInfoAddress > SectionHeader->VirtualAddress && RuntimeFunction->UnwindInfoAddress < (SectionHeader->VirtualAddress + SectionHeader->SizeOfRawData)) {
                    UnwindInfo = (UNWIND_INFO *)(FileBuffer + SectionHeader->PointerToRawData + (RuntimeFunction->UnwindInfoAddress - SectionHeader->VirtualAddress));
                    if (UnwindInfo->Version == 1) {
                      memset (UnwindInfo + 1, 0, UnwindInfo->CountOfUnwindCodes * sizeof (UINT16));
                      memset (UnwindInfo, 0, sizeof (UNWIND_INFO));
                    }
                  }
                }
                memset (RuntimeFunction, 0, sizeof (RUNTIME_FUNCTION));
              }

              break;
            }
          }
          Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_EXCEPTION].Size = 0;
          Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_EXCEPTION].VirtualAddress = 0;
        }
      }
    }

    //
    // Strip zero padding at the end of the .reloc section 
    //
    if (Optional64->NumberOfRvaAndSizes > EFI_IMAGE_DIRECTORY_ENTRY_DEBUG) {
      if (Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size != 0) {
        SectionHeader = (EFI_IMAGE_SECTION_HEADER *)(FileBuffer + DosHdr->e_lfanew + sizeof(UINT32) + sizeof (EFI_IMAGE_FILE_HEADER) + PeHdr->FileHeader.SizeOfOptionalHeader);
        for (Index = 0; Index < PeHdr->FileHeader.NumberOfSections; Index++, SectionHeader++) {
          //
          // Look for the Section Header that starts as the same virtual address as the Base Relocation Data Directory
          //
          if (SectionHeader->VirtualAddress == Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].VirtualAddress) {
            SectionHeader->Misc.VirtualSize = Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size;
            AllignedRelocSize = (Optional64->DataDirectory[EFI_IMAGE_DIRECTORY_ENTRY_BASERELOC].Size + Optional64->FileAlignment - 1) & (~(Optional64->FileAlignment - 1));
            //
            // Check to see if there is zero padding at the end of the base relocations
            //
            if (AllignedRelocSize < SectionHeader->SizeOfRawData) {
              //
              // Check to see if the base relocations are at the end of the file
              //
              if (SectionHeader->PointerToRawData + SectionHeader->SizeOfRawData == Optional64->SizeOfImage) {
                //
                // All the required conditions are met to strip the zero padding of the end of the base relocations section
                //
                Optional64->SizeOfImage -= (SectionHeader->SizeOfRawData - AllignedRelocSize);
                Optional64->SizeOfInitializedData -= (SectionHeader->SizeOfRawData - AllignedRelocSize);
                SectionHeader->SizeOfRawData = AllignedRelocSize;
                FileLength = Optional64->SizeOfImage;
              }
            }
          }
        }
      }
    }
  }

  if (OutImageType == FW_TE_IMAGE) {
    if ((PeHdr->FileHeader.NumberOfSections &~0xFF) || (Type &~0xFF)) {
      //
      // Pack the subsystem and NumberOfSections into 1 byte. Make sure they fit both.
      //
      Error (NULL, 0, 0, InImageName, "image subsystem or NumberOfSections cannot be packed into 1 byte");
      Status = STATUS_ERROR;
      goto Finish;
    }

    //
    // Update Image to TeImage
    //
    FileLength = FileLength - TEImageHeader.StrippedSize;
    memcpy (FileBuffer + sizeof (EFI_TE_IMAGE_HEADER), FileBuffer + TEImageHeader.StrippedSize, FileLength);
    memcpy (FileBuffer, &TEImageHeader, sizeof (EFI_TE_IMAGE_HEADER));
  }

  FWriteFile (fpOut, FileBuffer, FileLength);
  FileBuffer = NULL;

Finish:
  if (FileBuffer != NULL) {
    free (FileBuffer);
  }

  if (fpOut != NULL) {
    //
    // Write converted data into fpOut file and close output file.
    //
    fclose (fpOut);
  }
  
  return Status;
}