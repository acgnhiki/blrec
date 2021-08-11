import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  OnDestroy,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import { catchError, concatAll, switchMap } from 'rxjs/operators';
import { interval, of, Subscription } from 'rxjs';
import { NzNotificationService } from 'ng-zorro-antd/notification';

import { TaskData, DataSelection } from './shared/task.model';
import { retry } from 'src/app/shared/rx-operators';
import { TaskService } from './shared/services/task.service';
import { StorageService } from '../core/services/storage.service';

const SELECTION_STORAGE_KEY = 'app-tasks-selection';
const REVERSE_STORAGE_KEY = 'app-tasks-reverse';

@Component({
  selector: 'app-tasks',
  templateUrl: './tasks.component.html',
  styleUrls: ['./tasks.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TasksComponent implements OnInit, OnDestroy {
  loading: boolean = true;
  dataList: TaskData[] = [];
  selection: DataSelection;
  reverse: boolean;
  filterTerm = '';

  private dataSubscription?: Subscription;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private notification: NzNotificationService,
    private storage: StorageService,
    private taskService: TaskService
  ) {
    this.selection = this.retrieveSelection();
    this.reverse = this.retrieveReverse();
  }

  ngOnInit(): void {
    this.syncTaskData();
  }

  ngOnDestroy(): void {
    this.desyncTaskData();
  }

  onSelectionChanged(selection: DataSelection): void {
    this.selection = selection;
    this.storeSelection(selection);
    this.desyncTaskData();
    this.syncTaskData();
  }

  onReverseChanged(reverse: boolean): void {
    this.reverse = reverse;
    this.storeReverse(reverse);
    if (reverse) {
      this.dataList = [...this.dataList.reverse()];
      this.changeDetector.markForCheck();
    }
  }

  private retrieveSelection(): DataSelection {
    const selection = this.storage.getData(
      SELECTION_STORAGE_KEY
    ) as DataSelection | null;
    return selection !== null ? selection : DataSelection.ALL;
  }

  private retrieveReverse(): boolean {
    return this.storage.getData(REVERSE_STORAGE_KEY) === 'true';
  }

  private storeSelection(value: DataSelection): void {
    this.storage.setData(SELECTION_STORAGE_KEY, value);
  }

  private storeReverse(value: boolean): void {
    this.storage.setData(REVERSE_STORAGE_KEY, value.toString());
  }

  private syncTaskData(): void {
    this.dataSubscription = of(of(0), interval(1000))
      .pipe(
        concatAll(),
        switchMap(() => this.taskService.getAllTaskData(this.selection)),
        catchError((error: HttpErrorResponse) => {
          this.notification.error('获取任务数据出错', error.message);
          throw error;
        }),
        retry(10, 3000)
      )
      .subscribe(
        (dataList) => {
          this.loading = false;
          this.dataList = this.reverse ? dataList.reverse() : dataList;
          this.changeDetector.markForCheck();
        },
        (error: HttpErrorResponse) => {
          this.notification.error(
            '获取任务数据出错',
            '网络连接异常, 请待网络正常后刷新。',
            { nzDuration: 0 }
          );
        }
      );
  }

  private desyncTaskData(): void {
    this.dataSubscription?.unsubscribe();
  }
}
