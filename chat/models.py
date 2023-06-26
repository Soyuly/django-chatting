from django.db import models


# Create your models here.
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
