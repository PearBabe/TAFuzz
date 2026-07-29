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

#ifndef ROMEO_STACK_MACHINE_HH
#define ROMEO_STACK_MACHINE_HH

#include <vector>
#include <list>
#include <string>
#include <cstddef>

#include <rvalue.hh>
#include <printable.hh>
#include <sword.hh>

namespace romeo
{
    class RValue;
    class PState;

    struct StackCell
    {
        memrep v;
        std::byte s;
    };

    class SProgram: public Printable
    {
        private:
            std::list<word> instrs;

        public:
            SProgram();
            SProgram(const word);
            SProgram(const std::vector<word>&);
            void add(const SProgram&);

            unsigned size() const;

            std::vector<word> program() const;
            static std::string instruction_to_string(word, unsigned&);
            std::string to_string() const;

    };

    struct addr_guess
    {
        const std::byte* address;
        uint32_t size;
        uint32_t contents_size;

        addr_guess(const std::byte* a, uint32_t s, uint32_t cs): address(a), size(s), contents_size(cs) {}
    };

    class StackMachine
    {
        private:
            std::vector<StackCell> stack;
            unsigned int head;

            std::list<addr_guess> address_guesses; // pairs size, contents_size
            std::list<unsigned int> fhstack;

            void push(unsigned& i, const value);
            void pushf(unsigned& i, const fvalue);
            void pusha(unsigned& i, const std::byte*);
            void pushu(unsigned& i);
            void pop(unsigned& i);
            void dup(unsigned& i);
            void addr(unsigned& i, std::byte V[], const size_t offset);
            void addrc(unsigned& i, const std::byte C[], const size_t offset);
            void store8_(unsigned& i);
            void loadp(unsigned& i);
            void storep(unsigned& i);
            void loadf(unsigned& i);
            void storef(unsigned& i);
            void memcopy(unsigned& i, const size_t);
            void index(unsigned& i, const uint32_t size, const uint32_t contents_size, int);
            void addp(unsigned& i);
            void add(unsigned& i);
            void sub(unsigned& i);
            void div(unsigned& i);
            void mod(unsigned& i);
            void mul(unsigned& i);
            void eq(unsigned& i);
            void neq(unsigned& i);
            void leq(unsigned& i);
            void geq(unsigned& i);
            void lower(unsigned& i);
            void greater(unsigned& i);
            void minimum(unsigned& i);
            void maximum(unsigned& i);
            void bit_not(unsigned& i);
            void bit_and(unsigned& i);
            void bit_or(unsigned& i);
            void shiftl(unsigned& i);
            void shiftr(unsigned& i);
            void jz(unsigned& i, const unsigned offset);
            void jnz(unsigned& i, const unsigned offset);
            void jzu(unsigned& i, const unsigned offset);
            void jnzu(unsigned& i, const unsigned offset);
            void ju(unsigned& i, const unsigned offset);
            void jnu(unsigned& i, const unsigned offset);
            void jmp(unsigned& i, const unsigned offset);
            void logical_and(unsigned& i);
            void logical_or(unsigned& i);
            void logical_not(unsigned& i);
            void ret(unsigned& i, const std::vector<word>& I);
            void startf(unsigned& i);
            void endf(unsigned& i, bool);
            void deadlock(unsigned& i, const PState* S);
            void bounded(unsigned& i, const PState* S, const unsigned bound);
            void scbad(unsigned& i, const PState* S);
            void step_limit(unsigned& i, const PState* S, const unsigned limit, const bool strict);
            void fired(unsigned& i, const PState* S, const unsigned tid);
            void print(unsigned& i);

        public:
            enum instr_t { PUSH, PUSHF, PUSHA, PUSHU, POP, DUP, TOP, LOAD8, STORE8_, STORE8, LOAD16, STORE16, LOAD32, STORE32, LOAD64, STORE64, LOADP, STOREP, LOADF, STOREF, MEMCPY, INDEX, ALLINDEXES, ADDP, ADD, SUB, MUL, DIV, MOD, EQ, NEQ, LEQ, GEQ, LOWER, GREATER,  JZ, JNZ, JZU, JNZU, JU, JNU, JMP, SHIFTL, SHIFTR, BIT_NOT, BIT_AND, BIT_OR, MIN, MAX, ADDR, ADDRC, AND, OR, NOT, RET, STARTF, ENDF, DEADLOCK, BOUNDED, STEPS, SCBAD, FIRED, PRINT };
            
            StackMachine(const unsigned);

            RValue execute(const std::vector<word>&, std::byte[], const std::byte[], const PState*);
            RValue top();
            void print_stack() const;
    };

    template <typename T> struct LoadStore
    {
        static void load(std::vector<StackCell>& stack, std::list<addr_guess>& address_guesses, unsigned& head, unsigned& i)
        {
            //if (stack[head - 1].s & 1)
            if (address_guesses.empty())
            { 
                // ignore if the address is unknown (unknown litteral of structured type)-> same as popping address and pushing unknown
                if ((bool) (stack[head - 1].s & ((std::byte) 1))) 
                {
                    const std::byte* address = stack[head - 1].v.p;
                    stack[head - 1].v.i = *((T*) address);
                    stack[head - 1].s = *((std::byte*) (address + sizeof(T)));
                }
            } else {
                // cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
                // exit(1);
                
                // Load an unknown value
                stack[head - 1].v.i = 0;
                stack[head - 1].s = ((std::byte) 0);

                address_guesses.clear();
            }
            i++;
        }


        static void store(std::vector<StackCell>& stack, std::list<addr_guess>& address_guesses, unsigned& head, unsigned& i)
        {
            if (address_guesses.empty())
            { 
                const std::byte* address = stack[head - 1].v.p;
                head--;
                *((T*) address) = stack[head - 1].v.i;
                *((std::byte*) (address + sizeof(T))) = stack[head - 1].s;
                head--;
            } else {
                //cerr << error_tag(color_output) << "Cannot access memory with unknown offset." << endl;
                //exit(1);

                std::list<const std::byte*> L;
                L.push_back(stack[head - 1].v.p);
                head--;

                // std::byte[3][2] T
                // T[unknown][1] = 1;       -> {{x, u}, {x, u}, {x, u}} :: address_guesses = {(3, 2)}
                // T[1][unknown] = 1;       -> {{u, u}, {x, x}, {x, x}} :: address_guesses = {(2, 1)} 
                // T[unknown][unknown] = 1; -> {{u, u}, {u, u}, {u, u}} :: address_guesses = {(3, 2), (2, 1)}
                for (auto p: address_guesses)
                {
                    std::list<const std::byte*> R;
                    for (auto j: L)
                    {
                        for (word i = 0; i < p.size; i++)
                        {
                            R.push_back(j + i * p.contents_size);
                        }
                    }
                    L = R;
                }

                for (auto address: L)
                {
                    *((T*) address) = 0;
                    *((std::byte*) (address + sizeof(T))) = ((std::byte) 0);
                }
                head--;

                address_guesses.clear();

            }
            i++;
        }
    };

}

#endif

