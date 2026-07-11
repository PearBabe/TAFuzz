#  This file is part of the Roméo model-checking software
# 
# Copyright École Centrale de Nantes, LS2N
# 
# Contributors: Didier Lime (2014-2025)
# 
# Didier.Lime@ec-nantes.fr
# 
# This software is a computer program whose purpose is to perform
# parametric model checking on timed and hybrid systems.
# 
# This software is governed by the CeCILL license under French law and
# abiding by the rules of distribution of free software.  You can  use, 
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info". 
# 
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability. 
# 
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or 
# data to be ensured and,  more generally, to use and operate it in the 
# same conditions as regards security. 
# 
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.
# 
# =========================== Editable part ===================================
# Name of executable
EXE=romeo-cli

# C compiler and linker
# CC=/usr/share/clang/scan-build-3.4/c++-analyzer
# CC = clang++
CC=g++

# Bison
YACC = bison --report=all

# Flex
LEX = flex

# Compilation flags
RELEASE_CFLAGS= -O3 -Wall
OPTIM_CFLAGS= -O3 -g -Wall -DROMEO_PROFILE
DEBUG_CFLAGS= -O0 -g -Wall -DROMEO_PROFILE
# DEBUG_CFLAGS= -O0 -g -Wall -DROMEO_PROFILE -fsanitize=undefined -fno-omit-frame-pointer

CFLAGS=$(DEBUG_CFLAGS)
ADD_FLAGS=-std=c++17
#CFLAGS += -finstrument-functions

# Additional libraries
LIBRARIES = -lgmp -lgmpxx -lppl
# LIBRARIES = -lubsan -lgmp -lgmpxx -lppl -static-libubsan

# Linking flags
LDFLAGS = 
#LDFLAGS = -pg
#LDFLAGS = -lSaturn

ifndef VERSION
VERSION= dev
endif

GITHASH = $(shell git rev-parse HEAD 2>/dev/null || echo source-archive)
PYTHON ?= python3
ADD_FLAGS+=-DPOLY_COEFFICIENT_MPZ

ifeq ($(OS),Windows)
	# Windows specific stuff here
	CC=x86_64-w64-mingw32-g++
	EXE := $(EXE).exe
    STATIC_FLAGS=-static
    STATIC_LIBRARIES= \
    	/home/did/recherche/tools/libs/win32/lib/libppl.a \
        /home/did/recherche/tools/libs/win32/lib/libgmpxx.a \
        /home/did/recherche/tools/libs/win32/lib/libgmp.a
    LIBRARY_DIR =-L/home/did/recherche/tools/libs/win32/lib # -L/usr/local/lib
    INCLUDE_DIR =-I. -I/home/did/recherche/tools/libs/win32/include -I/usr/local/include
    ADD_FLAGS+=-DROMEO_WIN
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
		#linux specific
        STATIC_FLAGS=-static
        # Linux static custom PPL
        #STATIC_LIBRARIES= /usr/local/lib/libppl.a \
        #    /usr/lib/x86_64-linux-gnu/libgmpxx.a \
        #    /usr/lib/x86_64-linux-gnu/libgmp.a

        # Linux static 
        STATIC_LIBRARIES= \
            /usr/lib/x86_64-linux-gnu/libppl.a \
            /usr/lib/x86_64-linux-gnu/libgmpxx.a \
            /usr/lib/x86_64-linux-gnu/libgmp.a

        # Location of additional librairies
        LIBRARY_DIR =-L/usr/lib/x86_64-linux-gnu # -L/usr/local/lib
        
        # Additonal headers
        INCLUDE_DIR =-I. -I/usr/include/x86_64-linux-gnu -I/usr/local/include
		ADD_FLAGS+=-DROMEO_LINUX

		DATE =$(shell date --rfc-3339='date')
    endif

    ifeq ($(UNAME_S),Darwin)
		#OS X specific
		ADD_FLAGS+=-DROMEO_MAC -DNO_STD_BYTE -mmacosx-version-min=10.9 -std=c++11
		LDFLAGS+=-mmacosx-version-min=10.9 -stdlib=libc++
 		# the default version of Bison on mac is too old, use a newer one
		# to be install in /usr/local/bin
		YACC := /usr/local/bin/$(YACC)
        STATIC_FLAGS=
        STATIC_LIBRARIES= /usr/local/lib/libppl.a /usr/local/lib/libgmp.a /usr/local/lib/libgmpxx.a
        LIBRARY_DIR=-L/usr/local/lib
        INCLUDE_DIR =-I. -I/usr/local/include
		DATE =$(shell date)
    endif
endif

