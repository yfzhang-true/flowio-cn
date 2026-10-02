/**
 * pn_hal_esp32/src/ble_twin.c — BLE GATT 双胎服务实现（S5）
 *
 * 契约真源：firmware/twin/BLE.md（UUID 表/服务属性/载荷布局/时序）。
 * 线程模型：
 *   - NimBLE host 任务（port 自建）跑协议栈与 GATT 回调；
 *   - cmd write 回调只投 FreeRTOS 队列，cmd_task 出队调 pn_cmd_feed()
 *     （与串口同一 CLI 解析路径，互斥由 pn_cmd_feed 内部保证）；
 *   - state notify 由 main 的 10ms control_task 调 ble_twin_tick_10ms() 驱动；
 *   - 小共享态（resp 行/pwm 参数/state 帧）由 s_lock 串行化。
 * QEMU：esp32s3 无 BT 控制器仿真 → init 打印跳过（pn_hal_esp32_is_qemu 检测）。
 * 编译期未开 BT（CONFIG_BT_ENABLED）：全接口 stub，链接零成本。
 */
#include "sdkconfig.h"          /* CONFIG_BT_ENABLED（IDF 不强制注入，须显式 include） */

#include "pn_hal_esp32/ble_twin.h"
#include "pn_core/actions.h"
#include "pn_core/ble_frame.h"
#include "pn_core/cli.h"
#include "pn_hal_esp32/hal_esp32.h"

#include <stdio.h>

#ifdef CONFIG_BT_ENABLED

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "esp_timer.h"
#include "esp_mac.h"
#include "nvs_flash.h"

#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_gap.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "store/config/ble_store_config.h"
#include "os/os_mbuf.h"

/* 本版 IDF 的 ble_store_config.h 未声明 init（实现在同组件 .c）——显式声明 */
extern void ble_store_config_init(void);

#include <string.h>
#include <stdio.h>

/* ---------- UUID（BLE.md §2：基址 f10a5c00-0000-4b1e-9c2d-8e3a1b0f0000） ----------
 * NimBLE 128bit 存储为小端字节数组：value[0]=UUID 最低位字节（=后缀低字节）。 */
#define PN_BLE_UUID_BASE_LE(sfx) {                                    \
    (uint8_t)((sfx) & 0xFF), (uint8_t)(((sfx) >> 8) & 0xFF),          \
    0x0F, 0x1B, 0x3A, 0x8E, 0x2D, 0x9C, 0x1E, 0x4B,                   \
    0x00, 0x00, 0x00, 0x5C, 0x0A, 0xF1 }

#define PN_BLE_UUID_SUFFIX_SVC_CMD    0x0001
#define PN_BLE_UUID_SUFFIX_CHR_CMD    0x0002
#define PN_BLE_UUID_SUFFIX_CHR_RESP   0x0003
#define PN_BLE_UUID_SUFFIX_SVC_TELEM  0x0004
#define PN_BLE_UUID_SUFFIX_CHR_STATE  0x0005
#define PN_BLE_UUID_SUFFIX_CHR_NOTEN  0x0006
#define PN_BLE_UUID_SUFFIX_SVC_CFG    0x0007
#define PN_BLE_UUID_SUFFIX_CHR_PWM    0x0008
#define PN_BLE_UUID_SUFFIX_CHR_BREV   0x0009

static const ble_uuid128_t s_uuid_svc_cmd = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_SVC_CMD),
};
static const ble_uuid128_t s_uuid_chr_cmd = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_CHR_CMD),
};
static const ble_uuid128_t s_uuid_chr_resp = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_CHR_RESP),
};
static const ble_uuid128_t s_uuid_svc_telem = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_SVC_TELEM),
};
static const ble_uuid128_t s_uuid_chr_state = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_CHR_STATE),
};
static const ble_uuid128_t s_uuid_chr_noten = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_CHR_NOTEN),
};
static const ble_uuid128_t s_uuid_svc_cfg = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_SVC_CFG),
};
static const ble_uuid128_t s_uuid_chr_pwm = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_CHR_PWM),
};
static const ble_uuid128_t s_uuid_chr_brev = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = PN_BLE_UUID_BASE_LE(PN_BLE_UUID_SUFFIX_CHR_BREV),
};

