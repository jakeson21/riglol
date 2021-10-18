find_package (PythonInterp 3.7 REQUIRED)

add_executable(riglol
		riglol.c mraes.c mralloc.c mrarth0.c mrarth1.c mrarth2.c mrarth3.c
		mrbits.c mrbrick.c mrbuild.c mrcore.c mrcrt.c mrcurve.c mrdouble.c
		mrebrick.c mrec2m.c mrecn2.c mrfast.c mrflash.c mrflsh1.c
		mrflsh2.c mrflsh3.c mrflsh4.c mrfpe.c mrfrnd.c mrgcd.c mrgcm.c
		mrgf2m.c mrio1.c mrio2.c mrjack.c mrlucas.c mrmonty.c mrmuldv.c
		mrpi.c mrpower.c mrprime.c mrrand.c mrround.c mrscrt.c mrsha3.c
		mrshs256.c mrshs512.c mrshs.c mrsmall.c mrsroot.c mrstrong.c
		mrxgcd.c mrzzn2b.c mrzzn2.c mrzzn3.c mrzzn4.c
	)
target_link_libraries(riglol m)
target_include_directories(riglol PUBLIC "${PROJECT_BINARY_DIR}/src")

configure_file(config.h.in config.h)
add_custom_command(
		OUTPUT ${PROJECT_BINARY_DIR}/src/options.h
		MAIN_DEPENDENCY options.h.in
		DEPENDS gen_options.py options.json
		WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
		COMMAND ${PYTHON_EXECUTABLE} gen_options.py > ${PROJECT_BINARY_DIR}/src/options.h
		)
target_sources(riglol PUBLIC ${PROJECT_BINARY_DIR}/src/options.h)

if(${CMAKE_SYSTEM_NAME} STREQUAL Web)
	message("Building for web")
	target_link_options(riglol PUBLIC "SHELL:-s EXPORTED_FUNCTIONS='[_make_licence,_select_priv_key,_get_version]'")
	target_link_options(riglol PUBLIC "SHELL:-s EXTRA_EXPORTED_RUNTIME_METHODS='[ccall, cwrap]'")
	target_link_options(riglol PUBLIC "SHELL:-s WASM=1")
endif()
