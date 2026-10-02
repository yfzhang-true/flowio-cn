/** sensor_if.c — 传感器抽象：转发 tca9548 并映射错误码（纯逻辑） */
#include "pn_core/sensor_if.h"
#include "pn_core/tca9548.h"

#include <stddef.h>   /* NULL（交叉编译器不传递包含） */

/* tca_err_t → sens_err_t 契约：ERR_BUS→DISCONNECT，ERR_CHAN→DISCONNECT
 * （对上层而言两者都是"这路没有可用的传感器"） */
static sens_err_t map_err(tca_err_t e)
{
    switch (e) {
    case TCA_OK:       return SENS_OK;
    case TCA_ERR_BUS:  return SENS_DISCONNECT;
    case TCA_ERR_CHAN: return SENS_DISCONNECT;
    }
    return SENS_DISCONNECT;
}

sens_err_t sensor_probe(uint8_t ch, sensor_type_t *out)
{
    uint8_t n = 0;
    tca_err_t e = tca_scan(ch, NULL, 0, &n);      /* 只取挂载数量 */
    if (e != TCA_OK) return map_err(e);
    if (out) *out = (n > 0) ? SENSOR_MOCK_XGZP : SENSOR_NONE;
    return SENS_OK;
}

sens_err_t sensor_read_pa(uint8_t ch, int32_t *pa10)
{
    return map_err(tca_read_pa(ch, pa10));
}
