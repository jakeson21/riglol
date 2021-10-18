#!/bin/bash

PLATFORMS="linux64 linux32 win64 win32 web osx64"
PROCESSES=4

VERSION=$(cat VERSION)

OSX_NAME="osxcross"

build_osxcross() {
	docker image build -t ${OSX_NAME} osxcross-docker
}

build_emscripten() {
	git clone --depth 1 https://github.com/emscripten-core/emsdk.git
	cd emsdk
	./emsdk install latest
	./emsdk activate latest
	source ./emsdk_env.sh
	cd ..
}

build_platform() {
	platform=$1
	rm -rf build/${platform}
	mkdir -p build/${platform}
	if [[ q${platform} == qosx64 ]]; then
		build_osxcross
		docker run -d --user $(id -u):$(id -g) -v ${PWD}:/riglol --name ${OSX_NAME} ${OSX_NAME}
		docker exec -w /riglol ${OSX_NAME} cmake -H. -Bbuild/${platform} -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=cmake/${platform}.cmake -DRIGLOL_VERSION=${VERSION}
		docker exec -w /riglol/build/${platform} ${OSX_NAME} make -j${PROCESSES}

		docker stop ${OSX_NAME}
		docker rm ${OSX_NAME}
		docker image rm ${OSX_NAME}
	else
		if [[ q${platform} == qweb ]]; then
			cd build/${platform}
			build_emscripten
			cd ../../
		fi
		cmake -H. -Bbuild/${platform} -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=cmake/${platform}.cmake -DRIGLOL_VERSION=${VERSION}
		cd build/${platform}
		make -j${PROCESSES}
		cd ../../
	fi
}


for platform in $PLATFORMS; do
	build_platform ${platform}
	mkdir -p bin/${platform}
	rm -f bin/${platform}/*
	cp build/${platform}/src/riglol* bin/${platform}
	if [ q${platform} == "qweb" ]; then
		cp src/riglol.html bin/web/index.html
		cp src/options.json bin/web/options.json
	fi

	if [[ q${platform} == qlinux* ]]; then
		rm bin/riglol-*-${platform}.tar.gz
		tar -C bin/${platform} --transform "s,^\.,riglol-${platform}-${VERSION}," -zcf bin/riglol-${VERSION}-${platform}.tar.gz .
	else
		rm bin/riglol-*-${platform}.zip
		zip -j bin/riglol-${VERSION}-${platform}.zip bin/${platform}/*
	fi
done

tar --transform "s,^\.,riglol-${VERSION}," -zcf bin/riglol-${VERSION}.tar.gz cmake src CMakeLists.txt VERSION build.sh
