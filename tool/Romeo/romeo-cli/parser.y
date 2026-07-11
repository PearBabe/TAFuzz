/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2025)

Didier.Lime@ec-nantes.fr

This software is a computer program whose purpose is to perform
parametric model checking on timed and hybrid systems.

This software is governed by the CeCILL license under French law and
abiding by the rules of distribution of free software.  You can  use, 
modify and/ or redistribute the software under the terms of the CeCILL
license as circulated by CEA, CNRS and INRIA at the following URL
"http://www.cecill.info". 

As a counterpart to the access to the source code and  rights to copy,
modify and redistribute granted by the license, users are provided only
with a limited warranty  and the software's author,  the holder of the
economic rights,  and the successive licensors  have only  limited
liability. 

In this respect, the user's attention is drawn to the risks associated
with loading,  using,  modifying and/or developing or reproducing the
software by the user in light of its specific status of free software,
that may mean  that it is complicated to manipulate,  and  that  also
therefore means  that it is reserved for developers  and  experienced
professionals having in-depth computer knowledge. Users are therefore
encouraged to load and test the software's suitability as regards their
requirements in conditions enabling the security of their systems and/or 
data to be ensured and,  more generally, to use and operate it in the 
same conditions as regards security. 

The fact that you are presently reading this means that you have had
knowledge of the CeCILL license and that you accept its terms. */

%{
#include <iostream>
#include <sstream>
#include <climits>
#include <cstdlib>
#include <string>
#include <vector>
#include <map>
#include <set>
//#include <typeinfo>

#include <parser_data.hh>

#include <expression.hh>
#include <instruction.hh>
#include <lexpression.hh>
#include <sexpression.hh>
#include <access_expression.hh>
#include <lconstraint.hh>
#include <rvalue.hh>
#include <valuation.hh>
#include <type.hh>
#include <type_list.hh>
#include <variable.hh>
#include <function.hh>

#include <cts.hh>
#include <time_interval.hh>

#include <properties.hh>
#include <control_reach.hh>
#include <backward_mincost.hh>

#include <dproperty.hh>

#include <job.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;

extern ParserData* pdata;
extern TypeList _romeo_types;

int yylex();
void yyerror(const char*);

#define YYERROR_VERBOSE 1
#define YYDEBUG 1 

union tpart_type
{
    char* str;
    const GenericExpression* expr;
};

map<string,tpart_type> tparts;
map<string,string> options;

extern int yylineno;
extern char* yytext;

%}

//%define lr.type lalr
%define parse.trace 
%define parse.lac full
%define parse.error detailed
//%glr-parser

%defines

%union{
	int64_t val;
	int32_t smallval;
	char * str;
    const GenericExpression* expr;
    const LExpression* lexpr;
    const LConstraint* bexpr;
    const Instruction* instr;
    const Property* prop;
    const TimeInterval* time;
    const Type* type;
    const Transition* tr;
    instruction::Block* block;
    const Function* funct;
    std::pair<const Transition*, const LExpression*>* trf;
    std::vector<std::pair<const Transition*, const LExpression*>*>* trfseq;
    std::vector<std::pair<const Type*, std::string> >* lfield;
    std::vector<const Expression*>* exprl;
    std::vector<const Type*>* typel;
    std::pair<const Type*, std::string>* field;
    std::pair<const GenericExpression*, const Property*>* prop2;
    std::list<int32_t>* lsmallval;
    std::list<RValue>* lrv;
    std::vector<std::string>* lstr;
}

%token<val> LOG
%token<val> TRANS
%token<val> PARAMETERS
%token<str> SPARAM
%token<str> IDENTIFIER
%token<str> TYPE
%token<val> MAX
%token<val> MIN
%token<val> NUMBER
%token<val> CHECK
%token<val> WITH
%token<val> SIMULATE
%token<val> RETIME
%token<val> GRAPH
%token<val> INFTY
%token<val> TRUE
%token<val> FALSE
%token<val> BOUNDED
%token<val> DEADLOCK
%token<val> INITIALLY
%token<val> STRUCT
%token<val> ENUM
%token<val> TYPEDEF
%token<val> CONST
%token<val> RETURN
%token<val> DO
%token<val> WHEN
%token<val> SPEED
%token<val> ALLOW
%token<val> INTERMEDIATE
%token<val> PRIORITY
%token<val> WHILE
%token<val> FOR
%token<val> FORALL
%token<val> EXISTS
%token<val> IF
%token<val> ELSE
%token<val> EQ
%token<val> NEQ
%token<val> LEQ
%token<val> GEQ
%token<val> INC
%token<val> DEC
%token<val> BREAK
%token<val> CONTINUE
%token<val> MINVAL
%token<val> MAXVAL
%token<val> MINCLOCK
%token<val> MAXCLOCK
%token<val> BITNOT
%token<val> BITANDREF
%token<val> BITOR
%token<val> SHIFTL
%token<val> SHIFTR
%token<val> MINCOST
%token<val> COST
%token<val> COST_RATE
%token<val> COST_HEURISTIC
%token<val> CONTROL
%token<val> SCONTROL
%token<str> PTOP
%token<str> AE
%token<str> U

%precedence PTOP LEF LGEF MINCOST CONTROL SCONTROL

%nonassoc LEADSTO

%left ','
%nonassoc LEQ EQ GEQ NEQ '<' '>'

%left IMPLY
%left OR
%left AND
%precedence NOT
%nonassoc SHIFTL SHIFTR
%left BITANDREF BITOR
%precedence BITNOT
%left '+' '-' 
%left '*' '/' '%'
%left ROMEO_UMINUS

%type<time> Interval
%type<time> PropInterval
%type<val> Constness 
%type<val> PropLeftBound 
%type<val> LeftBound 
%type<val> RightBound 
%type<val> OptVal 
%type<val> OptClock 
%type<expr> Property
%type<prop> TemporalProperty
%type<expr> MarkingProperty
%type<prop> StepLimit
%type<prop> LimitCost
%type<val> LimitOp
%type<prop2> PropertyWithCost
%type<expr> RightValue
%type<lrv> ListRightValues
%type<expr> LeftValue
%type<expr> FunctionC
%type<expr> OptCond
%type<prop> OptInvariant
%type<trfseq> TransitionSequence
%type<tr> TransitionDecl
%type<trfseq> NonEmptyTSequence
%type<trf> TransitionFiring
%type<lexpr> FiringConstraint
%type<lfield> FieldList
%type<lstr> StringList
%type<field> FieldDecl
%type<funct> Function
%type<exprl> ExpressionList
%type<exprl> NonEmptyExpressionList
%type<typel> ArgsList
%type<type> ArgDecl
%type<type> NonArrayType
%type<type> Type
%type<smallval> ArrayDim
%type<lsmallval> ArrayDims

%type<instr> Instruction
%type<instr> Assign
%type<instr> AssignList
%type<instr> ConstInit
%type<instr> IfInstruction
%type<instr> SemicolonInstruction
%type<instr> SemicolonOtherInstruction
%type<instr> NoSemicolonInstruction
%type<block> BlockInstruction
%type<instr> InitList
%type<instr> InitItem


