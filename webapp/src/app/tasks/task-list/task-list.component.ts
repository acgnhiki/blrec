import { Component, ChangeDetectionStrategy, Input } from '@angular/core';

import { TaskData } from '../shared/task.model';

@Component({
  selector: 'app-task-list',
  templateUrl: './task-list.component.html',
  styleUrls: ['./task-list.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskListComponent {
  @Input() dataList: TaskData[] = [];

  trackByRoomId(index: number, data: TaskData): number {
    return data.room_info.room_id;
  }
}
