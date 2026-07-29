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

USER root
RUN apt-get -o Acquire::Retries=8 update && \
    apt-get -o Acquire::Retries=8 install -y --no-install-recommends \
    bison \
    flex && \
    rm -rf /var/lib/apt/lists/*
USER ubuntu

COPY --chown=ubuntu:ubuntu kamailio.patch ${WORKDIR}/kamailio.patch
COPY --chown=ubuntu:ubuntu pjsip.patch ${WORKDIR}/pjsip.patch

# Set up environment variables for ASAN
ENV ASAN_OPTIONS='abort_on_error=1:symbolize=0:detect_leaks=0:detect_stack_use_after_return=1:detect_container_overflow=0:poison_array_cookie=0:malloc_fill_byte=0:max_malloc_fill_size=16777216'

# Download and compile Kamalio for fuzzing
RUN cd $WORKDIR && \
    for attempt in 1 2 3 4 5; do \
      rm -rf kamailio; \
      if git clone --filter=blob:none --no-checkout https://github.com/kamailio/kamailio.git kamailio && \
         git -C kamailio checkout --detach 2648eb3; then \
        break; \
      fi; \
      rm -rf kamailio; \
      echo "kamailio clone retry ${attempt}/5"; \
      sleep 5; \
    done && \
    test -d kamailio/.git && \
    git -C kamailio rev-parse --verify 2648eb3^{commit} >/dev/null && \
    cd kamailio && \
    patch -p1 < $WORKDIR/kamailio.patch && \
    CC=afl-clang-fast make MEMPKG=sys cfg && \
    AFL_USE_ASAN=1 CC=afl-clang-fast make all $MAKE_OPT

# Build SIP client to simulate the callee
RUN cd $WORKDIR && \
    for attempt in 1 2 3 4 5; do \
      rm -rf pjproject; \
      if git clone --filter=blob:none --no-checkout https://github.com/pjsip/pjproject.git pjproject && \
         git -C pjproject checkout --detach bba95b8; then \
        break; \
      fi; \
      rm -rf pjproject; \
      echo "pjproject clone retry ${attempt}/5"; \
      sleep 5; \
    done && \
    test -d pjproject/.git && \
    git -C pjproject rev-parse --verify bba95b8^{commit} >/dev/null && \
    cd pjproject && \
    patch -p1 < $WORKDIR/pjsip.patch && \
    ./configure && \
    make dep && make clean && make $MAKE_OPT

# Download and compile Kamalio for code coverage analysis
RUN cd $WORKDIR && \
    for attempt in 1 2 3 4 5; do \
      rm -rf kamailio-gcov; \
      if git clone --filter=blob:none --no-checkout https://github.com/kamailio/kamailio.git kamailio-gcov && \
         git -C kamailio-gcov checkout --detach 2648eb3; then \
        break; \
      fi; \
      rm -rf kamailio-gcov; \
      echo "kamailio-gcov clone retry ${attempt}/5"; \
      sleep 5; \
    done && \
    test -d kamailio-gcov/.git && \
    git -C kamailio-gcov rev-parse --verify 2648eb3^{commit} >/dev/null && \
    cd kamailio-gcov && \
    patch -p1 < $WORKDIR/kamailio.patch && \
    make CC_EXTRA_OPTS="-fprofile-arcs -ftest-coverage" LD_EXTRA_OPTS="-fprofile-arcs -ftest-coverage" MEMPKG=sys cfg && \
    make CC_EXTRA_OPTS="-fprofile-arcs -ftest-coverage" LD_EXTRA_OPTS="-fprofile-arcs -ftest-coverage" all $MAKE_OPT

COPY --chown=ubuntu:ubuntu in-sip ${WORKDIR}/in-sip
COPY --chown=ubuntu:ubuntu cov_script.sh ${WORKDIR}/cov_script
COPY --chown=ubuntu:ubuntu run.sh ${WORKDIR}/run
COPY --chown=ubuntu:ubuntu run_pjsip.sh ${WORKDIR}/run_pjsip
COPY --chown=ubuntu:ubuntu kamailio-basic.cfg ${WORKDIR}/kamailio-basic.cfg
COPY --chown=ubuntu:ubuntu StarWars3.wav ${WORKDIR}/StarWars3.wav
