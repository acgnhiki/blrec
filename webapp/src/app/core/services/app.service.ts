import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { UrlService } from './url.service';
import { AppInfo, appStatus } from '../models/app.models';

@Injectable({
  providedIn: 'root',
})
export class AppService {
  constructor(private http: HttpClient, private url: UrlService) {}

  getAppInfo(): Observable<AppInfo> {
    const url = this.url.makeApiUrl(`/api/v1/app/info`);
    return this.http.get<AppInfo>(url);
  }

  getAppStatus(): Observable<appStatus> {
    const url = this.url.makeApiUrl(`/api/v1/app/status`);
    return this.http.get<appStatus>(url);
  }

  restartApp(): Observable<undefined> {
    const url = this.url.makeApiUrl(`/api/v1/app/restart`);
    return this.http.post<undefined>(url, null);
  }

  exitApp(): Observable<undefined> {
    const url = this.url.makeApiUrl(`/api/v1/app/exit`);
    return this.http.post<undefined>(url, null);
  }
}
