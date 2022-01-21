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

import { PostprocessingSettings } from '../shared/setting.model';
import { DELETE_STRATEGIES, SYNC_FAILED_WARNING_TIP } from '../shared/constants/form';
import {
  SettingsSyncService,
  SyncStatus,
  calcSyncStatus,
} from '../shared/services/settings-sync.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-post-processing-settings',
  templateUrl: './post-processing-settings.component.html',
  styleUrls: ['./post-processing-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PostProcessingSettingsComponent implements OnInit, OnChanges {
  @Input() settings!: PostprocessingSettings;
  syncStatus!: SyncStatus<PostprocessingSettings>;

  readonly settingsForm: FormGroup;
  readonly deleteStrategies = DELETE_STRATEGIES;
  readonly syncFailedWarningTip = SYNC_FAILED_WARNING_TIP;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private settingsSyncService: SettingsSyncService
  ) {
    this.settingsForm = formBuilder.group({
      injectExtraMetadata: [''],
      remuxToMp4: [''],
      deleteSource: [''],
    });
  }

  get injectExtraMetadataControl() {
    return this.settingsForm.get('injectExtraMetadata') as FormControl;
  }

  get remuxToMp4Control() {
    return this.settingsForm.get('remuxToMp4') as FormControl;
  }

  get deleteSourceControl() {
    return this.settingsForm.get('deleteSource') as FormControl;
  }

  ngOnChanges(): void {
    this.syncStatus = mapValues(this.settings, () => true);
    this.settingsForm.setValue(this.settings);
  }

  ngOnInit(): void {
    this.settingsSyncService
      .syncSettings(
        'postprocessing',
        this.settings,
        this.settingsForm.valueChanges as Observable<PostprocessingSettings>
      )
      .subscribe((detail) => {
        this.syncStatus = { ...this.syncStatus, ...calcSyncStatus(detail) };
        this.changeDetector.markForCheck();
      });
  }
}