/* ---------- 运行态 ---------- */
static SemaphoreHandle_t s_lock;                  /* resp 行/pwm/state 帧共享锁 */
static QueueHandle_t    s_cmd_q;
typedef struct {
    uint16_t len;
    uint8_t  buf[PN_BLE_CMD_MAX];
} cmd_msg_t;

static uint16_t s_conn_h = BLE_HS_CONN_HANDLE_NONE;
static uint16_t s_chr_val_h_cmd, s_chr_val_h_resp, s_chr_val_h_state;
static bool     s_resp_sub, s_state_sub;
static volatile uint8_t s_notify_en;

static char s_adv_name[24];                       /* FLOWIO-P1-XXXX */
static char s_serial[13];                         /* BT MAC 12 hex */

/* Config 服务 RAM 镜像（BLE.md §4.3：pump_max | hold_duty | hold_ms LE） */
static uint8_t s_pwm_params[4];

/* resp：最近一条 CLI 应答行（cli_out sink 写入） */
static char    s_resp_line[64];
static uint8_t s_resp_len;

/* state：最近一次打包的 20B 帧（read 特征返回它） */
static uint8_t s_state_frame[PN_BLE_STATE_LEN];

static int put_line_locked(const char *line);     /* 前向声明 */
static void start_adv(void);

/* ---------- GATT 访问回调 ---------- */

/* DeviceInfo（0x180A）：三个只读 ASCII 特征 */
static int acc_devinfo(uint16_t conn, uint16_t attr,
                       struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr;
    const char *s;
    switch ((int)(intptr_t)arg) {
    case 0:  s = PN_FW_VERSION; break;                        /* 0x2A26 */
    case 1:  s = s_serial;       break;                        /* 0x2A25 */
    default: s = PN_BOARD_REV;   break;                        /* 0009 */
    }
    if (ctxt->op != BLE_GATT_ACCESS_OP_READ_CHR) return BLE_ATT_ERR_READ_NOT_PERMITTED;
    return os_mbuf_append(ctxt->om, s, (uint16_t)strlen(s));
}

