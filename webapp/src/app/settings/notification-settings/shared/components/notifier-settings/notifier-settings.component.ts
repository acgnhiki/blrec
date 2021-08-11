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

import { NotifierSettings } from '../../../../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-notifier-settings',
  templateUrl: './notifier-settings.component.html',
  styleUrls: ['./notifier-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotifierSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: NotifierSettings;
  @Input() keyOfSettings!:
    | 'emailNotification'
    | 'serverchanNotification'
    | 'pushplusNotification';

  syncStatus!: SyncStatus<NotifierSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      enabled: [''],
    });
  }

  get enabledControl() {
    return this.settingsForm.get('enabled') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        this.keyOfSettings,
        this.settings,
        this.settingsForm.valueChanges as Observable<NotifierSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
