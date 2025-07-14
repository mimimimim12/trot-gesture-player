import cv2
import mediapipe as mp
import numpy as np
import time
import os
import sys 
import vlc # VLC 라이브러리 임포트

# --- 설정 변수 ---
# 오디오 파일 경로 (MP3, WAV 등 VLC가 지원하는 모든 형식 가능)
# WAV 파일을 사용하신다면 아래와 같이 '.wav'로 변경해야 합니다.
AUDIO_FILE = os.path.join("audio", "grace-in-hanbok.wav") 
initial_playback_speed = 1.0

# 제스처 감지 쿨다운 시간 (초)
GESTURE_COOLDOWN_TIME = 0.7 

# --- MediaPipe 초기화 ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

try:
    hands = mp_hands.Hands(
        model_complexity=0, 
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        max_num_hands=1 
    )
except Exception as e:
    print(f"오류: MediaPipe Hands 초기화 실패: {e}")
    print("MediaPipe 라이브러리가 올바르게 설치되었는지 확인하세요. (pip install mediapipe)")
    sys.exit(1) 

# --- 제스처 감지 도우미 함수 ---
# (이 부분은 이전 코드와 동일합니다. 손가락 랜드마크 인덱스와 제스처 감지 로직)
THUMB_TIP = mp_hands.HandLandmark.THUMB_TIP 
THUMB_IP = mp_hands.HandLandmark.THUMB_IP   

INDEX_TIP = mp_hands.HandLandmark.INDEX_FINGER_TIP 
INDEX_PIP = mp_hands.HandLandmark.INDEX_FINGER_PIP 

MIDDLE_TIP = mp_hands.HandLandmark.MIDDLE_FINGER_TIP 
MIDDLE_PIP = mp_hands.HandLandmark.MIDDLE_FINGER_PIP 

RING_TIP = mp_hands.HandLandmark.RING_FINGER_TIP 
RING_PIP = mp_hands.HandLandmark.RING_FINGER_PIP 

PINKY_TIP = mp_hands.HandLandmark.PINKY_TIP 
PINKY_PIP = mp_hands.HandLandmark.PINKY_PIP 

def is_finger_extended(landmarks, tip_id, pip_id, threshold=0.03):
    if landmarks is None: return False
    tip_y = landmarks.landmark[tip_id].y
    pip_y = landmarks.landmark[pip_id].y
    return tip_y < pip_y - threshold

def is_fist_gesture(landmarks):
    if landmarks is None: return False
    return (landmarks.landmark[INDEX_TIP].y > landmarks.landmark[INDEX_PIP].y + 0.03 and
            landmarks.landmark[MIDDLE_TIP].y > landmarks.landmark[MIDDLE_PIP].y + 0.03 and
            landmarks.landmark[RING_TIP].y > landmarks.landmark[RING_PIP].y + 0.03 and
            landmarks.landmark[PINKY_TIP].y > landmarks.landmark[PINKY_PIP].y + 0.03)

def is_open_palm_gesture(landmarks):
    if landmarks is None: return False
    return (is_finger_extended(landmarks, THUMB_TIP, THUMB_IP, 0.05) and 
            is_finger_extended(landmarks, INDEX_TIP, INDEX_PIP) and
            is_finger_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP) and
            is_finger_extended(landmarks, RING_TIP, RING_PIP) and
            is_finger_extended(landmarks, PINKY_TIP, PINKY_PIP))

def is_thumb_only_extended_gesture(landmarks):
    if landmarks is None: return False
    return (is_finger_extended(landmarks, THUMB_TIP, THUMB_IP, 0.05) and 
            not is_finger_extended(landmarks, INDEX_TIP, INDEX_PIP, 0.02) and 
            not is_finger_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP, 0.02) and 
            not is_finger_extended(landmarks, RING_TIP, RING_PIP, 0.02) and 
            not is_finger_extended(landmarks, PINKY_TIP, PINKY_PIP, 0.02))

