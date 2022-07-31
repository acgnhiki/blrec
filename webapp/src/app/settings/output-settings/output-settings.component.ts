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

import { OutputSettings } from '../shared/setting.model';
import { filterValueChanges } from '../shared/rx-operators';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import { SYNC_FAILED_WARNING_TIP } from '../shared/constants/form';

@Component({
  selector: 'app-output-settings',
  templateUrl: './output-settings.component.html',
  styleUrls: ['./output-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OutputSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: OutputSettings;
  syncStatus!: SyncStatus<OutputSettings>;

  readonly settingsForm: FormGroup;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      outDir: [''],
      pathTemplate: [''],
      filesizeLimit: [
        '',
        [
          Validators.required,
          Validators.min(0),
          Validators.max(1073731086581), // 1073731086581(999.99 GB)
        ],
      ],
      durationLimit: [
        '',
        [
          Validators.required,
          Validators.min(0),
          Validators.max(359999), // 359999(99:59:59)
        ],
      ],
    });
  }

  get outDirControl() {
    return this.settingsForm.get('outDir') as FormControl;
  }

  get pathTemplateControl() {
    return this.settingsForm.get('pathTemplate') as FormControl;
  }

  get filesizeLimitControl() {
    return this.settingsForm.get('filesizeLimit') as FormControl;
  }

  get durationLimitControl() {
    return this.settingsForm.get('durationLimit') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'output',
        this.settings,
        this.settingsForm.valueChanges.pipe(
          filterValueChanges<OutputSettings>(this.settingsForm)
        )
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
