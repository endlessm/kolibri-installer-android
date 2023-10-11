OSNAME := $(shell uname -s)

ifeq ($(OSNAME), Darwin)
	PLATFORM := macosx
else
	PLATFORM := linux
endif

ANDROID_HOME ?= $(HOME)/.android/sdk
ANDROID_API := 33

ADB := adb
DOCKER := docker
PODMAN := podman
TOOLBOX := toolbox

.PHONY: clean
clean:
	./gradlew clean

.PHONY: kolibri.apk
# Build debug and release APKs
kolibri.apk:
	./gradlew build

.PHONY: kolibri.aab
# Bundle debug and release APKs
kolibri.aab:
	./gradlew bundle

.PHONY: install
# Install the debug APK
install:
	./gradlew installDebug

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

logcat:
	$(ADB) logcat '*:F' EndlessKey EKWebConsole AndroidRuntime python.stdout python.stderr

$(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager:
	@echo "Downloading Android SDK command line tools"
	wget https://dl.google.com/android/repository/commandlinetools-$(PLATFORM)-7583922_latest.zip
	rm -rf cmdline-tools
	unzip commandlinetools-$(PLATFORM)-7583922_latest.zip
# This is unfortunate since it will download the command line tools
# again, but after this it will be properly installed and updatable.
	yes y | ./cmdline-tools/bin/sdkmanager "cmdline-tools;latest" --sdk_root=$(ANDROID_HOME)
	rm -rf cmdline-tools
	rm commandlinetools-$(PLATFORM)-7583922_latest.zip

sdk: $(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager
	yes y | $(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager "platform-tools"
	yes y | $(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager "platforms;android-$(ANDROID_API)"
	yes y | $(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager "system-images;android-$(ANDROID_API);google_apis_playstore;x86_64"
	yes y | $(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager "build-tools;33.0.2"
	@echo "Accepting all licenses"
	yes | $(ANDROID_HOME)/cmdline-tools/latest/bin/sdkmanager --licenses

clean-sdk:
	rm -rf ${ANDROID_HOME}