def is_pinky_only_extended_gesture(landmarks):
    if landmarks is None: return False
    return (not is_finger_extended(landmarks, THUMB_TIP, THUMB_IP, 0.05) and 
            not is_finger_extended(landmarks, INDEX_TIP, INDEX_PIP, 0.02) and 
            not is_finger_extended(landmarks, MIDDLE_TIP, MIDDLE_PIP, 0.02) and 
            not is_finger_extended(landmarks, RING_TIP, RING_PIP, 0.02) and 
            is_finger_extended(landmarks, PINKY_TIP, PINKY_PIP, 0.05))


# --- 오디오 재생 관련 변수 및 함수 (VLC 기반으로 전면 재구성) ---
vlc_instance = None
vlc_player = None
current_playback_speed = initial_playback_speed
is_playing = False # 실제 VLC 플레이어의 재생 상태를 추적 (pause/play)
last_gesture_time = time.time() 

def init_vlc_player(file_path):
    global vlc_instance, vlc_player
    if not os.path.exists(file_path):
        print(f"오류: 오디오 파일을 찾을 수 없습니다: {file_path}")
        print("프로젝트 폴더 안에 'audio' 폴더가 있고, 지정된 파일이 있는지 확인하세요.")
        return False
    try:
        # VLC 인스턴스 생성 (옵션 추가 가능: 예: '--no-video' 등)
        vlc_instance = vlc.Instance()
        vlc_player = vlc_instance.media_player_new()
        media = vlc_instance.media_new(file_path)
        vlc_player.set_media(media)
        # 미디어 준비 완료까지 기다릴 수 있음 (선택 사항)
        # vlc_player.audio_set_volume(70) # 볼륨 설정 (0-100)
        print(f"VLC 플레이어 초기화 완료: {file_path}")
        return True
    except Exception as e:
        print(f"오류: VLC 플레이어 초기화 실패: {e}")
        print("VLC Media Player가 설치되어 있고 python-vlc 라이브러리가 올바르게 설치되었는지 확인하세요.")
        print("만약 python-vlc 설치 시 컴파일 오류가 발생했다면, Microsoft C++ Build Tools를 설치해야 합니다.")
        return False

def play_audio():
    global is_playing, vlc_player, current_playback_speed
    if vlc_player is None:
        print("오류: VLC 플레이어가 초기화되지 않았습니다. 재생할 수 없습니다.")
        return

    if not vlc_player.is_playing(): # 현재 재생 중이 아니라면 (멈춰있거나 일시정지)
        vlc_player.play()
        # vlc_player.set_time(0) # 매번 처음부터 재생하고 싶다면 주석 해제
        is_playing = True
        print(f"음악 재생 시작 (속도: {current_playback_speed:.1f}x)")
    
    # 재생 중이든 아니든, 속도 변경은 항상 적용 (VLC는 실시간 변경 가능)
    vlc_player.set_rate(current_playback_speed)


def stop_audio():
    global is_playing, vlc_player
    if vlc_player is None: return

    if vlc_player.is_playing(): # 재생 중이라면 일시 정지 (pause)
        vlc_player.pause()
        is_playing = False
        print("음악 정지.")
    elif not vlc_player.is_playing() and is_playing: # 일시정지 상태였다면 (정지 명령만 수행했기에)
        vlc_player.play() # 다시 재생
        is_playing = True
        print("음악 재개.")


# --- 메인 비디오 루프 ---
# 웹캠 초기화 및 오류 처리
try:
    cap = cv2.VideoCapture(0) # 0번 카메라 (보통 기본 웹캠)
    if not cap.isOpened():
        raise IOError("카메라를 열 수 없습니다. 카메라가 연결되어 있고 다른 프로그램에서 사용 중이 아닌지 확인하세요.")
except Exception as e:
    print(f"오류: 웹캠 초기화 실패: {e}")
    sys.exit(1) 

