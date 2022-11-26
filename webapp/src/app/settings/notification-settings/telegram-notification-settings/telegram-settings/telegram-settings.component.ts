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

import { TelegramSettings } from '../../../shared/setting.model';
import { filterValueChanges } from '../../../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-telegram-settings',
  templateUrl: './telegram-settings.component.html',
  styleUrls: ['./telegram-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TelegramSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: TelegramSettings;
  syncStatus!: SyncStatus<TelegramSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      token: ['', [Validators.required, Validators.pattern(/^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$/)]],
      chatid: ['', [Validators.required, Validators.pattern(/^(-|[0-9]){0,}$/)]],
      server: ['', [Validators.pattern(/^https?:\/\/[a-zA-Z0-9-_.]+(:[0-9]+)?/)]],
    });
  }

  get tokenControl() {
    return this.settingsForm.get('token') as FormControl;
  }

  get chatidControl() {
    return this.settingsForm.get('chatid') as FormControl;
  }

  get serverControl() {
    return this.settingsForm.get('server') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    console.log(this.settings);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'telegramNotification',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<Partial<TelegramSettings>>(this.settingsForm)
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
