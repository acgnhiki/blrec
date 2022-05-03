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

import { PushdeerSettings } from '../../../shared/setting.model';
import { filterValueChanges } from '../../../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-pushdeer-settings',
  templateUrl: './pushdeer-settings.component.html',
  styleUrls: ['./pushdeer-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PushdeerSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: PushdeerSettings;
  syncStatus!: SyncStatus<PushdeerSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      server: ['', [Validators.pattern(/^https?:\/\/.+/)]],
      pushkey: [
        '',
        [Validators.required, Validators.pattern(/^[a-zA-Z\d]{41}$/)],
      ],
    });
  }

  get serverControl() {
    return this.settingsForm.get('server') as FormControl;
  }

  get pushkeyControl() {
    return this.settingsForm.get('pushkey') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'pushdeerNotification',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<Partial<PushdeerSettings>>(this.settingsForm)
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
