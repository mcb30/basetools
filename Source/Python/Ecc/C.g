
grammar C;
options {
    language=Python;
    backtrack=true;
    memoize=true;
    k=2;
}

@header {
    import CodeFragment
    import FileProfile
}

@members {
        
    def printTokenInfo(self, line, offset, tokenText):
    	print str(line)+ ',' + str(offset) + ':' + str(tokenText)
        
    def StorePredicateExpression(self, StartLine, StartOffset, EndLine, EndOffset, Text):
    	PredExp = CodeFragment.PredicateExpression(Text, (StartLine, StartOffset), (EndLine, EndOffset))
    	FileProfile.PredicateExpressionList.append(PredExp)
    	
    def StoreEnumerationDefinition(self, StartLine, StartOffset, EndLine, EndOffset, Text):
    	EnumDef = CodeFragment.EnumerationDefinition(Text, (StartLine, StartOffset), (EndLine, EndOffset))
    	FileProfile.EnumerationDefinitionList.append(EnumDef)
    	
    def StoreStructUnionDefinition(self, StartLine, StartOffset, EndLine, EndOffset, Text):
    	SUDef = CodeFragment.StructUnionDefinition(Text, (StartLine, StartOffset), (EndLine, EndOffset))
    	FileProfile.StructUnionDefinitionList.append(SUDef)
    	
    def StoreTypedefDefinition(self, StartLine, StartOffset, EndLine, EndOffset, FromText, ToText):
    	Tdef = CodeFragment.TypedefDefinition(FromText, ToText, (StartLine, StartOffset), (EndLine, EndOffset))
    	FileProfile.TypedefDefinitionList.append(Tdef)
    
    def StoreFunctionDefinition(self, StartLine, StartOffset, EndLine, EndOffset, ModifierText, DeclText, LeftBraceLine, LeftBraceOffset, DeclLine, DeclOffset):
    	FuncDef = CodeFragment.FunctionDefinition(ModifierText, DeclText, (StartLine, StartOffset), (EndLine, EndOffset), (LeftBraceLine, LeftBraceOffset), (DeclLine, DeclOffset))
    	FileProfile.FunctionDefinitionList.append(FuncDef)
    	
    def StoreVariableDeclaration(self, StartLine, StartOffset, EndLine, EndOffset, ModifierText, DeclText):
    	VarDecl = CodeFragment.VariableDeclaration(ModifierText, DeclText, (StartLine, StartOffset), (EndLine, EndOffset))
    	FileProfile.VariableDeclarationList.append(VarDecl)
    
    def StoreFunctionCalling(self, StartLine, StartOffset, EndLine, EndOffset, FuncName, ParamList):
    	FuncCall = CodeFragment.FunctionCalling(FuncName, ParamList, (StartLine, StartOffset), (EndLine, EndOffset))
    	FileProfile.FunctionCallingList.append(FuncCall)

}

translation_unit
	: external_declaration*
	;


/*function_declaration
@after{
  print $function_declaration.text
}
	: declaration_specifiers IDENTIFIER '(' parameter_list ')' ';'
	;
*/
external_declaration
options {k=1;}
/*@after{
  print $external_declaration.text
}*/
	: ( declaration_specifiers? declarator declaration* '{' )=> function_definition
	| declaration
	| macro_statement (';')?
	;
	


function_definition
scope {
  ModifierText;
  DeclText;
  LBLine;
  LBOffset;
  DeclLine;
  DeclOffset;
}
@init {
  $function_definition::ModifierText = '';
  $function_definition::DeclText = '';
  $function_definition::LBLine = 0;
  $function_definition::LBOffset = 0;
  $function_definition::DeclLine = 0;
  $function_definition::DeclOffset = 0;
}
@after{
  self.StoreFunctionDefinition($function_definition.start.line, $function_definition.start.charPositionInLine, $function_definition.stop.line, $function_definition.stop.charPositionInLine, $function_definition::ModifierText, $function_definition::DeclText, $function_definition::LBLine, $function_definition::LBOffset, $function_definition::DeclLine, $function_definition::DeclOffset)
}
	:	d=declaration_specifiers? declarator
		(	declaration+ a=compound_statement	// K&R style
		|	b=compound_statement				// ANSI style
		) { 
		    if d != None:
		      $function_definition::ModifierText = $declaration_specifiers.text
		    else:
		      $function_definition::ModifierText = ''
		    $function_definition::DeclText = $declarator.text
		    $function_definition::DeclLine = $declarator.start.line
		    $function_definition::DeclOffset = $declarator.start.charPositionInLine
		    if a != None:
		      $function_definition::LBLine = $a.start.line
		      $function_definition::LBOffset = $a.start.charPositionInLine
		    else:
		      $function_definition::LBLine = $b.start.line
		      $function_definition::LBOffset = $b.start.charPositionInLine
		  }
	;

