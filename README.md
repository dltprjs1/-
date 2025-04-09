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
       ![스크린샷 2025-04-09 오후 6 06 26](https://github.com/user-attachments/assets/46567935-4d24-4d6b-b304-ae7af3414f91)
       ![스크린샷 2025-04-09 오후 6 06 41](https://github.com/user-attachments/assets/c3fd2c94-e3f7-4e18-b8b4-87abf1fb8f72)
       ![스크린샷 2025-04-09 오후 6 06 52](https://github.com/user-attachments/assets/9770c74a-a282-4006-a59e-7ef551b26d68)
   10) github access token(PAT) 생성 (github.com/유저명 -> settings -> developer setting ...)
   11) jenkins Dashboard -> jenkins 관리 -> credentials -> globals -> add Credentials
       - USERNAME: github 유저명
       - PW: access Token(PAT)
       - ID: 해당 Credentials의 고유 명칭
   13) git webhook 설정 (github.com/유저명/레포지토리명 -> settings -> webhook)
       - webhook URL은 jenkins 브라우저 접속 URL -> ex)http://localhost:8080/github-webhook/ (포드포워딩 시 : http://외부IP:외부Port)
         -> 마지막 '/' 필수!
         -> 포드포워딩 필요
         -> 방화벽 해제 필요
         -> 필자의 경우 TP-Link에서 포트포워딩 정책을 막고 있어서 cloudflare 임시 URL 사용
       - Content-Type: application/json
       - Event: Just the push event
       <img width="784" alt="스크린샷 2025-04-09 오후 6 10 15" src="https://github.com/user-attachments/assets/c05d8950-e2ac-4670-9be7-606700c88aca" />

   14) 배포용 서버 git, git-lfs, pm2 깔려 있는지 확인! 없다면 설치 및 pull 셋팅 진행
       - brew install git
       - brew install git-lfs
       - git install lfs 
       - npm install -g pm2
       - git remote add origin https://github.com/유저명/레포지토리.git
  
2. git repository에 업로딩
   1) git init
   2) git add .
   3) git commit -m "new Project"
   4) git remote add origin https://github.com/유저이름/레포이름.git << 이미 origin이 있다면, 제거 (git remote remove origin) 후 다시 입력
   5) 업로드: git push -u origin main
