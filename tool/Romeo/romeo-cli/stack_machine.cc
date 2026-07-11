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

#include <vector>
#include <iostream>
#include <cstring>
#include <string>
#include <sstream>

#include <stack_machine.hh>
#include <rvalue.hh>
#include <color_output.hh>
#include <type_list.hh>
#include <pstate.hh>

using namespace romeo;
using namespace std;

extern TypeList _romeo_types;

SProgram::SProgram()
{
}

SProgram::SProgram(const word i)
{
    instrs.push_back(i);
}

SProgram::SProgram(const vector<word>& I)
{
    for (auto i: I)
    {
        instrs.push_back(i);
    }
}

void SProgram::add(const SProgram& P)
{
    for (auto i: P.instrs)
    {
        instrs.push_back(i);
    }
}

unsigned SProgram::size() const
{
    return instrs.size();
}

vector<word> SProgram::program() const
{
    vector<word> P;

    for (auto i: instrs)
    {
        P.push_back(i);
    }

    return P;
}

string SProgram::instruction_to_string(word i, unsigned& arg)
{
    stringstream s;
    switch (i)
    {
        case StackMachine::PUSH: // push a known integer constant
            s << "PUSH";
            arg = 1;
            break;
        case StackMachine::PUSHF: // push a known floating point constant
            s << "PUSHF";
            arg = 1;
            break;
        case StackMachine::PUSHA: // push a known constant address
            s << "PUSHA";
            arg = 1;
            break;
        case StackMachine::PUSHU: // push a generic unknown value
            s << "PUSHU";
            break;
        case StackMachine::POP: // pop the top element
            s << "POP";
            break;
        case StackMachine::TOP: // FIXME: returns as an integer... TOP8, TOP16... ?
            s << "TOP";
            break;
        case StackMachine::DUP:
            s << "DUP";
            break; 
        case StackMachine::ADDR:
            s << "ADDR";
            arg = 1;
            break;
        case StackMachine::ADDRC:
            s << "ADDRC";
            arg = 1;
            break;
        case StackMachine::STORE8_: // Write the 8bit value just below the top at the address at the top, pop both
            s << "STORE8_";
            break;
        case StackMachine::LOAD8: // Overwrite the address at the top with the 8bit value at that address
            s << "LOAD8";
            break;
        case StackMachine::STORE8: // Write the 8bit value just below the top at the address at the top, pop both
            s << "STORE8";
            break;
        case StackMachine::LOAD16: // Overwrite the address at the top with the 16bit value at that address
            s << "LOAD16";
            break;
        case StackMachine::STORE16: // Write the 16bit value just below the top at the address at the top, pop both
            s << "STORE16";
            break;
        case StackMachine::LOAD32: // Overwrite the address at the top with the 32bit value at that address
            s << "LOAD32";
            break;
        case StackMachine::STORE32: // Write the 32bit value just below the top at the address at the top, pop both
            s << "STORE32";
            break;
        case StackMachine::LOAD64: // Overwrite the address at the top with the 64bit value at that address
            s << "LOAD64";
            break;
        case StackMachine::STORE64: // Write the 64bit value just below the top at the address at the top, pop both
            s << "STORE64";
            break;
        case StackMachine::LOADP: // Overwrite the address at the top with the pointer value at that address
            s << "LOADP";
            break;
        case StackMachine::STOREP: // Write the pointer value just below the top at the address at the top, pop both
            s << "STOREP";
            break;
        case StackMachine::LOADF: // Overwrite the address at the top with the real value at that address
            s << "LOADF";
            break;
        case StackMachine::STOREF: // Write the real value just below the top at the address at the top, pop both
            s << "STOREF";
            break;
        case StackMachine::MEMCPY: // copy 
            s << "MEMCPY";
            arg = 1;
            break;
        case StackMachine::INDEX: // Array index
            s << "INDEX";
            arg = 3;
            break;
        case StackMachine::ADDP: // Add the two topmost values: pointer version
            s << "ADDP";
            break;
        case StackMachine::ADD: // Add the two topmost values, pop them and push the result (actually overwrite the second)
            s << "ADD";
            break;
        case StackMachine::SUB: // Subtract the two topmost values, pop them and push the result (actually overwrite the second)
            s << "SUB";
            break;
        case StackMachine::MUL: // Multiply the two topmost values, pop them and push the result (actually overwrite the second)
            s << "MUL";
            break;
        case StackMachine::DIV: // Divide the two topmost values, pop them and push the quotient (actually overwrite the second)
            s << "DIV";
            break;
        case StackMachine::MOD: // Divide the two topmost values, pop them and push the remainder (actually overwrite the second)
            s << "MOD";
            break;
        case StackMachine::EQ:// Test equality of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "EQ";
            break;
        case StackMachine::NEQ:// Test difference of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "NEQ";
            break;
        case StackMachine::LEQ:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
            s << "LEQ";
            break;
        case StackMachine::GEQ:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
            s << "GEQ";
            break;
        case StackMachine::LOWER:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
            s << "LOWER";
            break;
        case StackMachine::GREATER:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
            s << "GREATER";
            break;
        case StackMachine::MIN:// Min of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "MIN";
            break;
        case StackMachine::MAX:// Max of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "MAX";
            break;
        case StackMachine::BIT_NOT:// Bitwise not of the topmost value, pop it and push the result (actually overwrite)
            s << "BIT_NOT";
            break;
        case StackMachine::BIT_AND:// Bitwise and of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "BIT_AND";
            break;
        case StackMachine::BIT_OR:// Bitwise or of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "BIT_OR";
            break;
        case StackMachine::SHIFTL:// left shift of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "SHIFTL";
            break;
        case StackMachine::SHIFTR:// right shift of the two topmost values, pop them and push the result (actually overwrite the second)
            s << "SHIFTR";
            break;
        case StackMachine::JZ: // relative jump if the top value is zero. Pop that value.
            s << "JZ";
            arg = 1;
            break;
        case StackMachine::JNZ: // relative jump if the top value is zero. Pop that value.
            s << "JNZ";
            arg = 1;
            break;
        case StackMachine::JZU: // relative jump if the top value is zero or unknown. Pop that value.
            s << "JZU";
            arg = 1;
            break;
        case StackMachine::JNZU: // relative jump if the top value is not zero or is unknown. Pop that value.
            s << "JNZU";
            arg = 1;
            break;
        case StackMachine::JU: // relative jump if the top value is unknown. Pop that value.
            s << "JU";
            arg = 1;
            break;
        case StackMachine::JNU: // relative jump if the top value is not unknown. Pop that value.
            s << "JNU";
            arg = 1;
            break;
        case StackMachine::JMP: // unconditional relative jump 
            s << "JMP";
            arg = 1;
            break;
        case StackMachine::AND: // logical and
            s << "AND";
            break;
        case StackMachine::OR: // logical or
            s << "OR";
            break;
        case StackMachine::NOT: // logical not
            s << "NOT";
            break;
        case StackMachine::RET: // Skip to next ENDF
            s << "RET";
            break;
        case StackMachine::STARTF: // End of function
            s << "STARTF";
            break;
        case StackMachine::ENDF: // End of function without result
            s << "ENDF";
            arg = 1;
            break;
        case StackMachine::DEADLOCK: // Deadlock state property
            s << "DEADLOCK";
            break;
        case StackMachine::BOUNDED: // Bounded state property
            s << "BOUNDED";
            arg = 1;
            break;
        case StackMachine::SCBAD: // SCBAD (safety control) state property
            s << "SCBAD";
            break;
        case StackMachine::STEPS: // Step limit state property
            s << "STEPS";
            arg = 2;
            break;
        case StackMachine::FIRED: // Fired transition state property
            s << "FIRED";
            arg = 1;
            break;
        case StackMachine::PRINT: // Print value 
            s << "PRINT";
            break;
        default:
            s << i;
            break;
    }

    return s.str();
}

