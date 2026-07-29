cmake_minimum_required(VERSION 3.20)

project(TAFuzzStaticAnalysis VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

option(RIFT_BUILD_TESTS "Build the project-neutral baseline smoke tests" ON)
option(RIFT_BUILD_LLVM_BASELINES "Build LLVM/MemorySSA/SVF weak baselines" ON)
set(
  RIFT_CLANG_INCLUDE_DIR
  ""
  CACHE PATH
  "Optional root containing clang/AST/*.h when the runtime package lacks development headers"
)
set(
  RIFT_CLANG_CPP_LIBRARY
  ""
  CACHE FILEPATH
  "Path to the monolithic Clang 18 shared library"
)

find_package(LLVM REQUIRED CONFIG)
if(NOT LLVM_VERSION_MAJOR EQUAL 18)
  message(FATAL_ERROR "RIFT requires LLVM 18, found ${LLVM_PACKAGE_VERSION}")
endif()

# M5 local truth-change summaries use the system Z3 C++ API.  Keep Z3 in the
# production runtime attestation and fail configuration if either the headers
# or the exact shared-library dependency is absent.
find_path(RIFT_Z3_INCLUDE_DIR NAMES z3++.h)
find_library(RIFT_Z3_LIBRARY NAMES z3)
if(NOT RIFT_Z3_INCLUDE_DIR OR NOT RIFT_Z3_LIBRARY)
  message(FATAL_ERROR "RIFT M5 requires z3++.h and libz3")
endif()
add_library(rift_z3 UNKNOWN IMPORTED GLOBAL)
set_target_properties(rift_z3 PROPERTIES
  IMPORTED_LOCATION "${RIFT_Z3_LIBRARY}"
  INTERFACE_INCLUDE_DIRECTORIES "${RIFT_Z3_INCLUDE_DIR}"
)

if(RIFT_CLANG_INCLUDE_DIR)
  if(NOT EXISTS "${RIFT_CLANG_INCLUDE_DIR}/clang/AST/AST.h")
    message(FATAL_ERROR
      "RIFT_CLANG_INCLUDE_DIR does not contain clang/AST/AST.h: "
      "${RIFT_CLANG_INCLUDE_DIR}")
  endif()
  set(RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS "${RIFT_CLANG_INCLUDE_DIR}")
else()
  find_path(
    RIFT_SYSTEM_CLANG_INCLUDE_DIR
    clang/AST/AST.h
    HINTS "${LLVM_INCLUDE_DIRS}" /usr/lib/llvm-18/include
  )
  if(NOT RIFT_SYSTEM_CLANG_INCLUDE_DIR)
    message(FATAL_ERROR
      "Clang development headers were not found. Set RIFT_CLANG_INCLUDE_DIR "
      "or run scripts/bootstrap_clang18_headers.sh.")
  endif()
  set(RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS "${RIFT_SYSTEM_CLANG_INCLUDE_DIR}")
endif()

if(NOT RIFT_CLANG_CPP_LIBRARY)
  find_library(
    RIFT_CLANG_CPP_LIBRARY
    NAMES clang-cpp clang-cpp.so.18.1 libclang-cpp.so.18.1
    HINTS /usr/lib/llvm-18/lib /usr/lib/x86_64-linux-gnu
  )
endif()
if(NOT RIFT_CLANG_CPP_LIBRARY OR NOT EXISTS "${RIFT_CLANG_CPP_LIBRARY}")
  message(FATAL_ERROR
    "The monolithic Clang 18 shared library was not found; set "
    "RIFT_CLANG_CPP_LIBRARY explicitly.")
endif()
add_library(rift_clang_cpp SHARED IMPORTED GLOBAL)
set_target_properties(
  rift_clang_cpp PROPERTIES IMPORTED_LOCATION "${RIFT_CLANG_CPP_LIBRARY}")

add_library(rift_ast_baselines STATIC
  core/baselines/ast/ast_baselines.cpp
  core/baselines/ast/moonshine_rw.cpp
  core/baselines/ast/plain_pdg.cpp
)
target_include_directories(rift_ast_baselines
  PUBLIC
    "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/core/baselines/ast"
)
target_include_directories(rift_ast_baselines SYSTEM PRIVATE
  ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
  ${LLVM_INCLUDE_DIRS}
)
target_compile_options(rift_ast_baselines PRIVATE -Wall -Wextra -Werror)
target_link_libraries(rift_ast_baselines PUBLIC rift_clang_cpp LLVM)

add_library(rift_production_core STATIC
  core/production/sha256.cpp
  core/production/identity.cpp
  core/production/compilation_plan.cpp
  core/production/value_transfer.cpp
  core/production/artifact_loader.cpp
  core/production/clang_indexer.cpp
  core/production/binding.cpp
  core/production/influence.cpp
  core/production/model.cpp
  core/production/capabilities.cpp
  core/production/frontier.cpp
  core/production/payload_projection.cpp
  core/production/predicate_occurrence.cpp
  core/production/recipe.cpp
)
target_include_directories(rift_production_core
  PUBLIC "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
  PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/core/production"
)
target_include_directories(rift_production_core SYSTEM PRIVATE
  ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
  ${LLVM_INCLUDE_DIRS}
  ${RIFT_Z3_INCLUDE_DIR}
)
target_compile_options(rift_production_core PRIVATE
  -Wall -Wextra -Wpedantic -Werror)
target_link_libraries(rift_production_core PUBLIC rift_clang_cpp LLVM rift_z3)

file(GLOB_RECURSE RIFT_PRODUCTION_MANIFEST_INPUTS CONFIGURE_DEPENDS
  "${CMAKE_CURRENT_SOURCE_DIR}/core/production/*"
  "${CMAKE_CURRENT_SOURCE_DIR}/include/rift/core/*"
  "${CMAKE_CURRENT_SOURCE_DIR}/schema/*"
)
list(FILTER RIFT_PRODUCTION_MANIFEST_INPUTS EXCLUDE REGEX
  "/core/production/production_smoke\\.cpp$")
list(APPEND RIFT_PRODUCTION_MANIFEST_INPUTS
  "${CMAKE_CURRENT_SOURCE_DIR}/cli/production_entry.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/cli/production_main.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/cli/production_main.h"
  "${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_embedded_manifest.py"
)
set(RIFT_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(RIFT_BUILD_MANIFEST_HEADER
  "${RIFT_GENERATED_DIR}/rift_build_manifest.h")
set(RIFT_BUILD_MANIFEST_JSON
  "${RIFT_GENERATED_DIR}/rift_build_manifest.json")
add_custom_command(
  OUTPUT "${RIFT_BUILD_MANIFEST_HEADER}" "${RIFT_BUILD_MANIFEST_JSON}"
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_embedded_manifest.py"
    --source-root "${CMAKE_CURRENT_SOURCE_DIR}"
    --output-header "${RIFT_BUILD_MANIFEST_HEADER}"
    --output-json "${RIFT_BUILD_MANIFEST_JSON}"
  DEPENDS ${RIFT_PRODUCTION_MANIFEST_INPUTS}
  VERBATIM
)
add_custom_target(rift_embedded_manifest_artifacts
  DEPENDS "${RIFT_BUILD_MANIFEST_HEADER}" "${RIFT_BUILD_MANIFEST_JSON}")

add_executable(tafuzz-sa
  cli/production_entry.cpp
  cli/production_main.cpp
)
add_dependencies(tafuzz-sa rift_embedded_manifest_artifacts)
target_include_directories(tafuzz-sa PRIVATE "${RIFT_GENERATED_DIR}")
target_include_directories(tafuzz-sa SYSTEM PRIVATE
  ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
  ${LLVM_INCLUDE_DIRS}
)
target_compile_options(tafuzz-sa PRIVATE -Wall -Wextra -Werror)
target_link_libraries(tafuzz-sa PRIVATE
  rift_production_core rift_clang_cpp LLVM)

# Keep the M3 weak baselines available without making the portable production
# analyzer load SVF/Z3 or baseline-only code.  The frozen M3 publication
# artifacts retain their original analyzer binary and are not regenerated.
add_executable(tafuzz-sa-baselines
  cli/baseline_main.cpp
  cli/production_main.cpp
)
add_dependencies(tafuzz-sa-baselines rift_embedded_manifest_artifacts)
target_include_directories(tafuzz-sa-baselines PRIVATE "${RIFT_GENERATED_DIR}")
target_include_directories(tafuzz-sa-baselines SYSTEM PRIVATE
  ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
  ${LLVM_INCLUDE_DIRS}
)
target_compile_options(tafuzz-sa-baselines PRIVATE -Wall -Wextra -Werror)
target_compile_definitions(tafuzz-sa-baselines PRIVATE
  RIFT_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}"
  RIFT_SCHEMA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/schema"
)
target_link_libraries(tafuzz-sa-baselines PRIVATE
  rift_ast_baselines rift_production_core rift_clang_cpp LLVM)

if(RIFT_BUILD_LLVM_BASELINES)
  find_package(SVF CONFIG REQUIRED)
  if(NOT SVF_VERSION VERSION_EQUAL "3.2")
    message(FATAL_ERROR "RIFT M3 requires SVF 3.2, found ${SVF_VERSION}")
  endif()

  add_library(rift_llvm_baselines STATIC
    core/baselines/llvm/llvm_baselines.cpp
    core/baselines/llvm/llvm_ir_common.cpp
    core/baselines/llvm/llvm_ssa.cpp
    core/baselines/llvm/llvm_memoryssa.cpp
    core/baselines/llvm/svf_valueflow.cpp
  )
  target_include_directories(rift_llvm_baselines
    PUBLIC "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
    PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/core/baselines/llvm"
  )
  target_include_directories(rift_llvm_baselines SYSTEM PRIVATE
    ${LLVM_INCLUDE_DIRS}
  )
  target_compile_options(rift_llvm_baselines PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_llvm_baselines
    PUBLIC SVF::SvfLLVM SVF::SvfCore LLVM)
  target_compile_definitions(
    tafuzz-sa-baselines PRIVATE RIFT_WITH_LLVM_BASELINES=1)
  target_link_libraries(tafuzz-sa-baselines PRIVATE rift_llvm_baselines)
endif()

if(RIFT_BUILD_TESTS)
  include(CTest)
  foreach(smoke IN ITEMS assignment moonshine plain_pdg)
    add_executable(
      rift_${smoke}_smoke
      "core/baselines/ast/${smoke}_smoke.cpp"
    )
    target_include_directories(rift_${smoke}_smoke SYSTEM PRIVATE
      ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
      ${LLVM_INCLUDE_DIRS}
    )
    target_compile_options(rift_${smoke}_smoke PRIVATE -Wall -Wextra -Werror)
    target_link_libraries(
      rift_${smoke}_smoke PRIVATE rift_ast_baselines rift_clang_cpp LLVM)
    add_test(NAME rift_${smoke}_smoke COMMAND rift_${smoke}_smoke)
  endforeach()

  foreach(cli_regression IN ITEMS
      compile_directory_invariance
      path_invocation
      tool_error_mapping
      repeated_method_last_wins)
    add_test(
      NAME rift_cli_${cli_regression}
      COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/cli_regressions.py"
        --mode "${cli_regression}"
        --binary "$<TARGET_FILE:tafuzz-sa-baselines>"
    )
    set_tests_properties(rift_cli_${cli_regression} PROPERTIES
      ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1"
      RUN_SERIAL TRUE)
  endforeach()

  add_test(
    NAME rift_production_schema_contract
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/schema/validate_schemas.py"
      --schema-dir "${CMAKE_CURRENT_SOURCE_DIR}/schema"
  )
  set_tests_properties(rift_production_schema_contract PROPERTIES
    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")

  add_test(
    NAME rift_embedded_build_manifest
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/build_manifest_test.py"
  )
  set_tests_properties(rift_embedded_build_manifest PROPERTIES
    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")

  add_test(
    NAME rift_embedded_build_manifest_parallel
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/embedded_manifest_parallel.py"
      --generator
        "${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_embedded_manifest.py"
      --source-root "${CMAKE_CURRENT_SOURCE_DIR}"
  )
  set_tests_properties(rift_embedded_build_manifest_parallel PROPERTIES
    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1"
    TIMEOUT 60)

  add_test(
    NAME rift_production_cli_portability
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/production_cli_portability.py"
      --binary "$<TARGET_FILE:tafuzz-sa>"
  )
  set_tests_properties(rift_production_cli_portability PROPERTIES
    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1"
    RUN_SERIAL TRUE)

  add_executable(
    rift_production_smoke
    core/production/production_smoke.cpp
  )
  target_include_directories(rift_production_smoke SYSTEM PRIVATE
    ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
    ${LLVM_INCLUDE_DIRS}
  )
  target_compile_options(rift_production_smoke PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_production_smoke PRIVATE rift_production_core)
  add_test(NAME rift_production_smoke COMMAND rift_production_smoke)

  add_executable(
    rift_file_sha256_smoke
    tests/file_sha256_smoke.cpp
  )
  target_compile_options(rift_file_sha256_smoke PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_file_sha256_smoke PRIVATE rift_production_core)
  add_test(NAME rift_file_sha256_smoke COMMAND rift_file_sha256_smoke)
  set_tests_properties(rift_file_sha256_smoke PROPERTIES
    RUN_SERIAL TRUE
    TIMEOUT 60)

  foreach(m5_smoke IN ITEMS model_vm frontier recipe)
    add_executable(
      rift_${m5_smoke}_smoke
      "tests/${m5_smoke}_smoke.cpp"
    )
    target_include_directories(rift_${m5_smoke}_smoke SYSTEM PRIVATE
      ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
      ${LLVM_INCLUDE_DIRS}
      ${RIFT_Z3_INCLUDE_DIR}
    )
    target_compile_options(rift_${m5_smoke}_smoke PRIVATE
      -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(rift_${m5_smoke}_smoke PRIVATE rift_production_core)
    add_test(NAME rift_${m5_smoke}_smoke COMMAND rift_${m5_smoke}_smoke)
  endforeach()

  add_executable(
    rift_predicate_occurrence_smoke
    tests/predicate_occurrence_smoke.cpp
  )
  target_include_directories(rift_predicate_occurrence_smoke SYSTEM PRIVATE
    ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
    ${LLVM_INCLUDE_DIRS}
  )
  target_compile_options(rift_predicate_occurrence_smoke PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_predicate_occurrence_smoke PRIVATE
    rift_production_core)
  add_test(
    NAME rift_predicate_occurrence_smoke
    COMMAND rift_predicate_occurrence_smoke)

  add_executable(
    rift_value_transfer_smoke
    tests/value_transfer_smoke.cpp
  )
  target_include_directories(rift_value_transfer_smoke SYSTEM PRIVATE
    ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
    ${LLVM_INCLUDE_DIRS}
  )
  target_compile_options(rift_value_transfer_smoke PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_value_transfer_smoke PRIVATE
    rift_production_core)
  add_test(
    NAME rift_value_transfer_smoke
    COMMAND rift_value_transfer_smoke)

  add_executable(
    rift_payload_projection_smoke
    tests/payload_projection_smoke.cpp
  )
  target_include_directories(rift_payload_projection_smoke SYSTEM PRIVATE
    ${RIFT_EFFECTIVE_CLANG_INCLUDE_DIRS}
    ${LLVM_INCLUDE_DIRS}
  )
  target_compile_options(rift_payload_projection_smoke PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_payload_projection_smoke PRIVATE
    rift_production_core)
  add_test(
    NAME rift_payload_projection_smoke
    COMMAND rift_payload_projection_smoke)

  add_test(
    NAME rift_predicate_occurrence_schema_smoke
    COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/predicate_occurrence_schema_smoke.py"
      --binary "$<TARGET_FILE:rift_predicate_occurrence_smoke>"
      --schema-dir "${CMAKE_CURRENT_SOURCE_DIR}/schema"
  )
  set_tests_properties(rift_predicate_occurrence_schema_smoke PROPERTIES
    ENVIRONMENT "PYTHONDONTWRITEBYTECODE=1")

  add_executable(
    rift_capabilities_smoke
    tests/capabilities_smoke.cpp
  )
  target_include_directories(rift_capabilities_smoke SYSTEM PRIVATE
    ${LLVM_INCLUDE_DIRS}
  )
  target_compile_options(rift_capabilities_smoke PRIVATE
    -Wall -Wextra -Wpedantic -Werror)
  target_link_libraries(rift_capabilities_smoke PRIVATE rift_production_core)
  add_test(
    NAME rift_capabilities_smoke
    COMMAND rift_capabilities_smoke
      "${CMAKE_CURRENT_SOURCE_DIR}/../../benchmark/rift/m5/model_packs/neutral_executor_capabilities.json"
  )

  if(RIFT_BUILD_LLVM_BASELINES)
    find_program(RIFT_CLANG_18_EXECUTABLE NAMES clang-18 REQUIRED)
    find_program(RIFT_OPT_18_EXECUTABLE NAMES opt-18 REQUIRED)
    set(RIFT_LLVM_FIXTURE_DIR "${CMAKE_CURRENT_BINARY_DIR}/llvm-fixtures")
    set(RIFT_LLVM_MEMORY_FIXTURE "${RIFT_LLVM_FIXTURE_DIR}/neutral-memory.bc")
    set(RIFT_LLVM_SSA_FIXTURE "${RIFT_LLVM_FIXTURE_DIR}/neutral-ssa.bc")
    add_custom_command(
      OUTPUT "${RIFT_LLVM_MEMORY_FIXTURE}"
      COMMAND "${CMAKE_COMMAND}" -E make_directory "${RIFT_LLVM_FIXTURE_DIR}"
      COMMAND "${RIFT_CLANG_18_EXECUTABLE}"
        -g -O0 -fno-discard-value-names -Xclang -disable-O0-optnone
        -emit-llvm -c
        "${CMAKE_CURRENT_SOURCE_DIR}/core/baselines/llvm/fixtures/neutral_baseline_fixture.c"
        -o "${RIFT_LLVM_MEMORY_FIXTURE}"
      DEPENDS core/baselines/llvm/fixtures/neutral_baseline_fixture.c
      VERBATIM
    )
    add_custom_command(
      OUTPUT "${RIFT_LLVM_SSA_FIXTURE}"
      COMMAND "${RIFT_OPT_18_EXECUTABLE}" -passes=mem2reg
        "${RIFT_LLVM_MEMORY_FIXTURE}" -o "${RIFT_LLVM_SSA_FIXTURE}"
      DEPENDS "${RIFT_LLVM_MEMORY_FIXTURE}"
      VERBATIM
    )
    add_custom_target(rift_llvm_fixture_bitcode
      DEPENDS "${RIFT_LLVM_MEMORY_FIXTURE}" "${RIFT_LLVM_SSA_FIXTURE}")

    add_executable(rift_llvm_baselines_smoke
      core/baselines/llvm/fixtures/llvm_baselines_smoke.cpp)
    target_compile_options(rift_llvm_baselines_smoke PRIVATE
      -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(rift_llvm_baselines_smoke PRIVATE rift_llvm_baselines)
    add_dependencies(rift_llvm_baselines_smoke rift_llvm_fixture_bitcode)
    add_test(
      NAME rift_llvm_baselines_smoke
      COMMAND rift_llvm_baselines_smoke
        "${RIFT_LLVM_SSA_FIXTURE}" "${RIFT_LLVM_MEMORY_FIXTURE}"
    )
  endif()
endif()
