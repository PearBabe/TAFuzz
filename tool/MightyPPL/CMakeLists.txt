# minimum required CMAKE version
CMAKE_MINIMUM_REQUIRED(VERSION 3.10 FATAL_ERROR)
project(MightyPPL)

include(CTest)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake)

# compiler must be 17
set(CMAKE_CXX_STANDARD 17)

# required if linking to static library
add_definitions(-DANTLR4CPP_STATIC)

# using /MD flag for antlr4_runtime (for Visual C++ compilers only)
set(ANTLR4_WITH_STATIC_CRT OFF)

# Specify the version of the antlr4 library needed for this project.
# By default the latest version of antlr4 will be used.  You can specify a
# specific, stable version by setting a repository tag value or a link
# to a zip file containing the libary source.
# set(ANTLR4_TAG 4.13.1)
# set(ANTLR4_ZIP_REPOSITORY https://github.com/antlr/antlr4/archive/refs/tags/4.13.1.zip)

include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# add external build for antlrcpp
include(ExternalAntlr4Cpp)
# add antrl4cpp artifacts to project environment
include_directories(${ANTLR4_INCLUDE_DIRS})

# set variable pointing to the antlr tool that supports C++
# this is not required if the jar file can be found under PATH environment
set(ANTLR_EXECUTABLE ${CMAKE_CURRENT_SOURCE_DIR}/external/antlr-4.13.1-complete.jar)
# add macros to generate ANTLR Cpp code from grammar
find_package(ANTLR REQUIRED)

# Call macro to add lexer and grammar to your build dependencies.
antlr_target(MitlGrammar Mitl.g4 VISITOR
            PACKAGE mightypplcpp)
         #antlr_target(SampleGrammarParser TParser.g4 PARSER
         #             PACKAGE antlrcpptest
         #             DEPENDS_ANTLR SampleGrammarLexer
         #             COMPILE_FLAGS -lib ${ANTLR_SampleGrammarLexer_OUTPUT_DIR})

# include generated files in project environment
include_directories(${ANTLR_MitlGrammar_OUTPUT_DIR})
#include_directories(${ANTLR_SampleGrammarParser_OUTPUT_DIR})

set(EXTERNAL_INSTALL_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/external")

add_subdirectory (${EXTERNAL_INSTALL_LOCATION}/buddy buddy)

#file(MAKE_DIRECTORY ${EXTERNAL_INSTALL_LOCATION}/monitaal)

ExternalProject_add(monitaal
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../MoniTAal
    DOWNLOAD_COMMAND ""
    UPDATE_COMMAND ""
    CMAKE_ARGS (
        -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}
        -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER} -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
        -DCMAKE_INSTALL_PREFIX=${EXTERNAL_INSTALL_LOCATION}/monitaal -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DMONITAAL_BUILD_BIN=ON -DMONITAAL_BUILD_BENCH=ON)
)

include_directories(${EXTERNAL_INSTALL_LOCATION}/monitaal/include/monitaal)
link_directories(${EXTERNAL_INSTALL_LOCATION}/monitaal/lib)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/build/monitaal-prefix/src/monitaal-build/external/include)
link_directories(${CMAKE_CURRENT_SOURCE_DIR}/build/monitaal-prefix/src/monitaal-build/external/lib)


#add_subdirectory(${EXTERNAL_INSTALL_LOCATION}/monitaal monitaal)

#target_include_directories(MoniTAal INTERFACE ${EXTERNAL_INSTALL_LOCATION}/monitaal)


# add generated grammar to demo binary target
add_executable(mitppl main.cpp
               MitlFormulaVisitor.cpp
               MitlTypingVisitor.cpp
               MitlCheckNNFVisitor.cpp
               MitlToNNFVisitor.cpp
               MitlAtomNumberingVisitor.cpp
               MitlCollectTemporalVisitor.cpp
               MitlGetBDDVisitor.cpp
               TAwithBDDEdges.cpp
               Finally.cpp
               Once.cpp
               Globally.cpp
               Historically.cpp
               Until.cpp
               Since.cpp
               Release.cpp
               Trigger.cpp
               PnueliFn.cpp
               PnueliOn.cpp
               PnueliGn.cpp
               PnueliHn.cpp
               CountFn.cpp
               CountOn.cpp
	               CountGn.cpp
	               CountHn.cpp
	               MightyPPL.cpp
	               MightyPPLRuntimeOptions.cpp
	               ${ANTLR_MitlGrammar_CXX_OUTPUTS})


