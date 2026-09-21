cmake_minimum_required(VERSION 3.16)
project(pn_tests C)
set(CMAKE_C_STANDARD 11)

set(PN_CORE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../components/pn_core)

add_library(pn_core STATIC
    ${PN_CORE_DIR}/src/actions.c
    ${PN_CORE_DIR}/src/closedloop.c
    ${PN_CORE_DIR}/src/proto.c
)
target_include_directories(pn_core PUBLIC ${PN_CORE_DIR}/include)

add_executable(pn_tests
    test_main.c
    test_actions.c
    test_closedloop.c
    test_proto.c
    mock_hal.c
)
target_include_directories(pn_tests PRIVATE ${PN_CORE_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(pn_tests pn_core)

if(WIN32)
    target_compile_definitions(pn_tests PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()

enable_testing()
add_test(NAME pn_tests COMMAND pn_tests)
