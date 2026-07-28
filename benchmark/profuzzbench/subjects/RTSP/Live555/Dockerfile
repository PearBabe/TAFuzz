FROM ubuntu:20.04

# Install common dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -o Acquire::Retries=8 update && \
    apt-get -o Acquire::Retries=8 install -y --no-install-recommends ca-certificates && \
    sed -i \
      -e 's|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
      -e 's|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
      /etc/apt/sources.list && \
    update-ca-certificates && \
    printf 'Acquire::Retries "8";\nAcquire::http::Pipeline-Depth "0";\nAcquire::http::Timeout "180";\nAcquire::https::Timeout "180";\n' \
      > /etc/apt/apt.conf.d/80-retry && \
    apt-get -o Acquire::Retries=8 update && \
    apt-get -o Acquire::Retries=8 install -y --no-install-recommends \
      sudo \
      apt-utils \
      build-essential \
      openssl \
      clang \
      graphviz-dev \
      git \
      autoconf \
      libgnutls28-dev \
      libssl-dev \
      llvm \
      llvm-10-dev \
      python3-pip \
      nano \
      net-tools \
      vim \
      gdb \
      netcat-openbsd \
      strace \
      wget && \
    rm -rf /var/lib/apt/lists/*

# Add a new user ubuntu, pass: ubuntu
RUN groupadd ubuntu && \
    useradd -rm -d /home/ubuntu -s /bin/bash -g ubuntu -G sudo -u 1000 ubuntu -p "$(openssl passwd -1 ubuntu)"

RUN chmod 777 /tmp

RUN python3 -m pip install \
      --no-cache-dir \
      --retries 8 \
      --timeout 180 \
      --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
      gcovr==4.2

# Use ubuntu as default username
USER ubuntu
WORKDIR /home/ubuntu

# Import environment variable to pass as parameter to make (e.g., to make parallel builds with -j)
ARG MAKE_OPT

# Keep GitHub transfers compatible with the Docker Desktop proxy.
RUN git config --global http.version HTTP/1.1 && \
    git config --global http.maxRequests 1 && \
    git config --global http.lowSpeedLimit 1 && \
    git config --global http.lowSpeedTime 600

# Set up fuzzers
RUN for attempt in 1 2 3 4 5; do \
      git clone --depth 1 --single-branch https://github.com/profuzzbench/aflnet.git aflnet && break || \
      { rm -rf aflnet; echo "aflnet clone retry ${attempt}/5"; sleep 5; }; \
    done && \
    test -d aflnet/.git && \
    cd aflnet && \
    make clean all $MAKE_OPT && \
    cd llvm_mode && make $MAKE_OPT

RUN for attempt in 1 2 3 4 5; do \
      git clone --depth 1 --single-branch https://github.com/profuzzbench/aflnwe.git aflnwe && break || \
      { rm -rf aflnwe; echo "aflnwe clone retry ${attempt}/5"; sleep 5; }; \
    done && \
    test -d aflnwe/.git && \
    cd aflnwe && \
    make clean all $MAKE_OPT && \
    cd llvm_mode && make $MAKE_OPT

# Set up environment variables for AFLNet
ENV WORKDIR="/home/ubuntu/experiments"
ENV AFLNET="/home/ubuntu/aflnet"
ENV PATH="${PATH}:${AFLNET}:/home/ubuntu/.local/bin:${WORKDIR}"
ENV AFL_PATH="${AFLNET}"
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 \
    AFL_SKIP_CPUFREQ=1 \
    AFL_NO_AFFINITY=1


RUN mkdir $WORKDIR

COPY --chown=ubuntu:ubuntu fuzzing.patch ${WORKDIR}/fuzzing.patch
COPY --chown=ubuntu:ubuntu gcov.patch ${WORKDIR}/gcov.patch

# Set up environment variables for ASAN
ENV ASAN_OPTIONS='abort_on_error=1:symbolize=0:detect_leaks=0:detect_stack_use_after_return=1:detect_container_overflow=0:poison_array_cookie=0:malloc_fill_byte=0:max_malloc_fill_size=16777216'

# Download and compile Live555 for fuzzing
RUN cd $WORKDIR && \
    for attempt in 1 2 3 4 5; do \
      rm -rf live555; \
      if git clone --filter=blob:none --no-checkout https://github.com/rgaufman/live555.git live555 && \
         git -C live555 checkout --detach ceeb4f4; then \
        break; \
      fi; \
      rm -rf live555; \
      echo "live555 clone retry ${attempt}/5"; \
      sleep 5; \
    done && \
    test -d live555/.git && \
    git -C live555 rev-parse --verify ceeb4f4^{commit} >/dev/null && \
    cd live555 && \
    patch -p1 < $WORKDIR/fuzzing.patch && \
    ./genMakefiles linux && \
    (AFL_USE_ASAN=1 make clean all $MAKE_OPT || make all)

# Set up Live555 for fuzzing
RUN cd ${WORKDIR}/live555/testProgs && \
    cp ${AFLNET}/tutorials/live555/sample_media_sources/*.* ./

# Download and compile Live555 for coverage analysis
RUN cd $WORKDIR && \
    for attempt in 1 2 3 4 5; do \
      rm -rf live555-cov; \
      if git clone --filter=blob:none --no-checkout https://github.com/rgaufman/live555.git live555-cov && \
         git -C live555-cov checkout --detach ceeb4f4; then \
        break; \
      fi; \
      rm -rf live555-cov; \
      echo "live555-cov clone retry ${attempt}/5"; \
      sleep 5; \
    done && \
    test -d live555-cov/.git && \
    git -C live555-cov rev-parse --verify ceeb4f4^{commit} >/dev/null && \
    cd live555-cov && \
    patch -p1 < $WORKDIR/gcov.patch && \
    ./genMakefiles linux && \
    make CFLAGS="-fprofile-arcs -ftest-coverage" CPPFLAGS="-fprofile-arcs -ftest-coverage" CXXFLAGS="-fprofile-arcs -ftest-coverage" LDFLAGS="-fprofile-arcs -ftest-coverage" clean all

# Set up Live555 for coverage analysis
RUN cd ${WORKDIR}/live555-cov/testProgs && \
    cp ${AFLNET}/tutorials/live555/sample_media_sources/*.* ./

COPY --chown=ubuntu:ubuntu kill-server.sh ${WORKDIR}/kill-server
COPY --chown=ubuntu:ubuntu in-rtsp ${WORKDIR}/in-rtsp
COPY --chown=ubuntu:ubuntu rtsp.dict ${WORKDIR}/rtsp.dict
COPY --chown=ubuntu:ubuntu cov_script.sh ${WORKDIR}/cov_script
COPY --chown=ubuntu:ubuntu run.sh ${WORKDIR}/run