/* Command 服务：cmd write / resp read+notify */
static int acc_cmd(uint16_t conn, uint16_t attr,
                   struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR &&
        (uintptr_t)arg == PN_BLE_UUID_SUFFIX_CHR_CMD) {
        /* cmd 帧入队（0xA5 帧或 ASCII 行均可），cmd_task 出队统一走 pn_cmd_feed */
        cmd_msg_t m = { 0 };
        uint16_t copied = 0;
        int rc = ble_hs_mbuf_to_flat(ctxt->om, m.buf, PN_BLE_CMD_MAX, &copied);
        if (rc != 0) return rc;
        m.len = copied;
        if (!s_cmd_q || xQueueSend(s_cmd_q, &m, 0) != pdTRUE) {
            printf("[BLE] cmd queue full, dropped\n");
            return BLE_ATT_ERR_PREPARE_QUEUE_FULL; /* CCC 语义近似：忙 */
        }
        return 0;
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR &&
        (uintptr_t)arg == PN_BLE_UUID_SUFFIX_CHR_RESP) {
        int rc;
        xSemaphoreTake(s_lock, portMAX_DELAY);
        rc = os_mbuf_append(ctxt->om, (const uint8_t *)s_resp_line, s_resp_len);
        xSemaphoreGive(s_lock);
        return rc;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

/* Telemetry 服务：state read / notify_en read+write */
static int acc_telem(uint16_t conn, uint16_t attr,
                     struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr;
    if ((uintptr_t)arg == PN_BLE_UUID_SUFFIX_CHR_STATE) {
        if (ctxt->op != BLE_GATT_ACCESS_OP_READ_CHR)
            return BLE_ATT_ERR_READ_NOT_PERMITTED;
        int rc;
        xSemaphoreTake(s_lock, portMAX_DELAY);
        rc = os_mbuf_append(ctxt->om, s_state_frame, PN_BLE_STATE_LEN);
        xSemaphoreGive(s_lock);
        return rc;
    }
    /* notify_en */
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        uint8_t v = s_notify_en;
        return os_mbuf_append(ctxt->om, &v, 1);
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t v = 0;
        uint16_t copied = 0;
        if (ble_hs_mbuf_to_flat(ctxt->om, &v, 1, &copied) != 0 || copied != 1)
            return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
        s_notify_en = v;
        printf("[BLE] notify_en=%u\n", (unsigned)v);
        return 0;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

/* Config 服务：pwm_params read+write（4B RAM 镜像，BLE.md §3.4） */
static int acc_cfg(uint16_t conn, uint16_t attr,
                   struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    int rc;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        xSemaphoreTake(s_lock, portMAX_DELAY);
        rc = os_mbuf_append(ctxt->om, s_pwm_params, 4);
        xSemaphoreGive(s_lock);
        return rc;
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t tmp[4];
        uint16_t copied = 0;
        if (ble_hs_mbuf_to_flat(ctxt->om, tmp, 4, &copied) != 0 || copied != 4)
            return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
        xSemaphoreTake(s_lock, portMAX_DELAY);
        memcpy(s_pwm_params, tmp, 4);
        xSemaphoreGive(s_lock);
        printf("[BLE] pwm: max=%u hold=%u delay=%ums\n",
               s_pwm_params[0], s_pwm_params[1],
               (unsigned)(s_pwm_params[2] | ((uint16_t)s_pwm_params[3] << 8)));
        return 0;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

/* ---------- GATT 表（四服务，BLE.md §3） ---------- */
static const struct ble_gatt_svc_def gatt_svcs[] = {
{
    .type = BLE_GATT_SVC_TYPE_PRIMARY,
    .uuid = BLE_UUID16_DECLARE(0x180A),            /* DeviceInfo（SIG） */
    .characteristics = (struct ble_gatt_chr_def[]) {
        { .uuid = BLE_UUID16_DECLARE(0x2A26),      /* fw_version */
          .access_cb = acc_devinfo, .arg = (void *)(intptr_t)0,
          .flags = BLE_GATT_CHR_F_READ },
        { .uuid = BLE_UUID16_DECLARE(0x2A25),      /* serial_no */
          .access_cb = acc_devinfo, .arg = (void *)(intptr_t)1,
          .flags = BLE_GATT_CHR_F_READ },
        { .uuid = &s_uuid_chr_brev.u,              /* board_rev（自定 0009） */
          .access_cb = acc_devinfo, .arg = (void *)(intptr_t)2,
          .flags = BLE_GATT_CHR_F_READ },
        { 0 },
    },
},
{
    .type = BLE_GATT_SVC_TYPE_PRIMARY,
    .uuid = &s_uuid_svc_cmd.u,                    /* FlowIO Command（0001） */
    .characteristics = (struct ble_gatt_chr_def[]) {
        { .uuid = &s_uuid_chr_cmd.u,               /* cmd（0002） */
          .access_cb = acc_cmd, .arg = (void *)(intptr_t)PN_BLE_UUID_SUFFIX_CHR_CMD,
          .flags = BLE_GATT_CHR_F_WRITE,
          .val_handle = &s_chr_val_h_cmd },
        { .uuid = &s_uuid_chr_resp.u,              /* resp（0003） */
          .access_cb = acc_cmd, .arg = (void *)(intptr_t)PN_BLE_UUID_SUFFIX_CHR_RESP,
          .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
          .val_handle = &s_chr_val_h_resp },
        { 0 },
    },
},
{
    .type = BLE_GATT_SVC_TYPE_PRIMARY,
    .uuid = &s_uuid_svc_telem.u,                  /* FlowIO Telemetry（0004） */
    .characteristics = (struct ble_gatt_chr_def[]) {
        { .uuid = &s_uuid_chr_state.u,             /* state（0005，20B） */
          .access_cb = acc_telem, .arg = (void *)(intptr_t)PN_BLE_UUID_SUFFIX_CHR_STATE,
          .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
          .val_handle = &s_chr_val_h_state },
        { .uuid = &s_uuid_chr_noten.u,             /* notify_en（0006） */
          .access_cb = acc_telem, .arg = (void *)(intptr_t)PN_BLE_UUID_SUFFIX_CHR_NOTEN,
          .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE },
        { 0 },
    },
},
{
    .type = BLE_GATT_SVC_TYPE_PRIMARY,
    .uuid = &s_uuid_svc_cfg.u,                    /* FlowIO Config（0007） */
    .characteristics = (struct ble_gatt_chr_def[]) {
        { .uuid = &s_uuid_chr_pwm.u,               /* pwm_params（0008，4B） */
          .access_cb = acc_cfg, .arg = (void *)(intptr_t)PN_BLE_UUID_SUFFIX_CHR_PWM,
          .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE },
        { 0 },
    },
},
    { 0 },
};

/* ---------- GAP：广播 / 连接 / 订阅 ---------- */
static int gap_event(struct ble_gap_event *event, void *arg)
{
    (void)arg;
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status != 0) {           /* 建连失败 → 重新广播 */
            s_conn_h = BLE_HS_CONN_HANDLE_NONE;
            start_adv();
            return 0;
        }
        s_conn_h = event->connect.conn_handle;
        printf("[BLE] connected handle=%u\n", s_conn_h);
        return 0;
    case BLE_GAP_EVENT_DISCONNECT:
        printf("[BLE] disconnected reason=%d\n", event->disconnect.reason);
        s_conn_h = BLE_HS_CONN_HANDLE_NONE;
        s_resp_sub = s_state_sub = false;
        start_adv();                                /* 断开后由应用重启广播 */
        return 0;
    case BLE_GAP_EVENT_SUBSCRIBE:
        if (event->subscribe.attr_handle == s_chr_val_h_resp)
            s_resp_sub = event->subscribe.cur_notify || event->subscribe.cur_indicate;
        if (event->subscribe.attr_handle == s_chr_val_h_state)
            s_state_sub = event->subscribe.cur_notify || event->subscribe.cur_indicate;
        return 0;
    default:
        return 0;
    }
}

static void start_adv(void)
{
    struct ble_hs_adv_fields f = { 0 };
    f.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    f.uuids128 = &s_uuid_svc_cmd;                   /* Command 服务 UUID（complete） */
    f.num_uuids128 = 1;
    f.uuids128_is_complete = 1;
    int rc = ble_gap_adv_set_fields(&f);

    struct ble_hs_adv_fields rf = { 0 };            /* 名字放 scan response（31B 装不下） */
    rf.name = (const uint8_t *)s_adv_name;
    rf.name_len = (uint8_t)strlen(s_adv_name);
    rf.name_is_complete = 1;
    if (rc == 0) rc = ble_gap_adv_rsp_set_fields(&rf);

    struct ble_gap_adv_params p = { 0 };
    p.conn_mode = BLE_GAP_CONN_MODE_UND;
    p.disc_mode = BLE_GAP_DISC_MODE_GEN;
    if (rc == 0)
        rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                               &p, gap_event, NULL);
    if (rc != 0) printf("[BLE] adv start failed rc=%d\n", rc);
}

