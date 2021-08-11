import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { environment } from 'src/environments/environment';
import { ResponseMessage } from '../../../shared/api.models';
import {
  TaskData,
  DataSelection,
  TaskParam,
  FileDetail,
  AddTaskResult,
} from '../task.model';

const apiUrl = environment.apiUrl;

@Injectable({
  providedIn: 'root',
})
export class TaskService {
  constructor(private http: HttpClient) {}

  getAllTaskData(
    select: DataSelection = DataSelection.ALL
  ): Observable<TaskData[]> {
    const url = apiUrl + '/api/v1/tasks/data';
    return this.http.get<TaskData[]>(url, { params: { select } });
  }

  getTaskData(roomId: number): Observable<TaskData> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/data`;
    return this.http.get<TaskData>(url);
  }

  getTaskFileDetails(roomId: number): Observable<FileDetail[]> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/files`;
    return this.http.get<FileDetail[]>(url);
  }

  getTaskParam(roomId: number): Observable<TaskParam> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/param`;
    return this.http.get<TaskParam>(url);
  }

  updateAllTaskInfos(): Observable<ResponseMessage> {
    const url = apiUrl + '/api/v1/tasks/info';
    return this.http.post<ResponseMessage>(url, null);
  }

  updateTaskInfo(roomId: number): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/info`;
    return this.http.post<ResponseMessage>(url, null);
  }

  addTask(roomId: number): Observable<AddTaskResult> {
    const url = apiUrl + `/api/v1/tasks/${roomId}`;
    return this.http.post<AddTaskResult>(url, null);
  }

  removeTask(roomId: number): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}`;
    return this.http.delete<ResponseMessage>(url);
  }

  removeAllTasks(): Observable<ResponseMessage> {
    const url = apiUrl + '/api/v1/tasks';
    return this.http.delete<ResponseMessage>(url);
  }

  startTask(roomId: number): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/start`;
    return this.http.post<ResponseMessage>(url, null);
  }

  startAllTasks(): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/start`;
    return this.http.post<ResponseMessage>(url, null);
  }

  stopTask(
    roomId: number,
    force: boolean = false,
    background: boolean = false
  ): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/stop`;
    return this.http.post<ResponseMessage>(url, { force, background });
  }

  stopAllTasks(
    force: boolean = false,
    background: boolean = false
  ): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/stop`;
    return this.http.post<ResponseMessage>(url, { force, background });
  }

  enableTaskMonitor(roomId: number): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/monitor/enable`;
    return this.http.post<ResponseMessage>(url, null);
  }

  enableAllMonitors(): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/monitor/enable`;
    return this.http.post<ResponseMessage>(url, null);
  }

  disableTaskMonitor(
    roomId: number,
    background: boolean = false
  ): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/monitor/disable`;
    return this.http.post<ResponseMessage>(url, { background });
  }

  disableAllMonitors(background: boolean = false): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/monitor/disable`;
    return this.http.post<ResponseMessage>(url, { background });
  }

  enableTaskRecorder(roomId: number): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/recorder/enable`;
    return this.http.post<ResponseMessage>(url, null);
  }

  enableAllRecorders(): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/recorder/enable`;
    return this.http.post<ResponseMessage>(url, null);
  }

  disableTaskRecorder(
    roomId: number,
    force: boolean = false,
    background: boolean = false
  ): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/${roomId}/recorder/disable`;
    return this.http.post<ResponseMessage>(url, { force, background });
  }

  disableAllRecorders(
    force: boolean = false,
    background: boolean = false
  ): Observable<ResponseMessage> {
    const url = apiUrl + `/api/v1/tasks/recorder/disable`;
    return this.http.post<ResponseMessage>(url, { force, background });
  }
}
