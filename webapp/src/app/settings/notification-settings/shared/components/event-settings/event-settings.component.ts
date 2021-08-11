import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  OnChanges,
  ChangeDetectorRef,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

import mapValues from 'lodash-es/mapValues';
import { Observable } from 'rxjs';

import { NotificationSettings } from '../../../../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-event-settings',
  templateUrl: './event-settings.component.html',
  styleUrls: ['./event-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EventSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: NotificationSettings;
  @Input() keyOfSettings!:
    | 'emailNotification'
    | 'serverchanNotification'
    | 'pushplusNotification';

  syncStatus!: SyncStatus<NotificationSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      notifyBegan: [''],
      notifyEnded: [''],
      notifyError: [''],
      notifySpace: [''],
    });
  }

  get notifyBeganControl() {
    return this.settingsForm.get('notifyBegan') as FormControl;
  }

  get notifyEndedControl() {
    return this.settingsForm.get('notifyEnded') as FormControl;
  }

  get notifyErrorControl() {
    return this.settingsForm.get('notifyError') as FormControl;
  }

  get notifySpaceControl() {
    return this.settingsForm.get('notifySpace') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        this.keyOfSettings,
        this.settingsForm.value,
        this.settingsForm.valueChanges as Observable<NotificationSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