static void on_sync(void)
{
    ble_svc_gap_device_name_set(s_adv_name);
    start_adv();
    printf("[BLE] advertising as %s\n", s_adv_name);
}

static void on_reset(int reason)
{
    printf("[BLE] host reset, reason=%d\n", reason);
}

/* ---------- cmd 分发任务（与串口同一 pn_cmd_feed 入口） ---------- */
static void cmd_task(void *arg)
{
    (void)arg;
    cmd_msg_t m;
    for (;;) {
        if (xQueueReceive(s_cmd_q, &m, portMAX_DELAY) == pdTRUE)
            pn_cmd_feed(m.buf, m.len);
    }
}

/* ---------- CLI 应答行 sink（cli_out → resp 特征） ---------- */
static int put_line_locked(const char *line)
{
    size_t n = strlen(line);
    if (n >= sizeof(s_resp_line)) n = sizeof(s_resp_line) - 1;
    memcpy(s_resp_line, line, n);
    s_resp_line[n] = 0;
    s_resp_len = (uint8_t)n;
    return 0;
}

static void resp_sink(const char *line)
{
    struct os_mbuf *om = NULL;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    put_line_locked(line);
    if (s_resp_sub && s_conn_h != BLE_HS_CONN_HANDLE_NONE)
        om = ble_hs_mbuf_from_flat(s_resp_line, s_resp_len);
    xSemaphoreGive(s_lock);
    if (om)
        ble_gatts_notify_custom(s_conn_h, s_chr_val_h_resp, om);
}