# VLC 플레이어 초기화
if not init_vlc_player(AUDIO_FILE):
    cap.release()
    cv2.destroyAllWindows()
    sys.exit(1)

# ★★★ 프로그램 시작 시 음악 자동 재생 (여기서만 호출) ★★★
play_audio()
print("프로그램 시작: 음악 자동 재생 시작")


# 자원 해제를 위한 try-finally 블록
try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("경고: 웹캠에서 프레임을 읽을 수 없습니다. 웹캠 연결을 확인하거나 종료합니다.")
            break

        frame = cv2.flip(frame, 1) # 좌우 반전 (거울 모드)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        hands_results = hands.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        current_time = time.time()
        
        # 손 인식 및 제스처 감지
        if hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # 제스처 감지 및 오디오 제어 (쿨다운 적용)
                if current_time - last_gesture_time > GESTURE_COOLDOWN_TIME:
                    # 1. 주먹을 쥐면 음악이 정지/재생 토글
                    if is_fist_gesture(hand_landmarks):
                        if vlc_player.is_playing(): # VLC가 실제로 재생 중이라면
                            stop_audio() # 일시 정지
                            print("제스처 감지: 주먹 (음악 정지)")
                        else: # VLC가 정지 또는 일시정지 상태라면
                            play_audio() # 재생 재개
                            print("제스처 감지: 주먹 (음악 재생)")
                        last_gesture_time = current_time 
                    
                    # 2. 손바닥을 피면 기계튠으로 조정 (1.5배 속도)
                    elif is_open_palm_gesture(hand_landmarks):
                        # 현재 속도와 다를 때만 변경
                        if current_playback_speed != 1.5: 
                            current_playback_speed = 1.5 
                            play_audio() # 속도 적용 (재생 중이 아니라면 재생도 시작)
                            last_gesture_time = current_time
                            print(f"제스처 감지: 손바닥 펴기 (속도 {current_playback_speed:.1f}x - '기계튠' 효과)")
                    
                    # 3. 엄지손가락만 필 경우 2배 속도로
                    elif is_thumb_only_extended_gesture(hand_landmarks):
                        # 현재 속도와 다를 때만 변경
                        if current_playback_speed != 2.0: 
                            current_playback_speed = 2.0 
                            play_audio()
                            last_gesture_time = current_time
                            print(f"제스처 감지: 엄지손가락만 펴기 (속도 {current_playback_speed:.1f}x)")
                    
                    # 4. 새끼손가락만 필 경우 원래 속도로
                    elif is_pinky_only_extended_gesture(hand_landmarks):
                        # 현재 속도와 다를 때만 변경
                        if current_playback_speed != 1.0: 
                            current_playback_speed = 1.0 
                            play_audio()
                            last_gesture_time = current_time
                            print(f"제스처 감지: 새끼손가락만 펴기 (속도 {current_playback_speed:.1f}x)")

        # 화면에 정보 표시
        cv2.putText(image, f"Speed: {current_playback_speed:.2f}x", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        # VLC의 실제 재생 상태를 확인하여 표시
        cv2.putText(image, f"Audio Playing: {vlc_player.is_playing() if vlc_player else False}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255) if (vlc_player and vlc_player.is_playing()) else (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(image, f"Last Gesture: {round(current_time - last_gesture_time, 2)}s ago", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)


        cv2.imshow('Easy Gesture Music Controller', image)

        # 'q' 키를 누르면 종료
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

finally:
    # --- 리소스 해제 ---
    print("프로그램 종료 중...")
    if 'cap' in locals() and cap.isOpened(): 
        cap.release()
    cv2.destroyAllWindows()
    if 'vlc_player' in locals() and vlc_player:
        vlc_player.stop() # VLC 플레이어 정지
        vlc_player.release() # VLC 리소스 해제
        vlc_instance.release() # VLC 인스턴스 해제
    if 'hands' in locals() and hands: 
        hands.close()
    print("프로그램이 종료되었습니다.")