declaration
	: a='typedef' b=declaration_specifiers? 
	  c=init_declarator_list d=';' 
	  {
	  if b != None:
	    self.StoreTypedefDefinition($a.line, $a.charPositionInLine, $d.line, $d.charPositionInLine, $b.text, $c.text)
	  else:
	    self.StoreTypedefDefinition($a.line, $a.charPositionInLine, $d.line, $d.charPositionInLine, '', $c.text)
	  }	
	| s=declaration_specifiers t=init_declarator_list? e=';' 
	{
	if t != None:
	  self.StoreVariableDeclaration($s.start.line, $s.start.charPositionInLine, $t.start.line, $t.start.charPositionInLine, $s.text, $t.text)
	}
	;

declaration_specifiers
	:   (   storage_class_specifier
		|   type_specifier
        |   type_qualifier
        )+
	;

init_declarator_list
	: init_declarator (',' init_declarator)*
	;

init_declarator
	: declarator ('=' initializer)? 
	;

storage_class_specifier
	: 'extern'
	| 'static'
	| 'auto'
	| 'register'
	| 'STATIC'
	;

type_specifier
	: 'void'
	| 'char'
	| 'short'
	| 'int'
	| 'long'
	| 'float'
	| 'double'
	| 'signed'
	| 'unsigned'
	| s=struct_or_union_specifier
	{
	if s.stop != None:
	  self.StoreStructUnionDefinition($s.start.line, $s.start.charPositionInLine, $s.stop.line, $s.stop.charPositionInLine, $s.text)
	}
	| e=enum_specifier
	{
	if e.stop != None:
	  self.StoreEnumerationDefinition($e.start.line, $e.start.charPositionInLine, $e.stop.line, $e.stop.charPositionInLine, $e.text)
	}
	| (IDENTIFIER type_qualifier* declarator)=> type_id
	;

type_id
    :   IDENTIFIER
    	//{self.printTokenInfo($a.line, $a.pos, $a.text)}
    ;

struct_or_union_specifier
options {k=3;}
	: struct_or_union IDENTIFIER? '{' struct_declaration_list '}'
	| struct_or_union IDENTIFIER
	;

struct_or_union
	: 'struct'
	| 'union'
	;

struct_declaration_list
	: struct_declaration+
	;

struct_declaration
	: specifier_qualifier_list struct_declarator_list ';'
	;

specifier_qualifier_list
	: ( type_qualifier | type_specifier )+
	;

struct_declarator_list
	: struct_declarator (',' struct_declarator)*
	;

struct_declarator
	: declarator (':' constant_expression)?
	| ':' constant_expression
	;

enum_specifier
options {k=3;}
	: 'enum' '{' enumerator_list ','? '}'
	| 'enum' IDENTIFIER '{' enumerator_list ','? '}'
	| 'enum' IDENTIFIER
	;

enumerator_list
	: enumerator (',' enumerator)*
	;

enumerator
	: IDENTIFIER ('=' constant_expression)?
	;

type_qualifier
	: 'const'
	| 'volatile'
	| 'IN'
	| 'OUT'
	| 'OPTIONAL'
	| 'CONST'
	| 'UNALIGNED'
	| 'VOLATILE'
	| 'GLOBAL_REMOVE_IF_UNREFERENCED'
	| 'EFIAPI'
	| 'EFI_BOOTSERVICE'
	| 'EFI_RUNTIMESERVICE'
	;

declarator
	: pointer? ('EFIAPI')? ('EFI_BOOTSERVICE')? ('EFI_RUNTIMESERVICE')? direct_declarator
//	| ('EFIAPI')? ('EFI_BOOTSERVICE')? ('EFI_RUNTIMESERVICE')? pointer? direct_declarator
	| pointer
	;

direct_declarator
	: IDENTIFIER declarator_suffix*
	| '(' ('EFIAPI')? declarator ')' declarator_suffix+
	;

declarator_suffix
	:   '[' constant_expression ']'
    |   '[' ']'
    |   '(' parameter_type_list ')'
    |   '(' identifier_list ')'
    |   '(' ')'
	;

pointer
	: '*' type_qualifier+ pointer?
	| '*' pointer
	| '*'
	;

parameter_type_list
	: parameter_list (',' ('OPTIONAL')? '...')?
	;

parameter_list
	: parameter_declaration (',' ('OPTIONAL')? parameter_declaration)*
	;

parameter_declaration
	: declaration_specifiers (declarator|abstract_declarator)* ('OPTIONAL')?
	//accomerdate user-defined type only, no declarator follow.
	| pointer* IDENTIFIER
	;

identifier_list
	: IDENTIFIER
	(',' IDENTIFIER)*
	;