string SProgram::to_string() const
{
    stringstream s;
    unsigned arg = 0;

    unsigned k = 0;
    for (auto i: instrs)
    {
        s << k << ":\t";
        if (arg > 0)
        {
            s << i;
            arg--;;
        } else {
            s << instruction_to_string(i, arg);
        }
        s << endl;
        k++;
    }

    return s.str();
}

StackMachine::StackMachine(const unsigned n): stack(vector<StackCell>(n)), head(0)
{
}

RValue StackMachine::top()
{
    if (head == 0)
    {
        cerr << error_tag(color_output) << "Top: empty execution stack." << endl;
        exit(1);
    }

    RValue r(stack[head - 1].v.i, stack[head - 1].s);
    head = 0;

    return r;
}

void StackMachine::push(unsigned& i, const value v)
{
    stack[head].v.i = v;
    stack[head].s = ((byte) 1);
    head++;
    i += 2;
}

void StackMachine::pushf(unsigned& i, const fvalue v)
{
    stack[head].v.f = v;
    stack[head].s = ((byte) 1);
    head++;
    i += 2;
}

void StackMachine::pusha(unsigned& i, const byte* a)
{
    stack[head].v.p = a;
    stack[head].s = ((byte) 1);
    head++;
    i += 2;
}

void StackMachine::pushu(unsigned& i)
{
    stack[head].v.i = 0;
    stack[head].s = ((byte) 0);
    head++;
    i++;
}

