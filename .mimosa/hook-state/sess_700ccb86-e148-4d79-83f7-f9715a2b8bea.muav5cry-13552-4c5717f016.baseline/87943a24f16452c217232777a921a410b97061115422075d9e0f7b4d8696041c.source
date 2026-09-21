/** test_main.c — 测试入口与汇总 */
#include "test_util.h"

void test_actions_all(void);
void test_closedloop_all(void);
void test_proto_all(void);

int pn_tests_run = 0;
int pn_tests_failed = 0;

int main(void)
{
    printf("=== pn_core host unit tests ===\n");
    test_actions_all();
    test_closedloop_all();
    test_proto_all();
    printf("=== %d tests, %d failed ===\n", pn_tests_run, pn_tests_failed);
    return pn_tests_failed ? 1 : 0;
}
