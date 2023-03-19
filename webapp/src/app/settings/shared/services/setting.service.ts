import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Observable } from 'rxjs';

import { UrlService } from 'src/app/core/services/url.service';
import {
  Settings,
  TaskOptions,
  TaskOptionsIn,
  SettingsIn,
  SettingsOut,
} from '../setting.model';

@Injectable({
  providedIn: 'root',
})
export class SettingService {
  constructor(private http: HttpClient, private url: UrlService) {}

  getSettings(
    include: Array<keyof Settings> | null = null,
    exclude: Array<keyof Settings> | null = null
  ): Observable<Settings> {
    const url = this.url.makeApiUrl(`/api/v1/settings`);
    return this.http.get<Settings>(url, {
      params: {
        include: include ?? [],
        exclude: exclude ?? [],
      },
    });
  }

  /**
   * Change settings of the application
   *
   * Change the output directory will cause the application be **restarted**!
   *
   * Change network request headers will cause
   * **all** the Danmaku client be **reconnected**!
   *
   * @param settings settings to change
   * @returns settings of the application
   */
  changeSettings(settings: SettingsIn): Observable<SettingsOut> {
    const url = this.url.makeApiUrl(`/api/v1/settings`);
    return this.http.patch<SettingsOut>(url, settings);
  }

  getTaskOptions(roomId: number): Observable<TaskOptions> {
    const url = this.url.makeApiUrl(`/api/v1/settings/tasks/${roomId}`);
    return this.http.get<TaskOptions>(url);
  }

  /**
   * Change task-specific options
   *
   * Task-specific options will shadow the corresponding global settings.
   * Explicitly set options to **null** will remove the value shadowing.
   *
   * Change network request headers will cause the Danmaku client be **reconnected**!
   *
   * @param roomId the real room id of the task
   * @param options options to change
   * @returns changed options
   */
  changeTaskOptions(
    roomId: number,
    options: TaskOptionsIn
  ): Observable<TaskOptions> {
    const url = this.url.makeApiUrl(`/api/v1/settings/tasks/${roomId}`);
    return this.http.patch<TaskOptions>(url, options);
  }
}
