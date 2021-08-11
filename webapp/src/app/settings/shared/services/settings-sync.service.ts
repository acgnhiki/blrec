import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, filter, map, scan, switchMap, tap } from 'rxjs/operators';
import isEmpty from 'lodash-es/isEmpty';
import isEqual from 'lodash-es/isEqual';
import mapValues from 'lodash-es/mapValues';
import { NzMessageService } from 'ng-zorro-antd/message';

import { retry } from '../../../shared/rx-operators';
import { difference } from '../../../shared/utils';
import { SettingsIn } from '../setting.model';
import { SettingService } from './setting.service';

type SK = keyof SettingsIn;
type SV = SettingsIn[SK];

export interface DetailWithResult<V extends SV> {
  prev: V;
  curr: V;
  diff: Partial<V>;
  result: V;
}

export interface DetailWithError<V extends SV> {
  prev: V;
  curr: V;
  diff: Partial<V>;
  error: HttpErrorResponse;
}

export type SyncStatus<Type extends SV> = {
  [Property in keyof Type]: boolean;
};

export function calcSyncStatus<V extends SV>(
  detail: DetailWithResult<V> | DetailWithError<V>
): Partial<SyncStatus<V>> {
  const successful = 'result' in detail;
  return mapValues(detail.diff, () => successful);
}

@Injectable({
  providedIn: 'root',
})
export class SettingsSyncService {
  constructor(
    private message: NzMessageService,
    private settingService: SettingService
  ) {}

  syncSettings<K extends SK, V extends SV>(
    key: K,
    initialValue: V,
    valueChanges: Observable<V>
  ): Observable<DetailWithResult<V> | DetailWithError<V>> {
    return valueChanges.pipe(
      scan<V, [V, V, Partial<V>]>(
        ([, prev], curr) => [
          prev,
          curr,
          difference(curr!, prev!) as Partial<V>,
        ],
        [initialValue, initialValue, {} as Partial<V>]
      ),
      filter(([, , diff]) => !isEmpty(diff)),
      switchMap(([prev, curr, diff]) =>
        this.settingService.changeSettings({ [key]: diff }).pipe(
          retry(3, 300),
          tap(
            (settings) => {
              console.assert(
                isEqual(settings[key], curr),
                'result settings should equal current settings',
                { curr, result: settings[key] }
              );
            },
            (error: HttpErrorResponse) => {
              this.message.error(`设置出错: ${error.message}`);
            }
          ),
          map((settings) => ({ prev, curr, diff, result: settings[key] as V })),
          catchError((error: HttpErrorResponse) =>
            of({ prev, curr, diff, error })
          )
        )
      ),
      tap((detail) => console.debug(`${key} settings sync detail:`, detail))
    );
  }
}
