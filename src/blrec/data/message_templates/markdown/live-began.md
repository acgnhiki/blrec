主播：[{{ event.data.user_info.name }}](https://space.bilibili.com/{{ event.data.user_info.uid }})

标题：[{{ event.data.room_info.title }}](https://live.bilibili.com/{{ event.data.room_info.room_id }})

分区：[{{ event.data.room_info.parent_area_name }}·{{ event.data.room_info.area_name }}](https://live.bilibili.com/p/eden/area-tags?parentAreaId={{ event.data.room_info.parent_area_id }}&areaId={{ event.data.room_info.area_id }})

房间：[
  {%- if event.data.room_info.short_room_id > 0 -%}
    {{ event.data.room_info.short_room_id }}{% raw %}, {% endraw %}
  {%- endif -%}
    {{ event.data.room_info.room_id }}
](https://live.bilibili.com/{{ event.data.room_info.room_id }})
{% if event.data.room_info.live_start_time > 0 %}
开播：{{ event.data.room_info.live_start_time | datetimestring }}
{% endif %}
![直播间封面]({{ event.data.room_info.cover }})
