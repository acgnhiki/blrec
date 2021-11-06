import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
} from '@angular/core';

import { RoomInfo } from '../../shared/task.model';

@Component({
  selector: 'app-task-room-info-detail',
  templateUrl: './task-room-info-detail.component.html',
  styleUrls: ['./task-room-info-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskRoomInfoDetailComponent implements OnInit {
  @Input() loading: boolean = true;
  @Input() roomInfo!: RoomInfo;

  constructor() {}

  ngOnInit(): void {}
}
