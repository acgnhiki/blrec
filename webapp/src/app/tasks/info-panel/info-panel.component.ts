import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  OnDestroy,
  ChangeDetectorRef,
  Output,
  EventEmitter,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import { NzNotificationService } from 'ng-zorro-antd/notification';
import { interval, of, Subscription, zip } from 'rxjs';
import { catchError, concatAll, switchMap } from 'rxjs/operators';
import { retry } from 'src/app/shared/rx-operators';

import { Metadata, RunningStatus, TaskData } from '../shared/task.model';
import { TaskService } from '../shared/services/task.service';
import { StreamProfile } from '../shared/task.model';

@Component({
  selector: 'app-info-panel',
  templateUrl: './info-panel.component.html',
  styleUrls: ['./info-panel.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InfoPanelComponent implements OnInit, OnDestroy {
  @Input() data!: TaskData;
  @Input() profile!: StreamProfile;
  @Input() metadata: Metadata | null = null;
  @Output() close = new EventEmitter<undefined>();

  readonly RunningStatus = RunningStatus;
  private dataSubscription?: Subscription;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private notification: NzNotificationService,
    private taskService: TaskService
  ) {}

  ngOnInit(): void {
    this.syncData();
  }

  ngOnDestroy(): void {
    this.desyncData();
  }

  isBlurayStreamQuality(): boolean {
    return /_bluray/.test(this.data.task_status.stream_url);
  }

  closePanel(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.close.emit();
  }

  private syncData(): void {
    this.dataSubscription = of(of(0), interval(1000))
      .pipe(
        concatAll(),
        switchMap(() =>
          zip(
            this.taskService.getStreamProfile(this.data.room_info.room_id),
            this.taskService.getMetadata(this.data.room_info.room_id)
          )
        ),
        catchError((error: HttpErrorResponse) => {
          this.notification.error('获取数据出错', error.message);
          throw error;
        }),
        retry(3, 1000)
      )
      .subscribe(
        ([profile, metadata]) => {
          this.profile = profile;
          this.metadata = metadata;
          this.changeDetector.markForCheck();
        },
        (error: HttpErrorResponse) => {
          this.notification.error(
            '获取数据出错',
            '网络连接异常, 请待网络正常后刷新。',
            { nzDuration: 0 }
          );
        }
      );
  }
  private desyncData(): void {
    this.dataSubscription?.unsubscribe();
  }
}
