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

import { SpaceSettings } from '../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from '../shared/constants/form';

@Component({
  selector: 'app-disk-space-settings',
  templateUrl: './disk-space-settings.component.html',
  styleUrls: ['./disk-space-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DiskSpaceSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: SpaceSettings;
  syncStatus!: SyncStatus<SpaceSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  readonly intervalOptions = [
    { label: '10 秒', value: 10 },
    { label: '30 秒', value: 30 },
    { label: '1 分钟', value: 60 },
    { label: '3 分钟', value: 180 },
    { label: '5 分钟', value: 300 },
    { label: '10 分钟', value: 600 },
  ];

  readonly thresholdOptions = [
    { label: '1 GB', value: 1024 ** 3 },
    { label: '3 GB', value: 1024 ** 3 * 3 },
    { label: '5 GB', value: 1024 ** 3 * 5 },
    { label: '10 GB', value: 1024 ** 3 * 10 },
    { label: '20 GB', value: 1024 ** 3 * 20 },
  ];

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      recycleRecords: [''],
      checkInterval: [''],
      spaceThreshold: [''],
    });
  }

  get recycleRecordsControl() {
    return this.settingsForm.get('recycleRecords') as FormControl;
  }

  get checkIntervalControl() {
    return this.settingsForm.get('checkInterval') as FormControl;
  }

  get spaceThresholdControl() {
    return this.settingsForm.get('spaceThreshold') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'space',
        this.settings,
        this.settingsForm.valueChanges as Observable<SpaceSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
