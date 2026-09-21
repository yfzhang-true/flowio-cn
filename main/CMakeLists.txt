idf_component_register(
    SRCS "main.c"
    REQUIRES pn_core pn_hal_esp32
    PRIV_REQUIRES esp_timer
)
