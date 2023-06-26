# Django 채팅 기능 구현하기

### 0. redis(noSQL DB 설치하기)

https://inpa.tistory.com/entry/REDIS-%F0%9F%93%9A-Window10-%ED%99%98%EA%B2%BD%EC%97%90-Redis-%EC%84%A4%EC%B9%98%ED%95%98%EA%B8%B0

mac의 경우

```bash
brew install redis
brew services start redis
```

### 1. 가상환경 생성 후 실행

```bash
python -m venv myvenv
source myvenv/bin/activate
```

### 2. 필요한 라이브러리들 설치

```bash
pip install -r requirements.txt
```

### 3. chat이라는 앱 만들기

```bash
django-admin startapp chat
```

### 4. chat 폴더 안에 기본적인 모델을 만들기

```python
class Messaage(models.Model):
    user = models.CharField(max_length=100)
    room = models.ForeignKey(
        "Room", related_name="room", on_delete=models.CASCADE, db_column="room_id"
    )
    content = models.TextField()
    send_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.content

    def last_30_messages(self):
        return Messaage.objects.order_by("created_at").all()[:30]


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    status = models.IntegerField(default=0)
```

- 방 정보를 저장하는 Room 모델과, 메세지의 내용을 저장하는 Message 모델 생성

### 5. chat/views.py 작성

```python
from django.shortcuts import render
from .models import Messaage, Room

def index(request):
    return render(request, "index.html")

def room(request, room_name, nickname):
    # 방이 있으면 해당 방 정보를 들고오고, 방이 없으면 새로운 방을 생성한다.
    room, created = Room.objects.get_or_create(name=room_name)

    # 만약 최초로 방이 생성되면 DB에 저장
    if created:
        room.save()

    # 해당 방의 메세지 내용만 들고오기
    messages = Messaage.objects.filter(room=room)

    return render(
        request,
        "room.html",
        {"room_name": room_name, "messages": messages, "user": nickname},
    )
```

### 6. chat/urls.py 작성

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:room_name>/<str:nickname>", views.room, name="room"),
]
```

### 7. 프로젝트 내부의 urls에 방금 채팅앱의 urls 추가

```python
from django.conf.urls import include
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("chat/", include("chat.urls")),
    path("admin/", admin.site.urls),
]
```

### 8. 템플릿 폴더에 html 파일 넣기

index.html

```javascript
document.querySelector("#room-name-submit").onclick = function (e) {
  const roomName = document.querySelector("#room-name-input").value;
  const userName = document.querySelector("#nickname-input").value;
  window.location.pathname = `/chat/${roomName}/${userName}`;
};
```

- 자신의 프로젝트에서 방 번호 입력하는 부분의 Input태그 아이디를 <strong>room-name-input</strong>으로 설정
- 자신의 프로젝트에서 유저 닉네임 입력하는 부분의 Input태그 id를 <strong>nickname-input</strong>으로 설정

room.html

```javascript
// 방 이름 입력
const roomName = "{{room_name}}";

// 웹소켓 요청 주소
const chatSocket = new WebSocket(
  `ws://${window.location.host}/ws/chat/${roomName}/`
);

/**
 * 서버로부터 메세지를 수신했을 때 실행되는 이벤트 핸들러
 */
chatSocket.onmessage = function (e) {
  // 서버로 부터 데이터 수신
  const data = JSON.parse(e.data);

  // 받은 데이터를 화면에 추가
  document.querySelector(
    "#chat-log"
  ).innerHTML += `<div>${data.user} : ${data.message}</div>`;
};

/**
 * 웹소켓 연결이 끊겼을 때 발생하는 핸들러
 */
chatSocket.onclose = function (e) {
  console.error("Chat socket closed unexpectedly");
};

/**
 * 엔터 눌렀을 때 자동으로 메세지가 보내지게 하기 위해 설정
 */
document.querySelector("#chat-message-input").focus();
document.querySelector("#chat-message-input").onkeyup = function (e) {
  if (e.keyCode === 13) {
    // enter, return
    document.querySelector("#chat-message-submit").click();
  }
};

/**
 * 전송버튼을 눌러 메세지를 보낼 때 발생하는 이벤트 핸들러
 */
