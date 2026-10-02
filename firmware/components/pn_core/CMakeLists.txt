idf_component_register(
    SRCS "src/actions.c" "src/closedloop.c" "src/proto.c" "src/cli.c" "src/leak_detect.c"
         "src/tca9548.c" "src/sensor_if.c"
    INCLUDE_DIRS "include"
    PRIV_REQUIRES pn_ml
)
