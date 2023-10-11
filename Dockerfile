# Dockerfile for build

FROM docker.io/endlessm/eos:master

# Install the dependencies for the build system
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y \
        java-common \
        ca-certificates-java && \
    apt-get install -y \
        git \
        openjdk-17-jdk-headless \
        python-is-python3 \
        python3 \
        python3-pip \
        wget \
        unzip \
        && \
    apt-get clean

# Install Android SDK
ENV ANDROID_HOME=/opt/android/sdk
COPY Makefile /tmp/
RUN make -C /tmp setup && \
  rm -f /tmp/Makefile

# install python dependencies
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt && \
  rm -f /tmp/requirements.txt

# Configure gradle for use in docker. Disable gradle's automatically
# detected rich console doesn't work in docker. Disable the gradle
# daemon since it will be stopped as soon as the container exits.
ENV GRADLE_OPTS="-Dorg.gradle.console=plain -Dorg.gradle.daemon=false"

# Create a mount point for the build cache and make it world writable so
# that the volume can be used by an unprivileged user without additional
# setup.
RUN mkdir /cache && chmod 777 /cache

CMD [ "./gradlew", "build", "bundle" ]