%start Input
%%

Input:
    DefList System { pdata->cts->find_constants(); } PropertyList
    ;

System:
    ParamConstraint InitVars TransitionList TimeCost 
    { 
    }
    ;

TimeCost:
    %empty                     { }
    | COST_RATE RightValue     { pdata->cts->cost = ParserData::enforce_le($2); }
    | COST_RATE RightValue COST_HEURISTIC RightValue 
    { 
        pdata->cts->cost = ParserData::enforce_le($2); 
        pdata->cts->cost_heuristic = ParserData::enforce_le($4); 
    }
    ;

BlockInstruction: 
    '{' '}'                   { $$ = new instruction::Block(yylineno); }
    | '{' { $<block>$ = pdata->new_block(); } InstructionList '}'   
    { 
        $$ = $<block>2; 
        pdata->pop_block();
    }
    ;


InstructionList:
    Instruction                     
    { 
        if (!$1->is_nop())
            pdata->current_block()->add_instruction($1); 
        else
            delete $1;
    }
    | InstructionList Instruction   
    { 
        if (!$2->is_nop())
            pdata->current_block()->add_instruction($2); 
        else
            delete $2;
    }
    ;


Instruction:
    SemicolonInstruction ';'        { $$ = $1; }
    | SemicolonOtherInstruction ';'   { $$ = $1; }
    | NoSemicolonInstruction        { $$ = $1; }
    ;

SemicolonInstruction:
    %empty          { $$ = new instruction::Nop(); }
    | FunctionC     { $$ = ParserData::enforce_instr($1); }
    | LeftValue INC { 
        const lexpression::AccessExpression* op = ParserData::enforce_access($1);
        $$ = new instruction::Assignment(*op, *new lexpression::Addition(*new lexpression::RLValue(*static_cast<const lexpression::AccessExpression*>(op->copy(*pdata->cts)), yylineno),*new lexpression::Litteral(1, yylineno), yylineno), yylineno); 
    }
    | LeftValue DEC 
    { 
        const lexpression::AccessExpression* op = ParserData::enforce_access($1);
        $$ = new instruction::Assignment(*op, *new lexpression::Subtraction(*new lexpression::RLValue(*static_cast<const lexpression::AccessExpression*>(op->copy(*pdata->cts)), yylineno),*new lexpression::Litteral(1, yylineno), yylineno), yylineno); 
    }
    | AssignList    { $$ = $1; }
    | Type { pdata->current_type = $1; } InitList
    { 
        $$ = $3;
    }
    | TypeDef { $$ = new instruction::Nop(); }    
    | ConstInit { $$ = $1; }
    ;
    
ConstInit:
    CONST { pdata->constness = true; } Type { pdata->current_type = $3; } InitList
    { 
        $$ = $5;
        pdata->constness = false;
    }
    ;

AssignList:
    Assign                  { $$ = $1; }
    | AssignList ',' Assign { $$ = new instruction::Comma(*$1, *$3, yylineno); }
    ;

Assign:
    LeftValue '=' RightValue
    { 
        const LExpression* r = ParserData::enforce_le($3);
        if (!$1->is_access())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": expression cannot be assigned to: " << *$1 <<  endl;
            exit(1);
        }
        const lexpression::AccessExpression* l = static_cast<const lexpression::AccessExpression*>($1);
        const Type& t = l->access_type();
        const Type* t2 = nullptr;

        if ($3->is_rvalue())
        {
            const lexpression::Litteral* lit = static_cast<const lexpression::Litteral*>($3);
            RValue rv = lit->get_value();

            if (rv.get_type().is_raw()) 
            {
                const size_t tsize = t.size();
                byte* raw = new byte[tsize];
                list<const Type*> L = t.split();
                list<RValue> R = rv.split();

                if (L.size() != R.size())
                {
                    cerr << error_tag(color_output) << "Line " << yylineno << ": incompatible constant array or field assignment to " << *$1 << endl;
                    exit(1);
                }

                size_t o = 0;
                auto i = R.begin();
                for (auto x: L)
                {
                    x->set(raw + o, *i); 
                    o += x->size();
                    i++;
                }


                r = new lexpression::Litteral(RValue(t, raw), yylineno);
            } else {
                t2 = &rv.get_type();
            }
        } else if ($3->is_access()) {
            t2 = &static_cast<const lexpression::AccessExpression*>($3)->access_type();
        } else if ($3->is_rlvalue()) {
            t2 = &static_cast<const lexpression::RLValue*>($3)->get_type();
        }
                
        if (t2 != nullptr && (!t.is_numeric() || !t2->is_numeric()) && t2->id != t.id)
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": incompatible types in assignment: " << t.to_string() << " and " << t2->to_string() << endl;
            exit(1);
        }


        $$ = new instruction::Assignment(*ParserData::enforce_access($1), *r, yylineno); 
    }
    ;

SemicolonOtherInstruction:
    RETURN RightValue
    {
        $$ = new instruction::Return(*ParserData::enforce_le($2), yylineno);
    }
    | DO BlockInstruction WHILE '(' Property ')'
    {
        $$ = new instruction::DoWhile(*ParserData::enforce_lc($5), *new instruction::LoopBlock(*$2), yylineno);
    } 
    | LOG RightValue
    {
        $$ = new instruction::Log(*ParserData::enforce_le($2), yylineno);
    }
    ;

InitList:
    InitItem                    { $$ = $1; }
    | InitList ',' InitItem     
    { 
        if ($3->is_nop()) 
            $$ = $1;
        else
            $$ = new instruction::Comma(*$1, *$3, yylineno);
    }
    ;

