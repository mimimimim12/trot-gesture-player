# Dockerfile
# Ubuntu 22.04 LTS (Jammy Jellyfish) 기반 이미지 사용
FROM ubuntu:22.04 

# 필요한 시스템 패키지 업데이트 및 설치
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    ffmpeg \
    vlc \
    libgl1-mesa-glx \
    libgtk2.0-0 \
    libusb-1.0-0-dev \ 
    v4l-utils \       
    udev \           
    pulseaudio-utils \ 
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Python 실행 파일 경로 설정
ENV PATH="/usr/bin:${PATH}"

# 작업 디렉토리 설정
WORKDIR /app

# 호스트의 requirements.txt 파일을 컨테이너의 /app 디렉토리로 복사
COPY requirements.txt .

# requirements.txt에 명시된 Python 라이브러리 설치
RUN pip3 install --no-cache-dir -r requirements.txt

# 호스트의 모든 프로젝트 파일(현재 디렉토리의 모든 파일 및 폴더)을 컨테이너의 /app 디렉토리로 복사
COPY . .

# VLC 캐시 디렉토리를 생성하고 권한을 설정합니다.
RUN mkdir -p /root/.cache/vlc && chmod -R 777 /root/.cache/vlc

# 컨테이너가 시작될 때 실행될 기본 명령어
CMD ["python3", "trot_gesture_player.py"]