/** test_util.h — 极简测试框架（无外部依赖） */
#pragma once

#include <stdio.h>

extern int pn_tests_run;
extern int pn_tests_failed;

#define CHECK(cond) do { \
    if (!(cond)) { \
        printf("      FAIL %s:%d  CHECK(%s)\n", __FILE__, __LINE__, #cond); \
        ++pn_tests_failed; \
    } \
} while (0)

#define RUN_TEST(fn) do { \
    int before = pn_tests_failed; \
    printf("[ RUN ] %s\n", #fn); \
    ++pn_tests_run; \
    fn(); \
    printf("[ %s ] %s\n", (before == pn_tests_failed) ? "PASS" : "FAIL", #fn); \
} while (0)
