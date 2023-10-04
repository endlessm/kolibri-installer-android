# Run with ARCHES="arch1 arch2" to build for a smaller set of
# architectures.
ARCHES ?= \
	armeabi-v7a \
	arm64-v8a \
	x86 \
	x86_64
export ARCHES

ARCH_OPTIONS := $(foreach arch,$(ARCHES),--arch=$(arch))

OSNAME := $(shell uname -s)

ifeq ($(OSNAME), Darwin)
	PLATFORM := macosx
else
	PLATFORM := linux
endif

ANDROID_API := 33
ANDROIDNDKVER := 25.0.8775105

SDK := ${ANDROID_HOME}/android-sdk-$(PLATFORM)

ADB := adb
DOCKER := docker
P4A := p4a
PODMAN := podman
PYTHON_FOR_ANDROID := python-for-android
TOOLBOX := toolbox

ifdef EXPLOREPLUGIN_WHEEL_PATH
	EXPLOREPLUGIN_WHEEL := ${EXPLOREPLUGIN_WHEEL_PATH}
	EXPLOREPLUGIN_TARGET := src
else
	EXPLOREPLUGIN_WHEEL := kolibri_explore_plugin
	EXPLOREPLUGIN_TARGET := _explore
endif

# This checks if an environment variable with a specific name
# exists. If it doesn't, it prints an error message and exits.
# For example to check for the presence of the ANDROIDSDK environment
# variable, you could use:
# make guard-ANDROIDSDK
guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

needs-android-dirs:
	$(MAKE) guard-ANDROIDSDK
	$(MAKE) guard-ANDROIDNDK

# Clear out downloaded and built assets
CLEAN_DEPS = \
	clean-kolibri \
	clean-apps-bundle \
	clean-collections \
	clean-local-kolibri-explore-plugin \
	clean-loadingScreen
CLEAN_FILES = \
	dist \
	tmpenv \
	apps-bundle.zip \
	collections.zip \
	$(EXPLOREPLUGIN_WHEEL)

clean: $(CLEAN_DEPS)
	- rm -rf $(CLEAN_FILES)
	- find src -type f -name '*.pyc' -delete
	- $(PYTHON_FOR_ANDROID) clean_dists

deepclean: clean clean-whl
	- $(PYTHON_FOR_ANDROID) clean_builds
	- yes y | $(DOCKER) system prune -a

.PHONY: clean-whl
clean-whl:
	rm -rf whl

.PHONY: get-whl
get-whl: clean-whl
	mkdir -p whl
	wget -O whl/kolibri.whl "${whl}"

clean-kolibri:
	- rm -rf src/kolibri

# Extract the whl file
src/kolibri: clean-kolibri
	unzip -qo whl/kolibri.whl "kolibri/*" -x "kolibri/dist/py2only*" -d src/
