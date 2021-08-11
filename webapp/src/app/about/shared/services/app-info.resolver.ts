import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot,
} from '@angular/router';

import { Observable } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { NGXLogger } from 'ngx-logger';
import { NzNotificationService } from 'ng-zorro-antd/notification';

import { AppInfo } from 'src/app/core/models/app.models';
import { AppService } from 'src/app/core/services/app.service';
import { retry } from 'src/app/shared/rx-operators';

@Injectable()
export class AppInfoResolver implements Resolve<AppInfo> {
  constructor(
    private logger: NGXLogger,
    private notification: NzNotificationService,
    private appService: AppService
  ) {}
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<AppInfo> {
    return this.appService.getAppInfo().pipe(
      retry(3, 300),
      catchError((error: HttpErrorResponse) => {
        this.logger.error('Failed to get app info:', error);
        this.notification.error('获取后端应用信息出错', error.message, {
          nzDuration: 0,
        });
        throw error;
      })
    );
  }
}
