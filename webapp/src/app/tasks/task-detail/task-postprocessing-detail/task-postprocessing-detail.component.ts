import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
} from '@angular/core';

import { PostprocessorStatus, TaskStatus } from '../../shared/task.model';

@Component({
  selector: 'app-task-postprocessing-detail',
  templateUrl: './task-postprocessing-detail.component.html',
  styleUrls: ['./task-postprocessing-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskPostprocessingDetailComponent implements OnInit {
  @Input() loading: boolean = true;
  @Input() taskStatus!: TaskStatus;

  constructor() {}

  ngOnInit(): void {}

  get title(): string {
    switch (this.taskStatus.postprocessor_status) {
      case PostprocessorStatus.INJECTING:
        return '更新 FLV 元数据';
      case PostprocessorStatus.REMUXING:
        return '转换 FLV 为 MP4';
      default:
        return '文件处理';
    }
  }
}
