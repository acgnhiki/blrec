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

import { BiliApiSettings } from '../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from '../shared/constants/form';

@Component({
  selector: 'app-bili-api-settings',
  templateUrl: './bili-api-settings.component.html',
  styleUrls: ['./bili-api-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BiliApiSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: BiliApiSettings;
  syncStatus!: SyncStatus<BiliApiSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      baseApiUrl: [''],
      baseLiveApiUrl: [''],
      basePlayInfoApiUrl: [''],
    });
  }

  get baseApiUrlControl() {
    return this.settingsForm.get('baseApiUrl') as FormControl;
  }

  get baseLiveApiUrlControl() {
    return this.settingsForm.get('baseLiveApiUrl') as FormControl;
  }

  get basePlayInfoApiUrlControl() {
    return this.settingsForm.get('basePlayInfoApiUrl') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'biliApi',
        this.settings,
        this.settingsForm.valueChanges as Observable<BiliApiSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
