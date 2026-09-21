cmake_minimum_required(VERSION 3.16)
project(pn_virtual C)
set(CMAKE_C_STANDARD 11)

set(PN_CORE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../components/pn_core)

add_library(pn_core STATIC
    ${PN_CORE_DIR}/src/actions.c
    ${PN_CORE_DIR}/src/closedloop.c
    ${PN_CORE_DIR}/src/proto.c
    ${PN_CORE_DIR}/src/cli.c
)
target_include_directories(pn_core PUBLIC ${PN_CORE_DIR}/include)

add_executable(pn_virtual
    virtual_main.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../tests/mock_hal.c
)
target_include_directories(pn_virtual PRIVATE
    ${PN_CORE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../tests
)
target_link_libraries(pn_virtual pn_core)

if(WIN32)
    target_compile_definitions(pn_virtual PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()
