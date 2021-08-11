import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  OnChanges,
  ChangeDetectorRef,
} from '@angular/core';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  Validators,
} from '@angular/forms';

import mapValues from 'lodash-es/mapValues';

import { ServerchanSettings } from '../../../shared/setting.model';
import { filterValueChanges } from '../../../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-serverchan-settings',
  templateUrl: './serverchan-settings.component.html',
  styleUrls: ['./serverchan-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServerchanSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: ServerchanSettings;
  syncStatus!: SyncStatus<ServerchanSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      sendkey: ['', [Validators.required, Validators.pattern(/^[a-zA-Z\d]+$/)]],
    });
  }

  get sendkeyControl() {
    return this.settingsForm.get('sendkey') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'serverchanNotification',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<Partial<ServerchanSettings>>(this.settingsForm)
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
