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

#include <color_output.hh>
#include <valuation.hh>
#include <expression.hh>
#include <lexpression.hh>
#include <lconstraint.hh>
#include <instruction.hh>
#include <property.hh>
#include <time_interval.hh>
#include <transition.hh>
#include <type.hh>
#include <type_list.hh>
#include <function.hh>
#include <parser_data.hh>

using namespace romeo;

#include <parser.yacc.hh>

extern TypeList _romeo_types;
extern ParserData* pdata;

%}

%option noyywrap
%option nounput
%option noinput
%option yylineno

%x IN_COMMENT
%%

[ \t\n\r]+        ;
\/\/[^\n\r]*      ;
<INITIAL>       
{
    "/*"        BEGIN(IN_COMMENT);
}
<IN_COMMENT>
{
    "*/"        BEGIN(INITIAL);
    [^*]+       // eat comment in chunks
    "*"         // eat the lone star
}

"inf"           { return INFTY; }

"~"             { return BITNOT; }
"&"             { return BITANDREF; }
"|"             { return BITOR; }
"<<"            { return SHIFTL; }
">>"            { return SHIFTR; }

"and"	        { return AND; }
"&&"	        { return AND; }
"or"	        { return OR; }
"||"	        { return OR; }
"=>"	        { return IMPLY; }
"not"	        { return NOT; }
"!" 	        { return NOT; }

"=="            { return EQ; }
"!="            { return NEQ; }
"<="            { return LEQ; }
">="            { return GEQ; }
"max"	        { return MAX; }
"min"	        { return MIN; }

"++"            { return INC; }
"--"            { return DEC; }

"initially"	    { return INITIALLY; }
"parameters"    { return PARAMETERS; }
"check"         { pdata->check = true; return CHECK; }
"simulate"      { return SIMULATE; }
"graph"         { return GRAPH; }
"retime"        { return RETIME; }
"with"	        { return WITH; }

"true"          { return TRUE; }
"false"         { return FALSE; }
"-->"           { return LEADSTO; }
"bounded"	    { return BOUNDED; }
"deadlock"	    { return DEADLOCK; }

"struct"        { return STRUCT; }
"typedef"       { return TYPEDEF; }
"const"         { return CONST; }
"enum"          { return ENUM; }


"transition"	{ return TRANS; }
"when"          { return WHEN; }
"speed"         { return SPEED; }
"allow"         { return ALLOW; }
"intermediate"  { return INTERMEDIATE; }
"priority"      { return PRIORITY; }

"while"         { return WHILE; }
"for"           { return FOR; }
"forall"        { return FORALL; }
"exists"        { return EXISTS; }
"if"            { return IF; }
"else"          { return ELSE; }
"do"            { return DO; }

"return"        { return RETURN; }
"break"         { return BREAK; }
"continue"      { return CONTINUE; }

"minv"          { return MINVAL; }
"maxv"          { return MAXVAL; }
"minc"          { return MINCLOCK; }
"maxc"          { return MAXCLOCK; }

"cost"          { return COST; }
"cost_rate"     { return COST_RATE; }
"cost_heuristic" { return COST_HEURISTIC; }
"mincost"       { return MINCOST; }
"control"       { return CONTROL; }
"avoid"         { return SCONTROL; }

"__log"         { return LOG; }


\$[a-zA-Z0-9]+   { yylval.str = strdup(yytext); return SPARAM; }
\"[a-zA-Z:\'_][a-zA-Z0-9:\' _]*\" { 
                    size_t s = strlen(yytext)-1; 
                    yylval.str = strdup(yytext+1); 
                    yylval.str[s - 1] = '\0'; 

                    return IDENTIFIER; 
                }
[a-zA-Z\'_][a-zA-Z0-9:\'_]* { 
                    yylval.str = strdup(yytext); 
                    const Type* t = _romeo_types.lookup_type(yytext); 
                    if (t == nullptr)
                    {
                        if (pdata->check)
                        {
                            if (!strcmp(yytext, "U"))
                            {
                                return U;
                            } else if (!strcmp(yytext, "E") || !strcmp(yytext, "A")) {
                                return AE;
                            } else if (!strcmp(yytext, "AF") || !strcmp(yytext, "AG") || !strcmp(yytext, "EF") || !strcmp(yytext, "EG")) {
                                return PTOP;
                            } else {
                                return IDENTIFIER; 
                            }
                        } else {
                            return IDENTIFIER; 
                        }
                    } else {
                        return TYPE;
                    }
                }
[0-9]+	        { yylval.val = strtoll(yytext, NULL, 10); return NUMBER; }
0x[0-9a-fA-F]+	{ yylval.val = strtoll(yytext+2,NULL, 16); return NUMBER; }
0b[01_]+	    { 
                  size_t len = strlen(yytext);
                  char* t = (char*) calloc(len, sizeof(char));
                  size_t k = 0;
                  for (unsigned i = 2; i < len; i++)
                  {
                      if (yytext[i] != '_')
                      {
                          t[k] = yytext[i];
                          k++;
                      }
                  }
                  yylval.val = strtoll(t, NULL, 2);
                  free(t);
                  return NUMBER; }
[-+%*@\!/(){},\.#;:=<>\[\]] {   return yytext[0]; }
.               { std::cerr << error_tag(color_output) << "Line " << yylineno << ": invalid character (probably accent or special character): " << yytext << std::endl; exit(1); } 

