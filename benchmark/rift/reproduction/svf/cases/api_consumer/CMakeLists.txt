cmake_minimum_required(VERSION 3.23)
project(svf_api_consumer LANGUAGES CXX)

find_package(SVF 3.2 CONFIG REQUIRED)

add_executable(svf_api_smoke svf_api_smoke.cpp)
target_compile_features(svf_api_smoke PRIVATE cxx_std_17)
target_link_libraries(svf_api_smoke PRIVATE SVF::SvfLLVM SVF::SvfCore)