target_link_libraries(mitppl antlr4_static buddy MoniTAal pugixml pardibaal)
add_dependencies(mitppl monitaal)

set(TAMONITOR_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../src/TAMonitor)
set(TAMONITOR_PTA_SOURCE_DIR ${TAMONITOR_SOURCE_DIR}/PTA)

# 仅用于分析报告中的依赖可追溯性；若是首次干净配置、外部仓库尚未
# checkout，则明确记录 unknown，不把分支名冒充实际构建 commit。
set(TAMONITOR_PARDIBAAL_SOURCE_DIR
    ${CMAKE_CURRENT_BINARY_DIR}/monitaal-prefix/src/monitaal-build/pardibaal-prefix/src/pardibaal)
execute_process(
    COMMAND git -C ${TAMONITOR_PARDIBAAL_SOURCE_DIR} rev-parse HEAD
    RESULT_VARIABLE TAMONITOR_PARDIBAAL_GIT_RESULT
    OUTPUT_VARIABLE TAMONITOR_PARDIBAAL_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)
if(NOT TAMONITOR_PARDIBAAL_GIT_RESULT EQUAL 0)
    set(TAMONITOR_PARDIBAAL_COMMIT unknown)
endif()

find_package(PkgConfig REQUIRED)
pkg_check_modules(Z3 REQUIRED IMPORTED_TARGET z3)

add_library(TAMonitorPTA STATIC
            ${TAMONITOR_PTA_SOURCE_DIR}/PTATypes.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/PricedDBMOps.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/ExactDominance.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/AffineOptimizer.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/RomeoDBMOptimizer.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/BackwardPricedSolver.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/ReachableZoneGraph.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/MixedPricedSolver.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/PrefixCostAnalyzer.cpp
            ${TAMONITOR_PTA_SOURCE_DIR}/PrefixCostOutput.cpp)
target_include_directories(TAMonitorPTA PUBLIC
                           ${TAMONITOR_SOURCE_DIR}
                           ${TAMONITOR_PTA_SOURCE_DIR})