/* ---------- host 任务 ---------- */
static void host_task(void *param)
{
    (void)param;
    nimble_port_run();                              /* 阻塞至栈停止 */
    nimble_port_freertos_deinit();                  /* port 自清理本任务 */
}

/* ---------- 公共 API ---------- */
void ble_twin_init(void)
{
    /* QEMU esp32s3 无 BT 控制器仿真：跳过（BLE.md §8 双保险之一） */
    if (pn_hal_esp32_is_qemu()) {
        printf("[BLE] QEMU detected, skip BT init\n");
        return;
    }

    /* bond 持久化需要 NVS（失败按标准姿势擦除重试） */
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* serial_no / 广播名后缀 = BT MAC（BLE.md §5） */
    uint8_t mac[6] = { 0 };
    esp_read_mac(mac, ESP_MAC_BT);
    snprintf(s_serial, sizeof(s_serial), "%02X%02X%02X%02X%02X%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    snprintf(s_adv_name, sizeof(s_adv_name), "%s%04X", PN_BLE_ADV_PREFIX,
             (unsigned)((mac[4] << 8) | mac[5]));

    /* pwm 参数 RAM 镜像初值 = 编译期默认（契约 §3.4） */
    s_pwm_params[0] = 255;
    s_pwm_params[1] = PN_HOLD_DEFAULT_DUTY;
    s_pwm_params[2] = (uint8_t)(PN_HOLD_DEFAULT_DELAY_MS & 0xFF);
    s_pwm_params[3] = (uint8_t)(PN_HOLD_DEFAULT_DELAY_MS >> 8);

    strcpy(s_resp_line, "boot");                    /* 未产生应答时的 read 值 */
    s_resp_len = (uint8_t)strlen(s_resp_line);

    int16_t pa0[PN_BLE_PRESS_SLOTS] = { 0 };
    ble_state_pack(s_state_frame, 0, pa0, 0);       /* state 特征初始帧 */

    s_lock = xSemaphoreCreateMutex();
    s_cmd_q = xQueueCreate(8, sizeof(cmd_msg_t));
    if (!s_lock || !s_cmd_q) {
        printf("[BLE] os resource alloc failed\n");
        return;
    }

    err = nimble_port_init();
    if (err != ESP_OK) {
        printf("[BLE] nimble init failed %d\n", err);
        return;
    }

    /* 配对 just-works（契约 §5）：无 IO、bonding、无 MITM、LE 安全连接 */
    ble_hs_cfg.sync_cb  = on_sync;
    ble_hs_cfg.reset_cb = on_reset;
    ble_hs_cfg.sm_io_cap     = BLE_HS_IO_NO_INPUT_OUTPUT;
    ble_hs_cfg.sm_bonding   = 1;
    ble_hs_cfg.sm_mitm      = 0;
    ble_hs_cfg.sm_sc        = 1;
    ble_store_config_init();

    int rc = ble_gatts_count_cfg(gatt_svcs);
    if (rc == 0) rc = ble_gatts_add_svcs(gatt_svcs);
    if (rc == 0) ble_svc_gap_device_name_set(s_adv_name);
    if (rc != 0) {
        printf("[BLE] gatt register failed rc=%d\n", rc);
        return;
    }

    pn_cli_set_resp_sink(resp_sink);                /* CLI 应答行 → resp 特征 */
    xTaskCreate(cmd_task, "ble_cmd", 4096, NULL, 4, NULL);
    nimble_port_freertos_init(host_task);
    printf("[BLE] nimble up, serial=%s\n", s_serial);
}

