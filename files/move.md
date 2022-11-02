### 경로에 시간정보 넣기
폴더명에 string 값을 넣어주면 작업 시작할 때의 값으로 입력된다.

| string        | 포맷           | 예             |  
| ------------- |:--------------| :---------------|   
| {DATE}        | %Y-%m-%d      | 2022-11-01      |  
| {TIME}        | %H%M%S        | 180001          |  
| {DATETIME}    | %Y%m%d_%H%M%S | 20221101_180001 |    

<img src="https://cdn.discordapp.com/attachments/973582802102648882/1037096118271615086/unknown.png" width="50%" />

----
### 경로에 코드 사용
데이터 폴더/db/rclone.yaml 파일이 있다면 python 코드를 로딩하여 적용한다.

```yaml
folder_change_rule:
  - target: "{MY_DATETIME_1}"
    code: |
      import datetime
      now = datetime.datetime.now()
      RESULT = str(now)


  - target: "{MY_DATETIME_2}"
    code: |
      import datetime
      
      def main():
        now = datetime.datetime.now()
        return str(now).replace(':', '-')

      RESULT = main()
```

샘플 처럼 yaml 파일을 만들어 놓으면 경로에 target 값이 있는 경우 RESULT 값으로 대체한다.



### 옵션  
  
  * 구드 서버사이드  
    ```
    --drive-server-side-across-configs=true
    ```
    
  * 필터링 : [https://rclone.org/filtering/](https://rclone.org/filtering/)



### 활용 예
  * **FF DB 백업**  
    <img src="https://media.discordapp.net/attachments/973582802102648882/1037097616959361044/unknown.png" width="100%" />
    
    - 소스 : DB폴더 
    - 타겟 : {DATETIME} 값을 넣어서 폴더가 새로 생성되도록 함.  
    - 스케쥴링 : 시작시 한번 실행  


  * **코드 백업**  
    ```
    --transfers=4 --checkers=8 --create-empty-src-dirs --drive-chunk-size=256M --exclude=.git/** --exclude=__pycache__/** --exclude=*.log
    ```
