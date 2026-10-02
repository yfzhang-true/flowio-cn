idf_component_register(
    SRCS "src/hal_esp32.c" "src/ble_twin.c"
    INCLUDE_DIRS "include"
    REQUIRES driver pn_core
    PRIV_REQUIRES esp_timer led_strip bt nvs_flash esp_hw_support
)
