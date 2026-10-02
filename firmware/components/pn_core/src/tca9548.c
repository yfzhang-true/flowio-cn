/** tca9548.c — TCA9548A 纯逻辑驱动实现（mock 总线表 + hal 注入点） */
#include "pn_core/tca9548.h"

/* 本期通道拓扑：CH0/CH1=XGZP#1/#2，CH2-4 预留 */
#define TCA_CH_MAX      5
#define TCA_PER_CH_MAX  4        /* 每通道 mock 最多挂 4 个设备地址 */

static tca_i2c_write_fn s_fn;    /* 真机注入；NULL=主机 mock 模式 */

/* mock 总线表：attached=挂载地址，pa=该地址的 Pa×10 模拟值 */
static uint8_t s_mock_addr[TCA_CH_MAX][TCA_PER_CH_MAX];
static int32_t s_mock_pa[TCA_CH_MAX][TCA_PER_CH_MAX];
static uint8_t s_mock_n[TCA_CH_MAX];
static uint8_t s_mock_cur = TCA_MANIFOLD;   /* 当前选通通道（select 记录） */

uint8_t tca_encode(uint8_t ch)
{
    return (ch < TCA_CH_MAX) ? (uint8_t)(1u << ch) : 0;
}

void tca_bind(tca_i2c_write_fn fn)
{
    s_fn = fn;
}

tca_err_t tca_select(uint8_t ch)
{
    if (ch == TCA_MANIFOLD) {
        /* 汇流管直连：写 0x00 断开全部下游（旁路 encode——0xFF 编码本为非法 0） */
        if (s_fn) return (s_fn(TCA_ADDR, 0x00) == 0) ? TCA_OK : TCA_ERR_BUS;
        s_mock_cur = TCA_MANIFOLD;
        return TCA_OK;
    }
    uint8_t code = tca_encode(ch);
    if (code == 0) return TCA_ERR_CHAN;
    if (s_fn) return (s_fn(TCA_ADDR, code) == 0) ? TCA_OK : TCA_ERR_BUS;
    s_mock_cur = ch;             /* mock 模式：仅记录当前通道 */
    return TCA_OK;
}

void tca_mock_reset(void)
{
    for (int c = 0; c < TCA_CH_MAX; ++c) {
        s_mock_n[c] = 0;
        for (int i = 0; i < TCA_PER_CH_MAX; ++i) {
            s_mock_addr[c][i] = 0;
            s_mock_pa[c][i]   = 0;
        }
    }
    s_mock_cur = TCA_MANIFOLD;
}

void tca_mock_attach(uint8_t ch, uint8_t addr, int32_t pa10)
{
    if (ch >= TCA_CH_MAX) return;
    uint8_t n = s_mock_n[ch];
    if (n >= TCA_PER_CH_MAX) return;          /* 满员静默丢弃（测试契约） */
    s_mock_addr[ch][n] = addr;
    s_mock_pa[ch][n]   = pa10;
    s_mock_n[ch]       = (uint8_t)(n + 1);
}

tca_err_t tca_scan(uint8_t ch, uint8_t *addrs, uint8_t max, uint8_t *n_out)
{
    if (ch >= TCA_CH_MAX) return TCA_ERR_CHAN;
    if (s_fn) return TCA_ERR_BUS;   /* 真机探测由 hal 层负责（i2c probe 扫描） */
    uint8_t n = s_mock_n[ch];
    if (n_out) *n_out = n;
    if (addrs) {
        uint8_t c = (n > max) ? max : n;
        for (uint8_t i = 0; i < c; ++i) addrs[i] = s_mock_addr[ch][i];
    }
    return TCA_OK;
}

tca_err_t tca_read_pa(uint8_t ch, int32_t *pa10)
{
    if (ch >= TCA_CH_MAX) return TCA_ERR_CHAN;
    if (s_fn) return TCA_ERR_BUS;   /* 真机读数走 hal 的 XGZP 字节级路径 */
    (void)tca_select(ch);           /* 语义上先选通（mock 下仅记录，必 OK） */
    if (s_mock_n[ch] == 0) return TCA_ERR_BUS;      /* 空通道=总线无应答 */
    if (pa10) *pa10 = s_mock_pa[ch][0];             /* 首传感器 */
    return TCA_OK;
}