ADD_FLAGS+= -DROMEO_VERSION="\"version $(VERSION), $(DATE) -- $(GITHASH)\""
CFLAGS+= $(ADD_FLAGS)


# =========================== End of editable part ============================
.PHONY: all

# Main target
all: $(EXE)

# Release target
release: CFLAGS=$(RELEASE_CFLAGS) $(ADD_FLAGS)
release: static
	strip $(EXE)

# Release target (profiling)
release-profile: CFLAGS=$(OPTIM_CFLAGS) $(ADD_FLAGS)
release-profile: static

# Source files
SRCS = main.cc expression.cc cts.cc lobject.cc \
	   transition.cc variable.cc parameter.cc \
	   time_interval.cc generic_expression.cc \
       parser.yacc.cc parser.lex.cc parser_data.cc \
	   property.cc timed_property.cc property_AG.cc \
	   property_EU.cc property_AU.cc property_LT.cc \
	   result.cc pwt.cc vsstate.cc vsclass.cc vzone.cc \
       vsspoly.cc vscpoly.cc vscpar.cc timebounds.cc \
       vszpoly.cc vszpar.cc dbm.cc valuation.cc \
	   job.cc logger.cc polyhedron.cc linear_expression.cc \
	   color_output.cc printable.cc \
	   instruction.cc rvalue.cc lexpression.cc lconstraint.cc \
	   simple_property.cc type.cc type_list.cc access_expression.cc function.cc \
	   checked_types.cc dproperty.cc dresult.cc cost_EU.cc cvsclass.cc \
       cvsclass_gp.cc cvsclass_sp.cc vscpoly_costs.cc \
	   control_reach.cc control_result.cc graph_node.cc \
	   property_EEU.cc property_LEU.cc cost_EU_EEU.cc\
	   vscpar_costs.cc hparam_EU.cc\
	   pdbm.cc vpsclass.cc cost_dbm.cc bcvzone.cc bvzone.cc avalue.cc \
	   ldbm.cc vlsclass.cc vszpoly_costs.cc \
	   backward_mincost.cc stack_machine.cc sexpression.cc whash.cc

# Corresponding object files
OBJS=$(SRCS:.cc=.o)
DEPS=$(SRCS:.cc=.d)
TEST_EXE=romeo-backward-tests
TEST_SRCS=tests/backward_cost_dbm_tests.cc
TEST_OBJS=$(TEST_SRCS:.cc=.o)
CORE_OBJS=$(filter-out main.o,$(OBJS))
-include $(DEPS)
-include $(TEST_OBJS:.o=.d)

# Generic compilation rule
%.o: %.cc
	$(CC) $(INCLUDE_DIR) -c ${CFLAGS} -MMD -MP -o $@ $<

# Lexer
%.lex.cc: %.l 
	$(LEX) -o $@ $<
	
# Parser
%.yacc.cc: %.y
	$(YACC) -o $@ $<

# Linking
$(EXE): $(OBJS)
	$(CC) $(LDFLAGS) -o $(EXE) $(OBJS) $(LIBRARY_DIR) $(LIBRARIES)

$(TEST_EXE): $(CORE_OBJS) $(TEST_OBJS)
	$(CC) $(LDFLAGS) -o $(TEST_EXE) $(CORE_OBJS) $(TEST_OBJS) $(LIBRARY_DIR) $(LIBRARIES)

.PHONY: check check-sanitize

check: $(EXE) $(TEST_EXE)
	./$(TEST_EXE)
	$(PYTHON) tests/test_backward_cli.py --binary ./$(EXE)

check-sanitize:
	$(MAKE) clean
	# The parser/CTS AST is process-lifetime data in this release.  Keep this
	# target focused on memory-safety and UB; leak audits are run separately.
	ASAN_OPTIONS='detect_leaks=0:halt_on_error=1' UBSAN_OPTIONS='halt_on_error=1' \
		$(MAKE) check CFLAGS='$(DEBUG_CFLAGS) $(ADD_FLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='$(LDFLAGS) -fsanitize=address,undefined'


.PHONY: static clean distclean

# Static
static: $(OBJS)
	$(CC) $(STATIC_FLAGS) $(LDFLAGS) -o $(EXE) $(OBJS) $(STATIC_LIBRARIES)

# Clean
clean:
	rm -vf *.o *.d tests/*.o tests/*.d parser.lex.cc parser.yacc.cc parser.yacc.hh parser.yacc.output position.hh stack.hh location.hh

distclean: clean
	rm -vf $(EXE) $(TEST_EXE)

# Additional Dependencies
parser.lex.cc: parser.yacc.hh
parser.yacc.hh: parser.yacc.cc
