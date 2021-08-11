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

import { PushplusSettings } from '../../../shared/setting.model';
import { filterValueChanges } from '../../../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-pushplus-settings',
  templateUrl: './pushplus-settings.component.html',
  styleUrls: ['./pushplus-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PushplusSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: PushplusSettings;
  syncStatus!: SyncStatus<PushplusSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      token: ['', [Validators.required, Validators.pattern(/^[a-z\d]{32}$/)]],
      topic: [''],
    });
  }

  get tokenControl() {
    return this.settingsForm.get('token') as FormControl;
  }

  get topicControl() {
    return this.settingsForm.get('topic') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'pushplusNotification',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<PushplusSettings>(this.settingsForm)
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
