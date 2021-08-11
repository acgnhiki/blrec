import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable } from 'rxjs';

import { environment } from 'src/environments/environment';
import { AppInfo, appStatus } from '../models/app.models';

const apiUrl = environment.apiUrl;

@Injectable({
  providedIn: 'root',
})
export class AppService {
  constructor(private http: HttpClient) {}

  getAppInfo(): Observable<AppInfo> {
    const url = apiUrl + `/api/v1/app/info`;
    return this.http.get<AppInfo>(url);
  }

  getAppStatus(): Observable<appStatus> {
    const url = apiUrl + `/api/v1/app/status`;
    return this.http.get<appStatus>(url);
  }

  restartApp(): Observable<undefined> {
    const url = apiUrl + `/api/v1/app/restart`;
    return this.http.post<undefined>(url, null);
  }

  exitApp(): Observable<undefined> {
    const url = apiUrl + `/api/v1/app/exit`;
    return this.http.post<undefined>(url, null);
  }
}
