import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
} from '@angular/core';

import { TaskStatus } from '../../shared/task.model';

@Component({
  selector: 'app-task-recording-detail',
  templateUrl: './task-recording-detail.component.html',
  styleUrls: ['./task-recording-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskRecordingDetailComponent implements OnInit {
  @Input() loading: boolean = true;
  @Input() taskStatus!: TaskStatus;

  constructor() {}

  ngOnInit(): void {}
}
