import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import { catchError, map, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';
import { NzMessageService } from 'ng-zorro-antd/message';

import { TaskService } from './task.service';
import { ResponseMessage } from 'src/app/shared/api.models';

export interface AddTaskResultMessage {
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
}

@Injectable({
  providedIn: 'root',
})
export class TaskManagerService {
  constructor(
    private message: NzMessageService,
    private taskService: TaskService
  ) {}

  getAllTaskRoomIds(): Observable<number[]> {
    return this.taskService
      .getAllTaskData()
      .pipe(map((taskData) => taskData.map((data) => data.room_info.room_id)));
  }

  updateTaskInfo(roomId: number): Observable<ResponseMessage> {
    return this.taskService.updateTaskInfo(roomId).pipe(
      tap(
        () => {
          this.message.success('成功刷新任务的数据');
        },
        (error: HttpErrorResponse) => {
          this.message.error(`刷新任务的数据出错: ${error.message}`);
        }
      )
    );
  }

  updateAllTaskInfos(): Observable<ResponseMessage> {
    return this.taskService.updateAllTaskInfos().pipe(
      tap(
        () => {
          this.message.success('成功刷新全部任务的数据');
        },
        (error: HttpErrorResponse) => {
          this.message.error(`刷新全部任务的数据出错: ${error.message}`);
        }
      )
    );
  }

  addTask(roomId: number): Observable<AddTaskResultMessage> {
    return this.taskService.addTask(roomId).pipe(
      map((result) => {
        return {
          type: 'success',
          message: '成功添加任务',
        } as AddTaskResultMessage;
      }),
      catchError((error: HttpErrorResponse) => {
        let result: AddTaskResultMessage;
        if (error.status == 409) {
          result = {
            type: 'error',
            message: '任务已存在，不能重复添加。',
          };
        } else if (error.status == 403) {
          result = {
            type: 'warning',
            message: '任务数量超过限制，不能添加任务。',
          };
        } else if (error.status == 404) {
          result = {
            type: 'error',
            message: '直播间不存在',
          };
        } else {
          result = {
            type: 'error',
            message: `添加任务出错: ${error.message}`,
          };
        }
        return of(result);
      }),
      map((resultMessage) => {
        resultMessage.message = `${roomId}: ${resultMessage.message}`;
        return resultMessage;
      }),
      tap((resultMessage) => {
        this.message[resultMessage.type](resultMessage.message);
      })
    );
  }

  removeTask(roomId: number): Observable<ResponseMessage> {
    return this.taskService.removeTask(roomId).pipe(
      tap(
        () => {
          this.message.success('任务已删除');
        },
        (error: HttpErrorResponse) => {
          this.message.error(`删除任务出错: ${error.message}`);
        }
      )
    );
  }

  removeAllTasks(): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在删除全部任务...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.removeAllTasks().pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功删除全部任务');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`删除全部任务出错: ${error.message}`);
        }
      )
    );
  }

  startTask(roomId: number): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在运行任务...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.startTask(roomId).pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功运行任务');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`运行任务出错: ${error.message}`);
        }
      )
    );
  }

  startAllTasks(): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在运行全部任务...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.startAllTasks().pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功运行全部任务');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`运行全部任务出错: ${error.message}`);
        }
      )
    );
  }

  stopTask(
    roomId: number,
    force: boolean = false
  ): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在停止任务...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.stopTask(roomId, force).pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功停止任务');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`停止任务出错: ${error.message}`);
        }
      )
    );
  }

  stopAllTasks(force: boolean = false): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在停止全部任务...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.stopAllTasks(force).pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功停止全部任务');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`停止全部任务出错: ${error.message}`);
        }
      )
    );
  }

  enableRecorder(roomId: number): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在开启录制...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.enableTaskRecorder(roomId).pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功开启录制');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`开启录制出错: ${error.message}`);
        }
      )
    );
  }

  /**
   * Deprecated!
   * Enable all tasks' recorder will cause some problems.
   * Tasks those monitor are disabled won't work as expected!
   */
  enableAllRecorders(): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在开启全部任务的录制...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.enableAllRecorders().pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功开启全部任务的录制');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`开启全部任务的录制出错: ${error.message}`);
        }
      )
    );
  }

  disableRecorder(
    roomId: number,
    force: boolean = false
  ): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在关闭录制...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.disableTaskRecorder(roomId, force).pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功关闭录制');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`关闭录制出错: ${error.message}`);
        }
      )
    );
  }

  disableAllRecorders(force: boolean = false): Observable<ResponseMessage> {
    const messageId = this.message.loading('正在关闭全部任务的录制...', {
      nzDuration: 0,
    }).messageId;
    return this.taskService.disableAllRecorders(force).pipe(
      tap(
        () => {
          this.message.remove(messageId);
          this.message.success('成功关闭全部任务的录制');
        },
        (error: HttpErrorResponse) => {
          this.message.remove(messageId);
          this.message.error(`关闭全部任务的录制出错: ${error.message}`);
        }
      )
    );
  }

  cutStream(roomId: number) {
    return this.taskService.cutStream(roomId).pipe(
      tap(
        () => {
          this.message.success('文件切割已触发');
        },
        (error: HttpErrorResponse) => {
          if (error.status == 403) {
            this.message.warning('时长太短不能切割，请稍后再试。');
          } else {
            this.message.error(`切割文件出错: ${error.message}`);
          }
        }
      )
    );
  }
}