InitItem:
    IDENTIFIER                   
    { 
        if (pdata->current_type->is_reference())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": Cannot use references outside of functions: " << $1 << endl;
            exit(1);
        }

        if (pdata->constness)
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": Constant " << $1 << " must be initialized" << endl;
            exit(1);
        }

        pdata->cts->add_variable(string($1),*pdata->current_type, false, false, 0, 0, pdata->current_block(), false, pdata->top_level()); 
        $$ = new instruction::Nop(); 
    
        free($1);
    }
    | IDENTIFIER '=' RightValue  
    { 
        const LExpression* r = nullptr;
        const Type& t = *pdata->current_type;
        const Type* t2 = nullptr;

        if (t.is_reference())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": Cannot use references outside of functions: " << $1 << endl;
            exit(1);
        }

        if ($3->is_rvalue())
        {
            const lexpression::Litteral* lit =  static_cast<const lexpression::Litteral*>($3);
            RValue rv = lit->get_value();
            if (rv.get_type().is_raw()) 
            {
                const size_t tsize = t.size();
                byte* raw = new byte[tsize];
                list<const Type*> L = t.split();
                list<RValue> R = rv.split();

                if (L.size() != R.size())
                {
                    cerr << error_tag(color_output) << "Line " << yylineno << ": incompatible constant array or field initialisation of " << *$1 << endl;
                    exit(1);
                }

                size_t o = 0;
                auto i = R.begin();
                for (auto x: L)
                {
                    x->set(raw + o, *i); 
                    o += x->size();
                    i++;
                }

                r = new lexpression::Litteral(RValue(t, raw), yylineno);
            } else {
                t2 = &rv.get_type();
            }
        } else if ($3->is_access()) {
            t2 = &static_cast<const lexpression::AccessExpression*>($3)->access_type();
        } else if ($3->is_rlvalue()) {
            t2 = &static_cast<const lexpression::RLValue*>($3)->get_type();
        }
            
        if (t2 != nullptr && (!t.is_numeric() || !t2->is_numeric()) && t2->id != t.id)
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": incompatible types in initialisation: " << t.to_string() << " and " << t2->to_string() << endl;
            exit(1);
        }

        if (r == nullptr)
        {
            r = $3->is_rlvalue() && pdata->current_type->is_reference() ? static_cast<const lexpression::RLValue*>($3)->access_expr() : ParserData::enforce_le($3);
            if ($3->is_rlvalue() && pdata->current_type->is_reference())
            {
                delete $3;
            } 
        }

        const bool c  = pdata->constness;
        const bool st = c && r->is_static();
        const size_t prev_size = pdata->cts->static_consts.vbyte_size() * sizeof(byte);
                
        pdata->cts->add_variable(string($1),*pdata->current_type, c, st, 0, 0, pdata->current_block(), false, !c && pdata->top_level()); 
        
        if (st)
        {
            instruction::Initialisation I(*pdata->cts->last_added_variable(), *r, yylineno); 

            byte* backup = pdata->cts->statics;
            pdata->cts->statics = new byte[pdata->cts->static_consts.vbyte_size()];
            if (backup != nullptr)
            {
                memcpy(pdata->cts->statics, backup, prev_size);
                delete [] backup;
            }
            
            SExpression(&I).execute(nullptr, pdata->cts->statics);

            $$ = new instruction::Nop(); // No need to do the evaluation once again
        } else {
            $$ = new instruction::Initialisation(*pdata->cts->last_added_variable(), *r, yylineno); 
        }
        
        free($1);
    }
    ;

NoSemicolonInstruction:
    WHILE '(' Property ')' BlockInstruction 
    {
        // If we give directly $5 to While then a temp LoopBlock
        // will be created that will delete all instructions when deleted
        instruction::LoopBlock B(*$5);
        $$ = new instruction::While(*ParserData::enforce_lc($3), B, yylineno);
        B.clear();
        $5->clear(); // In order to delete it without deleting the instruction pointers
        delete $5;
    } 
    | IfInstruction { $$ = $1; }
    | FOR { $<block>$ = pdata->new_block(); } '(' SemicolonInstruction ';' Property ';' SemicolonInstruction ')' BlockInstruction
    {
        instruction::LoopBlock B(*$10);
        // Create a block around the for to properly scope the intialisation
        // e.g. for (int i=0...
        pdata->current_block()->add_instruction(new instruction::For(*$4,*$8,*ParserData::enforce_lc($6), B, yylineno));
        $$ = $<block>2;
        B.clear();
        $10->clear(); // In order to delete it without deleting the instruction pointers
        delete $10;
        pdata->pop_block();
    }
    | BlockInstruction { $$ = $1; }
    ;

IfInstruction:
    IF '(' Property ')' BlockInstruction
    {
        $$ = new instruction::If(*ParserData::enforce_lc($3), *$5, yylineno);
    }
    | IF '(' Property ')' BlockInstruction ELSE BlockInstruction
    {
        $$ = new instruction::IfElse(*ParserData::enforce_lc($3), *$5, *$7, yylineno);
    }
    | IF '(' Property ')' BlockInstruction ELSE IfInstruction
    {
        $$ = new instruction::IfElse(*ParserData::enforce_lc($3), *$5, *$7, yylineno);
    }
    ;

NonArrayType:
    TYPE  
    { 
        $$ = _romeo_types.lookup_type($1); 
        if ($$ == nullptr)
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": unknown type: " << $1 << endl;
            exit(1);
        }
        free($1);
    }
    | STRUCT '{' FieldList'}'
    {
        stringstream s;
        bool comma = false;
        s << "struct {";
        
        std::vector<std::pair<const Type*,std::string> >::iterator i;

        for (i=$3->begin(); i!=$3->end(); i++)
        {
            if (comma)
                s << ",";
            else
                comma = true;

            s << i->second << ":" << i->first->label;
        }
        s << "}";

        $$ = _romeo_types.lookup_type(s.str());
        if ($$ == nullptr)
        {
            Record* R = new Record(_romeo_types.ntypes(), s.str());
            for (i=$3->begin(); i!=$3->end(); i++)
                R->add_field(i->second, *i->first);
            _romeo_types.add_type(R);
            $$ = R;
        }
        delete $3;
    }
    | ENUM '{' StringList '}'
    {
        stringstream st;
        st << "#romeo_enum_";
        for (auto i: *$3)
        {
            st << i << "_";
        }
        
        const string& s = st.str();

        $$ = _romeo_types.lookup_type(s);
        if ($$ == nullptr)
        {
            $$ = new Enum(_romeo_types.ntypes(), s, *$3); 
            _romeo_types.add_type($$);
        }

        uint8_t k = 0;
        for (auto i: *$3)
        {
            pdata->cts->add_variable(i,*$$, true, true, 0, 0, nullptr, false, false); 
            instruction::Initialisation instr(*pdata->cts->last_added_variable(), *new lexpression::Litteral(RValue(*$$, k, ((byte) 1)), yylineno), yylineno);
            pdata->cts->statics = static_cast<byte*>(realloc(pdata->cts->statics, pdata->cts->static_consts.vbyte_size() * sizeof(byte)));
            SExpression(&instr).execute(nullptr, pdata->cts->statics);
            k++;
        }

        delete $3;
    }
    | Type BITANDREF
    { 
        if ($1->is_reference())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": cannot declare a reference on a reference" << endl;
            exit(1);
        }
        if (pdata->current_block() == nullptr)
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": cannot declare reference at top-level" << endl;
            exit(1);
        }
        string s = "(" +  $1->label + ")&";
        $$ = _romeo_types.lookup_type(s);
        if ($$ == nullptr)
        {
            $$ = new Reference(_romeo_types.ntypes(), s, *$1); 
        }
    }
    ;

Type:
    NonArrayType
    {
        $$ = $1;
    }
    | NonArrayType ArrayDims 
    {
        const Type * inner_type = $1;

        for (auto n: *$2)
        {
            stringstream s;
            s << "(" << inner_type->label << ")[" << n << "]";
            const Type* lookedup_type = _romeo_types.lookup_type(s.str());
            if (lookedup_type == nullptr)
            {
                inner_type = new Array(_romeo_types.ntypes(),s.str(),n,*inner_type);
                _romeo_types.add_type(inner_type);
            } else {
                inner_type = lookedup_type;
            }
        }
        delete $2;
        $$ = inner_type;
    }
    ;


