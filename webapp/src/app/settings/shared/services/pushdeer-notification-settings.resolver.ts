import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ActivatedRouteSnapshot,
  Resolve,
  RouterStateSnapshot,
} from '@angular/router';

import { Observable } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { NGXLogger } from 'ngx-logger';
import { NzNotificationService } from 'ng-zorro-antd/notification';

import { retry } from '../../../shared/rx-operators';
import { PushdeerNotificationSettings } from '../setting.model';
import { SettingService } from './setting.service';

@Injectable()
export class PushdeerNotificationSettingsResolver
  implements Resolve<PushdeerNotificationSettings>
{
  constructor(
    private logger: NGXLogger,
    private notification: NzNotificationService,
    private settingService: SettingService
  ) {}
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<PushdeerNotificationSettings> {
    return this.settingService.getSettings(['pushdeerNotification']).pipe(
      map((settings) => settings.pushdeerNotification),
      retry(3, 300),
      catchError((error: HttpErrorResponse) => {
        this.logger.error(
          'Failed to get PushDeer notification settings:',
          error
        );
        this.notification.error('获取 pushdeer 通知设置出错', error.message, {
          nzDuration: 0,
        });
        throw error;
      })
    );
  }
}
