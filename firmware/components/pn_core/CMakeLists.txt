idf_component_register(
    SRCS "src/actions.c" "src/closedloop.c" "src/proto.c" "src/cli.c" "src/leak_detect.c"
    INCLUDE_DIRS "include"
    PRIV_REQUIRES pn_ml
)