ArrayDim: 
    '[' RightValue ']' 
    {
        if (!$2->is_const())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": arrays must have a compile-time constant size" << endl;
            exit(1);
        } else {
            RValue x = SExpression($2).evaluate(nullptr, pdata->cts->statics);
            $$ = x.to_int();
        }
    }
    ;

ArrayDims:
    ArrayDim
    {
        // WARNING: here I assume arrays are indexed by 32 bits values 
        $$ = new list<int>(1, (int32_t) $1);
    }
    | ArrayDims ArrayDim
    {
        $1->push_front($2);
        $$ = $1;
    }
    ;

StringList:
    IDENTIFIER                { $$ = new std::vector<std::string>(1, $1); }
    | StringList ',' IDENTIFIER { $$ = $1; $1->push_back($3); }

FieldList:
    FieldDecl               { $$ = new std::vector<std::pair<const Type*,std::string> >(1,*$1); }
    | FieldList FieldDecl   { $$ = $1; $1->push_back(*$2); }
    ;

FieldDecl:
    Type IDENTIFIER ';' 
    { 
        $$ = new std::pair<const Type*,std::string>($1,$2);
        free($2);
    }
    ;

DefList:
    %empty
    | DefList Function { pdata->cts->add_function($2); }
    | DefList TypeDef ';'  { }
    | DefList ConstInit ';' { }
    ;

Function:
    Type IDENTIFIER '(' { pdata->new_block(); } ArgsList { pdata->last_var_id = ($5->size() > 0) ? pdata->cts->last_added_variable()->id: 0; }')' BlockInstruction   
    {
        // Add a block for parameters so they are not at top level
        $$ = new Function(0, $2, *pdata->cts, *$1, *$5, $8, ($5->size() > 0) ? pdata->last_var_id - ($5->size() - 1): 0);

        free($2);
        pdata->pop_block();
    }
    ;

TypeDef:
    TYPEDEF Type IDENTIFIER
    {
        Type* t = $2->copy();
        t->label = $3;
        t->id = _romeo_types.ntypes();
        _romeo_types.add_type(t);
        free($3);
    }
    ;

ArgsList:
    %empty                      { $$ = new std::vector<const Type*>(); }
    | ArgDecl                   { $$ = new std::vector<const Type*>(1, $1); }
    | ArgsList ',' ArgDecl      { $$ = $1; $$->push_back($3); }
    ;

Constness:
    %empty  { $$ = false; }
    | CONST { $$ = true;  }
    ;

ArgDecl:
    Constness Type IDENTIFIER
    { 
        pdata->cts->add_variable(string($3),*$2, $1, false, 0, 0, pdata->current_block(), false, false); 
        $$ = $2;
        free($3);
    }
    ;

InitVars:
    INITIALLY BlockInstruction { pdata->cts->initv=$2; pdata->push_block($2); }
    ;

TransitionList:
    %empty
    | TransitionList TransitionDecl 
    { 
        const Transition* t = pdata->cts->lookup_transition($2->label);
        if (t == nullptr)
        {
            pdata->cts->add_transition(*$2); 
            delete $2; 
        } else {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": Transition " << $2->label << " multiply-defined" << endl;
            exit(1);
        }

    }
    | TransitionList TransitionFor 
    { 
        for (auto t: pdata->tf_frames.back().trans)
        {
            // Instantiate all transitions and store in previous layer
            // That layer exists by construction
            for (int i = pdata->tf_frames.back().lbound; i <= pdata->tf_frames.back().rbound; i++)
            {
                const Transition* x = t->instantiate(*pdata->cts, pdata->tf_frames.size() - 1, i);
                const Transition* y = pdata->cts->lookup_transition(x->label);
                if (y == nullptr)
                {
                    byte V[pdata->cts->variables.vbyte_size()];
                    memset(V, 0, pdata->cts->variables.vbyte_size()); // value-initialisation -> 0
                    RValue g = x->guard.evaluate(V, pdata->cts->statics);
                    if (g.is_unknown() || g.to_int())
                    {
                        // Add transition only if its guard is not trivially false
                        // Typically when $1 == $2 for two nested structure for loops
                        // and the guard has $1 != $2
                        pdata->cts->add_transition(*x); 
                    }
                    delete x;
                } else {
                    cerr << error_tag(color_output) << "Line " << yylineno-1 << ": Transition " << x->label << " multiply-defined" << endl;
                    exit(1);
                }
            }
            delete t;
        }
        pdata->tf_frames.pop_back();
    }
    ;

TransitionFor:
    FOR SPARAM '=' RightValue ',' RightValue { pdata->tf_frames.push_back(TFFrame($2, SExpression($4).evaluate(nullptr, pdata->cts->statics).to_int(), SExpression($6).evaluate(nullptr, pdata->cts->statics).to_int())); } '{' TransitionListFor '}'
    {
    }
    ;

TransitionListFor:
    %empty
    | TransitionListFor TransitionDecl { pdata->tf_frames.back().trans.push_back($2); }
    | TransitionListFor TransitionFor  
    { 
        for (auto t: pdata->tf_frames.back().trans)
        {
            // Instantiate all transitions and store in previous layer
            // That layer exists by construction
            for (int i = pdata->tf_frames.back().lbound; i <= pdata->tf_frames.back().rbound; i++)
            {
                const Transition* x = t->instantiate(*pdata->cts, pdata->tf_frames.size() - 1, i);
                (--(--pdata->tf_frames.end()))->trans.push_back(x); // Here instantiate
            }
            delete t;
        }
        pdata->tf_frames.pop_back();
    }
    ;

PropertyList:
    PropertyDecl // No copy for only one property
    // We copy _before_ parsing properties because they may add their own parameters
    | PropertyList { pdata->init_new_cts_copy(); } PropertyDecl
    ;

TransitionDecl:
    TRANS TOptions IDENTIFIER Interval WHEN '(' Property ')' BlockInstruction
    {
        const romeo::Property* a;
        const Instruction* r;
        const LExpression* s;
        const LExpression* p;
        const LExpression* c;
        unsigned ctrl = CTRL_CONTROLLABLE;

        if (tparts.find("speed") != tparts.end()) {
            s = ParserData::enforce_le(tparts["speed"].expr);
        } else {
            s = new lexpression::Litteral(1, yylineno);
        }

        if (tparts.find("cost") != tparts.end()) {
            c = ParserData::enforce_le(tparts["cost"].expr);
        } else {
            c = nullptr;
        }

        if (tparts.find("priority") != tparts.end()) {
            p = ParserData::enforce_le(tparts["priority"].expr);
        } else {
            p = nullptr;
        }

        if (tparts.find("intermediate") != tparts.end()) {
            r = static_cast<const Instruction*>(tparts["intermediate"].expr);
        } else {
            r = new instruction::Nop();
        }

        if (tparts.find("allow") != tparts.end()) {
            a = ParserData::enforce_property(tparts["allow"].expr);
        } else {
            a = new lconstraint::True(yylineno);
        }

        if (tparts.find("control") != tparts.end()) {
            string cs = tparts["control"].str;
            if (cs.find('u') != string::npos) 
            {
                ctrl = ctrl & ~CTRL_CONTROLLABLE;
            }

            if (cs.find('d') != string::npos) 
            {
                ctrl = ctrl | CTRL_DELAYED;
            }

            if (cs.find('f') != string::npos) 
            {
                ctrl = ctrl | CTRL_FORCED;
            }
            free(tparts["control"].str);
        }

        if (pdata->cts->lookup_variable_scoped($3, pdata->blocks()))
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": Cannot create transition " << $3 << ": a variable with the same name already exists." << endl;
            exit(1);
        }

        // The ID is unique here, but not with instantiation later!
        // This will be fixed in cts::add_transition
        $$ = new Transition(pdata->ntrans, $3, ParserData::enforce_simple($7), $9, $4, r, s, p, c, false, ctrl, a);
        pdata->ntrans++;
        
        tparts.clear();
        free($3);
    }
    ;

