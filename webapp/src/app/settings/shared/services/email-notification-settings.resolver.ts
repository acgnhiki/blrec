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
import { EmailNotificationSettings } from '../setting.model';
import { SettingService } from './setting.service';

@Injectable()
export class EmailNotificationSettingsResolver
  implements Resolve<EmailNotificationSettings>
{
  constructor(
    private logger: NGXLogger,
    private notification: NzNotificationService,
    private settingService: SettingService
  ) {}
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<EmailNotificationSettings> {
    return this.settingService.getSettings(['emailNotification']).pipe(
      map((settings) => settings.emailNotification),
      retry(3, 300),
      catchError((error: HttpErrorResponse) => {
        this.logger.error('Failed to get email notification settings:', error);
        this.notification.error('获取邮件通知设置出错', error.message, {
          nzDuration: 0,
        });
        throw error;
      })
    );
  }
}
