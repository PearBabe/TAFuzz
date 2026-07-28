cmake_minimum_required(VERSION 3.10)
project(DFUZZPASS)

# Set compilers to clang-10 and clang++-10
set(CMAKE_C_COMPILER clang-10)
set(CMAKE_CXX_COMPILER clang++-10)

# Set LLVM config to version 10 and get LLVM configuration
set(LLVM_CONFIG_EXECUTABLE llvm-config-10)

# Execute llvm-config to get the necessary flags and directories
execute_process(COMMAND ${LLVM_CONFIG_EXECUTABLE} --includedir
                OUTPUT_VARIABLE LLVM_INCLUDE_DIRS
                OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(COMMAND ${LLVM_CONFIG_EXECUTABLE} --cxxflags
                OUTPUT_VARIABLE LLVM_CXX_FLAGS
                OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(COMMAND ${LLVM_CONFIG_EXECUTABLE} --ldflags
                OUTPUT_VARIABLE LLVM_LD_FLAGS
                OUTPUT_STRIP_TRAILING_WHITESPACE)

execute_process(COMMAND ${LLVM_CONFIG_EXECUTABLE} --version
                OUTPUT_VARIABLE LLVM_VERSION
                OUTPUT_STRIP_TRAILING_WHITESPACE)

message(STATUS "Found LLVM ${LLVM_VERSION}")
message(STATUS "Using LLVM include dir: ${LLVM_INCLUDE_DIRS}")

# Set your project compile flags.
# E.g. if using the C++ header files
# you will need to enable C++11 support
# for your compiler.
include_directories(${LLVM_INCLUDE_DIRS})

# Parse CXX flags
string(REPLACE " " ";" LLVM_CXX_FLAGS_LIST ${LLVM_CXX_FLAGS})
add_compile_options(${LLVM_CXX_FLAGS_LIST})

# Add debug flags
add_compile_options(-g -O0)

# Now build our tools
add_library(DFUZZPASS MODULE
    # List your source files here.
    DFUZZPASS.cpp
)

# Use C++11 to compile our pass (i.e., supply -std=c++11).
target_compile_features(DFUZZPASS PRIVATE cxx_range_for cxx_auto_type)

# LLVM is (typically) built with no C++ RTTI. We need to match that;
# otherwise, we'll get linker errors about missing RTTI data.
set_target_properties(DFUZZPASS PROPERTIES
    COMPILE_FLAGS "-fno-rtti"
)

# Get proper shared-library behavior (where symbols are not necessarily
# resolved when the shared library is linked) on OS X.
if(APPLE)
    set_target_properties(DFUZZPASS PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif(APPLE)