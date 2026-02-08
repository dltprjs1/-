# 이미지 처리 (PW => MSS)
    1.  PW(Process Window Capture) 
        - 지정 윈도우 창만 캡쳐가 가능
        - 화면이 가려져도 해당 윈도우 창의 현황을 캡쳐 할 수 있다.
        - 일부 게임의 경우 보안 이슈로 블락될 우려 존재
        - 전체 화면이 아닌 특정 창만 캡쳐할 할 수 있음
    2.  MSS(Microsoft ScreenShot API)[채택]
        - PW에 비해 이미지 처리 속도가 탁월하다. PW의 경우 이미지 처리 과정이 초당 3~4회 정도이나, MSS의 경우 초당 수십회까지 처리가능
        - Window뿐 만 아니라 다른 OS에서도 사용이 가능
        - 접근성이 용이하다.
        - 전체 화면을 기반으로 하지만 필자는 전처리 과정을 통해 PW와 동일하게 해당 창만 찍도록 작업
        - 창이 가려지면 가려진 상태 그래도 캡쳐
    3. SIFT(Scale Invariant Feature Transform) <- 몬스터 인식 [채택]
        - 처음 ORB(Oriented FAST and Rotated BRIEF)로 특이점을 찾아 몬스터 템플릿(사전준비)과 mss로 화면 전체 스캔한 이미지를 비교하여 매칭 시스템 개발하였으나, 정합성이 너무 떨어지는 문제 발생
        - 이후 SIFT를 통해 몬스터 템플릿과 전체화면 비교 후 점수제로 인식 (5정 이상일 경우 몬스터 확정)
        - 캐릭터 인식은 따로 진행하지 않았고, 미니맵의 좌우측 20%쪽으로 이동할 경우(좌우측 끝으로 이동 시 캐릭터는 정중앙에 위치하지 않음) KeySchedule에 맞게 이동 진행
        - SIFT는 스케일 변화에 강하여 해상도가 달라지더라도 인식률이 좋음

# Keyboard Library
    1.  현재 나의 좌표를 DI(Dependency Injection)를 통해 이미지 처리과정의 한 메서드에서 주입 받도록 설정하였고, 해당 메서드에 저장된 좌표를 불러와 수행
        - 수행 리스트
        a. 내 위치를 통해 이동 경로 파악
        b. 밧줄 위치 확인 및 이동
        c. 이동 공격 스킬+ 이동 스킬 사용 (추후 ORB를 활용한 캐릭터와 몬스터 인식 후 공격 스킬 사용)

# 거짓말 탐지기 감지(OCR)
    1.  pytesseract -> 문자 인식률이 좋으나, UI 인식률이 다소 떨어지며, 글자로 판단되는 섹션을 정해 해당 구역의 글자만 추출
    2.  easyocr[채택] -> pytessearact에 비해 UI 인지능력, 재해석 등 탁월한 수행능력을 보유하나, 문자 인식률이 다소 떨어짐
    3.  gemma3-27b-it -> 자연어 처리 구글 AI 모델을 무료(분 1,500 회 / 월 1,000,000 회)로 이용 가능하나, OCR의 경우 간헐적으로 잘못된 값을 반환
        gemma3 프롬프트 :
            system_prompt = (
                "너는 OCR 엔진이다. 이미지 안의 텍스트를 최대한 정확하게 추출해서 분석한다. "
                "반드시 지시한 형식으로만 대답해야 한다."
            )
            user_prompt = (
                "다음 이미지 안에 '창을', '3번', '클릭' 이 세 개의 단어 중 "
                "하나라도 보이면 True, 하나도 보이지 않으면 False 라고만 출력해. "
                "설명, 이유, 다른 문장 절대 쓰지 말고, 딱 한 단어로만 답해."
            )