PropertyDecl:
    CHECK OptionsList Property AdditionalConstraints
    { 
        pdata->jobs.push_back(new PropertyJob(pdata->jobs.size(),ParserData::enforce_property($3),*pdata->cts,options)); 
        options.clear();
    }
    | SIMULATE OptionsList TransitionSequence AdditionalConstraints
    {
        pdata->jobs.push_back(new SimulationJob(pdata->jobs.size(),*$3,*pdata->cts,options)); 
        delete $3;
        options.clear();
    }
    | RETIME OptionsList TransitionSequence AdditionalConstraints
    {
        pdata->jobs.push_back(new RetimeJob(pdata->jobs.size(),*$3,*pdata->cts,options)); 
        delete $3;
        options.clear();
    }
    | GRAPH OptionsList AdditionalConstraints
    {
        pdata->jobs.push_back(new GraphJob(pdata->jobs.size(),*pdata->cts,options)); 
        options.clear();
    }
    ;

AdditionalConstraints:
    %empty
    | AdditionalConstraints AdditionalConstraint
    ;

AdditionalConstraint:
    WITH '(' Property ')'   
    { 
        const Property* p = ParserData::enforce_property($3);
        if (!pdata->cts->initp.is_null())
        {
            pdata->cts->initp = new property::And(*static_cast<const Property*>(pdata->cts->initp.get_expr()), *p, yylineno); 
        } else {
            pdata->cts->initp = p;
        }
    }
    | WITH OptionsList
    ;

TransitionSequence:
    %empty              { $$ = new vector<pair<const Transition*,const LExpression*>*>(); }
    | NonEmptyTSequence { $$ = $1; }
    ;

NonEmptyTSequence:
    TransitionFiring                          { $$ = new vector<pair<const Transition*,const LExpression*>*>(1,$1); } 
    | NonEmptyTSequence ',' TransitionFiring  { $1->push_back($3); $$ = $1; }
    ;

TransitionFiring:
    IDENTIFIER FiringConstraint     
    { 
        const Transition* t = pdata->cts->lookup_transition(string($1));
        if (t == nullptr)
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": Unknown transition in simulation firing sequence: "<< $1 << endl;
            exit(1);
        } else {
            $$ = new pair<const Transition*, const LExpression*>(t,$2); 
        }

        free($1);
    }
    ;

FiringConstraint:
    %empty              { $$ = nullptr; }
    | '@' RightValue    { $$ = ParserData::enforce_le($2); }
    ; 

OptionsList:
    %empty
    | '[' Options ']'
    ;

Options:
    Option
    | Options ',' Option
    ;

Option:
    IDENTIFIER                  { options[string($1)] = ""; free($1); }
    | IDENTIFIER '=' IDENTIFIER { options[string($1)] = string($3); free($1); free($3); }
    | IDENTIFIER '=' NUMBER     { stringstream s; s << $3; options[string($1)] = s.str(); free($1); }
    ;

TOptions:
    %empty
    | '[' TransitionParts ']'
    ;    

TransitionParts:
    TPart                   
    | TransitionParts ',' TPart
    ;

TPart:
    SPEED '=' RightValue { tparts["speed"].expr = $3; }
    | PRIORITY '=' RightValue { tparts["priority"].expr = $3; }
    | INTERMEDIATE BlockInstruction { tparts["intermediate"].expr = $2; }
    | COST '=' RightValue { tparts["cost"].expr = $3; }
    | ALLOW '=' RightValue { tparts["allow"].expr = $3; }
    | CONTROL '=' IDENTIFIER { tparts["control"].str = $3; }
    ;
  
ParamConstraint:
    %empty
    | PARAMETERS Property 
    { 
        const Property* p = ParserData::enforce_property($2);
        pdata->cts->initp = p; 
    }
    ;

Interval:
    %empty                                           { $$ = new TimeInterval(new lexpression::Litteral(0, yylineno), new lexpression::Litteral(INT_MAX, yylineno), 0, 1, true); }
    | LeftBound RightValue ',' RightValue RightBound { $$ = new TimeInterval(ParserData::enforce_le($2), ParserData::enforce_le($4), $1, $5, false); }
    | LeftBound RightValue ',' INFTY RightBound      { $$ = new TimeInterval(ParserData::enforce_le($2), new lexpression::Litteral(INT_MAX, yylineno), $1, 1, true); }
    ;

PropInterval:
    %empty                                           { $$ = new TimeInterval(new lexpression::Litteral(0, yylineno), new lexpression::Litteral(INT_MAX, yylineno), 0, 1, true); }
    | PropLeftBound RightValue ',' RightValue RightBound { $$ = new TimeInterval(ParserData::enforce_le($2), ParserData::enforce_le($4), $1, $5, false); }
    | PropLeftBound RightValue ',' INFTY RightBound      { $$ = new TimeInterval(ParserData::enforce_le($2), new lexpression::Litteral(INT_MAX, yylineno), $1, 1, true); }
    ;

PropLeftBound:
    '['     { $$ = 0; }
    | '@' '['   { $$ = 0; }
    | '@' '('   { $$ = 1; }
    ;

LeftBound:
    '['     { $$ = 0; }
    | '('   { $$ = 1; }
    ;

RightBound:
    ']'     { $$ = 0; }
    | ')'   { $$ = 1; }
    ;

Property:
    MarkingProperty             { $$ = $1; }
    | TemporalProperty          { $$ = $1; }
    | NOT Property              { $$ = ParserData::enforce_property($2)->negation(*pdata->cts); }
    | Property AND Property     { $$ = new property::And(*ParserData::enforce_property($1),*ParserData::enforce_property($3), yylineno); }
    | Property OR Property      { $$ = new property::Or(*ParserData::enforce_property($1),*ParserData::enforce_property($3), yylineno); }
    | Property IMPLY Property   { $$ = new property::Or(*ParserData::enforce_property($1)->negation(*pdata->cts),*ParserData::enforce_property($3), yylineno); }
    ;