target_compile_features(TAMonitorPTA PUBLIC cxx_std_17)
target_compile_options(TAMonitorPTA PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_link_libraries(TAMonitorPTA PUBLIC pardibaal PkgConfig::Z3)
add_dependencies(TAMonitorPTA monitaal)

if(BUILD_TESTING)
    add_executable(TAMonitorPTATests
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/PTATests.cpp)
    target_compile_features(TAMonitorPTATests PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTATests PRIVATE -Wall -Wextra -Wpedantic)
    target_link_libraries(TAMonitorPTATests PRIVATE
                          TAMonitorPTA MoniTAal pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTATests monitaal)
    add_test(NAME TAMonitorPTATests COMMAND TAMonitorPTATests)

    add_executable(TAMonitorPTAReachabilityTests
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/ReachableZoneGraphTests.cpp)
    target_compile_features(TAMonitorPTAReachabilityTests PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTAReachabilityTests PRIVATE
                           -Wall -Wextra -Wpedantic)
    target_link_libraries(TAMonitorPTAReachabilityTests PRIVATE
                          TAMonitorPTA MoniTAal pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTAReachabilityTests monitaal)
    add_test(NAME TAMonitorPTAReachabilityTests
             COMMAND TAMonitorPTAReachabilityTests)

    add_executable(TAMonitorPTAMixedTests
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/MixedPricedSolverTests.cpp)
    target_compile_features(TAMonitorPTAMixedTests PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTAMixedTests PRIVATE
                           -Wall -Wextra -Wpedantic)
    target_link_libraries(TAMonitorPTAMixedTests PRIVATE
                          TAMonitorPTA MoniTAal pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTAMixedTests monitaal)
    add_test(NAME TAMonitorPTAMixedTests COMMAND TAMonitorPTAMixedTests)

    add_executable(TAMonitorPTAAffineTests
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/AffineOptimizerTests.cpp)
    target_compile_features(TAMonitorPTAAffineTests PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTAAffineTests PRIVATE
                           -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(TAMonitorPTAAffineTests PRIVATE
                          TAMonitorPTA pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTAAffineTests monitaal)
    add_test(NAME TAMonitorPTAAffineTests COMMAND TAMonitorPTAAffineTests)

    add_executable(TAMonitorPTAPrefixTests
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/PrefixCostAnalyzerTests.cpp)
    target_compile_features(TAMonitorPTAPrefixTests PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTAPrefixTests PRIVATE
                           -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(TAMonitorPTAPrefixTests PRIVATE
                          TAMonitorPTA MoniTAal pugixml pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTAPrefixTests monitaal)
    add_test(NAME TAMonitorPTAPrefixTests COMMAND TAMonitorPTAPrefixTests)

    add_executable(TAMonitorPTARomeoDifferential
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/RomeoDBMOptimizerTests.cpp)
    target_compile_features(TAMonitorPTARomeoDifferential PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTARomeoDifferential PRIVATE
                           -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(TAMonitorPTARomeoDifferential PRIVATE
                          TAMonitorPTA pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTARomeoDifferential monitaal)
    add_test(NAME TAMonitorPTARomeoTests
             COMMAND TAMonitorPTARomeoDifferential --cases 500)

    set(TAMONITOR_ROMEO_SOURCE_DIR
        ${CMAKE_CURRENT_SOURCE_DIR}/../Romeo/romeo-cli)
    add_executable(TAMonitorPTARomeoOriginalTests
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/RomeoOriginalComparison.cpp
                   ${TAMONITOR_ROMEO_SOURCE_DIR}/dbm.cc
                   ${TAMONITOR_ROMEO_SOURCE_DIR}/avalue.cc
                   ${TAMONITOR_ROMEO_SOURCE_DIR}/timebounds.cc
                   ${TAMONITOR_ROMEO_SOURCE_DIR}/valuation.cc
                   ${TAMONITOR_ROMEO_SOURCE_DIR}/printable.cc
                   ${TAMONITOR_ROMEO_SOURCE_DIR}/color_output.cc)
    target_include_directories(TAMonitorPTARomeoOriginalTests PRIVATE
                               ${TAMONITOR_ROMEO_SOURCE_DIR})
    target_compile_features(TAMonitorPTARomeoOriginalTests PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTARomeoOriginalTests PRIVATE
                           -ffunction-sections -fdata-sections)
    target_link_options(TAMonitorPTARomeoOriginalTests PRIVATE
                        -Wl,--gc-sections)
    target_link_libraries(TAMonitorPTARomeoOriginalTests PRIVATE
                          TAMonitorPTA pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTARomeoOriginalTests monitaal)
    add_test(NAME TAMonitorPTARomeoOriginalTests
             COMMAND TAMonitorPTARomeoOriginalTests)

    add_executable(TAMonitorPTAPrefixBenchmark
                   ${TAMONITOR_PTA_SOURCE_DIR}/tests/PrefixPerformanceBenchmark.cpp)
    target_compile_features(TAMonitorPTAPrefixBenchmark PRIVATE cxx_std_17)
    target_compile_options(TAMonitorPTAPrefixBenchmark PRIVATE
                           -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(TAMonitorPTAPrefixBenchmark PRIVATE
                          TAMonitorPTA pardibaal PkgConfig::Z3)
    add_dependencies(TAMonitorPTAPrefixBenchmark monitaal)
endif()

add_executable(TAMonitor
               ${TAMONITOR_SOURCE_DIR}/TAMonitorMain.cpp
               ${TAMONITOR_SOURCE_DIR}/TAMonitorOptions.cpp
               ${TAMONITOR_SOURCE_DIR}/TAMonitorMightyAdapter.cpp
               ${TAMONITOR_SOURCE_DIR}/TraceParser.cpp
               ${TAMONITOR_SOURCE_DIR}/MonitorRunner.cpp
               ${TAMONITOR_SOURCE_DIR}/ReportWriter.cpp
               ${TAMONITOR_PTA_SOURCE_DIR}/PTAAnalysis.cpp
               ${TAMONITOR_PTA_SOURCE_DIR}/PrefixRuntime.cpp
               MitlFormulaVisitor.cpp
               MitlTypingVisitor.cpp
               MitlCheckNNFVisitor.cpp
               MitlToNNFVisitor.cpp
               MitlAtomNumberingVisitor.cpp
               MitlCollectTemporalVisitor.cpp
               MitlGetBDDVisitor.cpp
               TAwithBDDEdges.cpp
               Finally.cpp
               Once.cpp
               Globally.cpp
               Historically.cpp
               Until.cpp
               Since.cpp
               Release.cpp
               Trigger.cpp
               PnueliFn.cpp
               PnueliOn.cpp
               PnueliGn.cpp
               PnueliHn.cpp
               CountFn.cpp
               CountOn.cpp
               CountGn.cpp
               CountHn.cpp
               MightyPPL.cpp
               MightyPPLRuntimeOptions.cpp
               ${ANTLR_MitlGrammar_CXX_OUTPUTS})

# 只把本次维护的适配文件提升为 Werror；MightyPPL 上游仍有既有的
# non-void visitor warning，不能把无关历史告警混入本功能验收。
set_source_files_properties(
    ${TAMONITOR_SOURCE_DIR}/TAMonitorMain.cpp
    ${TAMONITOR_SOURCE_DIR}/TAMonitorOptions.cpp
    ${TAMONITOR_SOURCE_DIR}/MonitorRunner.cpp
    ${TAMONITOR_PTA_SOURCE_DIR}/PrefixRuntime.cpp
    PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror")

target_include_directories(TAMonitor PRIVATE ${TAMONITOR_SOURCE_DIR})
target_compile_definitions(TAMonitor PRIVATE
    TAMONITOR_REPO_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/../.."
    TAMONITOR_XLSX_SCRIPT="${TAMONITOR_SOURCE_DIR}/make_tamonitor_xlsx.py"
    TAMONITOR_PARDIBAAL_COMMIT="${TAMONITOR_PARDIBAAL_COMMIT}")
target_link_libraries(TAMonitor antlr4_static buddy MoniTAal pugixml pardibaal TAMonitorPTA)
add_dependencies(TAMonitor monitaal)

if(BUILD_TESTING)
    find_package(PythonInterp 3 REQUIRED)
    add_test(
        NAME TAMonitorPTAIntegration
        COMMAND ${PYTHON_EXECUTABLE}
                ${TAMONITOR_PTA_SOURCE_DIR}/tests/PTAIntegrationTest.py
                --tamonitor $<TARGET_FILE:TAMonitor>
                --repo-root ${CMAKE_CURRENT_SOURCE_DIR}/../..)
    set_tests_properties(TAMonitorPTAIntegration PROPERTIES TIMEOUT 180)

    add_test(
        NAME TAMonitorPTAMixedIntegration
        COMMAND ${PYTHON_EXECUTABLE}
                ${TAMONITOR_PTA_SOURCE_DIR}/tests/PTAMixedIntegrationTest.py
                --tamonitor $<TARGET_FILE:TAMonitor>
                --repo-root ${CMAKE_CURRENT_SOURCE_DIR}/../..)
    set_tests_properties(TAMonitorPTAMixedIntegration PROPERTIES TIMEOUT 180)

    add_test(
        NAME TAMonitorPTAPrefixIntegration
        COMMAND ${PYTHON_EXECUTABLE}
                ${TAMONITOR_PTA_SOURCE_DIR}/tests/PTAPrefixIntegrationTest.py
                --tamonitor $<TARGET_FILE:TAMonitor>
                --repo-root ${CMAKE_CURRENT_SOURCE_DIR}/../..)
    set_tests_properties(TAMonitorPTAPrefixIntegration PROPERTIES TIMEOUT 180)
endif()


if (CMAKE_HOST_UNIX)
  # Make sure to link against threads (pthreads) library in order to be able to
  # make use of std::call_once in the code without producing runtime errors
  # (see also https://github.com/antlr/antlr4/issues/3708 and/or https://stackoverflow.com/q/51584960).
  set(THREADS_PREFER_PTHREAD_FLAG ON)
  find_package(Threads REQUIRED)

	  if (TARGET mitppl)
	    target_link_libraries(mitppl Threads::Threads)
	    message(STATUS "mitppl Linked with Threads!")
	  endif()

	  if (TARGET TAMonitor)
	    target_link_libraries(TAMonitor Threads::Threads)
	    message(STATUS "TAMonitor Linked with Threads!")
	  endif()

endif()
