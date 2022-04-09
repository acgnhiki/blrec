import {
  Component,
  OnChanges,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  ChangeDetectorRef,
  ViewChild,
} from '@angular/core';
import { NgForm } from '@angular/forms';

import cloneDeep from 'lodash-es/cloneDeep';

import type { Mutable } from '../../shared/utility-types';
import { difference } from '../../shared/utils';
import {
  TaskOptions,
  GlobalTaskSettings,
  TaskOptionsIn,
} from '../../settings/shared/setting.model';
import {
  PATH_TEMPLATE_PATTERN,
  FILESIZE_LIMIT_OPTIONS,
  DURATION_LIMIT_OPTIONS,
  STREAM_FORMAT_OPTIONS,
  QUALITY_OPTIONS,
  TIMEOUT_OPTIONS,
  DISCONNECTION_TIMEOUT_OPTIONS,
  BUFFER_OPTIONS,
  DELETE_STRATEGIES,
  SPLIT_FILE_TIP,
} from '../../settings/shared/constants/form';

type OptionsModel = NonNullable<TaskOptions>;

@Component({
  selector: 'app-task-settings-dialog',
  templateUrl: './task-settings-dialog.component.html',
  styleUrls: ['./task-settings-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskSettingsDialogComponent implements OnChanges {
  @Input() taskOptions!: Readonly<TaskOptions>;
  @Input() globalSettings!: Readonly<GlobalTaskSettings>;
  @Input() visible = false;

  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<TaskOptionsIn>();
  @Output() afterOpen = new EventEmitter<undefined>();
  @Output() afterClose = new EventEmitter<undefined>();

  @ViewChild(NgForm)
  ngForm!: NgForm;

  readonly warningTip =
    '需要重启弹幕客户端才能生效，如果任务正在录制可能会丢失弹幕！';
  readonly splitFileTip = SPLIT_FILE_TIP;
  readonly pathTemplatePattern = PATH_TEMPLATE_PATTERN;
  readonly filesizeLimitOptions = cloneDeep(FILESIZE_LIMIT_OPTIONS) as Mutable<
    typeof FILESIZE_LIMIT_OPTIONS
  >;
  readonly durationLimitOptions = cloneDeep(DURATION_LIMIT_OPTIONS) as Mutable<
    typeof DURATION_LIMIT_OPTIONS
  >;
  readonly streamFormatOptions = cloneDeep(STREAM_FORMAT_OPTIONS) as Mutable<
    typeof STREAM_FORMAT_OPTIONS
  >;
  readonly qualityOptions = cloneDeep(QUALITY_OPTIONS) as Mutable<
    typeof QUALITY_OPTIONS
  >;
  readonly timeoutOptions = cloneDeep(TIMEOUT_OPTIONS) as Mutable<
    typeof TIMEOUT_OPTIONS
  >;
  readonly disconnectionTimeoutOptions = cloneDeep(
    DISCONNECTION_TIMEOUT_OPTIONS
  ) as Mutable<typeof DISCONNECTION_TIMEOUT_OPTIONS>;
  readonly bufferOptions = cloneDeep(BUFFER_OPTIONS) as Mutable<
    typeof BUFFER_OPTIONS
  >;
  readonly deleteStrategies = cloneDeep(DELETE_STRATEGIES) as Mutable<
    typeof DELETE_STRATEGIES
  >;

  model!: OptionsModel;
  options!: TaskOptions;

  constructor(private changeDetector: ChangeDetectorRef) {}

  ngOnChanges(): void {
    this.options = cloneDeep(this.taskOptions);
    this.setupModel();
    this.changeDetector.markForCheck();
  }

  close(): void {
    this.setVisible(false);
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.visibleChange.emit(visible);
    this.changeDetector.markForCheck();
  }

  handleCancel(): void {
    this.cancel.emit();
    this.close();
  }

  handleConfirm(): void {
    this.confirm.emit(difference(this.options, this.taskOptions!));
    this.close();
  }

  private setupModel(): void {
    const model = {};

    for (const key of Object.keys(this.options)) {
      const prop = key as keyof TaskOptions;
      const options = this.options[prop];
      const globalSettings = this.globalSettings[prop];

      Reflect.set(
        model,
        prop,
        new Proxy(options, {
          get: (target, prop) => {
            return (
              Reflect.get(target, prop) ?? Reflect.get(globalSettings, prop)
            );
          },
          set: (target, prop, value) => {
            return Reflect.set(target, prop, value);
          },
        })
      );
    }

    this.model = model as OptionsModel;
  }
}