MarkingProperty:
    RightValue                  { $$ = ParserData::enforce_simple($1); }
    | BOUNDED '(' NUMBER ')'    { $$ = new property::Bounded($3, yylineno); }
    | DEADLOCK                  { $$ = new property::Deadlock(yylineno); }
    ;

PropertyWithCost:
    Property                    { $$ = new pair<const GenericExpression*, const Property*>($1, nullptr); }
    | Property AND LimitCost    { $$ = new pair<const GenericExpression*, const Property*>($1, $3); }
    | LimitCost AND Property    { $$ = new pair<const GenericExpression*, const Property*>($3, $1); }
    ;

TemporalProperty:
    PTOP PropInterval StepLimit '(' PropertyWithCost ')'
    { 
        const romeo::Property * s = $3;
        const romeo::Property * p = ParserData::enforce_simple($5->first);
        const romeo::TimeInterval * I = $2;
        const string op = $1;
        const romeo::property::CostLimit* cl = static_cast<const romeo::property::CostLimit*>($5->second);

        if (s == nullptr)
        {
            s = new lconstraint::True(yylineno);
        }
            
        if (cl != nullptr && op != "EF") 
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": cost limit not implemented for " << op << "." << endl; 
            exit(1);
        }

        if (cl != nullptr && !I->unconstrained()) 
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": Cannot use both cost limit and time interval." << endl; 
            exit(1);
        }

        if (options.count("zones"))
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": cost limit not implemented for zones."<< endl; 
            exit(1);
        }

        if (I->unconstrained())
        {
            delete I;
            if (op == "AF") 
            {
                $$ = new property::AU(s, p, yylineno);
            } else if (op == "EF") {

                if (options.count("hpa"))
                {
                    $$ = new property::HPEU(s, p, yylineno); 
                } else {       
                    $$ = new property::EU(s, p, cl, yylineno); 
                }
            } else if (op == "AG") {
                //const romeo::Property* n = p->negation(*pdata->cts);
                //$$ = new property::Not(*new property::EU(s, n, yylineno), yylineno);
                $$ = new property::AG(p, yylineno); 
            } else if (op == "EG") {
                const romeo::Property* n = p->negation(*pdata->cts);
                $$ = new property::Not(*new property::AU(s, n, yylineno), yylineno);
            } else {
                cerr << error_tag(color_output) << "Unknown operator: " << op << endl;
                exit(1);
            }
        } else {
            if (op == "AF") 
            {
                $$ = new property::TAU(s, p, *I, yylineno); 
            } else if (string($1) == "EF") {
                $$ = new property::TEU(s, p, *I, yylineno); 
            } else if (string($1) == "AG") {
                const romeo::Property* n = p->negation(*pdata->cts);
                $$ = new property::Not(*new property::TEU(s, n, *I, yylineno), yylineno);
            } else if (string($1) == "EG") {
                const romeo::Property* n = p->negation(*pdata->cts);
                $$ = new property::Not(*new property::TAU(s, n, *I, yylineno), yylineno);
            } else {
                cerr << error_tag(color_output) << "Unknown operator: " << op << endl;
                exit(1);
            }
        }
    }
    | AE '(' Property ')' U PropInterval StepLimit '(' PropertyWithCost ')' 
    { 
        const string op = $1;
        const romeo::Property * p = ParserData::enforce_simple($3);
        const romeo::TimeInterval * I = $6;
        const romeo::Property * s = $7;
        const romeo::Property * q = ParserData::enforce_simple($9->first);
        const romeo::property::CostLimit* cl = static_cast<const romeo::property::CostLimit*>($9->second);

        if (s != nullptr)
        {
            p = new property::And(*p, *s, yylineno);
        }

        if (cl != nullptr && op != "E") 
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": cost limit not implemented for " << op << "U." << endl; 
            exit(1);
        }
        
        if (options.count("zones"))
        {
            cerr << error_tag(color_output) << "Line " << yylineno-1 << ": cost limit not implemented for zones."<< endl; 
            exit(1);
        }
        
        if (I->unconstrained())
        {
            delete I;
            if (op == "A") 
            {
                $$ = new property::AU(p, q, yylineno); 
            } else if (op == "E") {
                if (options.count("hpa"))
                {
                    $$ = new property::HPEU(p, q, yylineno); 
                } else {       
                    $$ = new property::EU(p, q, cl, yylineno); 
                }
            } else {
                cerr << error_tag(color_output) << "Unknown operator: " << op << endl;
                exit(1);
            }
        } else {
            if (op == "A") 
            {
                $$ = new property::TAU(p, q, *I, yylineno); 
            } else if (op == "E") {
                $$ = new property::TEU(p, q, *I, yylineno); 
            } else {
                cerr << error_tag(color_output) << "Unknown operator: " << op << endl;
                exit(1);
            }
        }
    }
    | LEF '(' Property ')'
    { 
        const romeo::Property * p = new lconstraint::True(yylineno);
        $$ = new property::EEU(p, ParserData::enforce_simple($3), yylineno); 
    }
    | LGEF '(' Property ')' WITH PTOP '(' Property ')'
    { 
        if (string($6) == "AG")
        {
            const romeo::Property * p = ParserData::enforce_simple($8);
            $$ = new property::LEU(p, ParserData::enforce_simple($3), yylineno); 
        } else {
            cerr << error_tag(color_output) << "LGEF: Expected AG after with." << endl;
            exit(1);
        }
    }
    | '(' Property ')' LEADSTO PropInterval StepLimit '(' Property ')'
    {
        const romeo::Property * s = $6;
        const romeo::Property * p = ParserData::enforce_simple($2);
        const romeo::Property * q = ParserData::enforce_simple($8);
        const romeo::TimeInterval * I = $5;
        if (s != nullptr)
        {
            q = new property::And(*q, *s, yylineno);
        }

        if (I->unconstrained())
        {
            $$ = new property::LT(p, q, yylineno);
        } else {
            $$ = new property::TLT(p, q, *I, yylineno);
        }
    }
    | OptVal RightValue OptCond OptInvariant
    {
        $$ = new DProperty(*new SDPValue(ParserData::enforce_simple($3), $1, ParserData::enforce_le($2), yylineno), $4);
    }
    | OptClock IDENTIFIER OptCond OptInvariant
    {
        const Transition* t = pdata->cts->lookup_transition(string($2));
        if (t != nullptr) {
            const Property* p = ParserData::enforce_simple($4);
            if (p->has_cost())
            {
                cerr << error_tag(color_output) << "Line " << yylineno << ": Cannot use cost limit when finding clock min/max value. " << endl;
                exit(1);
            } else {
                $$ = new DProperty(*new SDPClock(ParserData::enforce_simple($3), $1, t, yylineno), p);
            }
        } else {
            cerr << error_tag(color_output) << "OptClock: Unknown transition: " << $2 << endl;
            exit(1);
        }

        free($2);
    }
    | MINCOST '(' Property ')'
    {
        const romeo::Property* p = ParserData::enforce_simple($3);
        if (options.count("zones") && !pdata->cts->has_hybrid() && !pdata->cts->has_params() && (!options.count("cmode") || options["cmode"] == "timed"))
        {
            $$ = new property::BackwardMincost(new lconstraint::True(yylineno), p, yylineno);
        } else {
            $$ = new property::CostEU(new lconstraint::True(yylineno), p, yylineno);
        }
    }
    | MINCOST '(' Property ')' U '(' Property ')'
    {
        const romeo::Property* p = ParserData::enforce_simple($3);
        const romeo::Property* q = ParserData::enforce_simple($7);

        if (options.count("zones") && !pdata->cts->has_hybrid() && !pdata->cts->has_params() && (!options.count("cmode") || options["cmode"] == "timed"))
        {
            $$ = new property::BackwardMincost(p, q, yylineno);
        } else {
            $$ = new property::CostEU(p, q, yylineno);
        }
    }
    | CONTROL '(' Property ')'
    {
        if (!pdata->cts->has_cost())
        {
            $$ = new property::ControlReach(new lconstraint::True(yylineno), ParserData::enforce_simple($3), property::CONTROL_REACH, yylineno);
        } else {
            $$ = new property::ControlReach(new lconstraint::True(yylineno), ParserData::enforce_simple($3), property::CONTROL_OPTIMAL, yylineno);
        }
    }
    | CONTROL '(' Property ')' U '(' Property ')'
    {
        if (!pdata->cts->has_cost())
        {
            $$ = new property::ControlReach(ParserData::enforce_simple($3), ParserData::enforce_simple($7), property::CONTROL_REACH, yylineno);
        } else {
            $$ = new property::ControlReach(ParserData::enforce_simple($3), ParserData::enforce_simple($7), property::CONTROL_OPTIMAL, yylineno);
        }
    }
    | SCONTROL '(' Property ')'
    {
        Property* a = new property::Or(*ParserData::enforce_simple($3), *new property::SCBad(yylineno), yylineno);
        $$ = new property::ControlReach(new lconstraint::True(yylineno), a, property::CONTROL_SAFE, yylineno);
    }
    ; 