# etc
    1.  몬스터 아이디 찾기 (https://maplestory.io/api/GMS/255/mob)
    2.  몬스터 이미지 보기 (http://maplestory.io/api/GMS/255/mob/{id}/render/stand/0/?resize=1&tryCount=0)
    3.  몬스터 프레임 다운로드 (https://maplestory.io/api/KMS/389/mob/{id}/download ) 
       4.  스킬 타격 이펙트 (https://www.inven.co.kr/board/maple/2299/2583884)

    * Famous monster for macro
        - Coolie Zombie: 5130107
        - Moon Bunny(Wolmyo): 9300061

# Update History
    1. 25.11.20
        - 이미지 처리 방식 변경 PW -> MSS
        - 거짓말 탐지기 인식 라이브러리 변경 pytesseract -> easyocr
        - 몬스터 인식 기능 추가: ORB
    2. 25.11.21
        - 몬스터 인식 방식 변경 ORB -> SIFT
        - pytesseract install 파일 삭제
        - 거짓말 탐지기 인식 범위 변경 (Height: 100% -> 72.5%)
        - 몬스터 인식 범위 수정 기능 추가
        - 몬스터 인식 시 공격 로직 변경
        - 몬스터 인식 시 필수 공격 시간(초) 기능 추가
        - 밧줄 타기 확인 로직 변경 (Target_Y -> Stage_Y)
        - 상단 이동 스킬 확인 로직 변경(Target_Y -> Stage_Y)
        - live_yellow_gui 채팅창 영역, 미니맵 영역, 스킬 범위 영역(몬스터 인식 영역) Draw 기능 추가
        - Debugging 모드 추가 (main에서 미니맵, 채팅창, 스킬 범위 영역(몬스터 인식 영역) 확인 가능)

# 해야 할 일
    LOW_STAGE, LOW_PATH 기능 제거
    자동 물약 충전, 줍기 기능
    캐릭터 인식 기능 및 캐릭터를 중심으로 스킬 범위 영역(몬스터 인식 역)확인 하도록 수정
        - 캐릭터가 인식 되지 않을 경우 중앙에서 
    Schedule Event는 다른 Event와 다르게 시간이 되면 자동 발생 되도록 수정
    매크로 방지몹 알림 및 공격 중단, 특정 이벤트(도어, 안전 구역 이동) 기능 추가
    밧줄 기능 고도화
    gui_config, live_yellow_gui 통합

# pyinstaller
    pyinstaller --onefile --noconsole --icon="myicon.ico" --version-file="v.txt" taskhostw.py

기술 모음

1. jenkins로 node.js 서버 맥미니에 CI/CD 구축
   1) 맥미니에서 jenkins 설치 - brew install jenkins-lts
   2) jenkins 실행 - brew services start jenkins-lts
   3) 브라우저에서 localhost:8080 접속
   4) 비밀번호 확인: cat /Users/$(whoami)/.jenkins/secrets/initialAdminPassword
   5) "추천 플러그인 설치" 진행
   6) 계정 생성
   7) git repository 생성 -> 2번 항목 참고
   8) new Item -> freestyle Project로 프로젝트 생성
   9) configure 설정 <br/>
   <img width="784" alt="스크린샷 2025-04-09 오후 6 10 15" src="https://github.com/user-attachments/assets/46567935-4d24-4d6b-b304-ae7af3414f91" />
   <img width="784" alt="스크린샷 2025-04-09 오후 6 10 15" src="https://github.com/user-attachments/assets/c3fd2c94-e3f7-4e18-b8b4-87abf1fb8f72" />
   <img width="784" alt="스크린샷 2025-04-09 오후 6 10 15" src="https://github.com/user-attachments/assets/9770c74a-a282-4006-a59e-7ef551b26d68" /><br/>
   10) github access token(PAT) 생성 (github.com/유저명 -> settings -> developer setting ...) <br/>
   12) jenkins Dashboard -> jenkins 관리 -> credentials -> globals -> add Credentials <br/>
       - USERNAME: github 유저명<br/>
       - PW: access Token(PAT)<br/>
       - ID: 해당 Credentials의 고유 명칭<br/>
   13) git webhook 설정 (github.com/유저명/레포지토리명 -> settings -> webhook)<br/>
       - webhook URL은 jenkins 브라우저 접속 URL -> ex)http://localhost:8080/github-webhook/ (포드포워딩 시 : http://외부IP:외부Port)<br/>
         -> 마지막 '/' 필수!<br/>
         -> 포드포워딩 필요<br/>
         -> 방화벽 해제 필요<br/>
         -> 필자의 경우 TP-Link에서 포트포워딩 정책을 막고 있어서 cloudflare 임시 URL 사용<br/>
       - Content-Type: application/json<br/>
       - Event: Just the push event<br/>
       <img width="784" alt="스크린샷 2025-04-09 오후 6 10 15" src="https://github.com/user-attachments/assets/c05d8950-e2ac-4670-9be7-606700c88aca" /><br/>

   14) 배포용 서버 git, git-lfs, pm2 깔려 있는지 확인! 없다면 설치 및 pull 셋팅 진행<br/>
       - brew install git<br/>
       - brew install git-lfs<br/>
       - git install lfs <br/>
       - npm install -g pm2<br/>
       - git remote add origin https://github.com/유저명/레포지토리.git<br/>
  
2. git repository에 업로딩
   1) git init
   2) git add .
   3) git commit -m "new Project"
   4) git remote add origin https://github.com/유저이름/레포이름.git << 이미 origin이 있다면, 제거 (git remote remove origin) 후 다시 입력
   5) 업로드: git push -u origin main