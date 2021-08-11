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

import { map } from 'rxjs/operators';
import transform from 'lodash-es/transform';
import mapValues from 'lodash-es/mapValues';

import { EmailSettings } from '../../../shared/setting.model';
import { filterValueChanges } from '../../../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-email-settings',
  templateUrl: './email-settings.component.html',
  styleUrls: ['./email-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmailSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: EmailSettings;
  syncStatus!: SyncStatus<EmailSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      srcAddr: ['', [Validators.required, Validators.email]],
      dstAddr: ['', [Validators.required, Validators.email]],
      authCode: ['', [Validators.required]],
      smtpHost: ['', [Validators.required]],
      smtpPort: ['', [Validators.required, Validators.pattern(/\d+/)]],
    });
  }

  get srcAddrControl() {
    return this.settingsForm.get('srcAddr') as FormControl;
  }

  get dstAddrControl() {
    return this.settingsForm.get('dstAddr') as FormControl;
  }

  get authCodeControl() {
    return this.settingsForm.get('authCode') as FormControl;
  }

  get smtpHostControl() {
    return this.settingsForm.get('smtpHost') as FormControl;
  }

  get smtpPortControl() {
    return this.settingsForm.get('smtpPort') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'emailNotification',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<EmailSettings>(this.settingsForm),
          map((settings) =>
            transform(
              settings,
              (result, value, prop) => {
                value = prop === 'smtpPort' ? parseInt(value as string) : value;
                Reflect.set(result, prop, value);
              },
              {} as EmailSettings
            )
          )
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
