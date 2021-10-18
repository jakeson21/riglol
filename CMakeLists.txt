list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

cmake_minimum_required(VERSION 3.10)

project(riglol VERSION ${RIGLOL_VERSION})

add_subdirectory(src)