void StackMachine::pop(unsigned& i)
{
    head--;
    i++;
}

void StackMachine::dup(unsigned& i)
{
    stack[head].v = stack[head - 1].v;
    stack[head].s = stack[head - 1].s;
    head++;
    i++;
}

void StackMachine::addr(unsigned& i, byte V[], const size_t offset)
{
    stack[head].v.p = V + offset;
    stack[head].s = (byte) (V != nullptr);
    head++;
    i += 2;
}

void StackMachine::addrc(unsigned& i, const byte C[], const size_t offset)
{
    stack[head].v.p = C + offset;
    stack[head].s = (byte) (C != nullptr);
    head++;
    i += 2;
}

void StackMachine::store8_(unsigned& i)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    { 
        const byte* address = stack[head - 1].v.p;
        head--;
        *((byte*) address) = (byte) stack[head - 1].v.i;
        head--;
    } else {
        cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
        exit(1);
    }
    i++;
}

void StackMachine::loadp(unsigned& i)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    { 
        const byte* address = stack[head - 1].v.p;
        stack[head - 1].v.p = *((byte**) address);
        //stack[head - 1].s = *((byte*) (address + sizeof(byte*)));
        stack[head - 1].s = ((byte) 1);
    } else {
        cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
        exit(1);
    }
    i++;
}


void StackMachine::storep(unsigned& i)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    { 
        const byte* address = stack[head - 1].v.p;
        head--;
        *((byte**) address) = (byte*) stack[head - 1].v.p;
        //*((byte*) (address + sizeof(byte*))) = stack[head - 1].s;
        head--;
    } else {
        cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
        exit(1);
    }
    i++;
}

void StackMachine::loadf(unsigned& i)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    { 
        const byte* address = stack[head - 1].v.p;
        stack[head - 1].v.f = *((fvalue*) address);
        stack[head - 1].s = *((byte*) (address + sizeof(fvalue)));
    } else {
        cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
        exit(1);
    }
    i++;
}

void StackMachine::storef(unsigned& i)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    { 
        const byte* address = stack[head - 1].v.p;
        head--;
        *((fvalue*) address) = stack[head - 1].v.f;
        *((byte*) (address + sizeof(fvalue))) = stack[head - 1].s;
        head--;
    } else {
        cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
        exit(1);
    }
    i++;
}

void StackMachine::memcopy(unsigned& i, const size_t size)
{

    const byte* src = stack[head - 2].v.p;
    const byte* dst = stack[head - 1].v.p;
    if (address_guesses.empty())
    { 
        memcpy((void*) dst, src, size);
    } else {

        std::list<const byte*> L;
        L.push_back(dst);

        for (auto p: address_guesses)
        {
            // Account only for uncertainty on the destination because we write
            // unknowns anyway.
            if (p.address == dst)
            {
                std::list<const byte*> R;
                for (auto a: L)
                {
                    for (word w = 0; w < p.size; w++)
                    {
                        R.push_back(a + w * p.contents_size);
                    }
                }
                L = R;
            }
        }

        for (auto address: L)
        {
            memset((void*) address, 0, size);
        }

        address_guesses.clear();
    }

    head -= 2;
    i += 2;
}