OptVal:
      MINVAL      { $$ = true; }
      | MAXVAL    { $$ = false; }
      ;

OptClock:
      MINCLOCK    { $$ = true; }
      | MAXCLOCK  { $$ = false; }
      ;

OptCond:
    %empty                 { $$ = new lconstraint::True(yylineno); }
    | WHEN '(' MarkingProperty ')' { $$ = $3; }
    ;      

OptInvariant:
    %empty                   { $$ = nullptr; }
    | WHILE '(' PropertyWithCost ')' 
    { 
        $$ = ParserData::enforce_property($3->first);
        if ($3->second != nullptr)
        {
            $$ = new property::And(*$$, *ParserData::enforce_property($3->second), yylineno);
        }
    }
    | WHILE '(' LimitCost ')' { $$ = $3; } 
    ;      

StepLimit:
    %empty           { $$ = nullptr; }
    | '#' LEQ NUMBER { $$ = new property::Steps($3, false, yylineno); }
    | '#' '<' NUMBER { $$ = new property::Steps($3, true, yylineno); }
    ;

LimitOp:
    LEQ     { $$ = 0; }
    | '<'   { $$ = 1; }
    ;

LimitCost:
    COST LimitOp RightValue 
    { 
        const LExpression* ub = ParserData::enforce_le($3);
        bool us = $2;

        if (ub != nullptr && ub->has_params())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << " : parameters forbidden in cost limit " << *ub << endl;
            exit(1);
        }

        $$ = new property::CostLimit(ub, us, yylineno); 
    }
    ;

