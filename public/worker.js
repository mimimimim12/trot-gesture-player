// 1. 'document is not defined' 에러를 막기 위한 코드 추가
if (typeof document === "undefined") {
  self.document = {
    currentScript: { src: "ffmpeg.min.js" }
  };
}

// 2. FFmpeg 웹워커용 라이브러리 로드
self.importScripts("https://unpkg.com/@ffmpeg/ffmpeg@0.11.0/dist/ffmpeg.min.js");

// 3. 메인 메시지 핸들러
self.onmessage = async (e) => {
  const file = e.data;
  const { createFFmpeg, fetchFile } = FFmpeg;
  const ffmpeg = createFFmpeg({ log: false });

  self.postMessage({ type: 'conversion-start' });

  try {
    if (!ffmpeg.isLoaded()) {
      await ffmpeg.load();
    }

    // MP3 파일을 가상 파일시스템에 기록
    ffmpeg.FS('writeFile', 'input.mp3', await fetchFile(file));

    // MP3 → WAV 변환
    await ffmpeg.run('-i', 'input.mp3', 'output.wav');

    // 변환된 파일 읽기
    const data = ffmpeg.FS('readFile', 'output.wav');

    // 메인 스레드로 전송
    self.postMessage(
      { type: 'conversion-complete', data: data.buffer },
      [data.buffer] // Transferable 객체로 전송 (메모리 효율)
    );
  } catch (error) {
    self.postMessage({ type: 'conversion-error', error: error?.message || '알 수 없는 오류' });
  }
};
