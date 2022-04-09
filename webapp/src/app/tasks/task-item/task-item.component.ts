import {
  Component,
  OnChanges,
  OnDestroy,
  Input,
  HostBinding,
  SimpleChanges,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { BreakpointObserver } from '@angular/cdk/layout';

import { Subject, zip } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';

import { retry } from '../../shared/rx-operators';
import { breakpoints } from '../shared/breakpoints';
import { SettingService } from '../../settings/shared/services/setting.service';
import { RunningStatus, TaskData } from '../shared/task.model';
import { TaskManagerService } from '../shared/services/task-manager.service';
import {
  TaskOptions,
  GlobalTaskSettings,
  TaskOptionsIn,
} from '../../settings/shared/setting.model';
import { TaskSettingsService } from '../shared/services/task-settings.service';

@Component({
  selector: 'app-task-item',
  templateUrl: './task-item.component.html',
  styleUrls: ['./task-item.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskItemComponent implements OnChanges, OnDestroy {
  @Input() data!: TaskData;
  @HostBinding('class.stopped') stopped = false;

  taskOptions?: TaskOptions;
  globalSettings?: GlobalTaskSettings;

  destroyed = new Subject<void>();
  useDrawer = false;
  menuDrawerVisible = false;
  switchPending = false;
  settingsDialogVisible = false;

  readonly RunningStatus = RunningStatus;

  constructor(
    breakpointObserver: BreakpointObserver,
    private changeDetector: ChangeDetectorRef,
    private message: NzMessageService,
    private modal: NzModalService,
    private settingService: SettingService,
    private taskManager: TaskManagerService,
    private appTaskSettings: TaskSettingsService
  ) {
    breakpointObserver
      .observe(breakpoints[0])
      .pipe(takeUntil(this.destroyed))
      .subscribe((state) => {
        this.useDrawer = state.matches;
        changeDetector.markForCheck();
      });
  }

  get roomId() {
    return this.data.room_info.room_id;
  }

  get toggleRecorderForbidden() {
    return !this.data.task_status.monitor_enabled;
  }

  get showInfoPanel() {
    return Boolean(this.appTaskSettings.getSettings(this.roomId).showInfoPanel);
  }

  set showInfoPanel(value: boolean) {
    this.appTaskSettings.updateSettings(this.roomId, { showInfoPanel: value });
  }

  ngOnChanges(changes: SimpleChanges): void {
    console.debug('[ngOnChanges]', this.roomId, changes);
    this.stopped =
      this.data.task_status.running_status === RunningStatus.STOPPED;
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }

  updateTaskInfo(): void {
    this.taskManager.updateTaskInfo(this.roomId).subscribe();
  }

  toggleRecorder(): void {
    if (this.toggleRecorderForbidden) {
      return;
    }

    if (this.switchPending) {
      return;
    }
    this.switchPending = true;

    if (this.data.task_status.recorder_enabled) {
      this.taskManager
        .disableRecorder(this.roomId)
        .subscribe(() => (this.switchPending = false));
    } else {
      this.taskManager
        .enableRecorder(this.roomId)
        .subscribe(() => (this.switchPending = false));
    }
  }

  removeTask(): void {
    this.taskManager.removeTask(this.roomId).subscribe();
  }

  startTask(): void {
    if (this.data.task_status.running_status === RunningStatus.STOPPED) {
      this.taskManager.startTask(this.roomId).subscribe();
    } else {
      this.message.warning('任务运行中，忽略操作。');
    }
  }

  stopTask(force: boolean = false): void {
    if (this.data.task_status.running_status === RunningStatus.STOPPED) {
      this.message.warning('任务处于停止状态，忽略操作。');
      return;
    }

    if (
      force &&
      this.data.task_status.running_status == RunningStatus.RECORDING
    ) {
      this.modal.confirm({
        nzTitle: '确定要强制停止任务？',
        nzContent: '正在录制的文件会被强行中断！确定要放弃正在录制的文件？',
        nzOnOk: () =>
          new Promise((resolve, reject) => {
            this.taskManager
              .stopTask(this.roomId, force)
              .subscribe(resolve, reject);
          }),
      });
    } else {
      this.taskManager.stopTask(this.roomId).subscribe();
    }
  }

  disableRecorder(force: boolean = false): void {
    if (!this.data.task_status.recorder_enabled) {
      this.message.warning('录制处于关闭状态，忽略操作。');
      return;
    }

    if (
      force &&
      this.data.task_status.running_status == RunningStatus.RECORDING
    ) {
      this.modal.confirm({
        nzTitle: '确定要强制停止录制？',
        nzContent: '正在录制的文件会被强行中断！确定要放弃正在录制的文件？',
        nzOnOk: () =>
          new Promise((resolve, reject) => {
            this.taskManager
              .disableRecorder(this.roomId, force)
              .subscribe(resolve, reject);
          }),
      });
    } else {
      this.taskManager.disableRecorder(this.roomId).subscribe();
    }
  }

  openSettingsDialog(): void {
    zip(
      this.settingService.getTaskOptions(this.roomId),
      this.settingService.getSettings([
        'output',
        'header',
        'danmaku',
        'recorder',
        'postprocessing',
      ])
    ).subscribe(
      ([taskOptions, globalSettings]) => {
        this.taskOptions = taskOptions;
        this.globalSettings = globalSettings;
        this.settingsDialogVisible = true;
        this.changeDetector.markForCheck();
      },
      (error: HttpErrorResponse) => {
        this.message.error(`获取任务设置出错: ${error.message}`);
      }
    );
  }

  cleanSettingsData(): void {
    delete this.taskOptions;
    delete this.globalSettings;
    this.changeDetector.markForCheck();
  }

  changeTaskOptions(options: TaskOptionsIn): void {
    this.settingService
      .changeTaskOptions(this.roomId, options)
      .pipe(retry(3, 300))
      .subscribe(
        (options) => {
          this.message.success('修改任务设置成功');
        },
        (error: HttpErrorResponse) => {
          this.message.error(`修改任务设置出错: ${error.message}`);
        }
      );
  }

  cutStream(): void {
    if (this.data.task_status.running_status === RunningStatus.RECORDING) {
      this.taskManager.cutStream(this.roomId).subscribe();
    }
  }
}
