cmake_minimum_required(VERSION 3.0)
project(winds_of_the_past Fortran)
enable_language(Fortran)

set(CMAKE_Fortran_FLAGS "-fdec-structure -Wall -fno-backtrace -fimplicit-none -no-pie")
set(FORTRAN_UNIX_DIR "" CACHE STRING "Directory containing the fortran-unix dependency")

add_executable(${PROJECT_NAME}
    main.f
    mod_bucket.f
    mod_crypto.f
    mod_consumption.f
    mod_turbine.f
    mod_user.f
)

target_link_libraries(${PROJECT_NAME}
    "${FORTRAN_UNIX_DIR}/libfortran-unix.a"
)
include_directories(${FORTRAN_UNIX_DIR})

set_target_properties(${PROJECT_NAME} PROPERTIES LINKER_LANGUAGE Fortran)
