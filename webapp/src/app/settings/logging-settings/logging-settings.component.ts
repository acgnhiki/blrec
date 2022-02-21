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
import range from 'lodash-es/range';

import { LoggingSettings } from '../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from '../shared/constants/form';

@Component({
  selector: 'app-logging-settings',
  templateUrl: './logging-settings.component.html',
  styleUrls: ['./logging-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoggingSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: LoggingSettings;
  syncStatus!: SyncStatus<LoggingSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  readonly logLevelOptions = [
    { label: 'VERBOSE', value: 'NOTSET' },
    { label: 'DEBUG', value: 'DEBUG' },
    { label: 'INFO', value: 'INFO' },
    { label: 'WARNING', value: 'WARNING' },
    { label: 'ERROR', value: 'ERROR' },
    { label: 'CRITICAL', value: 'CRITICAL' },
  ];

  readonly maxBytesOptions = range(1, 11).map((i) => ({
    label: `${i} MB`,
    value: 1024 ** 2 * i,
  }));

  readonly backupOptions = range(1, 31).map((i) => ({
    label: i.toString(),
    value: i,
  }));

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      logDir: [''],
      consoleLogLevel: [''],
      maxBytes: [''],
      backupCount: [''],
    });
  }

  get logDirControl() {
    return this.settingsForm.get('logDir') as FormControl;
  }

  get consoleLogLevelControl() {
    return this.settingsForm.get('consoleLogLevel') as FormControl;
  }

  get maxBytesControl() {
    return this.settingsForm.get('maxBytes') as FormControl;
  }

  get backupCountControl() {
    return this.settingsForm.get('backupCount') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'logging',
        this.settings,
        this.settingsForm.valueChanges as Observable<LoggingSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
