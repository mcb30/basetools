class UiSection ("parent = Section"):
    def __init__(self):
        self.Alignment = None
        self.StringData = None
        self.FileName = None


    def GenSection(OutputPath, ModuleName):
        #
        # Prepare the parameter of GenSection
        #
        OutputFile = OutputPath + ModuleName + Ffs.SectionSuffix('UI')
        GenSectionCmd = 'GenSection -o ' + OutputFile + ' -s EFI_SECTION_VERSION ' \
                         + '-n ' + '\"' + self.StringData + '\"' + BuildNum
        #
        # Call GenSection
        #
        popen(GenSectionCmd, mod = 'r')

        return OutputFile
