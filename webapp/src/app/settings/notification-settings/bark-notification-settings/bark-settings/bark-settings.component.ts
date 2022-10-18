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

import { BarkSettings } from '../../../shared/setting.model';
import { filterValueChanges } from '../../../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../../../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from 'src/app/settings/shared/constants/form';

@Component({
  selector: 'app-bark-settings',
  templateUrl: './bark-settings.component.html',
  styleUrls: ['./bark-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BarkSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: BarkSettings;
  syncStatus!: SyncStatus<BarkSettings>;

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
        [
          Validators.required,
          Validators.pattern(
            /^[a-zA-Z\d]+$/
          ),
        ],
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
    console.log(this.settings);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'barkNotification',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<Partial<BarkSettings>>(this.settingsForm)
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
