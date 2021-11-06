import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
} from '@angular/core';

import { UserInfo } from '../../shared/task.model';

@Component({
  selector: 'app-task-user-info-detail',
  templateUrl: './task-user-info-detail.component.html',
  styleUrls: ['./task-user-info-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskUserInfoDetailComponent implements OnInit {
  @Input() loading: boolean = true;
  @Input() userInfo!: UserInfo;

  constructor() {}

  ngOnInit(): void {}
}