void ble_twin_tick_10ms(void)
{
    static uint8_t div;
    if (!s_lock || !s_chr_val_h_state) return;      /* 未初始化/服务未就绪 */
    if (++div < 10) return;                         /* 10×10ms = 100ms = 10Hz */
    div = 0;

    /* 传感器 → pa10（读失败填 0x8000 哨兵；slot2-4 P1 预留恒 0，契约 §3.3） */
    int16_t pa[PN_BLE_PRESS_SLOTS] = { 0 };
    for (uint8_t i = 0; i < PN_SENSOR_COUNT && i < PN_BLE_PRESS_SLOTS; ++i) {
        float kpa;
        if (pn_read_pressure(i, &kpa) == PN_OK)
            pa[i] = (int16_t)(kpa * 10.0f + (kpa >= 0.f ? 0.5f : -0.5f));
        else
            pa[i] = PN_BLE_PRESS_INVALID;
    }
    uint16_t tick = (uint16_t)(esp_timer_get_time() / 100000);  /* ms/100 */

    xSemaphoreTake(s_lock, portMAX_DELAY);
    ble_state_pack(s_state_frame, (uint16_t)pn_get_state(), pa, tick);
    xSemaphoreGive(s_lock);

    if (!s_notify_en || !s_state_sub || s_conn_h == BLE_HS_CONN_HANDLE_NONE)
        return;
    struct os_mbuf *om = ble_hs_mbuf_from_flat(s_state_frame, PN_BLE_STATE_LEN);
    if (om)
        ble_gatts_notify_custom(s_conn_h, s_chr_val_h_state, om);
}

uint8_t ble_twin_hold_duty(void)
{
    if (!s_lock) return PN_HOLD_DEFAULT_DUTY;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    uint8_t v = s_pwm_params[1];
    xSemaphoreGive(s_lock);
    return v;
}

uint16_t ble_twin_hold_delay_ms(void)
{
    if (!s_lock) return PN_HOLD_DEFAULT_DELAY_MS;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    uint16_t v = (uint16_t)(s_pwm_params[2] | ((uint16_t)s_pwm_params[3] << 8));
    xSemaphoreGive(s_lock);
    return v;
}

#else /* !CONFIG_BT_ENABLED — stub（BT 关闭/QEMU 外的降级路径） */

void ble_twin_init(void)
{
    printf("[BLE] CONFIG_BT_ENABLED off, skip\n");
}

void ble_twin_tick_10ms(void) { }

uint8_t  ble_twin_hold_duty(void)      { return PN_HOLD_DEFAULT_DUTY; }
uint16_t ble_twin_hold_delay_ms(void)  { return PN_HOLD_DEFAULT_DELAY_MS; }

#endif /* CONFIG_BT_ENABLED */