RightValue:
    LeftValue                               { $$ = ($1->has_params() || $1->is_rvalue())? $1: new lexpression::RLValue(*ParserData::enforce_access($1), yylineno); }
    | NUMBER                                { $$ = new lexpression::Litteral($1, yylineno); } 
    | SPARAM                                
    { 
        int p = pdata->lookup_sparam($1); 
        if (p != -1)
        {
            $$ = new lexpression::SyntaxParameter(p, yylineno); 
        } else {
            cerr << error_tag(color_output) << "Line " << yylineno << ": Unknown static parameter: " << $1 << endl;
            exit(1);
        }
    } 
    | '(' Property ')'                      { $$ = $2; } 
    | MAX '(' RightValue ',' RightValue ')' { $$ = new lexpression::Max(*ParserData::enforce_numeric($3),*ParserData::enforce_numeric($5), yylineno); }
    | MIN '(' RightValue ',' RightValue ')' { $$ = new lexpression::Min(*ParserData::enforce_numeric($3),*ParserData::enforce_numeric($5), yylineno); }
    | RightValue '+' RightValue             { $$ = new lexpression::Addition(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue '-' RightValue             { $$ = new lexpression::Subtraction(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue '*' RightValue             { $$ = new lexpression::Multiplication(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue '/' RightValue             { $$ = new lexpression::Division(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue '%' RightValue             { $$ = new lexpression::Modulo(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | '-' RightValue %prec ROMEO_UMINUS     { $$ = new lexpression::Subtraction(*new lexpression::Litteral((value) 0, yylineno), *ParserData::enforce_numeric($2), yylineno); }
    | RightValue '<' RightValue             { $$ = new lconstraint::Less(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue LEQ RightValue             { $$ = new lconstraint::Leq(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue '>' RightValue             { $$ = new lconstraint::Greater(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue GEQ RightValue             { $$ = new lconstraint::Geq(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue EQ RightValue              { $$ = new lconstraint::Eq(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue NEQ RightValue             { $$ = new lconstraint::Neq(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue BITANDREF RightValue       { $$ = new lexpression::BitAnd(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue BITOR RightValue           { $$ = new lexpression::BitOr(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | BITNOT RightValue                     { $$ = new lexpression::BitNot(*ParserData::enforce_numeric($2), yylineno); } 
    | RightValue SHIFTL RightValue          { $$ = new lexpression::ShiftL(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | RightValue SHIFTR RightValue          { $$ = new lexpression::ShiftR(*ParserData::enforce_numeric($1),*ParserData::enforce_numeric($3), yylineno); } 
    | TRUE                                  { $$ = new lconstraint::True(yylineno); }
    | FALSE                                 { $$ = new lconstraint::False(yylineno); }
    | FunctionC                             { $$ = $1; }
    | '{' ListRightValues '}'               
    {
        // List is non-empty by construction
        // We encode Raw as
        // number of items in flattened list on 32 bits
        // individual ids of types
        // Raw data

        // First flatten all the rvalues so we have only numeric types
        list<RValue> flat;
        for (auto& x: *$2)
        {
            for (auto& y: x.split())
            {
                flat.push_back(y);
            }
        }

        
        size_t size = 0;
        size_t bsize = 0;
        for (auto v: flat)
        {
            bsize += v.get_type().size();
            size++;
        }
        
        const size_t header_size = (size + 1) * sizeof(uint32_t);
        byte* rv = new byte[header_size + bsize];

        *((uint32_t*) rv) = size;

        unsigned k = 0;
        unsigned i = 1;
        for (auto v: flat)
        {
            const Type& t = v.get_type();
            const unsigned ts = t.size();
            t.set(rv + header_size + k, v);
            *((uint32_t*) rv + i) = t.id; 
            i++;
            k += ts;
        }
        
        stringstream s;
        s << "Raw_" << (header_size + bsize);

        const Type* lookedup_type = _romeo_types.lookup_type(s.str());
        const Type* raw_type ;
        if (lookedup_type == nullptr)
        {
            raw_type = new Raw(_romeo_types.ntypes(), s.str(), header_size + bsize);
            _romeo_types.add_type(raw_type);
        } else {
            raw_type = lookedup_type;
        }   
        
        $$ = new lexpression::Litteral(RValue(*raw_type, rv), yylineno);
    }
    | FORALL IDENTIFIER
    {
        $<block>$ = pdata->new_block();
        pdata->cts->add_variable(string($2),*_romeo_types.lookup_type("uint32_t"), false, false, 0, 0, pdata->current_block(), true, false); 
    } '=' RightValue ',' RightValue ':' '(' Property ')'
    {
        const Variable* i = pdata->cts->lookup_variable_scoped($2, pdata->blocks());
        lconstraint::Forall* fa = new lconstraint::Forall(*new lexpression::LValue(*i, yylineno), *ParserData::enforce_le($5), *ParserData::enforce_le($7), *ParserData::enforce_simple($10), yylineno);
        pdata->current_block()->add_instruction(fa);
        pdata->pop_block();
        $$ = fa;
    } 
    | EXISTS IDENTIFIER
    {
        $<block>$ = pdata->new_block();
        pdata->cts->add_variable(string($2),*_romeo_types.lookup_type("uint32_t"), false, false, 0, 0, pdata->current_block(), true, false); 
    } '=' RightValue ',' RightValue ':' '(' Property ')'
    {
        const Variable* i = pdata->cts->lookup_variable_scoped($2, pdata->blocks());
        lconstraint::Exists* fa = new lconstraint::Exists(*new lexpression::LValue(*i, yylineno), *ParserData::enforce_le($5), *ParserData::enforce_le($7), *ParserData::enforce_simple($10), yylineno);
        pdata->current_block()->add_instruction(fa);
        pdata->pop_block();
        $$ = fa;
    } 
    ;

ListRightValues:
    RightValue 
    { 
        if (!$1->is_const())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": litteral array/struct elements should be constant." << endl;
            exit(1);
        }

        if ($1->is_rvalue())
        {
            $$ = new list<RValue>(1, static_cast<const lexpression::Litteral*>($1)->get_value());
        } else {
            $$ = new list<RValue>(1, SExpression(ParserData::enforce_le($1)).evaluate(nullptr, pdata->cts->statics)); 
        }
    }
    | RightValue ',' ListRightValues
    {
        if (!$1->is_const())
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": litteral array/struct elements should be constant." << endl;
            exit(1);
        }
        
        if ($1->is_rvalue())
        {
            $3->push_front(static_cast<const lexpression::Litteral*>($1)->get_value());
        } else {
            $3->push_front(SExpression(ParserData::enforce_le($1)).evaluate(nullptr, pdata->cts->statics));
        }

        $$ = $3;
    }

LeftValue:
    IDENTIFIER                 
    { 
        const Transition* t = pdata->cts->lookup_transition(string($1));
        if (t != nullptr) {
            $$ = new lexpression::ClockVariable(t, yylineno);
        } else {
            const Variable* v = pdata->cts->lookup_variable_scoped($1, pdata->blocks());
            if (v == nullptr)
            {
                // We have not found the variable
                // so we will check if it is is a global constant
                
                // Recreate of list of active blocks with only  
                // nullptr for top-level constants
                list<instruction::Block*> ab;
                ab.push_back(nullptr);
                //ab.push_back(*(++pdata->blocks()->begin())); // add the second element
                
                // Look-up
                v = pdata->cts->lookup_variable_scoped($1, &ab);
            }

            if (v != nullptr) {
                if (!v->get_type().is_reference())
                {
                    if (v->is_static() && v->get_type().is_numeric())
                    {
                        lexpression::RLValue J(*new lexpression::LValue(*v, yylineno), yylineno);
                        $$ = new lexpression::Litteral(SExpression(&J).evaluate(nullptr, pdata->cts->statics), yylineno);
                    } else {
                        $$ = new lexpression::LValue(*v, yylineno);
                    }
                } else {
                    $$ = new lexpression::ReferenceAccess(*v, yylineno);
                }
            } else {
               const Parameter* p = pdata->cts->lookup_parameter($1); 
               if (p == nullptr) {
                   p = pdata->cts->add_parameter(Parameter(pdata->cts->nparams(),$1));
               }
               $$ = new lexpression::Parameter(*p, yylineno); 
            } 
        }
        free($1);
    }
    | LeftValue '[' RightValue ']'
    {
        $$ = new lexpression::SubscriptAccess(*ParserData::enforce_access($1), ParserData::enforce_le($3), yylineno);
    }
    | LeftValue '.' IDENTIFIER
    {
        const lexpression::AccessExpression& e =  *ParserData::enforce_access($1);
        const Field* f = e.access_type().lookup_field($3);
        if (f == nullptr)
        {   
            cerr << error_tag(color_output) << "Line " << yylineno << ": Unknown record field: " << $3 << endl;
            exit(1);
        } else {
            $$ = new lexpression::FieldAccess(e, f->id, yylineno);
        }
        free($3);
    }
    ;

FunctionC:
    IDENTIFIER '(' ExpressionList ')'
    {
        std::vector<const Expression*>* args = $3;
        const Function* f = pdata->cts->lookup_function($1);
        if (f == nullptr)
        {
            cerr << error_tag(color_output) << "Line " << yylineno << ": Unknown function: " << $1 << endl;
            exit(1);
        } else {
            if (f->nargs() < args->size())
            {
                cerr << error_tag(color_output) << "Line " << yylineno << ": too many arguments in a call to " << f->label << endl;
                exit(1);
            }
            if (f->nargs() > args->size())
            {
                cerr << error_tag(color_output) << "Line " << yylineno << ": not enough arguments in a call to " << f->label << endl;
                exit(1);
            }
            $$ = new expression::FunctionCall(*f, *args, yylineno);
        }

        delete args;
        free($1);
    }
    ;

ExpressionList:
    %empty                            { $$ = new std::vector<const Expression*>(); }  
    | NonEmptyExpressionList          { $$ = $1; }
    ;

NonEmptyExpressionList:
    RightValue                        { $$ = new std::vector<const Expression*>(1, ParserData::enforce_le($1)); }
    | ExpressionList ',' RightValue   { $$ = $1; $$->push_back(ParserData::enforce_le($3)); }
    ;

%%

void yyerror (const char * s)
{
    cerr << error_tag(color_output) << "Line " << yylineno << ": " << s << " at " << yytext << endl;
}