type_name
	: specifier_qualifier_list abstract_declarator?
	| type_id
	;

abstract_declarator
	: pointer direct_abstract_declarator?
	| direct_abstract_declarator
	;

direct_abstract_declarator
	:	( '(' abstract_declarator ')' | abstract_declarator_suffix ) abstract_declarator_suffix*
	;

abstract_declarator_suffix
	:	'[' ']'
	|	'[' constant_expression ']'
	|	'(' ')'
	|	'(' parameter_type_list ')'
	;
	
initializer

	: assignment_expression
	| '{' initializer_list ','? '}'
	;

initializer_list
	: initializer (',' initializer )*
	;

// E x p r e s s i o n s

argument_expression_list
	:   assignment_expression ('OPTIONAL')? (',' assignment_expression ('OPTIONAL')?)*
	;

additive_expression
	: (multiplicative_expression) ('+' multiplicative_expression | '-' multiplicative_expression)*
	;

multiplicative_expression
	: (cast_expression) ('*' cast_expression | '/' cast_expression | '%' cast_expression)*
	;

cast_expression
	: '(' type_name ')' cast_expression
	| unary_expression
	;

unary_expression
	: postfix_expression
	| '++' unary_expression
	| '--' unary_expression
	| unary_operator cast_expression
	| 'sizeof' unary_expression
	| 'sizeof' '(' type_name ')'
	;

postfix_expression
scope {
  FuncCallText;
}
@init {
  $postfix_expression::FuncCallText = '';
}
	:   p=primary_expression {$postfix_expression::FuncCallText += $p.text}
        (   '[' expression ']'
        |   '(' a=')'{self.StoreFunctionCalling($p.start.line, $p.start.charPositionInLine, $a.line, $a.charPositionInLine, $postfix_expression::FuncCallText, '')}
        |   '(' c=argument_expression_list b=')' {self.StoreFunctionCalling($p.start.line, $p.start.charPositionInLine, $b.line, $b.charPositionInLine, $postfix_expression::FuncCallText, $c.text)}
        |   '(' macro_parameter_list ')'
        |   '.' x=IDENTIFIER {$postfix_expression::FuncCallText += '.' + $x.text}
        |   '*' y=IDENTIFIER {$postfix_expression::FuncCallText = $y.text}
        |   '->' z=IDENTIFIER {$postfix_expression::FuncCallText += '->' + $z.text}
        |   '++'
        |   '--'
        )*
	;
	
macro_parameter_list
	: parameter_declaration (',' parameter_declaration)*
	;

unary_operator
	: '&'
	| '*'
	| '+'
	| '-'
	| '~'
	| '!'
	;

primary_expression
	: IDENTIFIER
	| constant
	| '(' expression ')'
	;

constant
    :   HEX_LITERAL
    |   OCTAL_LITERAL
    |   DECIMAL_LITERAL
    |	CHARACTER_LITERAL
    |	(IDENTIFIER* STRING_LITERAL+)+ IDENTIFIER*
    |   FLOATING_POINT_LITERAL
    ;

/////

expression
	: assignment_expression (',' assignment_expression)*
	;

constant_expression
	: conditional_expression
	;

assignment_expression
	: lvalue assignment_operator assignment_expression
	| conditional_expression
	;
	
lvalue
	:	unary_expression
	;

assignment_operator
	: '='
	| '*='
	| '/='
	| '%='
	| '+='
	| '-='
	| '<<='
	| '>>='
	| '&='
	| '^='
	| '|='
	;

conditional_expression
	: e=logical_or_expression ('?' expression ':' conditional_expression {self.StorePredicateExpression($e.start.line, $e.start.charPositionInLine, $e.stop.line, $e.stop.charPositionInLine, $e.text)})?
	;

logical_or_expression
	: logical_and_expression ('||' logical_and_expression)*
	;

logical_and_expression
	: inclusive_or_expression ('&&' inclusive_or_expression)*
	;

inclusive_or_expression
	: exclusive_or_expression ('|' exclusive_or_expression)*
	;

exclusive_or_expression
	: and_expression ('^' and_expression)*
	;

and_expression
	: equality_expression ('&' equality_expression)*
	;
equality_expression
	: relational_expression (('=='|'!=') relational_expression )*
	;

relational_expression
	: shift_expression (('<'|'>'|'<='|'>=') shift_expression)*
	;

shift_expression
	: additive_expression (('<<'|'>>') additive_expression)*
	;

// S t a t e m e n t s

statement
	: labeled_statement
	| compound_statement
	| expression_statement
	| selection_statement
	| iteration_statement
	| jump_statement
	| macro_statement
	| asm_statement
	| asm1_statement
	| declaration
	;

asm1_statement
	: '_asm' '{' (~('}'))* '}'
	;

