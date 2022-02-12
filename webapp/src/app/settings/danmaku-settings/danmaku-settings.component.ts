import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  OnChanges,
  ChangeDetectorRef,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

import { Observable } from 'rxjs';
import mapValues from 'lodash-es/mapValues';

import { DanmakuSettings } from '../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from '../shared/constants/form';

@Component({
  selector: 'app-danmaku-settings',
  templateUrl: './danmaku-settings.component.html',
  styleUrls: ['./danmaku-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DanmakuSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: DanmakuSettings;
  syncStatus!: SyncStatus<DanmakuSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      danmuUname: [''],
      recordGiftSend: [''],
      recordFreeGifts: [''],
      recordGuardBuy: [''],
      recordSuperChat: [''],
      saveRawDanmaku: [''],
    });
  }

  get danmuUnameControl() {
    return this.settingsForm.get('danmuUname') as FormControl;
  }

  get recordGiftSendControl() {
    return this.settingsForm.get('recordGiftSend') as FormControl;
  }

  get recordFreeGiftsControl() {
    return this.settingsForm.get('recordFreeGifts') as FormControl;
  }

  get recordGuardBuyControl() {
    return this.settingsForm.get('recordGuardBuy') as FormControl;
  }

  get recordSuperChatControl() {
    return this.settingsForm.get('recordSuperChat') as FormControl;
  }

  get saveRawDanmakuControl() {
    return this.settingsForm.get('saveRawDanmaku') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'danmaku',
        this.settings,
        this.settingsForm.valueChanges as Observable<DanmakuSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
