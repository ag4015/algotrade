
configure_file(algotradeConfig.h.in ${CMAKE_CURRENT_SOURCE_DIR}/algotradeConfig.h)

add_subdirectory(krakenapi)

# add the executable
add_executable(algotrade
                Exchange.cpp
                main.cpp
               )

target_compile_options(algotrade PUBLIC -Wall -pedantic -g)

target_include_directories(algotrade PUBLIC
                           src/
                           )

target_link_libraries(algotrade PUBLIC kapi)
