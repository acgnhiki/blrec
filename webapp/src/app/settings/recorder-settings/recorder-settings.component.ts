import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  OnChanges,
  ChangeDetectorRef,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

import cloneDeep from 'lodash-es/cloneDeep';
import mapValues from 'lodash-es/mapValues';
import { Observable } from 'rxjs';

import type { Mutable } from '../../shared/utility-types';
import {
  BUFFER_OPTIONS,
  QUALITY_OPTIONS,
  SYNC_FAILED_WARNING_TIP,
  TIMEOUT_OPTIONS,
} from '../shared/constants/form';
import { RecorderSettings } from '../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';

@Component({
  selector: 'app-recorder-settings',
  templateUrl: './recorder-settings.component.html',
  styleUrls: ['./recorder-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecorderSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: RecorderSettings;
  syncStatus!: SyncStatus<RecorderSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;
  readonly qualityOptions = cloneDeep(QUALITY_OPTIONS) as Mutable<
    typeof QUALITY_OPTIONS
  >;
  readonly timeoutOptions = cloneDeep(TIMEOUT_OPTIONS) as Mutable<
    typeof TIMEOUT_OPTIONS
  >;
  readonly bufferOptions = cloneDeep(BUFFER_OPTIONS) as Mutable<
    typeof BUFFER_OPTIONS
  >;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      qualityNumber: [''],
      readTimeout: [''],
      bufferSize: [''],
    });
  }

  get qualityNumberControl() {
    return this.settingsForm.get('qualityNumber') as FormControl;
  }

  get readTimeoutControl() {
    return this.settingsForm.get('readTimeout') as FormControl;
  }

  get bufferSizeControl() {
    return this.settingsForm.get('bufferSize') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'recorder',
        this.settings,
        this.settingsForm.valueChanges as Observable<RecorderSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