document.querySelector("#chat-message-submit").onclick = function (e) {
  // Input필드의 valuea를 가져온다.
  const messageInputDom = document.querySelector("#chat-message-input");
  const message = messageInputDom.value;

  // 빈 메세지일 때는 메세지를 보내지 않음
  if (message === "") return;

  // 빈 메세지가 아닐 때는 서버에 해당 내용을 전송
  chatSocket.send(
    JSON.stringify({
      message: message,
      user: "{{user}}",
    })
  );

  // 인풋값 초기화
  messageInputDom.value = "";
};

/**
 * 채팅방 나가기를 클릭했을 때 호출되는 이벤트 핸들러
 */
document.querySelector("#room-leave").onclick = function (e) {
  chatSocket.close();
  window.location.pathname = `/chat`;
};
```

- 실제 채팅 기록이 나오는 부분의 태그 id를 <strong>chat-log</strong>로 설정하기
- 대화 내용 작성하는 부분의 태그 id를 <strong>chat-message-input</strong>로 설정하기
- 대화내용 전송 버튼 태그의 id를 <strong>chat-message-submit</strong>로 설정
- 방 종료버튼의 id를 <strong>room-leave</strong>로 설정

### 9. chat/consumer.py 만들기

```python
# chat/consumers.py
import json
from .models import Messaage, Room

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


"""
Django의 Views.py와 비슷한 클래스
여기에 웹소켓과 관련된 동작들을 정의해서 사용할 수 있음
"""


class ChatConsumer(AsyncWebsocketConsumer):

    """
    WebSocket 연결이 정상적으로 이루어졌을 때 호출되는 메소드
    클라이언트가 채팅에 연결하면 실행
    """

    async def connect(self):
        # 파라미터 값으로 채팅 룸을 이름을 가져온다.
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]

        # 웹 소켓 내부의 그룹이름
        self.room_group_name = "chat_%s" % self.room_name

        # 채널 레이어에 해당 방장 그룹 추가
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # 웹소켓 연결 허용
        await self.accept()

    """
    사용자와 WebSocket 연결이 종료됐을 때 호출되는 메소드
    클라이언트가 채팅에서 연결을 끊으면 실행
    """

    async def disconnect(self, close_code):
        # 현재 방의 연결을 끊는다.
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    """
    사용자가 메세지를 보낼 때 호출되는 메소드
    """

    async def receive(self, text_data):
        # 클라이언트에서 보낸 채팅 데이터를 들고온다.
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]  # 채팅 내용 부분 추출
        user = text_data_json["user"]  # 유저 닉네임 추출

        print("receive함수 실행")

        # 대화내용을 DB에 저장
        await self.save_massage_on_db(user, self.room_name, message)

        # 룸 그룹으로 메세지 보냄
        # type: chat_message => 아래에 있는 chat_message()실행
        # 만약에 type이 disconnect이면 종료 명령 실행
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "user": user,
            },
        )

    async def chat_message(self, event):
        print(event)
        message = event["message"]
        user = event["user"]

        print("chat_message함수 실행")

        # 웹소켓으로 메세지 보냄
        await self.send(text_data=json.dumps({"message": message, "user": user}))

    """
    데이터베이스에 메세지 내용을 저장하는 메소드
    """

    @database_sync_to_async
    def save_massage_on_db(self, user, room_name, message):
        room = Room.objects.get(name=room_name)
        message = Messaage.objects.create(user=user, room=room, content=message)

        message.save()

```

### 9. chat/rounting.py 추가

```python
# chat/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
]
```

### 9. settings.py 수정

1. INSTALLED_APPS에 channels와 chat앱 추가

```python
INSTALLED_APPS = [
    "channels",
    "chat",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
```

2. settings.py에 ASGI관련 설정 추가

```python
# Channels
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

- 여기서 hosts에 나중에 배포를 한다면 이 127.0.0.1을 배포 주소로 바꾸자.

### 10. 프로젝트 폴더의 asgi.py 파일 수정

```python
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import chat.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# application = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        # Just HTTP for now. (We can add other protocols later.)
        "websocket": AuthMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns)),
    }
)
```

### 11. 확인을 위한 runserver 실행

```bash
python manage.py runserver
```

```bash
System check identified no issues (0 silenced).
June 26, 2023 - 15:30:53
Django version 4.0, using settings 'config.settings'
Starting ASGI/Channels version 3.0.4 development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

- Django version 4.0, using settings 'config.settings'
  Starting ASGI/Channels version떠야 성공