# Cleanup:
	./scripts/cleanup-unused-locales.py -l \
	src/kolibri/locale \
	src/kolibri/dist/django/conf/locale \
	src/kolibri/dist/django/contrib/admin/locale \
	src/kolibri/dist/django/contrib/admindocs/locale \
	src/kolibri/dist/django/contrib/auth/locale \
	src/kolibri/dist/django/contrib/contenttypes/locale \
	src/kolibri/dist/django/contrib/flatpages/locale \
	src/kolibri/dist/django/contrib/gis/locale \
	src/kolibri/dist/django/contrib/humanize/locale \
	src/kolibri/dist/django/contrib/postgres/locale \
	src/kolibri/dist/django/contrib/redirects/locale \
	src/kolibri/dist/django/contrib/sessions/locale \
	src/kolibri/dist/django/contrib/sites/locale \
	src/kolibri/dist/django_filters/locale \
	src/kolibri/dist/mptt/locale \
	src/kolibri/dist/rest_framework/locale
	rm -rf \
	src/kolibri/dist/cext/cp27 \
	src/kolibri/dist/cext/cp34 \
	src/kolibri/dist/cext/cp35 \
	src/kolibri/dist/cext/cp36 \
	src/kolibri/dist/cext/cp37 \
	src/kolibri/dist/cext/cp38 \
	src/kolibri/dist/cext/*/Windows
	rm -rf \
	src/kolibri/dist/cheroot/test \
	src/kolibri/dist/magicbus/test \
	src/kolibri/dist/colorlog/tests \
	src/kolibri/dist/django_js_reverse/tests \
	src/kolibri/dist/future/tests \
	src/kolibri/dist/ipware/tests \
	src/kolibri/dist/more_itertools/tests \
	src/kolibri/dist/past/tests \
	src/kolibri/dist/sqlalchemy/testing
	find src/kolibri -name '*.js.map' -exec rm '{}' '+'
# End of cleanup.
# patch Django to allow migrations to be pyc files, as p4a compiles and deletes the originals
	sed -i 's/if name.endswith(".py"):/if name.endswith(".py") or name.endswith(".pyc"):/g' src/kolibri/dist/django/db/migrations/loader.py

.PHONY: apps-bundle.zip
apps-bundle.zip:
	@ if [ "${APPSBUNDLE_PATH}" = "" ]; then \
		wget -N https://github.com/endlessm/kolibri-explore-plugin/releases/latest/download/apps-bundle.zip; \
	else \
		cp '${APPSBUNDLE_PATH}' ./apps-bundle.zip; \
	fi

clean-apps-bundle:
	- rm -rf src/apps-bundle

src/apps-bundle: clean-apps-bundle apps-bundle.zip
	unzip -qo apps-bundle.zip -d src/apps-bundle

.PHONY: collections.zip
collections.zip:
	wget -N https://github.com/endlessm/endless-key-collections/releases/latest/download/collections.zip

clean-collections:
	- rm -rf src/collections

src/collections: clean-collections collections.zip
	unzip -qo collections.zip -d src/collections

# The * is to also remove the VERSION.dist-info directory:
clean-local-kolibri-explore-plugin:
	- rm -rf ${EXPLOREPLUGIN_TARGET}/kolibri_explore_plugin*
	- rmdir --ignore-fail-on-non-empty ${EXPLOREPLUGIN_TARGET}

.PHONY: local-kolibri-explore-plugin
local-kolibri-explore-plugin: clean-local-kolibri-explore-plugin
	pip install --target=${EXPLOREPLUGIN_TARGET} --no-deps ${EXPLOREPLUGIN_WHEEL}

clean-loadingScreen:
	- rm -rf assets/loadingScreen

assets/loadingScreen: clean-loadingScreen local-kolibri-explore-plugin
	cp -r ${EXPLOREPLUGIN_TARGET}/kolibri_explore_plugin/loadingScreen/ assets/

.PHONY: p4a_android_distro
p4a_android_distro: needs-android-dirs
	$(P4A) create $(ARCH_OPTIONS)

.PHONY: needs-version
needs-version: src/kolibri local-kolibri-explore-plugin
	$(eval VERSION_NAME ?= $(shell python3 scripts/version.py version_name))
	$(eval VERSION_CODE ?= $(shell python3 scripts/version.py version_code))
	$(eval EK_VERSION ?= $(shell python3 scripts/version.py ek_version))
	$(if $(VERSION_NAME), ,$(error VERSION_NAME not defined))
	$(if $(VERSION_CODE), ,$(error VERSION_CODE not defined))
	$(if $(EK_VERSION), ,$(error EK_VERSION not defined))

dist/version.json: needs-version
	rm -f $@
	mkdir -p dist
	echo '{"versionCode": "$(VERSION_CODE)", "versionName": "$(VERSION_NAME)", "ekVersion": "$(EK_VERSION)"}' > $@

DIST_DEPS = \
	p4a_android_distro \
	src/kolibri \
	src/apps-bundle \
	src/collections \
	assets/loadingScreen \
	needs-version \
	dist/version.json

.PHONY: kolibri.apk
# Build the signed version of the apk
kolibri.apk: $(DIST_DEPS)
	$(MAKE) guard-P4A_RELEASE_KEYSTORE
	$(MAKE) guard-P4A_RELEASE_KEYALIAS
	$(MAKE) guard-P4A_RELEASE_KEYSTORE_PASSWD
	$(MAKE) guard-P4A_RELEASE_KEYALIAS_PASSWD
	rm -f dist/kolibri-release-*.apk
	@echo "--- :android: Build APK"
	$(P4A) apk --release --sign $(ARCH_OPTIONS) --version="$(VERSION_NAME)" --numeric-version=$(VERSION_CODE)
	mkdir -p dist
	mv "kolibri-release-$(VERSION_NAME).apk" dist/kolibri-release-$(EK_VERSION).apk

.PHONY: kolibri.apk.unsigned
# Build the unsigned debug version of the apk
kolibri.apk.unsigned: $(DIST_DEPS)
	rm -f dist/kolibri-debug-*.apk
	@echo "--- :android: Build APK (unsigned)"
	$(P4A) apk $(ARCH_OPTIONS) --version="$(VERSION_NAME)" --numeric-version=$(VERSION_CODE)
	mkdir -p dist
	mv "kolibri-debug-$(VERSION_NAME).apk" dist/kolibri-debug-$(EK_VERSION).apk

.PHONY: kolibri.aab
# Build the signed version of the aab
kolibri.aab: $(DIST_DEPS)
	$(MAKE) guard-P4A_RELEASE_KEYSTORE
	$(MAKE) guard-P4A_RELEASE_KEYALIAS
	$(MAKE) guard-P4A_RELEASE_KEYSTORE_PASSWD
	$(MAKE) guard-P4A_RELEASE_KEYALIAS_PASSWD
	rm -f dist/kolibri-release-*.aab
	@echo "--- :android: Build AAB"
	$(P4A) aab --release --sign $(ARCH_OPTIONS) --version="$(VERSION_NAME)" --numeric-version=$(VERSION_CODE)
	mkdir -p dist
	mv "kolibri-release-$(VERSION_NAME).aab" dist/kolibri-release-$(EK_VERSION).aab

# DOCKER BUILD

# Build the docker image. Should only ever need to be rebuilt if project requirements change.
# Makes dummy file
.PHONY: build_docker
build_docker: Dockerfile
	$(DOCKER) build -t android_kolibri .

# Toolbox build
build_toolbox: Dockerfile-toolbox
	$(PODMAN) build -t android_kolibri_toolbox -f $< .
	$(TOOLBOX) rm -f android_kolibri || :
	$(TOOLBOX) create -c android_kolibri -i android_kolibri_toolbox

install:
	$(ADB) uninstall org.endlessos.Key || true 2> /dev/null
	$(ADB) install dist/*-debug-*.apk

logcat:
	$(ADB) logcat '*:F' EndlessKey EKWebConsole python:D PythonActivity:D

$(SDK)/cmdline-tools/latest/bin/sdkmanager:
	@echo "Downloading Android SDK command line tools"
	wget https://dl.google.com/android/repository/commandlinetools-$(PLATFORM)-7583922_latest.zip
	rm -rf cmdline-tools
	unzip commandlinetools-$(PLATFORM)-7583922_latest.zip
# This is unfortunate since it will download the command line tools
# again, but after this it will be properly installed and updatable.
	yes y | ./cmdline-tools/bin/sdkmanager "cmdline-tools;latest" --sdk_root=$(SDK)
	rm -rf cmdline-tools
	rm commandlinetools-$(PLATFORM)-7583922_latest.zip

sdk: $(SDK)/cmdline-tools/latest/bin/sdkmanager
	yes y | $(SDK)/cmdline-tools/latest/bin/sdkmanager "platform-tools"
	yes y | $(SDK)/cmdline-tools/latest/bin/sdkmanager "platforms;android-$(ANDROID_API)"
	yes y | $(SDK)/cmdline-tools/latest/bin/sdkmanager "system-images;android-$(ANDROID_API);google_apis_playstore;x86_64"
	yes y | $(SDK)/cmdline-tools/latest/bin/sdkmanager "build-tools;33.0.2"
	yes y | $(SDK)/cmdline-tools/latest/bin/sdkmanager "ndk;$(ANDROIDNDKVER)"
	ln -sfT ndk/$(ANDROIDNDKVER) $(SDK)/ndk-bundle
	@echo "Accepting all licenses"
	yes | $(SDK)/cmdline-tools/latest/bin/sdkmanager --licenses

# All of these commands are non-destructive, so if the cmdline-tools are already installed, make will skip
# based on the directory existing.
# The SDK installations will take a little time, but will not attempt to redownload if already installed.
setup:
	$(MAKE) guard-ANDROID_HOME
	$(MAKE) sdk
	@echo "Make sure to set the necessary environment variables"
	@echo "export ANDROIDSDK=$(SDK)"
	@echo "export ANDROIDNDK=$(SDK)/ndk-bundle"

clean-tools:
	rm -rf ${ANDROID_HOME}
