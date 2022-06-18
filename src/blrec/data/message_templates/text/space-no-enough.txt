路径：{{ event.data.path }}

阈值：{{ event.data.threshold | naturalsize }}

硬盘容量：{{ event.data.usage.total | naturalsize }}

已用空间：{{ event.data.usage.used | naturalsize }}

可用空间：{{ event.data.usage.free | naturalsize }}
