idf_component_register(
    SRCS "src/hal_esp32.c"
    INCLUDE_DIRS "include"
    REQUIRES driver pn_core
    PRIV_REQUIRES esp_timer
)