asm_statement
	: '__asm' '{' (~('}'))* '}'
	;
	
macro_statement
	: IDENTIFIER '(' declaration*  statement_list? expression? ')'
	;
	
labeled_statement
	: IDENTIFIER ':' statement
	| 'case' constant_expression ':' statement
	| 'default' ':' statement
	;

compound_statement
	: '{' declaration* statement_list? '}'
	;

statement_list
	: statement+
	;

expression_statement
	: ';'
	| expression ';'
	;

selection_statement
	: 'if' '(' e=expression ')' {self.StorePredicateExpression($e.start.line, $e.start.charPositionInLine, $e.stop.line, $e.stop.charPositionInLine, $e.text)} statement (options {k=1; backtrack=false;}:'else' statement)?
	| 'switch' '(' expression ')' statement
	;

iteration_statement
	: 'while' '(' e=expression ')' statement {self.StorePredicateExpression($e.start.line, $e.start.charPositionInLine, $e.stop.line, $e.stop.charPositionInLine, $e.text)}
	| 'do' statement 'while' '(' e=expression ')' ';' {self.StorePredicateExpression($e.start.line, $e.start.charPositionInLine, $e.stop.line, $e.stop.charPositionInLine, $e.text)}
	| 'for' '(' expression_statement e=expression_statement expression? ')' statement {self.StorePredicateExpression($e.start.line, $e.start.charPositionInLine, $e.stop.line, $e.stop.charPositionInLine, $e.text)}
	;

jump_statement
	: 'goto' IDENTIFIER ';'
	| 'continue' ';'
	| 'break' ';'
	| 'return' ';'
	| 'return' expression ';'
	;

IDENTIFIER
	:	LETTER (LETTER|'0'..'9')*
	;
	
fragment
LETTER
	:	'$'
	|  'A'..'Z'
	|  'a'..'z'
	|	'_'
	;

CHARACTER_LITERAL
    :   ('L')? '\'' ( EscapeSequence | ~('\''|'\\') ) '\''
    ;

STRING_LITERAL
    :  ('L')? '"' ( EscapeSequence | ~('\\'|'"') )* '"'
    ;
    
HEX_LITERAL : '0' ('x'|'X') HexDigit+ IntegerTypeSuffix? ;

DECIMAL_LITERAL : ('0' | '1'..'9' '0'..'9'*) IntegerTypeSuffix? ;

OCTAL_LITERAL : '0' ('0'..'7')+ IntegerTypeSuffix? ;

fragment
HexDigit : ('0'..'9'|'a'..'f'|'A'..'F') ;

fragment
IntegerTypeSuffix
	: ('u'|'U')
	| ('l'|'L')
	| ('u'|'U')  ('l'|'L')
	| ('u'|'U')  ('l'|'L') ('l'|'L')
	;

FLOATING_POINT_LITERAL
    :   ('0'..'9')+ '.' ('0'..'9')* Exponent? FloatTypeSuffix?
    |   '.' ('0'..'9')+ Exponent? FloatTypeSuffix?
    |   ('0'..'9')+ Exponent FloatTypeSuffix?
    |   ('0'..'9')+ Exponent? FloatTypeSuffix
	;

fragment
Exponent : ('e'|'E') ('+'|'-')? ('0'..'9')+ ;

fragment
FloatTypeSuffix : ('f'|'F'|'d'|'D') ;

fragment
EscapeSequence
    :  '\\' ('b'|'t'|'n'|'f'|'r'|'\"'|'\''|'\\')
    |   OctalEscape
    ;

fragment
OctalEscape
    :   '\\' ('0'..'3') ('0'..'7') ('0'..'7')
    |   '\\' ('0'..'7') ('0'..'7')
    |   '\\' ('0'..'7')
    ;

fragment
UnicodeEscape
    :   '\\' 'u' HexDigit HexDigit HexDigit HexDigit
    ;

WS  :  (' '|'\r'|'\t'|'\u000C'|'\n') {$channel=HIDDEN;}
    ;

// ingore '\' of line concatenation
BS  : ('\\') {$channel=HIDDEN;}
    ;
    
// ingore function modifiers
//FUNC_MODIFIERS  : 'EFIAPI' {$channel=HIDDEN;}
//    ;
    	
UnicodeVocabulary
    : '\u0003'..'\uFFFE'
    ;
COMMENT
    :   '/*' ( options {greedy=false;} : . )* '*/' {$channel=HIDDEN;}
    ;


LINE_COMMENT
    : '//' ~('\n'|'\r')* '\r'? '\n' {$channel=HIDDEN;}
    ;

// ignore #line info for now
LINE_COMMAND 
    : '#' ~('\n'|'\r')* '\r'? '\n' {$channel=HIDDEN;}
    ;
