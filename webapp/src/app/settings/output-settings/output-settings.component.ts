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
import cloneDeep from 'lodash-es/cloneDeep';
import mapValues from 'lodash-es/mapValues';

import type { Mutable } from '../../shared/utility-types';
import { OutputSettings } from '../shared/setting.model';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import {
  DURATION_LIMIT_OPTIONS,
  FILESIZE_LIMIT_OPTIONS,
  SPLIT_FILE_TIP,
  SYNC_FAILED_WARNING_TIP,
} from '../shared/constants/form';

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
  readonly splitFileTip = SPLIT_FILE_TIP;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;
  readonly filesizeLimitOptions = cloneDeep(FILESIZE_LIMIT_OPTIONS) as Mutable<
    typeof FILESIZE_LIMIT_OPTIONS
  >;
  readonly durationLimitOptions = cloneDeep(DURATION_LIMIT_OPTIONS) as Mutable<
    typeof DURATION_LIMIT_OPTIONS
  >;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      outDir: [''],
      pathTemplate: [''],
      filesizeLimit: [''],
      durationLimit: [''],
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
        this.settingsForm.valueChanges as Observable<OutputSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
