import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ActivatedRouteSnapshot,
  Resolve,
  RouterStateSnapshot,
} from '@angular/router';

import { Observable } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { NGXLogger } from 'ngx-logger';
import { NzNotificationService } from 'ng-zorro-antd/notification';

import { retry } from '../../../shared/rx-operators';
import { Settings } from '../setting.model';
import { SettingService } from './setting.service';

type PrimarySettings = Pick<
  Settings,
  | 'output'
  | 'logging'
  | 'header'
  | 'danmaku'
  | 'recorder'
  | 'postprocessing'
  | 'space'
>;

@Injectable()
export class SettingsResolver implements Resolve<PrimarySettings> {
  constructor(
    private logger: NGXLogger,
    private notification: NzNotificationService,
    private settingService: SettingService
  ) {}
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<PrimarySettings> {
    return this.settingService
      .getSettings([
        'output',
        'logging',
        'header',
        'danmaku',
        'recorder',
        'postprocessing',
        'space',
      ])
      .pipe(
        retry(3, 300),
        catchError((error: HttpErrorResponse) => {
          this.logger.error('Failed to get settings:', error);
          this.notification.error('获取设置出错', error.message, {
            nzDuration: 0,
          });
          throw error;
        })
      );
  }
}