void StackMachine::index(unsigned& i, const uint32_t size, const uint32_t contents_size, int decl_line)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    {
        if ((uint64_t) stack[head - 1].v.i >= size)
        {
            cerr << error_tag(color_output) << "Line " << decl_line << ": Cannot access index " <<stack[head - 1].v.i << " in array of size " << size << endl;
            exit(1);
        }
        stack[head - 2].v.p += stack[head - 1].v.i * contents_size;
    } else {
        address_guesses.push_back(addr_guess(stack[head - 2].v.p, size, contents_size));
    }

    i += 4;
    head--;
}

void StackMachine::addp(unsigned& i)
{
    stack[head - 2].v.p += stack[head - 1].v.i;
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}


void StackMachine::add(unsigned& i)
{
    stack[head - 2].v.i += stack[head - 1].v.i;
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::sub(unsigned& i)
{
    stack[head - 2].v.i -= stack[head - 1].v.i;
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::div(unsigned& i)
{
    const auto d = stack[head - 1].v.i;
    if (d != 0)
    {
        stack[head - 2].v.i /= stack[head - 1].v.i;
    } else {
        if (stack[head - 1].s != (byte) 0)
        {
            cerr << error_tag(color_output) << "Division by 0." << endl;
            exit(1);
        }
    }
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::mod(unsigned& i)
{
    stack[head - 2].v.i %= stack[head - 1].v.i;
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::mul(unsigned& i)
{
    const byte k2 = stack[head - 1].s & stack[head - 2].s; // both are known
    const byte z1 = stack[head - 1].s & ((byte) (stack[head - 1].v.i == 0)); // x1 is known to be 0
    const byte z2 = stack[head - 2].s & ((byte) (stack[head - 2].v.i == 0)); // x2 is known to be 0

    stack[head - 2].v.i *= stack[head - 1].v.i;
    stack[head - 2].s = k2 | z1 | z2;
    head--;
    i++;
}

void StackMachine::eq(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i == stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::neq(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i != stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::leq(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i <= stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::geq(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i >= stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::lower(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i < stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::greater(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i > stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::minimum(unsigned& i)
{
    stack[head - 2].v.i = std::min(stack[head - 2].v.i, stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::maximum(unsigned& i)
{
    stack[head - 2].v.i = std::max(stack[head - 2].v.i, stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::bit_not(unsigned& i)
{
    stack[head - 1].v.i = ~stack[head - 1].v.i;
    i++;
}

void StackMachine::bit_and(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i & stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::bit_or(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i | stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::shiftl(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i << stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::shiftr(unsigned& i)
{
    stack[head - 2].v.i = (stack[head - 2].v.i >> stack[head - 1].v.i);
    stack[head - 2].s &= stack[head - 1].s;
    head--;
    i++;
}

void StackMachine::jz(unsigned& i, const unsigned offset)
{
    if (stack[head - 1].v.i == 0)
    {
        i += offset + 1;
    } else {
        i += 2;
    }
    head--;
}

void StackMachine::jnz(unsigned& i, const unsigned offset)
{
    if (stack[head - 1].v.i != 0)
    {
        i += offset + 1;
    } else {
        i += 2;
    }
    head--;
}

void StackMachine::jzu(unsigned& i, const unsigned offset)
{
    if ((stack[head - 1].s & ((byte) 1)) == ((byte) 0) || stack[head - 1].v.i == 0)
    {
        i += offset + 1;
    } else {
        i += 2;
    }
    head--;
}

void StackMachine::jnzu(unsigned& i, const unsigned offset)
{
    if ((stack[head - 1].s & ((byte) 1)) == ((byte) 0) || stack[head - 1].v.i != 0)
    {
        i += offset + 1;
    } else {
        i += 2;
    }
    head--;
}

void StackMachine::ju(unsigned& i, const unsigned offset)
{
    if (!(bool) (stack[head - 1].s & ((byte) 1)))
    {
        i += offset + 1;
    } else {
        i += 2;
    }
    head--;
}

void StackMachine::jnu(unsigned& i, const unsigned offset)
{
    if ((bool) (stack[head - 1].s & ((byte) 1)))
    {
        i += offset + 1;
    } else {
        i += 2;
    }
    head--;
}

void StackMachine::jmp(unsigned& i, const unsigned offset)
{
    i += offset + 1;
}

void StackMachine::logical_and(unsigned& i)
{
    const byte k2 = stack[head - 1].s & stack[head - 2].s; // both are known
    const byte z1 = stack[head - 1].s & ((byte) (stack[head - 1].v.i == 0)); // x1 is known to be 0
    const byte z2 = stack[head - 2].s & ((byte) (stack[head - 2].v.i == 0)); // x2 is known to be 0
    
    stack[head - 2].v.i &= stack[head - 1].v.i;
    stack[head - 2].s = k2 | z1 | z2;
    
    head--;
    i++;
}

void StackMachine::logical_or(unsigned& i)
{
    const byte k2 = stack[head - 1].s & stack[head - 2].s; // both are known
    const byte z1 = stack[head - 1].s & ((byte) (stack[head - 1].v.i == 1)); // x1 is known to be 1
    const byte z2 = stack[head - 2].s & ((byte) (stack[head - 2].v.i == 1)); // x2 is known to be 1

    stack[head - 2].v.i |= stack[head - 1].v.i;
    stack[head - 2].s = k2 | z1 | z2;

    head--;
    i++;
}

void StackMachine::logical_not(unsigned& i)
{
    stack[head - 1].v.i = !stack[head - 1].v.i;
    i++;
}


void StackMachine::ret(unsigned& i, const vector<word>& I)
{
    i++;
    // Skip to the ENDF corresponding to this function
    // For that we count the number of STARTF and ENDF to
    // account for nested function calls
    unsigned calls = 1;
    while (calls != 0)
    {
        if (I[i] == StackMachine::ENDF)
        {
            calls--;
        } else if (I[i] == StackMachine::STARTF)
        {
            calls++;
        }
        i++;
    }
    i++; // skip the argument of endf to the next instruction
         // knowing we are already one past the ENDF
}


void StackMachine::startf(unsigned& i)
{
    // Just pop the memorized value of head
    fhstack.push_front(head);
    i++;
}

void StackMachine::endf(unsigned& i, bool b)
{
    // if we should have a result on the stack but have not we push
    // an unknown value
    if (b && fhstack.front() == head)
    {
        pushu(i);
        i++;
    } else {
        // Otherwise just go on
        i += 2;
    }

    // Pop the memorized value of head
    fhstack.pop_front();
}

void StackMachine::deadlock(unsigned& i, const PState* S)
{
    stack[head].v.i = S->deadlock();
    stack[head].s = ((byte) 1);
    head++;
    i++;
}


void StackMachine::bounded(unsigned& i, const PState* S, const unsigned bound)
{
    stack[head].v.i = S->bounded(bound);
    stack[head].s = ((byte) 1);
    head++;
    i += 2;
}

void StackMachine::scbad(unsigned& i, const PState* S)
{
    stack[head].v.i = S->safety_control_bad_state();
    stack[head].s = ((byte) 1);
    head++;
    i++;
}

void StackMachine::step_limit(unsigned& i, const PState* S, const unsigned limit, const bool strict)
{
    stack[head].v.i = S->step_limit(limit, strict);
    stack[head].s = ((byte) 1);
    head++;
    i += 3;
}

void StackMachine::fired(unsigned& i, const PState* S, const unsigned tid)
{
    stack[head].v.i = S->fired_transition(tid);
    stack[head].s = ((byte) 1);
    head++;
    i += 2;
}

void StackMachine::print(unsigned& i)
{
    if (stack[head-1].s == byte(0))
    {
        cout << "unknown" << endl;
    } else {
        cout << stack[head - 1].v.i << endl;
    }
    head--;
    i++;
}


RValue StackMachine::execute(const vector<word>& I, byte V[], const byte C[], const PState* S)
{
    unsigned i = 0;

    // cout << SProgram(I) << endl;
    while (i < I.size())
    {
        // unsigned arg = 0;
        // cout << endl;
        // cout << "instruction " << SProgram::instruction_to_string(I[i], arg);
        // unsigned k = 1;
        // while (arg > 0)
        // {
        //     cout << " " << I[i + k];
        //     k++;
        //     arg--;
        // }
        // cout << endl;
        switch (I[i])
        {
            case PUSH: // push a known constant
                push(i, I[i + 1]);
                break;
            case PUSHF: // push a known floating point constant
                pushf(i, I[i + 1]);
                break;
            case PUSHA: // push a known address
                pusha(i, (const byte*) I[i + 1]);
                break;
            case PUSHU: // push a generic unknown value
                pushu(i);
                break;
            case POP: // pop the top element
                pop(i);
                break;
            case TOP: // FIXME: returns as an integer... TOP8, TOP16... ?
                return top();
                break;
            case DUP:
                dup(i);
                break; 
            case ADDR:
                addr(i, V, I[i + 1]);
                break;
            case ADDRC:
                addrc(i, C, I[i + 1]);
                break;
            case STORE8_: // Write the 8bit value just below the top at the address at the top, pop both
                store8_(i);
                break;
            case LOAD8: // Overwrite the address at the top with the 8bit value at that address
                LoadStore<int8_t>::load(stack, address_guesses, head, i);
                break;
            case STORE8: // Write the 8bit value just below the top at the address at the top, pop both
                LoadStore<int8_t>::store(stack, address_guesses, head, i);
                break;
            case LOAD16: // Overwrite the address at the top with the 16bit value at that address
                LoadStore<int16_t>::load(stack, address_guesses, head, i);
                break;
            case STORE16: // Write the 16bit value just below the top at the address at the top, pop both
                LoadStore<int16_t>::store(stack, address_guesses, head, i);
                break;
            case LOAD32: // Overwrite the address at the top with the 32bit value at that address
                LoadStore<int32_t>::load(stack, address_guesses, head, i);
                break;
            case STORE32: // Write the 32bit value just below the top at the address at the top, pop both
                LoadStore<int32_t>::store(stack, address_guesses, head, i);
                break;
            case LOAD64: // Overwrite the address at the top with the 64bit value at that address
                LoadStore<int64_t>::load(stack, address_guesses, head, i);
                break;
            case STORE64: // Write the 64bit value just below the top at the address at the top, pop both
                LoadStore<int64_t>::store(stack, address_guesses, head, i);
                break;
            case LOADP: // Overwrite the address at the top with the pointer value at that address (assumed known)
                loadp(i);
                break;
            case STOREP: // Write the pointer value just below the top at the address at the top, pop both (do not store status)
                storep(i);
                break;
            case LOADF: // Overwrite the address at the top with the real value at that address
                loadf(i);
                break;
            case STOREF: // Write the real value just below the top at the address at the top, pop both
                storef(i);
                break;
            case MEMCPY: // copy 
                memcopy(i, I[i + 1]);
                break;
            case INDEX: // Array indexing: top of the stack is cell number, argument are number of cells and cell size
                index(i, I[i + 1], I[i + 2], I[i + 3]);
                break;
            case ADDP: // Add the two topmost values: pointer version
                addp(i);
                break;
            case ADD: // Add the two topmost values, pop them and push the result (actually overwrite the second)
                add(i);
                break;
            case SUB: // Subtract the two topmost values, pop them and push the result (actually overwrite the second)
                sub(i);
                break;
            case MUL: // Multiply the two topmost values, pop them and push the result (actually overwrite the second)
                mul(i);
                break;
            case DIV: // Divide the two topmost values, pop them and push the quotient (actually overwrite the second)
                div(i);
                break;
            case MOD: // Divide the two topmost values, pop them and push the remainder (actually overwrite the second)
                mod(i);
                break;
            case EQ:// Test equality of the two topmost values, pop them and push the result (actually overwrite the second)
                eq(i);
                break;
            case NEQ:// Test difference of the two topmost values, pop them and push the result (actually overwrite the second)
                neq(i);
                break;
            case LEQ:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
                leq(i);
                break;
            case GEQ:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
                geq(i);
                break;
            case LOWER:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
                lower(i);
                break;
            case GREATER:// Compare the two topmost values, pop them and push the result (actually overwrite the second)
                greater(i);
                break;
            case MIN:// Min of the two topmost values, pop them and push the result (actually overwrite the second)
                minimum(i);
                break;
            case MAX:// Max of the two topmost values, pop them and push the result (actually overwrite the second)
                maximum(i);
                break;
            case BIT_NOT:// Bitwise and of the two topmost values, pop them and push the result (actually overwrite the second)
                bit_not(i);
                break;
            case BIT_AND:// Bitwise and of the two topmost values, pop them and push the result (actually overwrite the second)
                bit_and(i);
                break;
            case BIT_OR:// Bitwise or of the two topmost values, pop them and push the result (actually overwrite the second)
                bit_or(i);
                break;
            case SHIFTL:// left shift of the two topmost values, pop them and push the result (actually overwrite the second)
                shiftl(i);
                break;
            case SHIFTR:// right shift of the two topmost values, pop them and push the result (actually overwrite the second)
                shiftr(i);
                break;
            case JZ: // relative jump if the top value is zero. Pop that value.
                jz(i, I[i+1]);
                break;
            case JNZ: // relative jump if the top value is not zero. Pop that value.
                jnz(i, I[i + 1]);
                break;
            case JZU: // relative jump if the top value is zero or unknown. Do not pop that value.
                jzu(i, I[i + 1]);
                break;
            case JNZU: // relative jump if the top value is unknown or not zero. Do not pop that value.
                jnzu(i, I[i + 1]);
                break;
            case JU: // relative jump if the top value is unknown. Pop that value.
                ju(i, I[i + 1]);
                break;
            case JNU: // relative jump if the top value is not unknown. Pop that value.
                jnu(i, I[i + 1]);
                break;
            case JMP: // unconditional relative jump 
                jmp(i, I[i + 1]);
                break;
            case StackMachine::AND: // logical and
                logical_and(i);
                break;
            case StackMachine::OR: // logical or
                logical_or(i);
                break;
            case StackMachine::NOT: // logical not
                logical_not(i);
                break;
            case StackMachine::RET: // Skip to next ENDF
                ret(i, I);
                break;
            case StackMachine::STARTF: // Start of function
                startf(i);
                break;
            case StackMachine::ENDF: // End of function with no result
                endf(i, I[i + 1]);
                break;
            case StackMachine::DEADLOCK: // Deadlock state property
                deadlock(i, S);
                break;
            case StackMachine::BOUNDED: // Bounded state property
                bounded(i, S, I[i + 1]);
                break;
            case StackMachine::SCBAD: // SCBAD (safety control) state property
                scbad(i, S);
                break;
            case StackMachine::STEPS: // Step limit state property
                step_limit(i, S, I[i + 1], I[i + 2]);
                break;
            case StackMachine::FIRED: // Fired transition state property
                fired(i, S, I[i + 1]);
                break;
            case StackMachine::PRINT: // Print value
                print(i);
                break;
            default:
                cerr << error_tag(color_output) << "Unknown instruction: " << I[i] << endl;
                exit(1);
                break;
        }

        // print_stack();
    }

    return RValue(0, ((byte) 0));
}

void StackMachine::print_stack() const
{
    cout << "--------------------------- head ---------------------------------" << endl;
    for (unsigned i = 0; i < head; i++)
    {
        cout << "( " << stack[head - i - 1].v.i << ", " << (int) stack[head - i - 1].s << " )" << endl;
    }
    // cout << "number of address guesses: " << address_guesses.size() << endl;
    cout << "-------------------------- bottom --------------------------------" << endl;
}
