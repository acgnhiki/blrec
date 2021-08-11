import { Component, ChangeDetectionStrategy, Input } from '@angular/core';

import { RunningStatus, TaskStatus } from '../shared/task.model';

@Component({
  selector: 'app-status-display',
  templateUrl: './status-display.component.html',
  styleUrls: ['./status-display.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusDisplayComponent {
  @Input() status!: TaskStatus;

  readonly RunningStatus = RunningStatus;
}
